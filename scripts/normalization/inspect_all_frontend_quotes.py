import os
import sys
import json
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), '.env'))

from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

insights_res = supabase.table("insights").select("theme, theme_label, sample_quotes").execute()

print("=== VISIBLE SAMPLE QUOTES IN INSIGHTS TABLE ===")
for r in insights_res.data:
    t = r['theme']
    l = r['theme_label']
    quotes = r.get('sample_quotes') or []
    print(f"\n--- {l} ({t}) --- [{len(quotes)} quotes]")
    for idx, q in enumerate(quotes):
        print(f"  {idx+1}. \"{q}\"")

# Check /api/verbatims initial 6 quotes
verb_res = supabase.table("raw_feedback").select("text, platform, theme").eq("is_processed", True).limit(6).execute()
print("\n=== TOP 6 QUOTES SERVED TO DASHBOARD CARDS (/api/verbatims) ===")
for idx, v in enumerate(verb_res.data):
    print(f"  {idx+1}. [{v['platform']} | {v['theme']}]: \"{v['text']}\"")
