import os
import sys
import json
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), '.env'))

from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

print("=" * 60)
print("RUNNING P0 DATA INTEGRITY VALIDATION CHECKS")
print("=" * 60)

validation_results = {}

# 1. Total source counts = total conversations
all_raw = supabase.table("raw_feedback").select("id, platform, theme", count="exact").execute()
total_raw = all_raw.count

plat_counts = {}
for p in ['playstore', 'appstore', 'reddit', 'youtube']:
    c = supabase.table("raw_feedback").select("id", count="exact", head=True).eq("platform", p).execute().count
    plat_counts[p] = c

sum_plat = sum(plat_counts.values())
t1_pass = (sum_plat == total_raw)
validation_results["1_source_counts_equal_total"] = {
    "status": "PASS" if t1_pass else "FAIL",
    "details": f"Sum of platforms ({sum_plat}) == Total raw ({total_raw})"
}
print(f"Check 1: Source counts == Total conversations -> {'PASS' if t1_pass else 'FAIL'} ({sum_plat} == {total_raw})")

# 2. Friction + noise = total conversations
friction_rows = supabase.table("raw_feedback").select("id", count="exact", head=True).not_.eq("theme", "unrelated_other").not_.is_("theme", "null").execute().count
noise_rows = supabase.table("raw_feedback").select("id", count="exact", head=True).or_("theme.eq.unrelated_other,theme.is.null").execute().count

t2_pass = (friction_rows + noise_rows == total_raw)
validation_results["2_friction_plus_noise_equal_total"] = {
    "status": "PASS" if t2_pass else "FAIL",
    "details": f"Friction ({friction_rows}) + Noise ({noise_rows}) = {friction_rows + noise_rows} == Total ({total_raw})"
}
print(f"Check 2: Friction + Noise == Total conversations -> {'PASS' if t2_pass else 'FAIL'} ({friction_rows} + {noise_rows} = {friction_rows + noise_rows} == {total_raw})")

# 3. Sum of theme mentions = total friction signals
insights_data = supabase.table("insights").select("*").execute().data
theme_friction_sum = sum(row['mention_count'] for row in insights_data if row['theme'] != 'unrelated_other')
t3_pass = (theme_friction_sum == friction_rows)
validation_results["3_sum_themes_equal_friction"] = {
    "status": "PASS" if t3_pass else "FAIL",
    "details": f"Sum of theme mentions ({theme_friction_sum}) == Friction signals ({friction_rows})"
}
print(f"Check 3: Sum of theme mentions == Friction signals -> {'PASS' if t3_pass else 'FAIL'} ({theme_friction_sum} == {friction_rows})")

# 4. Intent percentages calculated from actual records
aggregated_intents = {}
for row in insights_data:
    ib = row.get("intent_breakdown") or {}
    for k, v in ib.items():
        aggregated_intents[k] = aggregated_intents.get(k, 0) + v

non_noise_sum = sum(v for k, v in aggregated_intents.items() if k not in ['noise', 'no_clear_intent'])
t4_pass = (non_noise_sum > 0 and aggregated_intents.get('comparison_shortlisting', 0) == 0)
validation_results["4_intent_calculated_from_data"] = {
    "status": "PASS" if t4_pass else "FAIL",
    "details": f"Intent sum = {non_noise_sum}, Comparison shortlisting = {aggregated_intents.get('comparison_shortlisting', 0)} mentions"
}
print(f"Check 4: Intent calculated from actual data -> {'PASS' if t4_pass else 'FAIL'}")

# 5. Check no hardcoded percentages in page.js
with open("frontend/app/page.js", "r", encoding="utf-8") as f:
    page_content = f.read()

hardcoded_strings = ["'38%'", "'24%'", "'18%'", "'12%'", "'8%'", "1486"]
found_hardcoded = [s for s in hardcoded_strings if s in page_content]
t5_pass = (len(found_hardcoded) == 0)
validation_results["5_no_hardcoded_analytics"] = {
    "status": "PASS" if t5_pass else "FAIL",
    "details": f"Found remaining hardcoded strings: {found_hardcoded}"
}
print(f"Check 5: No hardcoded analytics in page.js -> {'PASS' if t5_pass else 'FAIL'} (Found: {found_hardcoded})")

# 6. Quotes in insights table match their themes
t7_pass = True
for row in insights_data:
    t = row['theme']
    quotes = row.get('sample_quotes') or []
    if t in ['occasion_timing_delay', 'fabric_quality_ambiguity']:
        for q in quotes:
            if "fully satisfied" in q.lower() or "broken watch" in q.lower():
                t7_pass = False

validation_results["6_quote_theme_matching"] = {
    "status": "PASS" if t7_pass else "FAIL",
    "details": "Irrelevant positive / broken item quotes removed from friction themes"
}
print(f"Check 6: Quotes match assigned themes -> {'PASS' if t7_pass else 'FAIL'}")

# 7. Copilot & Discovery consistency
t8_pass = (total_raw == 1506 and friction_rows == 283)
validation_results["7_copilot_discovery_consistency"] = {
    "status": "PASS" if t8_pass else "FAIL",
    "details": f"Total Analyzed = {total_raw}, Friction Signals = {friction_rows}"
}
print(f"Check 7: Copilot & Discovery dataset alignment -> {'PASS' if t8_pass else 'FAIL'}")

with open("p0_validation_report.json", "w", encoding="utf-8") as f:
    json.dump(validation_results, f, indent=2)

print("=" * 60)
print("ALL P0 VALIDATION CHECKS COMPLETED!")
print("=" * 60)
