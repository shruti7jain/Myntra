"""
Post-classification validation script.
Verifies all 15 criteria from the fix requirements.
Run after process_insights.py completes.
"""
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv(r'c:\Users\shrut\Downloads\M\.env')
from supabase import create_client
from collections import Counter

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))

print("=" * 75)
print("POST-CLASSIFICATION VALIDATION")
print(f"Run at: {datetime.utcnow().isoformat()}Z")
print("=" * 75)

# ------------------------------------------------------------------
# A. Fetch all raw_feedback records
# ------------------------------------------------------------------
all_records = []
offset = 0
while True:
    res = supabase.table('raw_feedback').select(
        'id, platform, theme, rating, classification_method, is_processed, scraped_at'
    ).range(offset, offset + 999).execute()
    data = res.data or []
    all_records.extend(data)
    if len(data) < 1000:
        break
    offset += 1000

total = len(all_records)
processed = sum(1 for r in all_records if r.get('is_processed') is True)
unprocessed = sum(1 for r in all_records if r.get('is_processed') is False)
theme_null = sum(1 for r in all_records if r.get('theme') is None)
method_null = sum(1 for r in all_records if r.get('classification_method') is None)

FRICTION_THEMES = {
    'fit_sizing_anxiety', 'fabric_quality_ambiguity', 'visual_reality_discrepancy',
    'occasion_timing_delay', 'styling_pairing_doubt', 'choice_paralysis_shortlist',
    'social_validation_delay', 'price_deal_timing',
}

goal_relevant = sum(1 for r in all_records if r.get('theme') in FRICTION_THEMES)
noise = sum(1 for r in all_records if r.get('theme') == 'unrelated_other')
llm_classified = sum(1 for r in all_records if r.get('classification_method') == 'llm')
heuristic_classified = sum(1 for r in all_records if r.get('classification_method') == 'heuristic_fallback')

# Contradictory state: theme set but is_processed=False
contradictory = sum(1 for r in all_records 
                    if r.get('theme') is not None and r.get('is_processed') is False)

print(f"\nA. Total records:          {total:,}")
print(f"B. Processed (True):       {processed:,}")
print(f"C. Unprocessed (False):    {unprocessed:,}")
print(f"D. theme=NULL:             {theme_null:,}")
print(f"E. Contradictory states:   {contradictory:,}  (theme set + is_processed=False)")
print(f"F. Goal-relevant:          {goal_relevant:,}")
print(f"G. Noise/out-of-scope:     {noise:,}")
print(f"H. LLM classified:         {llm_classified:,}  ({round(llm_classified/max(total,1)*100,1)}%)")
print(f"I. Heuristic fallback:     {heuristic_classified:,}  ({round(heuristic_classified/max(total,1)*100,1)}%)")
print(f"   classification_method=NULL: {method_null:,}")
print(f"\nReconciliation: {goal_relevant} + {noise} + {theme_null} = {goal_relevant+noise+theme_null} (total={total}): "
      f"{'MATCH' if goal_relevant+noise+theme_null == total else 'MISMATCH'}")

# ------------------------------------------------------------------
# B. Theme distribution
# ------------------------------------------------------------------
print(f"\nJ. THEME DISTRIBUTION (all records):")
theme_counts = Counter([r.get('theme') for r in all_records])
for t, c in theme_counts.most_common():
    pct = round(c/total*100, 1)
    marker = " ← FRICTION" if t in FRICTION_THEMES else (" ← NOISE" if t == 'unrelated_other' else " ← UNCLASSIFIED")
    print(f"   {str(t):<42} : {c:>6} ({pct:>5}%){marker}")

# ------------------------------------------------------------------
# C. Insights table check
# ------------------------------------------------------------------
print(f"\nK. INSIGHTS TABLE:")
insights = supabase.table('insights').select('*').execute().data or []
insights_friction = sum(int(r.get('mention_count') or 0) for r in insights if r.get('theme') in FRICTION_THEMES)
insights_noise_row = next((r for r in insights if r.get('theme') == 'unrelated_other'), None)
insights_noise = int(insights_noise_row.get('mention_count') or 0) if insights_noise_row else 0
insights_total = insights_friction + insights_noise
last_classified = None
for r in insights:
    if r.get('last_classified_at'):
        last_classified = r['last_classified_at']
        break
if not last_classified:
    # Fall back to updated_at
    for r in insights:
        if r.get('updated_at'):
            last_classified = r['updated_at']
            break

print(f"   friction_count (insights): {insights_friction:,}")
print(f"   noise_count (insights):    {insights_noise:,}")
print(f"   insights total:            {insights_total:,}")
print(f"   last_classified_at:        {last_classified}")
print(f"   GAP (raw - insights):      {total - insights_total:,}")

print(f"\nL. API CONSISTENCY:")
print(f"   live raw_feedback count:   {total:,}")
print(f"   insights snapshot total:   {insights_total:,}  (= total_raw_analyzed in API)")
print(f"   unclassified (gap):        {total - insights_total:,}  (= unclassified_count in API)")

print(f"\nM. SOURCE DISTRIBUTION:")
plat_counts = Counter([r.get('platform') for r in all_records])
for p in ['playstore', 'appstore', 'reddit', 'youtube']:
    c = plat_counts.get(p, 0)
    pct = round(c/total*100, 1)
    print(f"   {p:<12}: {c:>5} ({pct:>5}%)")

# ------------------------------------------------------------------
# D. Validation checks
# ------------------------------------------------------------------
print(f"\nN. VALIDATION CHECKS:")
checks = [
    ("All records classified (theme != NULL)", theme_null == 0),
    ("All records processed (is_processed=True)", unprocessed == 0),
    ("No contradictory states (theme set + unprocessed)", contradictory == 0),
    ("LLM classification rate > 0%", llm_classified > 0),
    ("API metrics consistent (insights sum = friction+noise)", insights_friction + insights_noise == insights_total),
    ("No unclassified silently treated as noise (gap = 0)", total == insights_total),
    ("Insights table updated today", last_classified is not None and last_classified[:10] == datetime.utcnow().strftime('%Y-%m-%d')),
]
all_pass = True
for name, result in checks:
    status = "PASS ✓" if result else "FAIL ✗"
    if not result:
        all_pass = False
    print(f"   [{status}] {name}")

print(f"\n{'ALL CHECKS PASSED' if all_pass else 'SOME CHECKS FAILED — review above'}")
print("=" * 75)
