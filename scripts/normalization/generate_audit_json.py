import os
import sys
import json
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), '.env'))

from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

raw_total = supabase.table("raw_feedback").select("id", count="exact", head=True).execute().count

plat_counts = {}
for plat in ['playstore', 'appstore', 'reddit', 'youtube']:
    c = supabase.table("raw_feedback").select("id", count="exact", head=True).eq("platform", plat).execute().count
    plat_counts[plat] = c

proc_true = supabase.table("raw_feedback").select("id", count="exact", head=True).eq("is_processed", True).execute().count
proc_false = supabase.table("raw_feedback").select("id", count="exact", head=True).eq("is_processed", False).execute().count

all_raw = []
offset = 0
while True:
    res = supabase.table("raw_feedback").select("id, platform, theme, rating, classification_method, is_processed, text, external_id").range(offset, offset + 999).execute()
    data = res.data or []
    all_raw.extend(data)
    if len(data) < 1000:
        break
    offset += 1000

from collections import Counter
theme_counts_all = Counter([r.get("theme") for r in all_raw])
theme_counts_proc = Counter([r.get("theme") for r in all_raw if r.get("is_processed") is True])
method_counts = Counter([r.get("classification_method") for r in all_raw])

insights_res = supabase.table("insights").select("*").execute()

report = {
    "raw_total": raw_total,
    "plat_counts": plat_counts,
    "is_processed_true": proc_true,
    "is_processed_false": proc_false,
    "method_counts": dict(method_counts),
    "theme_counts_all": dict(theme_counts_all),
    "theme_counts_proc": dict(theme_counts_proc),
    "insights_table": insights_res.data
}

with open("audit_summary.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, default=str)

print("Wrote audit_summary.json successfully!")
