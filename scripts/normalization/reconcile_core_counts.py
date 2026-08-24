import os
import sys
import json
from collections import Counter
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), '.env'))

from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

# Fetch all records from raw_feedback
all_records = []
offset = 0
while True:
    res = supabase.table("raw_feedback").select("id, platform, theme, rating, classification_method, is_processed, text, external_id").range(offset, offset + 999).execute()
    data = res.data or []
    all_records.extend(data)
    if len(data) < 1000:
        break
    offset += 1000

total_conv = len(all_records)
print(f"A. Total Conversations: {total_conv}")

# Platform distribution
plat_counts = Counter([r['platform'] for r in all_records])
print("\nE. Source Distribution:")
for p in ['playstore', 'appstore', 'youtube', 'reddit']:
    c = plat_counts.get(p, 0)
    pct = round(c / total_conv * 100, 2)
    print(f"   - {p}: {c} ({pct}%)")

# Theme counts (pure theme classification without ad-hoc rating filter)
theme_counts_pure = Counter([r.get('theme') for r in all_records])
friction_themes = [
    "fit_sizing_anxiety",
    "fabric_quality_ambiguity",
    "visual_reality_discrepancy",
    "occasion_timing_delay",
    "styling_pairing_doubt",
    "choice_paralysis_shortlist",
    "social_validation_delay"
]

total_friction_pure = sum(theme_counts_pure.get(t, 0) for t in friction_themes)
total_noise_pure = theme_counts_pure.get("unrelated_other", 0) + theme_counts_pure.get(None, 0)

print(f"\nB. Total Friction Signals (Pure Theme): {total_friction_pure}")
print(f"C. Total Noise (Pure Theme): {total_noise_pure}")
print(f"D. Friction Rate: {round(total_friction_pure / total_conv * 100, 2)}%")
print(f"   Reconciliation Check: {total_friction_pure} + {total_noise_pure} = {total_friction_pure + total_noise_pure} (Total = {total_conv}) -> {'MATCH' if total_friction_pure + total_noise_pure == total_conv else 'MISMATCH'}")

print("\nF. Friction Theme Distribution (Pure Theme):")
for t in friction_themes:
    c = theme_counts_pure.get(t, 0)
    pct = round(c / total_friction_pure * 100, 2) if total_friction_pure else 0
    print(f"   - {t}: {c} ({pct}% of friction, {round(c / total_conv * 100, 2)}% of total)")

# Now check with rating >= 4 filter (the legacy /api/insights logic)
friction_with_rating_filter = 0
noise_with_rating_filter = 0
theme_counts_with_rating_filter = Counter()

for r in all_records:
    t = r.get('theme')
    rating = r.get('rating')
    if not t or t == 'unrelated_other' or (rating is not None and rating >= 4):
        noise_with_rating_filter += 1
    else:
        friction_with_rating_filter += 1
        theme_counts_with_rating_filter[t] += 1

print(f"\n--- COMPARISON WITH RATING >= 4 FILTER ---")
print(f"Friction Signals (with rating filter): {friction_with_rating_filter}")
print(f"Noise (with rating filter): {noise_with_rating_filter}")
for t in friction_themes:
    c = theme_counts_with_rating_filter.get(t, 0)
    pct = round(c / friction_with_rating_filter * 100, 2) if friction_with_rating_filter else 0
    print(f"   - {t}: {c} ({pct}%)")

