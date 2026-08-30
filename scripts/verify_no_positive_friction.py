import os
import sys
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("[ERROR] Missing Supabase credentials in environment. Check .env file.")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

FRICTION_THEMES = {
    'fit_sizing_anxiety',
    'fabric_quality_ambiguity',
    'visual_reality_discrepancy',
    'occasion_timing_delay',
    'styling_pairing_doubt',
    'choice_paralysis_shortlist',
    'social_validation_delay',
    'price_deal_timing'
}

def check_rating_violations():
    print("=" * 75)
    # Print a neutral title without special characters to avoid Windows encoding crashes
    print("MYNTRA DISCOVERY ENGINE - POSITIVE REVIEW FRICTION VERIFICATION")
    print("=" * 75)
    print("Fetching all records with friction themes from raw_feedback...")
    
    all_records = []
    offset = 0
    page_size = 1000
    
    while True:
        res = supabase.table("raw_feedback").select(
            "id, platform, theme, rating, text"
        ).not_.is_("theme", "null").neq("theme", "unrelated_other").range(offset, offset + page_size - 1).execute()
        
        data = res.data or []
        if not data:
            break
        all_records.extend(data)
        offset += len(data)
        if len(data) < page_size:
            break
            
    print(f"Total reviews tagged with friction theme: {len(all_records)}")
    
    violations = []
    for r in all_records:
        r_id = r.get("id")
        platform = r.get("platform", "unknown")
        rating = r.get("rating")
        theme = r.get("theme")
        text = r.get("text", "")
        
        # Rule 1: Exclude reviews with rating >= 4
        is_violation = False
        reason = ""
        
        if platform in ["playstore", "appstore"]:
            if rating is None:
                is_violation = True
                reason = "Unknown rating (rating is null/missing) on review platform"
            else:
                try:
                    val = float(rating)
                    if val >= 4.0:
                        is_violation = True
                        reason = f"High rating (rating={rating}) on review platform"
                except (TypeError, ValueError):
                    is_violation = True
                    reason = f"Malformed rating (rating={rating}) on review platform"
        else:
            # YouTube / Reddit comments don't have ratings naturally.
            # But if a rating is somehow set and is >= 4, flag it.
            if rating is not None:
                try:
                    val = float(rating)
                    if val >= 4.0:
                        is_violation = True
                        reason = f"High rating (rating={rating}) on comment platform"
                except (TypeError, ValueError):
                    pass
                    
        if is_violation:
            violations.append({
                "id": r_id,
                "platform": platform,
                "rating": rating,
                "theme": theme,
                "text": text,
                "reason": reason
            })
            
    print("-" * 75)
    if not violations:
        print("VERIFICATION RESULT: PASS")
        print("No positive reviews or reviews with missing ratings are tagged as friction.")
        print("=" * 75)
        return True
    else:
        print("VERIFICATION RESULT: FAIL")
        print(f"Found {len(violations)} violations! Positive reviews cannot be classified as friction.")
        print("-" * 75)
        for v in violations:
            print(f"Violation ID: {v['id']}")
            print(f"  Platform: {v['platform'].upper()}")
            print(f"  Rating  : {v['rating']}")
            print(f"  Theme   : {v['theme']}")
            print(f"  Reason  : {v['reason']}")
            clean_text = v['text'][:150].encode('ascii', 'ignore').decode('ascii')
            print(f"  Text    : \"{clean_text}...\"")
            print("-" * 75)
        print("=" * 75)
        return False

if __name__ == "__main__":
    success = check_rating_violations()
    sys.exit(0 if success else 1)
