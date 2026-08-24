import os
import sys
import json
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), '.env'))

from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

print("=== RAW FEEDBACK TOTAL COUNTS ===")
raw_total = supabase.table("raw_feedback").select("id", count="exact", head=True).execute().count
print(f"Total raw_feedback rows: {raw_total}")

for plat in ['playstore', 'appstore', 'reddit', 'youtube']:
    c = supabase.table("raw_feedback").select("id", count="exact", head=True).eq("platform", plat).execute().count
    print(f"  Platform {plat}: {c}")

proc_true = supabase.table("raw_feedback").select("id", count="exact", head=True).eq("is_processed", True).execute().count
proc_false = supabase.table("raw_feedback").select("id", count="exact", head=True).eq("is_processed", False).execute().count
print(f"is_processed=True: {proc_true}")
print(f"is_processed=False: {proc_false}")

print("\n=== CLASSIFICATION METHODS IN RAW_FEEDBACK ===")
methods = ["llm", "heuristic_fallback", "nlp_heuristics", "null"]
for m in ["llm", "heuristic_fallback"]:
    c = supabase.table("raw_feedback").select("id", count="exact", head=True).eq("classification_method", m).execute().count
    print(f"  Method {m}: {c}")
null_c = supabase.table("raw_feedback").select("id", count="exact", head=True).is_("classification_method", "null").execute().count
print(f"  Method null: {null_c}")

print("\n=== THEMES IN RAW_FEEDBACK (ALL ROWS) ===")
# Fetch all themes from raw_feedback
all_raw = []
offset = 0
while True:
    res = supabase.table("raw_feedback").select("id, platform, theme, rating, classification_method, is_processed, text").range(offset, offset + 999).execute()
    data = res.data or []
    all_raw.extend(data)
    if len(data) < 1000:
        break
    offset += 1000

from collections import Counter
theme_counts = Counter([r.get("theme") for r in all_raw])
print("All rows theme breakdown:")
for t, cnt in theme_counts.most_common():
    print(f"  {t}: {cnt}")

proc_raw = [r for r in all_raw if r.get("is_processed") is True]
proc_theme_counts = Counter([r.get("theme") for r in proc_raw])
print("\nis_processed=True theme breakdown:")
for t, cnt in proc_theme_counts.most_common():
    print(f"  {t}: {cnt}")

print("\nRating breakdown for all raw:")
rating_counts = Counter([r.get("rating") for r in all_raw])
for r, cnt in sorted(rating_counts.items(), key=lambda x: str(x[0])):
    print(f"  Rating {r}: {cnt}")

print("\n=== INSIGHTS TABLE ===")
insights_res = supabase.table("insights").select("*").execute()
for row in insights_res.data:
    print(json.dumps(row, indent=2, default=str))

