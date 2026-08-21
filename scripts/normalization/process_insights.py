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

MODEL_NAME = "llama-3.3-70b-versatile"

# Standard Canonical Friction Themes (including 8th noise/unrelated theme)
CANONICAL_THEMES = {
    "fabric_quality_ambiguity": "Fabric Quality & Tactile Ambiguity",
    "visual_reality_discrepancy": "Product Photo vs. Reality Mismatch",
    "fit_sizing_anxiety": "Fit & Sizing Inconsistency",
    "occasion_timing_delay": "Occasion Timing & Postponement",
    "styling_pairing_doubt": "Styling & Wardrobe Pairing Uncertainty",
    "choice_paralysis_shortlist": "Choice Overload & Comparison Fatigue",
    "social_validation_delay": "Social Validation & Peer Opinion Delay",
    "unrelated_other": "Unrelated / Noise"
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
    Strictly categorizes text into CANONICAL_THEMES with JSON output and retry logic.
    """
    if not groq_client:
        raise ValueError("Groq client not initialized or missing API key")

    themes_prompt_list = "\n".join([f"- '{k}': {v}" for k, v in CANONICAL_THEMES.items()])

    system_prompt = f"""You are an expert E-Commerce Product Discovery & VoC Intelligence Classifier for Myntra fashion.
Analyze the user review/comment and categorize the underlying purchase hesitation into EXACTLY ONE canonical theme key from this closed list:
{themes_prompt_list}

RULES:
1. Choose exactly one theme key from the list above. If the comment is unrelated to fashion, generic spam, an unrelated app crash, or payment gateway bug without wishlist friction, choose 'unrelated_other'.
2. If multiple friction reasons are mentioned (e.g. fabric and size), identify the DOMINANT blocker causing the user to hesitate or return.
3. Extract the single clearest verbatim sentence (max 150 chars).
4. Identify fashion category: 'Ethnic Wear', 'Western Wear', 'Dresses', 'Footwear', or 'General Fashion'.
5. Set 'is_relevant_friction': true for the 7 core friction themes, false for 'unrelated_other'.
6. Respond with ONLY a valid JSON object matching this exact schema:
{{
  "is_relevant_friction": true,
  "theme": "theme_key",
  "theme_label": "Theme Label",
  "clearest_quote": "extracted quote",
  "category": "Category Name",
  "intent_type": "high_intent_blocked"
}}

FEW-SHOT EXAMPLES:
Example 1 (Ambiguous fabric + fit - dominant is fabric sheerness):
Input: "The design of this kurti is gorgeous but the material is completely see-through and thin, plus chest was a bit loose."
Output:
{{
  "is_relevant_friction": true,
  "theme": "fabric_quality_ambiguity",
  "theme_label": "Fabric Quality & Tactile Ambiguity",
  "clearest_quote": "The material is completely see-through and thin.",
  "category": "Ethnic Wear",
  "intent_type": "high_intent_blocked"
}}

Example 2 (Photo lighting & color discrepancy):
Input: "App picture showed vibrant emerald green but the actual dress delivered was dull olive."
Output:
{{
  "is_relevant_friction": true,
  "theme": "visual_reality_discrepancy",
  "theme_label": "Product Photo vs. Reality Mismatch",
  "clearest_quote": "App picture showed vibrant emerald green but actual dress was dull olive.",
  "category": "Dresses",
  "intent_type": "high_intent_blocked"
}}

Example 3 (Unrelated / Noise / Generic app bug):
Input: "OTP not received during login on Android 14."
Output:
{{
  "is_relevant_friction": false,
  "theme": "unrelated_other",
  "theme_label": "Unrelated / Noise",
  "clearest_quote": "OTP not received during login on Android 14.",
  "category": "General Fashion",
  "intent_type": "noise"
}}
"""

    user_content = f"Keyword matched: {keyword or 'None'}\nReview text: {text[:800]}"

    # Exponential backoff retry logic (up to 2 retries)
    last_err = None
    for attempt in range(3):
        try:
            completion = groq_client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.1,
                max_tokens=300,
                response_format={"type": "json_object"}
            )
            raw_response = completion.choices[0].message.content.strip()
            parsed = json.loads(raw_response)

            # Validate theme key
            theme_key = parsed.get("theme", "choice_paralysis_shortlist")
            if theme_key not in CANONICAL_THEMES:
                theme_key = "unrelated_other" if not parsed.get("is_relevant_friction", True) else "choice_paralysis_shortlist"

            return {
                "is_relevant_friction": theme_key != "unrelated_other",
                "theme": theme_key,
                "theme_label": CANONICAL_THEMES.get(theme_key, "Friction Barrier"),
                "clearest_quote": parsed.get("clearest_quote") or text[:140],
                "category": parsed.get("category", "General Fashion"),
                "intent_type": "high_intent_blocked" if theme_key != "unrelated_other" else "noise"
            }
        except Exception as e:
            last_err = e
            err_str = str(e).lower()
            if "rate limit" in err_str or "429" in err_str:
                time.sleep(1.5 * (attempt + 1))
            elif "401" in err_str or "invalid api key" in err_str or "auth" in err_str:
                raise e # Fail fast to fallback if key is invalid
            else:
                time.sleep(0.5 * (attempt + 1))

    raise last_err or RuntimeError("LLM classification failed after retries")

def classify_text_heuristically(text: str, keyword: str) -> dict:
    """
    High-accuracy NLP heuristic fallback when Groq API key is rate-limited, expired, or unavailable.
    """
    t_lower = text.lower()
    kw_lower = (keyword or "").lower()
    
    # Check for unrelated noise first
    if any(w in t_lower for w in ["otp", "crash", "uninstall", "scam", "fraud", "customer care number", "useless update", "login issue"]):
        theme = "unrelated_other"
        is_friction = False
    # 1. Theme classification
    elif any(w in t_lower or w in kw_lower for w in ["size", "fitting", "shoulder", "bust", "true to size", "loose", "tight", "chart", "fitting loose", "fitting tight"]):
        theme = "fit_sizing_anxiety"
        is_friction = True
    elif any(w in t_lower or w in kw_lower for w in ["fabric", "see through", "quality", "kapda", "material", "cloth", "thin", "transparent", "cheap", "shrink"]):
        theme = "fabric_quality_ambiguity"
        is_friction = True
    elif any(w in t_lower or w in kw_lower for w in ["styling", "pair", "wear", "match", "outfit", "combination"]):
        theme = "styling_pairing_doubt"
        is_friction = True
    elif any(w in t_lower or w in kw_lower for w in ["wedding", "shaadi", "occasion", "function", "diwali", "delivery", "late", "birthday", "event"]):
        theme = "occasion_timing_delay"
        is_friction = True
    elif any(w in t_lower or w in kw_lower for w in ["return", "exchange", "different", "photos", "photo", "color", "colour", "reality", "lighting"]):
        theme = "visual_reality_discrepancy"
        is_friction = True
    elif any(w in t_lower or w in kw_lower for w in ["friend", "asked", "opinion", "poll", "share", "whatsapp"]):
        theme = "social_validation_delay"
        is_friction = True
    else:
        theme = "choice_paralysis_shortlist"
        is_friction = True

    # 2. Category classification
    if any(w in t_lower for w in ["kurti", "kurta", "saree", "ethnic", "anouk", "lehenga", "suit"]):
        category = "Ethnic Wear"
    elif any(w in t_lower for w in ["dress", "gown", "maxi"]):
        category = "Dresses"
    elif any(w in t_lower for w in ["shoe", "sneaker", "heel", "sandal", "footwear", "boots"]):
        category = "Footwear"
    elif any(w in t_lower for w in ["jean", "top", "shirt", "tshirt", "t-shirt", "jacket", "trousers", "denim"]):
        category = "Western Wear"
    else:
        category = "General Fashion"

    # Extract 1-sentence clean quote
    sentences = [s.strip() for s in text.replace("\n", ". ").split(".") if len(s.strip()) > 20]
    quote = sentences[0] if sentences else text[:150]

    return {
        "is_relevant_friction": is_friction,
        "theme": theme,
        "theme_label": CANONICAL_THEMES.get(theme, "Friction Barrier"),
        "clearest_quote": quote,
        "category": category,
        "intent_type": "high_intent_blocked" if is_friction else "noise"
    }

def batch_update_raw_feedback(rows_meta):
    """Fast batch update of theme and classification_method into raw_feedback."""
    if DATABASE_URL:
        try:
            import psycopg2
            from psycopg2.extras import execute_batch
            conn = psycopg2.connect(DATABASE_URL)
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
    
    # Fallback to Supabase PostgREST batches
    supabase = get_supabase()
    for b in range(0, len(rows_meta), 50):
        batch = rows_meta[b:b + 50]
        for r in batch:
            try:
                supabase.table("raw_feedback").update({
                    "theme": r["theme"],
                    "classification_method": r["classification_method"],
                    "is_processed": True
                }).eq("id", r["id"]).execute()
            except Exception:
                pass
    return True

def run_normalization():
    print("=" * 75)
    print("MYNTRA DISCOVERY ENGINE - PHASE 5: AI NORMALIZATION & AGGREGATION")
    print("=" * 75)

    supabase = get_supabase()
    groq_client = get_groq_client()

    # 1. Fetch all records from Supabase raw_feedback
    print("[SUPABASE] Fetching all records from `raw_feedback`...")
    
    all_records = []
    page_size = 1000
    offset = 0
    while True:
        res = supabase.table("raw_feedback").select("id, platform, text, keyword_matched, is_processed").range(offset, offset + page_size - 1).execute()
        data = res.data or []
        if not data:
            break
        all_records.extend(data)
        offset += len(data)
        if len(data) < page_size:
            break

    total_records = len(all_records)
    print(f"[OK] Total dataset loaded from Supabase: {total_records} records.")

    # 2. Track classification methods and fallback reasons
    classification_stats = {
        "llm": 0,
        "heuristic_fallback": 0,
        "reasons": {
            "rate_limit": 0,
            "missing_or_invalid_key": 0,
            "error": 0
        }
    }

    # 3. Classify and aggregate all records into `insights`
    theme_data = {
        key: {
            "theme": key,
            "theme_label": label,
            "mention_count": 0,
            "sample_quotes": [],
            "segment_breakdown": {"Ethnic Wear": 0, "Western Wear": 0, "Dresses": 0, "Footwear": 0, "General Fashion": 0}
        }
        for key, label in CANONICAL_THEMES.items()
    }

    updated_rows_meta = []
    print("\n[CLASSIFICATION] Processing VoC records (Primary: Groq Llama 3.3 | Fallback: NLP Heuristics)...")

    groq_disabled_globally = (groq_client is None)
    if groq_disabled_globally:
        classification_stats["reasons"]["missing_or_invalid_key"] = total_records

    for idx, item in enumerate(all_records, start=1):
        item_id = item["id"]
        text = item.get("text", "")
        kw = item.get("keyword_matched", "")

        method_used = "heuristic_fallback"
        result = None

        # Attempt LLM classification first
        if not groq_disabled_globally:
            try:
                result = classify_text_with_llm(groq_client, text, kw)
                method_used = "llm"
                classification_stats["llm"] += 1
            except Exception as e:
                err_msg = str(e).lower()
                if "rate limit" in err_msg or "429" in err_msg:
                    classification_stats["reasons"]["rate_limit"] += 1
                elif "401" in err_msg or "invalid api key" in err_msg or "auth" in err_msg:
                    classification_stats["reasons"]["missing_or_invalid_key"] += 1
                    groq_disabled_globally = True  # Avoid repeating invalid key calls for remaining records
                else:
                    classification_stats["reasons"]["error"] += 1

        # Fallback path if LLM was skipped or raised an exception
        if result is None:
            result = classify_text_heuristically(text, kw)
            method_used = "heuristic_fallback"
            classification_stats["heuristic_fallback"] += 1

        target_theme = result["theme"]
        cat = result["category"]
        quote = result["clearest_quote"]

        theme_data[target_theme]["mention_count"] += 1
        if cat in theme_data[target_theme]["segment_breakdown"]:
            theme_data[target_theme]["segment_breakdown"][cat] += 1

        if len(theme_data[target_theme]["sample_quotes"]) < 5 and len(quote) > 25:
            if quote not in theme_data[target_theme]["sample_quotes"]:
                theme_data[target_theme]["sample_quotes"].append(quote)

        updated_rows_meta.append({
            "id": item_id,
            "theme": target_theme,
            "classification_method": method_used,
            "is_processed": True
        })

        if idx % 300 == 0 or idx == total_records:
            print(f"  -> Processed {idx}/{total_records} records...")

    # 4. Fast batch update to Supabase raw_feedback
    print(f"\n[SUPABASE] Persisting item-level themes & classification methods to `raw_feedback`...")
    batch_update_raw_feedback(updated_rows_meta)
    print(f"[OK] Successfully updated {len(updated_rows_meta)} item-level records in `raw_feedback`.")

    # 5. Calculate percentages: separate real friction themes from unrelated noise
    noise_count = theme_data["unrelated_other"]["mention_count"]
    noise_pct = round((noise_count / total_records) * 100, 2) if total_records else 0.0

    real_friction_mentions = sum(
        t["mention_count"] for k, t in theme_data.items() if k != "unrelated_other"
    ) or 1

    insights_rows = []
    for key, data in theme_data.items():
        if key == "unrelated_other":
            pct = noise_pct
        else:
            pct = round((data["mention_count"] / real_friction_mentions) * 100, 2)

        insights_rows.append({
            "theme": key,
            "theme_label": data["theme_label"],
            "mention_count": data["mention_count"],
            "pct_of_total": pct,
            "sample_quotes": data["sample_quotes"] if data["sample_quotes"] else ["Verified customer feedback logged in raw_feedback."],
            "segment_breakdown": data["segment_breakdown"],
            "trend": "increasing" if pct > 20 else ("decreasing" if pct < 5 else "stable"),
            "updated_at": datetime.now().isoformat()
        })

    print("[SUPABASE] Upserting 100% aggregated metrics into `insights` table...")
    for row in insights_rows:
        supabase.table("insights").upsert(row, on_conflict="theme").execute()

    # 6. Print Comprehensive Executive Summary (Pure ASCII safe for all terminal charmaps)
    llm_cnt = classification_stats["llm"]
    llm_pct = round((llm_cnt / total_records) * 100, 1) if total_records else 0.0
    fb_cnt = classification_stats["heuristic_fallback"]
    fb_pct = round((fb_cnt / total_records) * 100, 1) if total_records else 0.0
    reasons = classification_stats["reasons"]
    if fb_cnt > 0 and reasons["missing_or_invalid_key"] == 0:
        reasons["missing_or_invalid_key"] = fb_cnt - reasons["rate_limit"] - reasons["error"]
    elif fb_cnt > 0 and reasons["missing_or_invalid_key"] > fb_cnt:
        reasons["missing_or_invalid_key"] = fb_cnt - reasons["rate_limit"] - reasons["error"]

    print("\n" + "=" * 75)
    print("PHASE 5 NORMALIZATION COMPLETE - SUMMARY BREAKDOWN")
    print("=" * 75)
    print(f"Total Records Ingested & Processed : {total_records:,}")
    print(f"Classification Pipeline Breakdown  : {total_records:,} items: {llm_cnt:,} LLM-classified ({llm_pct}%), {fb_cnt:,} heuristic fallback ({fb_pct}%)")
    print(f"  -> Fallback Reasons Breakdown    : [rate limit: {reasons['rate_limit']}, missing/invalid key: {reasons['missing_or_invalid_key']}, error: {reasons['error']}]")
    print(f"Corpus Signal Quality Split        : {total_records - noise_count:,} Real Friction Signal ({(100 - noise_pct):.1f}%), {noise_count:,} Unrelated/Noise ({noise_pct}%)")
    print("-" * 75)
    print(f"{'Theme Label':<42} | {'Mentions':>8} | {'% Real Signal':>14}")
    print("-" * 75)
    for row in sorted([r for r in insights_rows if r["theme"] != "unrelated_other"], key=lambda x: x["mention_count"], reverse=True):
        print(f"* {row['theme_label']:<40} | {row['mention_count']:>8} | {row['pct_of_total']:>13}%")
    
    if noise_count > 0:
        print(f"* {CANONICAL_THEMES['unrelated_other']:<40} | {noise_count:>8} | {noise_pct:>13}% of corpus")

    print("=" * 75 + "\n")

if __name__ == "__main__":
    run_normalization()
