import os
import sys
import json
import random
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

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

THEME_KEYS = list(CANONICAL_THEMES.keys())

def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("Missing Supabase credentials in .env")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def run_human_validation(sample_size: int = 40, output_file: str = "validation_results.json"):
    print("=" * 75)
    print("MYNTRA DISCOVERY ENGINE - HUMAN-IN-THE-LOOP CLASSIFICATION VALIDATION")
    print("=" * 75)
    print(f"Goal: Evaluate {sample_size} randomly sampled VoC records for AI-Human Agreement Rate.")
    print("Instructions: For each review, type 'y' (Agree) or 'n' (Disagree), or 'q' to quit early.\n")

    supabase = get_supabase()

    # 1. Fetch classified records from raw_feedback
    print("[SUPABASE] Fetching classified records from `raw_feedback`...")
    res = supabase.table("raw_feedback").select("id, platform, text, keyword_matched, theme, classification_method").not_.is_("theme", "null").execute()
    data = res.data or []

    if not data:
        # Fallback to fetching all records if theme column was just populated
        res = supabase.table("raw_feedback").select("id, platform, text, keyword_matched").limit(1000).execute()
        data = res.data or []

    if not data:
        print("[ERROR] No records found in `raw_feedback`. Please run process_insights.py first.")
        return

    print(f"[OK] Found {len(data)} classified records in database.")
    
    # 2. Randomly sample items
    actual_sample_size = min(sample_size, len(data))
    sampled_records = random.sample(data, actual_sample_size)

    agreed_count = 0
    disagreed_count = 0
    disagreements = []
    evaluated_count = 0

    print("-" * 75)

    for i, item in enumerate(sampled_records, start=1):
        item_id = item.get("id")
        platform = item.get("platform", "unknown")
        text = item.get("text", "").strip()
        assigned_theme = item.get("theme", "choice_paralysis_shortlist")
        method = item.get("classification_method", "heuristic_fallback")
        theme_label = CANONICAL_THEMES.get(assigned_theme, assigned_theme)

        print(f"\n[{i}/{actual_sample_size}] Platform: {platform.upper()} (ID: {item_id} | Method: {method})")
        print(f"Text: \"{text[:300]}{'...' if len(text) > 300 else ''}\"")
        print(f"AI Assigned Theme: [{assigned_theme}] -> {theme_label}")

        while True:
            choice = input("Do you agree with this AI classification? (y/n / q to quit): ").strip().lower()
            if choice in ['y', 'yes']:
                agreed_count += 1
                evaluated_count += 1
                print("[AGREED]")
                break
            elif choice in ['n', 'no']:
                disagreed_count += 1
                evaluated_count += 1
                print("\nSelect what the correct theme should be:")
                for idx, (k, v) in enumerate(CANONICAL_THEMES.items(), start=1):
                    print(f"  [{idx}] {k} ({v})")
                
                user_theme_choice = input("Enter theme number [1-8] or custom note: ").strip()
                if user_theme_choice.isdigit() and 1 <= int(user_theme_choice) <= len(THEME_KEYS):
                    user_corrected_theme = THEME_KEYS[int(user_theme_choice) - 1]
                else:
                    user_corrected_theme = user_theme_choice or "unrelated_other"

                disagreements.append({
                    "id": item_id,
                    "platform": platform,
                    "text": text,
                    "ai_theme": assigned_theme,
                    "ai_theme_label": theme_label,
                    "user_theme": user_corrected_theme,
                    "user_theme_label": CANONICAL_THEMES.get(user_corrected_theme, user_corrected_theme),
                    "classification_method": method
                })
                print(f"[DISAGREED] Marked as '{user_corrected_theme}'")
                break
            elif choice in ['q', 'quit']:
                print("\n[INFO] Validation session stopped early by user.")
                break
            else:
                print("Please enter 'y', 'n', or 'q'.")

        if choice in ['q', 'quit']:
            break

    if evaluated_count == 0:
        print("[INFO] No items evaluated. Exiting without writing results.")
        return

    # 3. Calculate agreement percentage
    agreement_pct = round((agreed_count / evaluated_count) * 100, 2)

    results_payload = {
        "sample_size": evaluated_count,
        "agreed_count": agreed_count,
        "disagreed_count": disagreed_count,
        "agreement_pct": agreement_pct,
        "timestamp": datetime.now().isoformat(),
        "disagreements": disagreements
    }

    # 4. Save to validation_results.json
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results_payload, f, indent=2)

    print("\n" + "=" * 75)
    print("HUMAN-AI VALIDATION SUMMARY REPORT")
    print("=" * 75)
    print(f"Total Evaluated Sample Size : {evaluated_count} / {actual_sample_size}")
    print(f"Human-AI Agreement Count    : {agreed_count}")
    print(f"Disagreement Count          : {disagreed_count}")
    print(f"Reported AI Agreement Rate  : {agreement_pct}%")
    print(f"Results saved to            : {output_file}")
    print("=" * 75 + "\n")

if __name__ == "__main__":
    sample_n = 40
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        sample_n = int(sys.argv[1])
    run_human_validation(sample_size=sample_n)
