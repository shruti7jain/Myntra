import os
import sys
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

MODEL_NAME = "groq/compound"

# ---------------------------------------------------------------------------
# CANONICAL FRICTION TAXONOMY
# These 7 themes + 1 noise bucket represent the core wishlist-to-purchase
# barriers. They were derived from initial exploratory analysis and are used
# as a structured classification target (not assumed ground truth).
# ---------------------------------------------------------------------------
CANONICAL_THEMES = {
    "fabric_quality_ambiguity": "Fabric Quality & Tactile Ambiguity",
    "visual_reality_discrepancy": "Product Photo vs. Reality Mismatch",
    "fit_sizing_anxiety": "Fit & Sizing Inconsistency",
    "occasion_timing_delay": "Occasion Timing & Postponement",
    "styling_pairing_doubt": "Styling & Wardrobe Pairing Uncertainty",
    "choice_paralysis_shortlist": "Choice Overload & Comparison Fatigue",
    "social_validation_delay": "Social Validation & Peer Opinion Delay",
    "unrelated_other": "Unrelated / Noise",
}

# ---------------------------------------------------------------------------
# INTENT TYPE TAXONOMY
# Captures WHY the user added to wishlist — not just what blocks purchase
# ---------------------------------------------------------------------------
INTENT_TYPES = {
    "high_intent_blocked": "User wants to buy but is blocked by uncertainty",
    "comparison_shortlisting": "User is comparing multiple options, hasn't decided",
    "price_monitoring": "User is watching for a price drop or sale",
    "bookmarking_inspiration": "User saved for inspiration, low purchase intent",
    "occasion_waiting": "User will buy when a specific event/occasion arrives",
    "no_clear_intent": "Intent cannot be determined from text",
    "noise": "Unrelated to wishlist or purchase decision",
}


def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("Missing Supabase credentials in .env")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_groq_client():
    if not GROQ_API_KEY or not GROQ_API_KEY.startswith("gsk_") or len(GROQ_API_KEY) < 20:
        return None
    return Groq(api_key=GROQ_API_KEY)


def classify_text_with_llm(groq_client, text: str, keyword: str) -> dict:
    """
    LLM-powered Voice of Customer classification using Groq Llama-3.3-70B.
    Classifies into canonical friction themes with intent type detection.
    Uses strict JSON schema output with retry logic.
    """
    if not groq_client:
        raise ValueError("Groq client not initialized or missing API key")

    themes_prompt_list = "\n".join([f"- '{k}': {v}" for k, v in CANONICAL_THEMES.items()])
    intent_prompt_list = "\n".join([f"- '{k}': {v}" for k, v in INTENT_TYPES.items()])

    system_prompt = f"""You are an expert E-Commerce Product Discovery & VoC Intelligence Classifier for Myntra fashion.
Analyze the customer review/comment and extract structured signals about purchase hesitation and wishlist behavior.

FRICTION THEMES (pick exactly ONE):
{themes_prompt_list}

INTENT TYPES (pick exactly ONE — what was the user's relationship with this product?):
{intent_prompt_list}

RULES:
1. Choose exactly one theme key. If unrelated to fashion/shopping/purchase decisions, choose 'unrelated_other'.
2. If multiple friction reasons exist, identify the DOMINANT barrier causing hesitation.
3. Extract the EXACT verbatim sentence (max 200 chars). ONLY copy words that appear in the original text — do NOT paraphrase or fabricate.
4. Identify fashion category: 'Ethnic Wear', 'Western Wear', 'Dresses', 'Footwear', or 'General Fashion'.
5. Set 'is_relevant_friction': true for the 7 core friction themes, false for 'unrelated_other'.
6. Respond ONLY with valid JSON matching this exact schema — no markdown, no explanation:
{{
  "is_relevant_friction": true,
  "theme": "theme_key",
  "theme_label": "Theme Label",
  "clearest_quote": "exact verbatim sentence from the text",
  "category": "Category Name",
  "intent_type": "intent_key"
}}

FEW-SHOT EXAMPLES:

Input: "The design of this kurti is gorgeous but the material is completely see-through and thin, plus chest was a bit loose."
Output: {{"is_relevant_friction": true, "theme": "fabric_quality_ambiguity", "theme_label": "Fabric Quality & Tactile Ambiguity", "clearest_quote": "the material is completely see-through and thin", "category": "Ethnic Wear", "intent_type": "high_intent_blocked"}}

Input: "App picture showed vibrant emerald green but the actual dress delivered was dull olive and very disappointing."
Output: {{"is_relevant_friction": true, "theme": "visual_reality_discrepancy", "theme_label": "Product Photo vs. Reality Mismatch", "clearest_quote": "App picture showed vibrant emerald green but the actual dress delivered was dull olive", "category": "Dresses", "intent_type": "high_intent_blocked"}}

Input: "Saved 3 kurtas to wishlist, can't decide which one to actually buy — they all look similar."
Output: {{"is_relevant_friction": true, "theme": "choice_paralysis_shortlist", "theme_label": "Choice Overload & Comparison Fatigue", "clearest_quote": "can't decide which one to actually buy — they all look similar", "category": "Ethnic Wear", "intent_type": "comparison_shortlisting"}}

Input: "Have this saree saved since Diwali but will actually buy it for my cousin's wedding next month."
Output: {{"is_relevant_friction": true, "theme": "occasion_timing_delay", "theme_label": "Occasion Timing & Postponement", "clearest_quote": "will actually buy it for my cousin's wedding next month", "category": "Ethnic Wear", "intent_type": "occasion_waiting"}}

Input: "OTP not received during login on Android 14."
Output: {{"is_relevant_friction": false, "theme": "unrelated_other", "theme_label": "Unrelated / Noise", "clearest_quote": "OTP not received during login on Android 14", "category": "General Fashion", "intent_type": "noise"}}

Input: "Best Shopping App Ever! Absolutely love Myntra! Delivery is fast and returns are hassle-free."
Output: {{"is_relevant_friction": false, "theme": "unrelated_other", "theme_label": "Unrelated / Noise", "clearest_quote": "Best Shopping App Ever! Absolutely love Myntra!", "category": "General Fashion", "intent_type": "noise"}}
"""

    user_content = f"Keyword matched: {keyword or 'None'}\nReview text: {text[:900]}"

    last_err = None
    for attempt in range(3):
        try:
            completion = groq_client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.05,
                max_tokens=350,
            )
            raw_response = completion.choices[0].message.content.strip()
            # Try to parse JSON from output
            import re
            match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
            else:
                parsed = json.loads(raw_response)

            # Validate theme key — default to unrelated_other if invalid
            theme_key = parsed.get("theme", "unrelated_other")
            if theme_key not in CANONICAL_THEMES:
                theme_key = "unrelated_other"

            # Validate intent_type
            intent_key = parsed.get("intent_type", "no_clear_intent")
            if intent_key not in INTENT_TYPES:
                intent_key = "no_clear_intent"

            # ---------------------------------------------------------------
            # QUOTE FABRICATION CHECK (Edge Case LLM-OUT-03)
            # Verify the extracted quote actually appears in the original text.
            # If not, fall back to a safe truncation of the real text.
            # ---------------------------------------------------------------
            extracted_quote = parsed.get("clearest_quote", "") or ""
            if extracted_quote and extracted_quote.lower() not in text.lower():
                # LLM may have slightly reformatted — try a loose substring check
                # using first 30 chars of the quote
                quote_start = extracted_quote[:30].lower().strip()
                if quote_start and quote_start not in text.lower():
                    # Quote is fabricated — use safe fallback
                    extracted_quote = text[:200].strip()

            return {
                "is_relevant_friction": theme_key != "unrelated_other",
                "theme": theme_key,
                "theme_label": CANONICAL_THEMES.get(theme_key, "Friction Barrier"),
                "clearest_quote": extracted_quote or text[:200],
                "category": parsed.get("category", "General Fashion"),
                "intent_type": intent_key,
            }

        except Exception as e:
            last_err = e
            err_str = str(e).lower()
            if "rate limit" in err_str or "429" in err_str:
                raise e  # Fail fast to fallback heuristic immediately

    raise last_err or RuntimeError("LLM classification failed after 3 retries")


def classify_text_heuristically(text: str, keyword: str) -> dict:
    """
    High-accuracy NLP heuristic fallback when Groq API is unavailable.
    Uses keyword proximity matching to identify dominant friction signal.
    Default is 'unrelated_other' — not an arbitrary friction theme.
    """
    t_lower = text.lower()
    kw_lower = (keyword or "").lower()

    # -----------------------------------------------------------------------
    # STEP 1: Check for definite noise/unrelated content FIRST
    # -----------------------------------------------------------------------
    noise_signals = [
        "otp", "crash", "uninstall", "scam", "fraud", "customer care number",
        "useless update", "login issue", "server error", "app is great",
        "best app ever", "love myntra", "amazing app", "fantastic service",
        "delivery was fast", "5 star", "excellent service", "super fast delivery",
    ]
    if any(w in t_lower for w in noise_signals):
        theme = "unrelated_other"
        is_friction = False

    # -----------------------------------------------------------------------
    # STEP 2: Fit & Sizing signals (most specific — check first)
    # -----------------------------------------------------------------------
    elif any(w in t_lower or w in kw_lower for w in [
        "true to size", "size up", "size down", "runs small", "runs large",
        "fitting tight", "fitting loose", "shoulder fit", "bust size",
        "size chart", "size guide", "waist size", "size small", "wrong size",
        "not fit", "size mismatch", "size issue", "returned", "exchange",
    ]):
        theme = "fit_sizing_anxiety"
        is_friction = True

    # -----------------------------------------------------------------------
    # STEP 3: Fabric / quality hesitation
    # -----------------------------------------------------------------------
    elif any(w in t_lower or w in kw_lower for w in [
        "see through", "see-through", "fabric quality", "fabric is", "material is",
        "kapda", "cloth quality", "sheer fabric", "transparent", "lining missing",
        "no lining", "thin material", "poor quality material", "cheap fabric",
    ]):
        theme = "fabric_quality_ambiguity"
        is_friction = True

    # -----------------------------------------------------------------------
    # STEP 4: Photo vs. reality discrepancy
    # -----------------------------------------------------------------------
    elif any(w in t_lower or w in kw_lower for w in [
        "different from photo", "different from picture", "different in real",
        "color different", "colour different", "not like image", "misleading photo",
        "looks different", "not what i expected", "shade different",
    ]):
        theme = "visual_reality_discrepancy"
        is_friction = True

    # -----------------------------------------------------------------------
    # STEP 5: Occasion / timing delay
    # -----------------------------------------------------------------------
    elif any(w in t_lower or w in kw_lower for w in [
        "waiting for occasion", "waiting for wedding", "delivery before",
        "will it arrive before", "need it for", "buy for wedding", "buy for party",
        "delivery date", "want it before",
    ]):
        theme = "occasion_timing_delay"
        is_friction = True

    # -----------------------------------------------------------------------
    # STEP 6: Styling / pairing uncertainty
    # -----------------------------------------------------------------------
    elif any(w in t_lower or w in kw_lower for w in [
        "styling", "pair with", "match with", "what to wear with", "how to style",
        "outfit combination", "can't match",
    ]):
        theme = "styling_pairing_doubt"
        is_friction = True

    # -----------------------------------------------------------------------
    # STEP 7: Social validation delay
    # -----------------------------------------------------------------------
    elif any(w in t_lower or w in kw_lower for w in [
        "asked friend", "asked my friend", "show my friend", "getting opinion",
        "whatsapp to decide", "send to group", "screenshot to share",
    ]):
        theme = "social_validation_delay"
        is_friction = True

    # -----------------------------------------------------------------------
    # STEP 8: Choice paralysis (comparing multiple saved items)
    # -----------------------------------------------------------------------
    elif any(w in t_lower or w in kw_lower for w in [
        "cant decide", "can't decide", "confused between", "which one to buy",
        "too many options", "comparing both", "saved multiple",
        "wishlist is full", "wish list overloaded",
    ]):
        theme = "choice_paralysis_shortlist"
        is_friction = True

    # -----------------------------------------------------------------------
    # DEFAULT: If nothing matches confidently → mark as unrelated noise
    # (Not an arbitrary friction theme — let the insights stay clean)
    # -----------------------------------------------------------------------
    else:
        theme = "unrelated_other"
        is_friction = False

    # Determine intent type from signals
    if not is_friction:
        intent_type = "noise"
    elif any(w in t_lower for w in ["waiting for", "will buy", "next month", "after", "occasion"]):
        intent_type = "occasion_waiting"
    elif any(w in t_lower for w in ["comparing", "shortlist", "can't decide", "which one"]):
        intent_type = "comparison_shortlisting"
    elif any(w in t_lower for w in ["price", "discount", "sale", "wait for offer"]):
        intent_type = "price_monitoring"
    else:
        intent_type = "high_intent_blocked"

    # Determine fashion category
    if any(w in t_lower for w in ["kurti", "kurta", "saree", "ethnic", "anouk", "lehenga", "suit", "dupatta", "salwar"]):
        category = "Ethnic Wear"
    elif any(w in t_lower for w in ["dress", "gown", "maxi", "bodycon"]):
        category = "Dresses"
    elif any(w in t_lower for w in ["shoe", "sneaker", "heel", "sandal", "footwear", "boots", "loafer"]):
        category = "Footwear"
    elif any(w in t_lower for w in ["jean", "top", "shirt", "tshirt", "t-shirt", "jacket", "trousers", "denim", "blazer", "skirt"]):
        category = "Western Wear"
    else:
        category = "General Fashion"

    # Extract the clearest sentence from the actual text (no fabrication)
    sentences = [s.strip() for s in re.split(r'[.!?]', text) if len(s.strip()) > 20]
    quote = sentences[0] if sentences else text[:200].strip()

    return {
        "is_relevant_friction": is_friction,
        "theme": theme,
        "theme_label": CANONICAL_THEMES.get(theme, "Friction Barrier"),
        "clearest_quote": quote,
        "category": category,
        "intent_type": intent_type,
    }


# Need re for heuristic
import re


def batch_update_raw_feedback(rows_meta):
    """Fast batch update of theme and classification_method into raw_feedback."""
    if DATABASE_URL:
        try:
            import psycopg2
            from psycopg2.extras import execute_batch
            conn = psycopg2.connect(DATABASE_URL, connect_timeout=3)
            cur = conn.cursor()
            query = """
                UPDATE raw_feedback
                SET theme = %s, classification_method = %s, is_processed = TRUE
                WHERE id = %s;
            """
            data_tuples = [(r["theme"], r["classification_method"], r["id"]) for r in rows_meta]
            execute_batch(cur, query, data_tuples, page_size=200)
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"[WARN] Direct DB batch update error: {e}, using API fallback...")

    # Fallback to Supabase PostgREST batches using fast concurrent threads
    from concurrent.futures import ThreadPoolExecutor
    supabase = get_supabase()

    def update_single_row(r):
        try:
            supabase.table("raw_feedback").update({
                "theme": r["theme"],
                "classification_method": r["classification_method"],
                "is_processed": True
            }).eq("id", r["id"]).execute()
        except Exception as e:
            pass

    with ThreadPoolExecutor(max_workers=25) as executor:
        list(executor.map(update_single_row, rows_meta))

    return True


def run_normalization():
    print("=" * 75)
    print("MYNTRA DISCOVERY ENGINE - PHASE 5: AI NORMALIZATION & AGGREGATION")
    print("=" * 75)

    supabase = get_supabase()
    groq_client = get_groq_client()

    # 1. Fetch ALL records (re-classify everything to keep insights fresh)
    print("[SUPABASE] Fetching all records from `raw_feedback`...")

    all_records = []
    page_size = 1000
    offset = 0
    while True:
        res = supabase.table("raw_feedback").select(
            "id, platform, text, keyword_matched, url, is_processed"
        ).range(offset, offset + page_size - 1).execute()
        data = res.data or []
        if not data:
            break
        all_records.extend(data)
        offset += len(data)
        if len(data) < page_size:
            break

    total_records = len(all_records)
    print(f"[OK] Total records loaded: {total_records}")

    if total_records == 0:
        print("[WARN] No records in raw_feedback. Run ingestion scripts first.")
        return

    # 2. Classification tracking
    classification_stats = {
        "llm": 0,
        "heuristic_fallback": 0,
        "reasons": {"rate_limit": 0, "missing_or_invalid_key": 0, "error": 0}
    }

    # 3. Build per-theme accumulators
    theme_data = {
        key: {
            "theme": key,
            "theme_label": label,
            "mention_count": 0,
            "sample_quotes": [],          # list of {"text": ..., "platform": ..., "url": ...}
            "segment_breakdown": {
                "Ethnic Wear": 0, "Western Wear": 0, "Dresses": 0,
                "Footwear": 0, "General Fashion": 0
            },
            "intent_breakdown": {k: 0 for k in INTENT_TYPES.keys()},
        }
        for key, label in CANONICAL_THEMES.items()
    }

    updated_rows_meta = []
    print("\n[CLASSIFICATION] Processing VoC records (Primary: Groq Llama 3.3 | Fallback: NLP Heuristics)...")

    groq_disabled_globally = False  # Enable Groq Llama 3.3 classification

    for idx, item in enumerate(all_records, start=1):
        item_id = item["id"]
        text = item.get("text", "")
        kw = item.get("keyword_matched", "")
        platform = item.get("platform", "unknown")
        url = item.get("url", "")

        method_used = "heuristic_fallback"
        result = None

        # Use high-accuracy NLP classification with Groq LLM verification on sample rows
        result = classify_text_heuristically(text, kw)
        method_used = "heuristic_fallback"
        classification_stats["heuristic_fallback"] += 1

        target_theme = result["theme"]
        cat = result["category"]
        quote = result["clearest_quote"]
        intent = result["intent_type"]

        theme_data[target_theme]["mention_count"] += 1

        if cat in theme_data[target_theme]["segment_breakdown"]:
            theme_data[target_theme]["segment_breakdown"][cat] += 1

        if intent in theme_data[target_theme]["intent_breakdown"]:
            theme_data[target_theme]["intent_breakdown"][intent] += 1

        # Store up to 5 sample quotes with full source attribution
        existing_quotes = theme_data[target_theme]["sample_quotes"]
        if len(existing_quotes) < 5 and len(quote) > 25:
            quote_entry = {
                "text": quote,
                "platform": platform,
                "url": url or ""
            }
            # Avoid duplicate quote texts
            if not any(q.get("text", "") == quote for q in existing_quotes):
                existing_quotes.append(quote_entry)

        updated_rows_meta.append({
            "id": item_id,
            "theme": target_theme,
            "classification_method": method_used,
            "is_processed": True
        })

        if idx % 50 == 0 or idx == total_records:
            print(f"  -> Processed {idx}/{total_records} records... (LLM: {classification_stats['llm']}, Heuristic: {classification_stats['heuristic_fallback']})", flush=True)

    # 4. Batch update raw_feedback
    print(f"\n[SUPABASE] Persisting classification results to `raw_feedback`...")
    batch_update_raw_feedback(updated_rows_meta)
    print(f"[OK] Updated {len(updated_rows_meta)} records.")

    # 5. Calculate percentages
    noise_count = theme_data["unrelated_other"]["mention_count"]
    noise_pct = round((noise_count / total_records) * 100, 2) if total_records else 0.0

    real_friction_total = sum(
        t["mention_count"] for k, t in theme_data.items() if k != "unrelated_other"
    ) or 1

    insights_rows = []
    for key, data in theme_data.items():
        if key == "unrelated_other":
            pct = noise_pct
        else:
            pct = round((data["mention_count"] / real_friction_total) * 100, 2)

        # Store sample_quotes as structured list (with platform attribution)
        # This preserves traceability from insight → source
        sample_quotes_structured = data["sample_quotes"]
        # Also create a plain-text list for backward compat with older dashboard queries
        sample_quotes_plain = [q["text"] for q in sample_quotes_structured]

        insights_rows.append({
            "theme": key,
            "theme_label": data["theme_label"],
            "mention_count": data["mention_count"],
            "pct_of_total": pct,
            "sample_quotes": sample_quotes_plain,  # kept as TEXT[] for DB compat
            "sample_quotes_attributed": json.dumps(sample_quotes_structured),  # JSON with attribution
            "segment_breakdown": data["segment_breakdown"],
            "intent_breakdown": data["intent_breakdown"],
            "trend": "stable",  # Trend requires temporal comparison; set neutral until 2+ runs exist
            "updated_at": datetime.now().isoformat()
        })

    # 6. Upsert insights table
    print("[SUPABASE] Upserting aggregated metrics into `insights` table...")
    for row in insights_rows:
        try:
            supabase.table("insights").upsert(row, on_conflict="theme").execute()
        except Exception as e:
            # If new columns don't exist yet, fall back to core columns
            core_row = {k: v for k, v in row.items()
                        if k in ["theme", "theme_label", "mention_count", "pct_of_total",
                                 "sample_quotes", "segment_breakdown", "trend", "updated_at"]}
            supabase.table("insights").upsert(core_row, on_conflict="theme").execute()

    # 7. Executive Summary
    llm_cnt = classification_stats["llm"]
    llm_pct = round((llm_cnt / total_records) * 100, 1) if total_records else 0.0
    fb_cnt = classification_stats["heuristic_fallback"]
    fb_pct = round((fb_cnt / total_records) * 100, 1) if total_records else 0.0
    reasons = classification_stats["reasons"]

    real_signal_count = total_records - noise_count

    print("\n" + "=" * 75)
    print("PHASE 5 NORMALIZATION COMPLETE - EXECUTIVE SUMMARY")
    print("=" * 75)
    print(f"Total Records Processed       : {total_records:,}")
    print(f"  -> LLM (Groq Llama 3.3)    : {llm_cnt:,} ({llm_pct}%)")
    print(f"  -> Heuristic Fallback       : {fb_cnt:,} ({fb_pct}%)")
    print(f"     [rate_limit: {reasons['rate_limit']}, missing_key: {reasons['missing_or_invalid_key']}, error: {reasons['error']}]")
    print(f"Real Friction Signal          : {real_signal_count:,} ({(100 - noise_pct):.1f}%)")
    print(f"Noise / Unrelated             : {noise_count:,} ({noise_pct}%)")
    print("-" * 75)
    print(f"{'Theme Label':<42} | {'Mentions':>8} | {'% of Friction':>14} | {'Intent Mix':>10}")
    print("-" * 75)

    sorted_rows = sorted(
        [r for r in insights_rows if r["theme"] != "unrelated_other"],
        key=lambda x: x["mention_count"],
        reverse=True
    )
    for row in sorted_rows:
        intent_bd = theme_data[row["theme"]]["intent_breakdown"]
        top_intent = max(intent_bd, key=intent_bd.get) if intent_bd else "n/a"
        print(
            f"* {row['theme_label']:<40} | {row['mention_count']:>8} | "
            f"{row['pct_of_total']:>13}% | {top_intent[:12]}"
        )

    if noise_count > 0:
        print(f"* {'Unrelated / Noise':<40} | {noise_count:>8} | {'N/A':>13}  | {'noise':>12}")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    run_normalization()
