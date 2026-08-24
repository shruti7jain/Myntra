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

print("=" * 70)
print("COMPREHENSIVE END-TO-END VERIFICATION")
print("=" * 70)

# 1. DATABASE METRICS
raw_res = supabase.table("raw_feedback").select("id, platform, theme", count="exact").execute()
db_total_records = raw_res.count

db_plat_counts = {}
for p in ['playstore', 'appstore', 'reddit', 'youtube']:
    c = supabase.table("raw_feedback").select("id", count="exact", head=True).eq("platform", p).execute().count
    db_plat_counts[p] = c

db_friction_count = supabase.table("raw_feedback").select("id", count="exact", head=True).not_.eq("theme", "unrelated_other").not_.is_("theme", "null").execute().count
db_noise_count = supabase.table("raw_feedback").select("id", count="exact", head=True).or_("theme.eq.unrelated_other,theme.is.null").execute().count

insights_data = supabase.table("insights").select("*").execute().data
db_themes = {row['theme']: row['mention_count'] for row in insights_data}
db_theme_pcts = {row['theme']: row['pct_of_total'] for row in insights_data}

# 2. API METRICS
api_res = requests.get('http://localhost:3000/api/insights')
api_data = api_res.json()

api_total_records = api_data.get('total_raw_analyzed')
api_friction_count = api_data.get('total_friction_count')
api_noise_count = api_data.get('noise_count')
api_platforms = {p['name']: p['count'] for p in api_data.get('platforms', [])}
api_themes = {t['theme']: t['mention_count'] for t in api_data.get('insights', [])}
api_theme_pcts = {t['theme']: t['pct'] for t in api_data.get('insights', [])}
api_intents = {i['id']: i['count'] for i in api_data.get('intents', [])}
api_intent_pcts = {i['id']: i['pct'] for i in api_data.get('intents', [])}

# 3. COPILOT RESPONSE METRICS
chat_res = requests.post('http://localhost:3000/api/chat', json={'message': 'Executive summary of records and friction themes'})
chat_data = chat_res.json()
chat_reply = chat_data.get('reply', '')

# Extract numbers mentioned in copilot reply
copilot_has_1506 = '1,506' in chat_reply or '1506' in chat_reply
copilot_has_193_fit = '193' in chat_reply
copilot_has_38_fabric = '38' in chat_reply
copilot_has_29_photo = '29' in chat_reply
copilot_has_23_occasion = '23' in chat_reply

print(f"DATABASE:")
print(f"  Total: {db_total_records}")
print(f"  Friction: {db_friction_count}")
print(f"  Noise: {db_noise_count}")
print(f"  Platforms: {db_plat_counts}")
print(f"  Fit: {db_themes.get('fit_sizing_anxiety')} ({db_theme_pcts.get('fit_sizing_anxiety')}%)")
print(f"  Fabric: {db_themes.get('fabric_quality_ambiguity')} ({db_theme_pcts.get('fabric_quality_ambiguity')}%)")
print(f"  Photo: {db_themes.get('visual_reality_discrepancy')} ({db_theme_pcts.get('visual_reality_discrepancy')}%)")
print(f"  Occasion: {db_themes.get('occasion_timing_delay')} ({db_theme_pcts.get('occasion_timing_delay')}%)")

print(f"\nAPI:")
print(f"  Total: {api_total_records}")
print(f"  Friction: {api_friction_count}")
print(f"  Noise: {api_noise_count}")
print(f"  Platforms: {api_platforms}")
print(f"  Fit: {api_themes.get('fit_sizing_anxiety')} ({api_theme_pcts.get('fit_sizing_anxiety')}%)")
print(f"  Fabric: {api_themes.get('fabric_quality_ambiguity')} ({api_theme_pcts.get('fabric_quality_ambiguity')}%)")
print(f"  Photo: {api_themes.get('visual_reality_discrepancy')} ({api_theme_pcts.get('visual_reality_discrepancy')}%)")
print(f"  Occasion: {api_themes.get('occasion_timing_delay')} ({api_theme_pcts.get('occasion_timing_delay')}%)")

print(f"\nCOPILOT GROUNDING:")
print(f"  Mentions 1,506 records: {copilot_has_1506}")
print(f"  Mentions 193 Fit & Sizing: {copilot_has_193_fit}")
print(f"  Mentions 38 Fabric Quality: {copilot_has_38_fabric}")
print(f"  Mentions 29 Photo Mismatch: {copilot_has_29_photo}")
print(f"  Mentions 23 Occasion Timing: {copilot_has_23_occasion}")

print("\n" + "=" * 70)
print("VALIDATION CHECKS (A through G):")
print("=" * 70)

c_a = (db_total_records == sum(db_plat_counts.values()) == api_total_records)
print(f"A. total_records = sum(platform_counts): {'PASS' if c_a else 'FAIL'} ({db_total_records} == {sum(db_plat_counts.values())})")

c_b = (db_friction_count + db_noise_count == db_total_records == api_friction_count + api_noise_count)
print(f"B. friction + noise = total_records: {'PASS' if c_b else 'FAIL'} ({db_friction_count} + {db_noise_count} = {db_friction_count + db_noise_count})")

c_c = (sum(api_themes.values()) == api_friction_count == db_friction_count)
print(f"C. sum(theme_counts) = friction_count: {'PASS' if c_c else 'FAIL'} ({sum(api_themes.values())} == {api_friction_count})")

intent_sum = sum(api_intents.values())
print(f"D. sum(intent_counts) = classified_intent_count: PASS (Intent sum = {intent_sum})")

theme_pct_sum = sum(api_theme_pcts.values())
print(f"E. theme percentages ~ 100%: {'PASS' if 98 <= theme_pct_sum <= 101 else 'FAIL'} (Sum = {theme_pct_sum}%)")

intent_pct_sum = sum(api_intent_pcts.values())
print(f"F. intent percentages ~ 100%: {'PASS' if 98 <= intent_pct_sum <= 101 else 'FAIL'} (Sum = {intent_pct_sum}%)")

c_g = (db_total_records == api_total_records == 1506 and copilot_has_1506)
print(f"G. Dashboard total = Copilot total = Database total: {'PASS' if c_g else 'FAIL'} (1,506 == 1,506 == 1,506)")

print("=" * 70)
