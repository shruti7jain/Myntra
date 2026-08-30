import os
import sys
import re
from collections import Counter
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), '.env'))

from supabase import create_client

# Suppress warnings to keep output clean
import warnings
warnings.filterwarnings("ignore")

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

# We import the heuristic classifier to see what the "pure text" theme would be
sys.path.append(os.path.join(os.getcwd(), 'scripts', 'normalization'))
from process_insights import classify_text_heuristically, is_excluded_by_rating, CANONICAL_THEMES

FRICTION_THEME_KEYS = {
    'fit_sizing_anxiety',
    'fabric_quality_ambiguity',
    'visual_reality_discrepancy',
    'occasion_timing_delay',
    'styling_pairing_doubt',
    'choice_paralysis_shortlist',
    'social_validation_delay',
    'price_deal_timing'
}

def analyze_friction_drop():
    print("Fetching raw records from raw_feedback...")
    all_records = []
    offset = 0
    while True:
        res = supabase.table("raw_feedback").select(
            "id, platform, theme, rating, text, keyword_matched, url"
        ).range(offset, offset + 999).execute()
        data = res.data or []
        all_records.extend(data)
        if len(data) < 1000:
            break
        offset += 1000

    print(f"Total records loaded: {len(all_records)}")

    # We will simulate the previous "pure" friction count (before rating filter)
    # and map the 226 records difference.
    # A record was previously friction if its pure heuristic/llm theme is in FRICTION_THEME_KEYS.
    # Note: since some records might have been classified by LLM, we check:
    # - If its database 'theme' is currently a friction theme, it IS currently friction.
    # - If its database 'theme' is unrelated_other, but it was classified as heuristic friction (or has a rating filter active),
    #   we inspect its details.
    
    previous_friction_list = []
    current_friction_list = []
    removed_list = []

    for r in all_records:
        theme = r.get("theme")
        platform = r.get("platform", "unknown")
        rating = r.get("rating")
        text = r.get("text", "")
        kw = r.get("keyword_matched", "")

        # Determine if it is currently classified as friction in the DB
        is_current_friction = theme in FRICTION_THEME_KEYS
        
        # Calculate pure heuristic theme (what it would be classified as based on text alone)
        pure_res = classify_text_heuristically(text, kw)
        pure_theme = pure_res["theme"]
        
        # We also check if rating filter is what excluded it
        rating_excluded = is_excluded_by_rating(platform, rating)

        # A record is considered "previously friction" if:
        # 1. It is currently friction in DB, OR
        # 2. It would have been classified as friction by pure heuristics/LLM, but was excluded by rating.
        is_previous_friction = is_current_friction or (pure_theme in FRICTION_THEME_KEYS and rating_excluded)

        if is_current_friction:
            current_friction_list.append(r)
            
        if is_previous_friction:
            previous_friction_list.append(r)
            if not is_current_friction:
                # This was removed from friction due to the rating exclusion filter!
                removed_list.append((r, pure_theme, rating_excluded))

    print(f"Computed Previous Friction Count: {len(previous_friction_list)}")
    print(f"Computed Current Friction Count: {len(current_friction_list)}")
    print(f"Difference (Removed records to analyze): {len(removed_list)}")

    # Categorize the removed records into:
    # A. Positive review — correctly removed (rating >= 4, review is positive)
    # B. Unrelated — correctly removed (rating < 4 or null, but text is general app/delivery/payment complaint with no fashion context)
    # C. Genuine friction — incorrectly removed (rating = null, but text describes actual fashion friction)
    # D. Ambiguous — requires review (rating = null or other, borderline comments)
    
    categories = {
        "A": [], # Positive review — correctly removed
        "B": [], # Unrelated — correctly removed
        "C": [], # Genuine friction — incorrectly removed
        "D": []  # Ambiguous
    }

    # Help detect if text is positive/app feedback/general
    def categorize_text(text, platform, rating):
        t_lower = text.lower()
        
        # Parse rating
        rating_val = None
        if rating is not None:
            try:
                rating_val = float(rating)
            except:
                pass

        # Case A: Positive review (Rating >= 4)
        if rating_val is not None and rating_val >= 4.0:
            return "A", "Rating >= 4 (Positive Review)"

        # Case B: Unrelated App feedback (complaints about bugs, logins, payments, slow customer service, returns of generic items without details)
        # Check if text describes a general app or customer service bug with no fashion/product detail:
        general_app_patterns = [
            "refund", "payment", "bank", "account", "customer care", "customer service", 
            "cheat", "scam", "worst service", "money", "failed", "cash", "transaction",
            "app crash", "server", "update", "notification", "otp", "login", "register",
            "delivery boy", "agent", "executive", "behavior", "attitude", "fraud"
        ]
        
        # Check if it has fashion/product detail keywords
        has_fashion_context = any(w in t_lower for w in [
            "fit", "size", "sizing", "fabric", "material", "quality", "cloth", "dress",
            "color", "colour", "photo", "reality", "look", "cotton", "wear", "tight", "loose",
            "design", "saree", "kurti", "brand", "product", "shoes"
        ])
        
        if not has_fashion_context:
            return "B", "Unrelated app/service feedback (no fashion context)"

        # Case C: Genuine friction (Rating is null or low, but describes clear product quality/fit/photo discrepancy)
        # E.g. "size chart is wrong", "fabric is bad", "different color sent", "fitting is bad"
        fashion_friction_patterns = [
            "tight", "loose", "chart", "fit", "sizing", "fabric", "material", "quality", 
            "photo", "reality", "different", "colour", "color", "wrong", "mismatch", "defect",
            "scratch", "torn", "damage", "authenticity", "fake", "duplicate", "copy"
        ]
        
        if any(p in t_lower for p in fashion_friction_patterns):
            if rating is None and platform in ["playstore", "appstore"]:
                return "C", "Genuine friction with rating=None (incorrectly removed under null rule)"
            else:
                return "C", f"Genuine friction with low rating (rating={rating})"

        # Default to Ambiguous/Borderline
        return "D", "Ambiguous/Borderline content"

    for r, pure_theme, rating_excluded in removed_list:
        text = r.get("text", "")
        platform = r.get("platform", "unknown")
        rating = r.get("rating")
        
        cat, reason = categorize_text(text, platform, rating)
        categories[cat].append({
            "record": r,
            "pure_theme": pure_theme,
            "rating_excluded": rating_excluded,
            "reason": reason
        })

    print(f"\nCategorization breakdown:")
    print(f"  A. Positive review — correctly removed: {len(categories['A'])}")
    print(f"  B. Unrelated — correctly removed: {len(categories['B'])}")
    print(f"  C. Genuine friction — incorrectly removed: {len(categories['C'])}")
    print(f"  D. Ambiguous — requires review: {len(categories['D'])}")

    # We will display exactly 30 examples of the potentially recoverable records (Category C)
    # Or D if C has fewer than 30.
    recoverable_examples = categories["C"] + categories["D"]
    
    print("\n" + "=" * 100)
    print("30 EXAMPLES OF POTENTIALLY RECOVERABLE GENUINE FRICTION (RATING = NULL OR BORDERLINE)")
    print("=" * 100)
    
    count = 0
    for idx, ex in enumerate(recoverable_examples[:30]):
        r = ex["record"]
        pure_theme = ex["pure_theme"]
        reason = ex["reason"]
        
        text = r.get("text", "").replace("\n", " ").strip()
        rating = r.get("rating")
        platform = r.get("platform", "")
        
        # Truncate text for table readability
        trunc_text = text if len(text) <= 150 else text[:147] + "..."
        
        print(f"Example #{idx+1}:")
        print(f"  Review Text : {trunc_text}")
        print(f"  Rating      : {rating} ({platform.upper()})")
        print(f"  Current Class: Out-of-Scope / Noise (unrelated_other)")
        print(f"  Why Genuine : {reason}")
        print(f"  Proposed Thm: {pure_theme} ({CANONICAL_THEMES.get(pure_theme, pure_theme)})")
        print("-" * 100)
        count += 1

    # Totals
    # X = Correctly removed (A + B)
    # Y = Potentially recoverable genuine friction (C)
    # Z = Ambiguous (D)
    x = len(categories["A"]) + len(categories["B"])
    y = len(categories["C"])
    z = len(categories["D"])
    
    print("\nSUMMARY STATS:")
    print(f"Previous friction: {len(previous_friction_list)}")
    print(f"Current friction: {len(current_friction_list)}")
    print(f"Correctly removed: {x}")
    print(f"Potentially recoverable genuine friction: {y}")
    print(f"Ambiguous: {z}")
    print(f"Potential final friction = 57 + {y} = {57 + y}")
    print("=" * 100)

if __name__ == "__main__":
    analyze_friction_drop()
