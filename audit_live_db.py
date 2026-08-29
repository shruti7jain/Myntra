import os
import sys
from dotenv import load_dotenv
from collections import Counter

load_dotenv(r'c:\Users\shrut\Downloads\M\.env')

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print('ERROR: Missing credentials')
    sys.exit(1)

from supabase import create_client
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

print("=" * 70)
print("LIVE DATABASE AUDIT - raw_feedback table")
print("=" * 70)

total = supabase.table('raw_feedback').select('id', count='exact', head=True).execute().count
print(f"TOTAL raw_feedback records: {total}")

print("\nPLATFORM BREAKDOWN:")
platform_sum = 0
for plat in ['playstore','appstore','reddit','youtube']:
    c = supabase.table('raw_feedback').select('id', count='exact', head=True).eq('platform', plat).execute().count
    print(f"  {plat}: {c}")
    platform_sum += (c or 0)
print(f"  platform_sum: {platform_sum}")

print("\nIS_PROCESSED BREAKDOWN:")
proc_t = supabase.table('raw_feedback').select('id', count='exact', head=True).eq('is_processed', True).execute().count
proc_f = supabase.table('raw_feedback').select('id', count='exact', head=True).eq('is_processed', False).execute().count
print(f"  is_processed=True:  {proc_t}")
print(f"  is_processed=False: {proc_f}")
print(f"  sum: {(proc_t or 0) + (proc_f or 0)}")

null_theme = supabase.table('raw_feedback').select('id', count='exact', head=True).is_('theme', 'null').execute().count
print(f"\ntheme=NULL (never classified): {null_theme}")

print("\nFetching all records for deep analysis...")
all_records = []
offset = 0
while True:
    res = supabase.table('raw_feedback').select(
        'id, platform, theme, rating, classification_method, is_processed, scraped_at, keyword_matched'
    ).range(offset, offset + 999).execute()
    data = res.data or []
    all_records.extend(data)
    if len(data) < 1000:
        break
    offset += 1000

print(f"Fetched {len(all_records)} records total")

print("\nTHEME DISTRIBUTION (all rows):")
theme_counts = Counter([r.get('theme') for r in all_records])
for theme, count in theme_counts.most_common():
    print(f"  {repr(theme)}: {count}")

print("\nCLASSIFICATION_METHOD DISTRIBUTION:")
method_counts = Counter([r.get('classification_method') for r in all_records])
for m, c in method_counts.most_common():
    print(f"  {repr(m)}: {c}")

FRICTION_THEMES = {
    'fit_sizing_anxiety',
    'fabric_quality_ambiguity',
    'visual_reality_discrepancy',
    'occasion_timing_delay',
    'styling_pairing_doubt',
    'choice_paralysis_shortlist',
    'social_validation_delay',
}
friction_pure = sum(1 for r in all_records if r.get('theme') in FRICTION_THEMES)
noise_pure = sum(1 for r in all_records if r.get('theme') == 'unrelated_other')
null_theme_count = sum(1 for r in all_records if r.get('theme') is None)
print(f"\nGOAL RELEVANCE (pure theme, no rating filter):")
print(f"  Goal-relevant (friction): {friction_pure}")
print(f"  Noise/out-of-scope:       {noise_pure}")
print(f"  theme=NULL:               {null_theme_count}")
print(f"  Sum check: {friction_pure + noise_pure + null_theme_count} == {len(all_records)}: {'MATCH' if friction_pure + noise_pure + null_theme_count == len(all_records) else 'MISMATCH'}")

# Cross-check is_processed=False breakdown by theme
unprocessed = [r for r in all_records if r.get('is_processed') is False]
unprocessed_null_theme = [r for r in unprocessed if r.get('theme') is None]
unprocessed_with_theme = [r for r in unprocessed if r.get('theme') is not None]
print(f"\nIS_PROCESSED=False breakdown:")
print(f"  Total unprocessed: {len(unprocessed)}")
print(f"  Unprocessed + theme=NULL: {len(unprocessed_null_theme)}")
print(f"  Unprocessed + theme SET:  {len(unprocessed_with_theme)}")
if unprocessed_with_theme:
    up_theme_counts = Counter([r.get('theme') for r in unprocessed_with_theme])
    for t, c in up_theme_counts.most_common():
        print(f"    {repr(t)}: {c}")

print("\n=== INSIGHTS TABLE (what API reads) ===")
insights = supabase.table('insights').select('*').execute().data or []
insights_friction = [r for r in insights if r.get('theme') in FRICTION_THEMES]
insights_noise = next((r for r in insights if r.get('theme') == 'unrelated_other'), None)
friction_from_insights = sum(int(r.get('mention_count') or 0) for r in insights_friction)
noise_from_insights = int(insights_noise.get('mention_count') or 0) if insights_noise else 0
print(f"  friction_count (insights table): {friction_from_insights}")
print(f"  noise_count (insights table):    {noise_from_insights}")
print(f"  insights_sum: {friction_from_insights + noise_from_insights}")
print(f"\nINSIGHTS rows (sorted by count):")
for r in sorted(insights, key=lambda x: -(x.get('mention_count') or 0)):
    print(f"  {r.get('theme')}: mention_count={r.get('mention_count')}, updated_at={str(r.get('updated_at'))[:19]}")

print(f"\nCROSS-CHECK SUMMARY:")
print(f"  total raw_feedback (API: total_raw_analyzed): {total}")
print(f"  platform_sum:                                 {platform_sum}")
print(f"  insights friction_count (API friction):       {friction_from_insights}")
print(f"  insights noise_count:                         {noise_from_insights}")
print(f"  insights total:                               {friction_from_insights + noise_from_insights}")
print(f"  GAP (raw - insights total):                   {(total or 0) - (friction_from_insights + noise_from_insights)}")
print(f"  GAP meaning: records in raw_feedback but NOT reflected in insights counts")

print(f"\nRATING FILTER SIMULATION:")
friction_with_filter = 0
noise_with_filter = 0
for r in all_records:
    theme = r.get('theme')
    rating = r.get('rating')
    if not theme or theme == 'unrelated_other' or (rating is not None and rating >= 4):
        noise_with_filter += 1
    else:
        friction_with_filter += 1
print(f"  With rating>=4 filter -> friction: {friction_with_filter}, noise: {noise_with_filter}")
print(f"  Without rating filter -> friction: {friction_pure}, noise: {noise_pure + null_theme_count}")
print(f"  Difference due to rating filter:   {friction_pure - friction_with_filter}")

print(f"\nKEYWORD_MATCHED distribution (top 10):")
kw_counts = Counter([r.get('keyword_matched') for r in all_records])
for kw, cnt in kw_counts.most_common(10):
    print(f"  {repr(kw)}: {cnt}")

print("\n" + "=" * 70)
print("AUDIT COMPLETE")
print("=" * 70)
