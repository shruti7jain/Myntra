import os
import sys
import re
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ---------------------------------------------------------------------------
# LLM MODEL SELECTION
# Confirmed working via diagnostic test (2026-08-29):
#   openai/gpt-oss-20b  → finish_reason=length, partial JSON, FAILS
#   openai/gpt-oss-120b → finish_reason=stop, full JSON, WORKS
# Batch size set small (6) to stay well under token ceiling per response.
# ---------------------------------------------------------------------------
LLM_MODEL = "openai/gpt-oss-120b"
BATCH_SIZE = 6          # 6 records × ~250 token response = ~1500 tokens, safely within limits
LLM_MAX_TOKENS = 1200   # per batch response
LLM_RATE_SLEEP = 4.0    # seconds between batches (conservative for rate limiting)

# ---------------------------------------------------------------------------
# CANONICAL FRICTION TAXONOMY
# These 8 themes + 1 noise bucket represent the core wishlist-to-purchase
# barriers identified through exploratory analysis of public fashion VoC.
# ---------------------------------------------------------------------------
CANONICAL_THEMES = {
    "fit_sizing_anxiety":         "Fit & Sizing Uncertainty",
    "fabric_quality_ambiguity":   "Fabric / Quality Uncertainty",
    "visual_reality_discrepancy": "Photo -> Reality Uncertainty",
    "occasion_timing_delay":      "Occasion / Timing / Postponement",
    "styling_pairing_doubt":      "Styling / Pairing Uncertainty",
    "choice_paralysis_shortlist": "Comparison / Choice Overload",
    "social_validation_delay":    "Social / External Validation",
    "price_deal_timing":          "Price / Deal Timing",
    "unrelated_other":            "Out-of-Scope / Noise",
}

# ---------------------------------------------------------------------------
# INTENT TYPE TAXONOMY
# Captures WHY the user added to wishlist / what is blocking purchase
# ---------------------------------------------------------------------------
INTENT_TYPES = {
    "high_intent_blocked":       "User wants to buy but is blocked by uncertainty",
    "comparison_shortlisting":   "User is comparing multiple options, hasn't decided",
    "price_monitoring":          "User is watching for a price drop or sale",
    "bookmarking_inspiration":   "User saved for inspiration, low purchase intent",
    "occasion_waiting":          "User will buy when a specific event/occasion arrives",
    "no_clear_intent":           "Intent cannot be determined from text",
    "noise":                     "Unrelated to wishlist or purchase decision",
}

# Map theme to canonical intent for insights aggregation
THEME_TO_INTENT = {
    "fit_sizing_anxiety":         "high_intent_blocked",
    "fabric_quality_ambiguity":   "high_intent_blocked",
    "visual_reality_discrepancy": "high_intent_blocked",
    "occasion_timing_delay":      "occasion_waiting",
    "styling_pairing_doubt":      "high_intent_blocked",
    "choice_paralysis_shortlist": "comparison_shortlisting",
    "social_validation_delay":    "high_intent_blocked",
    "price_deal_timing":          "price_monitoring",
    "unrelated_other":            "noise",
}


def has_explicit_fashion_friction_context(text: str) -> bool:
    if not text:
        return False
    t_lower = text.lower()
    
    # Fit & sizing
    is_fit = any(w in t_lower for w in ["tight", "loose", "sizing", "fit", "size chart", "wrong size", "large", "small"])
    # Fabric / Material Quality
    is_fabric = any(w in t_lower for w in ["fabric", "material", "stitching", "see-through", "transparent", "thin", "color fade", "colour fade", "shrink", "poor quality", "bad quality"])
    # Photo vs Reality
    is_photo = any(w in t_lower for w in ["photo", "reality", "different from picture", "look different", "mismatch", "image vs", "colour difference"])
    # Authenticity
    is_authenticity = any(w in t_lower for w in ["fake", "duplicate", "copy", "counterfeit", "not genuine"])
    # Price/Value
    is_price = any(w in t_lower for w in ["price", "expensive", "cheap", "costly", "value for money"])
    # Delivery/Policy block
    is_policy = any(w in t_lower for w in ["non-returnable", "cannot return", "exchange option", "return request declined", "return window closed", "delivery delay"])
    
    if not (is_fit or is_fabric or is_photo or is_authenticity or is_price or is_policy):
        return False
        
    # Exclude purely positive reviews
    positive_words = ["perfect", "excellent", "amazing", "good", "satisfied", "love", "like", "awesome", "best", "smooth", "happy", "fabulous", "nice", "premium", "comfortable", "beautiful", "neat", "recommend", "great"]
    is_positive_text = any(w in t_lower for w in positive_words) and not any(w in t_lower for w in ["bad", "poor", "worst", "fake", "scam", "cheat", "disappointed", "tight", "loose", "wrong", "mismatch"])
    if is_positive_text:
        return False
        
    return True


def is_excluded_by_rating(platform: str, rating, text: str = "") -> bool:
    """
    Returns True if a review should be excluded from friction themes based on rating.
    - App Store & Play Store reviews must have rating < 4.
    - If rating is null/missing/malformed for App Store & Play Store, exclude it unless it has explicit fashion friction context.
    - YouTube and Reddit comments don't have ratings, so they are not excluded.
    """
    if platform in ["playstore", "appstore"]:
        if rating is None:
            return not has_explicit_fashion_friction_context(text)
        try:
            val = float(rating)
            if val >= 4.0:
                return True
        except (TypeError, ValueError):
            return not has_explicit_fashion_friction_context(text)
    return False


def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("Missing Supabase credentials in .env")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_groq_client():
    """Returns Groq client if API key is valid, else None."""
    if not GROQ_API_KEY or not GROQ_API_KEY.startswith("gsk_") or len(GROQ_API_KEY) < 20:
        print("[LLM INIT] GROQ_API_KEY is missing or malformed — LLM disabled, heuristic only.", flush=True)
        return None
    print(f"[LLM INIT] Groq API key loaded (length={len(GROQ_API_KEY)}). Model: {LLM_MODEL}", flush=True)
    return Groq(api_key=GROQ_API_KEY)


def classify_batch_with_llm(groq_client, batch_items: list[dict]) -> tuple[dict, str | None]:
    """
    LLM-powered VoC classification via Groq.
    Returns (results_by_id, failure_reason).
    failure_reason is None on success, or a string describing why it failed.

    GOAL: Classify each text as a PRE-PURCHASE friction signal related to
    the Wishlist→Purchase gap: Why did an interested user NOT buy?

    Model: openai/gpt-oss-120b (confirmed working with finish_reason=stop)
    Batch size: 6 (keeps token count predictable and well under ceiling)
    """
    if not groq_client:
        return {}, "groq_client_not_initialized"

    system_prompt = """You are an expert VoC Intelligence Classifier for Myntra, an Indian fashion e-commerce app.

BUSINESS GOAL: Identify why a user who has shown interest in a fashion product (saved it, wishlisted it, considered it) does NOT purchase it.

CRITICAL DISTINCTION — classify based on TIMING of the friction:
- PRE-PURCHASE hesitation (user has NOT yet bought, something is preventing them) → friction theme
- POST-PURCHASE complaint (user already bought and is unhappy) → unrelated_other

FRICTION THEMES (PRE-PURCHASE ONLY):
- fit_sizing_anxiety: Unsure about size, afraid it won't fit, confused by size chart, doesn't know which size to order
- fabric_quality_ambiguity: Unsure about fabric feel/quality, worried it looks cheap/sheer/thin in real life
- visual_reality_discrepancy: Afraid the actual product will look different from the photos/listing
- occasion_timing_delay: Saving for a specific occasion, waiting until an event, uncertain about delivery timing
- styling_pairing_doubt: Unsure how to style or what to pair the item with, no styling inspiration
- choice_paralysis_shortlist: Can't decide between multiple saved/shortlisted options, too many choices
- social_validation_delay: Waiting for friend/family opinion before buying, seeking external validation
- price_deal_timing: Waiting for a discount or sale, price feels too high right now, monitoring price drops
- unrelated_other: Post-purchase complaints, delivery issues on already-placed orders, app bugs, purely positive reviews, customer service complaints

OUTPUT: Respond ONLY with a raw JSON array. No text before or after the array. Use strict double quotes.
[{"id":<id>,"theme":"<theme_key>","intent_type":"<intent>","clearest_quote":"<max 150 char direct quote>","category":"Western Wear|Ethnic Wear|Dresses|Footwear|General Fashion"}]

intent_type options: high_intent_blocked | comparison_shortlisting | price_monitoring | bookmarking_inspiration | occasion_waiting | no_clear_intent | noise"""

    input_payload = [{"id": r["id"], "text": (r.get("text") or "")[:400]} for r in batch_items]
    user_content = json.dumps(input_payload, ensure_ascii=False)

    for attempt in range(3):
        try:
            completion = groq_client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.05,
                max_tokens=LLM_MAX_TOKENS,
            )

            finish_reason = completion.choices[0].finish_reason
            raw_response = completion.choices[0].message.content.strip()

            # CRITICAL CHECK: if truncated, the JSON will be incomplete — do NOT use it
            if finish_reason == "length":
                print(f"[LLM TRUNCATED] finish_reason=length on attempt {attempt+1}. "
                      f"Response was cut off mid-JSON. Tokens used: {completion.usage.completion_tokens}. "
                      f"Falling back to heuristic for this batch.", flush=True)
                return {}, "finish_reason_length_truncated"

            # Strip <think>...</think> reasoning blocks (some models output these)
            clean_text = re.sub(r'<think>.*?</think>', '', raw_response, flags=re.DOTALL)
            if '<think>' in clean_text:
                clean_text = re.sub(r'<think>.*', '', clean_text, flags=re.DOTALL)

            # If stripping removed the JSON but raw has it, use raw
            if '[' not in clean_text and '[' in raw_response:
                clean_text = raw_response

            start_idx = clean_text.find('[')
            end_idx = clean_text.rfind(']')

            if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
                print(f"[LLM NO_JSON] Attempt {attempt+1}: No JSON array brackets found in response. "
                      f"Raw (first 200): {raw_response[:200]!r}", flush=True)
                raise ValueError("No JSON array brackets found in model output")

            candidate = clean_text[start_idx:end_idx+1]
            # Fix trailing commas before ] or }
            candidate = re.sub(r',\s*([\]}])', r'\1', candidate)

            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError as je:
                # Try to fix unquoted keys
                candidate_fixed = re.sub(r'([{,]\s*)([a-zA-Z0-9_]+)\s*:', r'\1"\2":', candidate)
                try:
                    parsed = json.loads(candidate_fixed)
                except Exception:
                    print(f"[LLM PARSE_ERROR] Attempt {attempt+1}: JSON parse failed: {je}. "
                          f"Candidate (first 300): {candidate[:300]!r}", flush=True)
                    raise

            results_by_id = {}
            for res in parsed:
                item_id = res.get("id")
                if item_id is None:
                    continue
                theme_key = res.get("theme", "unrelated_other")
                if theme_key not in CANONICAL_THEMES:
                    theme_key = "unrelated_other"
                intent_key = res.get("intent_type", "no_clear_intent")
                if intent_key not in INTENT_TYPES:
                    intent_key = "no_clear_intent"
                quote = res.get("clearest_quote") or res.get("quote") or ""
                results_by_id[item_id] = {
                    "is_relevant_friction": theme_key != "unrelated_other",
                    "theme": theme_key,
                    "theme_label": CANONICAL_THEMES.get(theme_key, "Unknown"),
                    "clearest_quote": quote[:200],
                    "category": res.get("category", "General Fashion"),
                    "intent_type": intent_key,
                }

            print(f"[LLM OK] Batch classified {len(results_by_id)}/{len(batch_items)} items "
                  f"(finish={finish_reason}, tokens={completion.usage.completion_tokens})", flush=True)
            return results_by_id, None

        except Exception as e:
            err_str = str(e).lower()
            err_type = type(e).__name__
            print(f"[LLM ERROR] Attempt {attempt+1}/3 failed: {err_type}: {e}", flush=True)
            if "429" in err_str or "rate limit" in err_str:
                sleep_time = 10.0 * (attempt + 1)
                print(f"[LLM RATE_LIMIT] Rate limited. Sleeping {sleep_time}s...", flush=True)
                time.sleep(sleep_time)
            else:
                time.sleep(2.0 * (attempt + 1))

    print(f"[LLM FAIL] All 3 attempts failed. Batch will use heuristic fallback.", flush=True)
    return {}, "all_attempts_failed"


def classify_text_heuristically(text: str, keyword: str) -> dict:
    """
    High-accuracy NLP heuristic fallback for when LLM is unavailable.
    Default is 'unrelated_other' — not an arbitrary friction theme.
    Explicitly separates POST-purchase complaints from PRE-purchase hesitation.
    """
    t_lower = text.lower()
    kw_lower = (keyword or "").lower()

    # -----------------------------------------------------------------------
    # STEP 1: Hard noise signals — always unrelated_other
    # -----------------------------------------------------------------------
    noise_signals = [
        "otp", "crash", "uninstall", "scam", "fraud", "customer care number",
        "useless update", "login issue", "server error", "app is great",
        "best app ever", "love myntra", "amazing app", "fantastic service",
        "delivery was fast", "5 star", "excellent service", "super fast delivery",
        "great in quality", "great quality", "benefited me", "love this app", "good app",
        "customer service", "cancel the return", "wrong product delivered",
        "investigation team", "not gonna place an order", "we are helpless"
    ]
    if any(w in t_lower for w in noise_signals):
        return _make_heuristic_result("unrelated_other", False, "noise", text)

    # -----------------------------------------------------------------------
    # STEP 2: Post-purchase complaint guard
    # Explicit purchase + complaint context → noise even if friction words present
    # -----------------------------------------------------------------------
    post_purchase_verbs = [
        "i bought", "i ordered", "ordered this", "bought this", "received this",
        "arrived and", "delivered this", "delivered but", "order kiya tha",
        "after receiving", "when i received", "upon delivery"
    ]
    post_purchase_complaints = [
        "too tight", "too loose", "wrong size", "size chart wrong", "not fit",
        "does not fit", "doesn't fit", "size issue", "return request",
        "returned it", "cancel the return", "refund", "wrong product"
    ]
    if (any(v in t_lower for v in post_purchase_verbs) and
            any(c in t_lower for c in post_purchase_complaints)):
        return _make_heuristic_result("unrelated_other", False, "noise", text)

    # -----------------------------------------------------------------------
    # STEP 3: Price / Deal timing — check BEFORE fit/fabric as it is distinct
    # -----------------------------------------------------------------------
    price_signals = [
        "wait for sale", "wait for discount", "price drop", "price too high",
        "out of budget", "too expensive", "not affordable", "wait for offer",
        "coupon apply", "price will decrease", "budget"
    ]
    if any(w in t_lower or w in kw_lower for w in price_signals):
        return _make_heuristic_result("price_deal_timing", True, "price_monitoring", text)

    # -----------------------------------------------------------------------
    # STEP 4: Fit & Sizing (pre-purchase context only)
    # -----------------------------------------------------------------------
    fit_signals = [
        "true to size", "size up", "size down", "runs small", "runs large",
        "fitting tight", "fitting loose", "shoulder fit", "bust size",
        "size chart", "size guide", "waist size", "size small", "wrong size",
        "not fit for", "not fitting", "does not fit me", "doesn't fit",
        "size mismatch", "size issue", "too tight", "too loose",
        "too small", "too large", "tight fit", "loose fit", "small size", "large size", "fitting", "fit"
    ]
    if any(w in t_lower or w in kw_lower for w in fit_signals):
        return _make_heuristic_result("fit_sizing_anxiety", True, "high_intent_blocked", text)

    # -----------------------------------------------------------------------
    # STEP 5: Fabric / quality hesitation (pre-purchase)
    # -----------------------------------------------------------------------
    fabric_signals = [
        "see through", "see-through", "fabric quality", "fabric is", "material is",
        "kapda", "cloth quality", "sheer fabric", "transparent", "lining missing",
        "no lining", "thin material", "poor quality material", "cheap fabric",
        "material looks", "kapda kaisa", "kaisi quality", "material kaisa", "fabric", "material"
    ]
    if any(w in t_lower or w in kw_lower for w in fabric_signals):
        return _make_heuristic_result("fabric_quality_ambiguity", True, "high_intent_blocked", text)

    # -----------------------------------------------------------------------
    # STEP 6: Photo vs. reality discrepancy (pre-purchase fear)
    # -----------------------------------------------------------------------
    photo_signals = [
        "different from photo", "different from picture", "different in real",
        "color different", "colour different", "not like image", "misleading photo",
        "looks different", "not what i expected", "shade different",
        "photo pe alag", "image se alag", "photo", "picture", "image"
    ]
    if any(w in t_lower or w in kw_lower for w in photo_signals):
        return _make_heuristic_result("visual_reality_discrepancy", True, "high_intent_blocked", text)

    # -----------------------------------------------------------------------
    # STEP 6b: Return / Policy / Exchange (Pre-purchase / Post-purchase blocker)
    # -----------------------------------------------------------------------
    policy_signals = [
        "non-returnable", "cannot return", "exchange option", "return request declined", "return window closed", "no return"
    ]
    if any(w in t_lower or w in kw_lower for w in policy_signals):
        return _make_heuristic_result("occasion_timing_delay", True, "occasion_waiting", text)

    # -----------------------------------------------------------------------
    # STEP 7: Occasion / timing delay
    # -----------------------------------------------------------------------
    occasion_signals = [
        "waiting for occasion", "waiting for wedding", "delivery before",
        "will it arrive before", "need it for", "buy for wedding", "buy for party",
        "want it before", "shaadi mein pehenna", "event ke liye",
        "function ke liye", "saving for trip",
    ]
    if any(w in t_lower or w in kw_lower for w in occasion_signals):
        return _make_heuristic_result("occasion_timing_delay", True, "occasion_waiting", text)

    # -----------------------------------------------------------------------
    # STEP 8: Styling / pairing uncertainty
    # -----------------------------------------------------------------------
    styling_signals = [
        "styling", "pair with", "match with", "what to wear with", "how to style",
        "outfit combination", "can't match", "kya pehnu", "kiske saath match",
        "combination nahi pata", "style ideas",
    ]
    if any(w in t_lower or w in kw_lower for w in styling_signals):
        return _make_heuristic_result("styling_pairing_doubt", True, "high_intent_blocked", text)

    # -----------------------------------------------------------------------
    # STEP 9: Social validation delay
    # -----------------------------------------------------------------------
    social_signals = [
        "asked friend", "asked my friend", "show my friend", "getting opinion",
        "whatsapp to decide", "send to group", "screenshot to share",
        "friend ki राय", "family opinion", "mom se poochna hai",
    ]
    if any(w in t_lower or w in kw_lower for w in social_signals):
        return _make_heuristic_result("social_validation_delay", True, "high_intent_blocked", text)

    # -----------------------------------------------------------------------
    # STEP 10: Choice paralysis (comparing saved items)
    # -----------------------------------------------------------------------
    choice_signals = [
        "cant decide", "can't decide", "confused between", "which one to buy",
        "too many options", "comparing both", "saved multiple",
        "wishlist is full", "wish list overloaded", "dono mein se",
        "ek choose karna mushkil",
    ]
    if any(w in t_lower or w in kw_lower for w in choice_signals):
        return _make_heuristic_result("choice_paralysis_shortlist", True, "comparison_shortlisting", text)

    # -----------------------------------------------------------------------
    # STEP 11: Wishlist / pre-purchase intent signals (general)
    # If text contains direct wishlist/save context but doesn't match above themes,
    # don't force-classify — mark noise and let LLM handle it on next run.
    # -----------------------------------------------------------------------
    wishlist_signals = [
        "wishlist", "wish list", "save for later", "saved item", "saved it",
        "bookmark", "buy later", "shortlist", "considering buying", "thinking of buying",
        "want to buy but", "kharidunga baad mein", "baad mein dekhna",
    ]
    if any(w in t_lower for w in wishlist_signals):
        # Has wishlist context but no clear friction signal detected → noise (LLM would do better)
        return _make_heuristic_result("unrelated_other", False, "bookmarking_inspiration", text)

    # -----------------------------------------------------------------------
    # DEFAULT: No friction signal identified → noise
    # -----------------------------------------------------------------------
    return _make_heuristic_result("unrelated_other", False, "noise", text)


def _make_heuristic_result(theme: str, is_friction: bool, intent: str, text: str) -> dict:
    """Helper to build a consistent heuristic result dict."""
    # Determine category from text
    t_lower = text.lower()
    if any(w in t_lower for w in ["kurti", "kurta", "saree", "ethnic", "lehenga", "suit", "dupatta", "salwar", "anouk"]):
        category = "Ethnic Wear"
    elif any(w in t_lower for w in ["dress", "gown", "maxi", "bodycon"]):
        category = "Dresses"
    elif any(w in t_lower for w in ["shoe", "sneaker", "heel", "sandal", "footwear", "boots", "loafer"]):
        category = "Footwear"
    elif any(w in t_lower for w in ["jean", "top", "shirt", "tshirt", "t-shirt", "jacket", "trousers", "denim", "blazer", "skirt"]):
        category = "Western Wear"
    else:
        category = "General Fashion"

    # Extract best quote sentence
    sentences = [s.strip() for s in re.split(r'[.!?]', text) if len(s.strip()) > 20]
    quote = sentences[0] if sentences else text[:200].strip()

    return {
        "is_relevant_friction": is_friction,
        "theme": theme,
        "theme_label": CANONICAL_THEMES.get(theme, "Unknown"),
        "clearest_quote": quote[:200],
        "category": category,
        "intent_type": intent,
    }


def batch_update_raw_feedback(rows_meta: list[dict]):
    """
    Batch update raw_feedback: set theme, classification_method, is_processed=True.
    Uses bulk upsert on primary key 'id' to act as updates. Extremely fast and avoids socket errors.
    """
    supabase = get_supabase()
    try:
        records = []
        for r in rows_meta:
            records.append({
                "id": r["id"],
                "external_id": r["external_id"],
                "platform": r["platform"],
                "text": r["text"],
                "theme": r["theme"],
                "classification_method": r["classification_method"],
                "is_processed": True
            })
        
        batch_size = 100
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            supabase.table("raw_feedback").upsert(batch).execute()
        return len(rows_meta)
    except Exception as e:
        print(f"[ERROR] Batch update failed: {e}", flush=True)
        return 0


def run_normalization(unprocessed_only: bool = False):
    """
    Main classification and aggregation pipeline.

    Args:
        unprocessed_only: If True, only classifies records where is_processed=False
                          and theme=NULL (newly ingested records). Faster for incremental runs.
                          If False (default), re-classifies ALL records for a fresh aggregation.
    """
    print("=" * 75)
    print("MYNTRA DISCOVERY ENGINE — CLASSIFICATION & AGGREGATION")
    print(f"Mode: {'INCREMENTAL (unprocessed only)' if unprocessed_only else 'FULL (all records)'}")
    print(f"LLM model: {LLM_MODEL}  |  Batch size: {BATCH_SIZE}")
    print("=" * 75)

    supabase = get_supabase()
    groq_client = get_groq_client()

    if groq_client is None:
        print("[WARN] Groq client not initialized. Will use heuristic fallback for ALL records.", flush=True)

    # ------------------------------------------------------------------
    # 1. Fetch records
    # ------------------------------------------------------------------
    print("[SUPABASE] Fetching records from raw_feedback...", flush=True)

    all_records = []
    page_size = 1000
    offset = 0

    query = supabase.table("raw_feedback").select(
        "id, platform, text, keyword_matched, url, is_processed, theme, rating, external_id"
    )
    if unprocessed_only:
        # Only fetch records that are truly unclassified
        query = supabase.table("raw_feedback").select(
            "id, platform, text, keyword_matched, url, is_processed, theme, rating, external_id"
        ).is_("classification_method", "null")

    while True:
        res = query.range(offset, offset + page_size - 1).execute()
        data = res.data or []
        if not data:
            break
        all_records.extend(data)
        offset += len(data)
        if len(data) < page_size:
            break

    total_records = len(all_records)
    print(f"[OK] Records fetched: {total_records}", flush=True)

    # ------------------------------------------------------------------
    # Pre-process rating exclusions to save LLM tokens and ensure strict safety
    # ------------------------------------------------------------------
    updated_rows_meta = []
    eligible_records = []
    
    classification_stats = {
        "llm": 0,
        "heuristic_fallback": 0,
        "failure_reasons": {},
        "llm_batch_successes": 0,
        "llm_batch_failures": 0,
    }
    
    for item in all_records:
        item_id = item["id"]
        platform = item.get("platform", "unknown")
        rating = item.get("rating")
        
        if is_excluded_by_rating(platform, rating, item.get("text", "")):
            updated_rows_meta.append({
                "id": item_id,
                "external_id": item.get("external_id"),
                "platform": platform,
                "text": item.get("text", ""),
                "theme": "unrelated_other",
                "classification_method": "heuristic_fallback",
                "is_processed": True,
            })
            classification_stats["heuristic_fallback"] += 1
        else:
            eligible_records.append(item)
            
    total_eligible = len(eligible_records)
    print(f"[RATING FILTER] {total_records - total_eligible} records excluded by rating. {total_eligible} records eligible for classification.", flush=True)

    if total_records == 0:
        print("[INFO] No records to classify. Either DB is empty or all records are already processed.")
        if not unprocessed_only:
            return
        print("[INFO] Proceeding to re-aggregate existing classifications into insights table...")
        _aggregate_and_upsert_insights(supabase, groq_client)
        return

    total_batches = (total_eligible + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"\n[CLASSIFICATION] {total_batches} batches × {BATCH_SIZE} records = {total_eligible} total eligible", flush=True)
    print(f"[CLASSIFICATION] Primary: Groq {LLM_MODEL}  |  Fallback: NLP Heuristics", flush=True)
    print("-" * 75, flush=True)

    for b_idx in range(total_batches):
        b_start = b_idx * BATCH_SIZE
        batch = eligible_records[b_start:b_start + BATCH_SIZE]
        llm_batch_results = {}
        failure_reason = None

        # Attempt LLM classification for this batch
        if groq_client:
            llm_batch_results, failure_reason = classify_batch_with_llm(groq_client, batch)
            if failure_reason:
                classification_stats["llm_batch_failures"] += 1
                reason_key = failure_reason
                classification_stats["failure_reasons"][reason_key] = \
                    classification_stats["failure_reasons"].get(reason_key, 0) + 1
                print(f"[HEURISTIC FALLBACK] Batch {b_idx+1}: reason={failure_reason}", flush=True)
                if failure_reason == "all_attempts_failed":
                    print("[LLM DISABLED] Hitting persistent rate limits / quota issues. Disabling LLM client for this run to prevent execution delays.", flush=True)
                    groq_client = None
            else:
                classification_stats["llm_batch_successes"] += 1

        # Classify each item in the batch
        for item in batch:
            item_id = item["id"]
            text = item.get("text", "")
            kw = item.get("keyword_matched", "")
            platform = item.get("platform", "unknown")
            url = item.get("url", "")

            if llm_batch_results and item_id in llm_batch_results:
                result = llm_batch_results[item_id]
                method_used = "llm"
                classification_stats["llm"] += 1
            else:
                result = classify_text_heuristically(text, kw)
                method_used = "heuristic_fallback"
                classification_stats["heuristic_fallback"] += 1

            updated_rows_meta.append({
                "id": item_id,
                "external_id": item.get("external_id"),
                "platform": platform,
                "text": text,
                "theme": result["theme"],
                "classification_method": method_used,
                "is_processed": True,
            })

        processed_so_far = min((b_idx + 1) * BATCH_SIZE, total_eligible)
        llm_rate = round(classification_stats["llm"] / max(processed_so_far, 1) * 100, 1)
        print(
            f"  Batch {b_idx+1:>4}/{total_batches} | {processed_so_far:>5}/{total_eligible} records | "
            f"LLM: {classification_stats['llm']} ({llm_rate}%) | "
            f"Heuristic: {classification_stats['heuristic_fallback'] - (total_records - total_eligible)}",
            flush=True
        )

        # Rate limiting: sleep between batches
        if groq_client and b_idx < total_batches - 1:
            time.sleep(LLM_RATE_SLEEP)

    # ------------------------------------------------------------------
    # 4. Persist classifications to raw_feedback
    # ------------------------------------------------------------------
    print(f"\n[SUPABASE] Writing {len(updated_rows_meta)} classifications to raw_feedback...", flush=True)
    written = batch_update_raw_feedback(updated_rows_meta)
    print(f"[OK] Written: {written}/{len(updated_rows_meta)} rows.", flush=True)

    # ------------------------------------------------------------------
    # 5. Re-aggregate ALL classified records into insights table
    #    (Always a full re-aggregation regardless of mode, to stay consistent)
    # ------------------------------------------------------------------
    _aggregate_and_upsert_insights(supabase, groq_client)

    # ------------------------------------------------------------------
    # 6. Print executive summary
    # ------------------------------------------------------------------
    total_processed = classification_stats["llm"] + classification_stats["heuristic_fallback"]
    llm_pct = round(classification_stats["llm"] / max(total_processed, 1) * 100, 1)
    heuristic_pct = round(classification_stats["heuristic_fallback"] / max(total_processed, 1) * 100, 1)

    print("\n" + "=" * 75)
    print("CLASSIFICATION COMPLETE — SUMMARY")
    print("=" * 75)
    print(f"Records classified this run : {total_processed:,}")
    print(f"  LLM ({LLM_MODEL}): {classification_stats['llm']:,} ({llm_pct}%)")
    print(f"  Heuristic fallback         : {classification_stats['heuristic_fallback']:,} ({heuristic_pct}%)")
    if classification_stats["failure_reasons"]:
        print(f"  LLM failure reasons:")
        for reason, count in classification_stats["failure_reasons"].items():
            print(f"    {reason}: {count} batches")
    print(f"  LLM batch successes : {classification_stats['llm_batch_successes']}")
    print(f"  LLM batch failures  : {classification_stats['llm_batch_failures']}")
    print("=" * 75 + "\n")


def _aggregate_and_upsert_insights(supabase, groq_client=None):
    """
    Reads ALL classified records from raw_feedback and re-aggregates
    into the insights table. This ensures the insights table is always
    a complete, current view of the classified population.

    total_raw_records is stored in insights so the API can read a
    consistent total from the same table as friction counts.
    """
    print("\n[AGGREGATION] Re-reading all classified records from raw_feedback...", flush=True)

    all_records = []
    offset = 0
    while True:
        res = supabase.table("raw_feedback").select(
            "id, platform, text, keyword_matched, url, theme, classification_method, is_processed, rating"
        ).range(offset, offset + 999).execute()
        data = res.data or []
        all_records.extend(data)
        if len(data) < 1000:
            break
        offset += 1000

    total_records = len(all_records)
    classified = [r for r in all_records if r.get("theme") is not None]
    unclassified = [r for r in all_records if r.get("theme") is None]

    print(f"[AGGREGATION] Total: {total_records} | Classified: {len(classified)} | "
          f"Unclassified (theme=NULL): {len(unclassified)}", flush=True)

    # Build theme accumulators
    theme_data = {
        key: {
            "theme": key,
            "theme_label": label,
            "mention_count": 0,
            "sample_quotes": [],
            "segment_breakdown": {
                "Ethnic Wear": 0, "Western Wear": 0, "Dresses": 0,
                "Footwear": 0, "General Fashion": 0
            },
            "intent_breakdown": {k: 0 for k in INTENT_TYPES.keys()},
            "llm_count": 0,
            "heuristic_count": 0,
        }
        for key, label in CANONICAL_THEMES.items()
    }

    for r in classified:
        theme_key = r.get("theme")
        platform = r.get("platform", "unknown")
        rating = r.get("rating")

        # Apply strict check: force to unrelated_other if rating >= 4 or rating is None (for reviews)
        if is_excluded_by_rating(platform, rating, r.get("text", "")):
            theme_key = "unrelated_other"

        if theme_key not in theme_data:
            continue

        method = r.get("classification_method", "heuristic_fallback")
        url = r.get("url", "")
        text = r.get("text", "")

        theme_data[theme_key]["mention_count"] += 1
        if method == "llm":
            theme_data[theme_key]["llm_count"] += 1
        else:
            theme_data[theme_key]["heuristic_count"] += 1

        # Populate intent breakdown based on the mapped theme
        intent = THEME_TO_INTENT.get(theme_key, "no_clear_intent")
        if intent in theme_data[theme_key]["intent_breakdown"]:
            theme_data[theme_key]["intent_breakdown"][intent] += 1

        # Category from text (lightweight re-classification for breakdown)
        t_lower = text.lower()
        if any(w in t_lower for w in ["kurti", "kurta", "saree", "ethnic", "lehenga", "salwar"]):
            cat = "Ethnic Wear"
        elif any(w in t_lower for w in ["dress", "gown", "maxi", "bodycon"]):
            cat = "Dresses"
        elif any(w in t_lower for w in ["shoe", "sneaker", "heel", "sandal", "footwear", "boots"]):
            cat = "Footwear"
        elif any(w in t_lower for w in ["jean", "top", "shirt", "jacket", "trousers", "denim", "blazer", "skirt"]):
            cat = "Western Wear"
        else:
            cat = "General Fashion"

        if cat in theme_data[theme_key]["segment_breakdown"]:
            theme_data[theme_key]["segment_breakdown"][cat] += 1

        # Store sample quotes (up to 8 per theme for richer evidence)
        existing = theme_data[theme_key]["sample_quotes"]
        if len(existing) < 8 and len(text) > 25:
            sentences = [s.strip() for s in re.split(r'[.!?]', text) if len(s.strip()) > 20]
            quote = sentences[0] if sentences else text[:200].strip()
            if not any(q.get("text") == quote for q in existing):
                existing.append({"text": quote[:200], "platform": platform, "url": url or ""})

    # Calculate totals
    noise_count = theme_data["unrelated_other"]["mention_count"]
    friction_themes = {k for k in CANONICAL_THEMES if k != "unrelated_other"}
    total_friction = sum(theme_data[k]["mention_count"] for k in friction_themes)
    real_friction_total = total_friction or 1

    now_ts = datetime.utcnow().isoformat()

    # Build insights rows
    insights_rows = []
    for key, data in theme_data.items():
        if key == "unrelated_other":
            pct = round((data["mention_count"] / total_records) * 100, 2) if total_records else 0.0
        else:
            pct = round((data["mention_count"] / real_friction_total) * 100, 2)

        sample_quotes_plain = [q["text"] for q in data["sample_quotes"]]
        sample_quotes_attributed = json.dumps(data["sample_quotes"])

        # Store total_raw_records in unrelated_other row as a convention
        # so the API can read a consistent total from the same table
        row = {
            "theme": key,
            "theme_label": data["theme_label"],
            "mention_count": data["mention_count"],
            "pct_of_total": pct,
            "sample_quotes": sample_quotes_plain,
            "sample_quotes_attributed": sample_quotes_attributed,
            "segment_breakdown": data["segment_breakdown"],
            "intent_breakdown": data["intent_breakdown"],
            "trend": "stable",
            "updated_at": now_ts,
        }
        insights_rows.append(row)

    # Upsert insights
    print(f"[SUPABASE] Upserting {len(insights_rows)} insight rows...", flush=True)
    for row in insights_rows:
        try:
            # Try with last_classified_at field
            row_with_ts = {**row, "last_classified_at": now_ts}
            supabase.table("insights").upsert(row_with_ts, on_conflict="theme").execute()
        except Exception:
            # last_classified_at column may not exist yet — fall back to core fields
            try:
                core_row = {k: v for k, v in row.items()
                            if k in ["theme", "theme_label", "mention_count", "pct_of_total",
                                     "sample_quotes", "sample_quotes_attributed",
                                     "segment_breakdown", "intent_breakdown", "trend", "updated_at"]}
                supabase.table("insights").upsert(core_row, on_conflict="theme").execute()
            except Exception as e2:
                print(f"[ERROR] Failed to upsert theme={row.get('theme')}: {e2}", flush=True)

    # Print aggregation summary
    print("\n" + "-" * 75)
    print(f"AGGREGATION SUMMARY (source: {total_records:,} raw_feedback records)")
    print("-" * 75)
    print(f"{'Theme':<42} | {'Count':>7} | {'% Friction':>10} | {'LLM':>5} | {'Heuristic':>9}")
    print("-" * 75)
    for key in sorted(friction_themes, key=lambda k: theme_data[k]["mention_count"], reverse=True):
        d = theme_data[key]
        pct_val = round(d["mention_count"] / real_friction_total * 100, 1)
        print(f"  {d['theme_label']:<40} | {d['mention_count']:>7} | {pct_val:>9}% | "
              f"{d['llm_count']:>5} | {d['heuristic_count']:>9}")
    d_noise = theme_data["unrelated_other"]
    print(f"  {'Out-of-Scope / Noise':<40} | {d_noise['mention_count']:>7} | {'N/A':>10} | "
          f"{d_noise['llm_count']:>5} | {d_noise['heuristic_count']:>9}")
    print(f"  {'theme=NULL (unclassified)':<40} | {len(unclassified):>7}")
    print("-" * 75)
    print(f"  Total friction signals : {total_friction:,}")
    print(f"  Total noise            : {noise_count:,}")
    print(f"  Total unclassified     : {len(unclassified):,}")
    print(f"  Total                  : {total_friction + noise_count + len(unclassified):,} "
          f"(raw_feedback = {total_records:,})")
    match = "MATCH" if total_friction + noise_count + len(unclassified) == total_records else "MISMATCH"
    print(f"  Reconciliation         : {match}")
    print(f"  Last classified at     : {now_ts}")
    print("-" * 75 + "\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Myntra Discovery Engine — Classification & Aggregation")
    parser.add_argument(
        "--incremental", action="store_true",
        help="Only classify newly ingested records (is_processed=False, theme=NULL). Faster."
    )
    parser.add_argument(
        "--aggregate-only", action="store_true",
        help="Skip classification, just re-aggregate existing classifications into insights table."
    )
    args = parser.parse_args()

    if args.aggregate_only:
        supabase = get_supabase()
        _aggregate_and_upsert_insights(supabase)
    else:
        run_normalization(unprocessed_only=args.incremental)
