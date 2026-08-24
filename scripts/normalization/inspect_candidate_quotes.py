import os
import sys
import json
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), '.env'))

from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

# Let's find real, high quality quotes for each theme in raw_feedback
themes = [
    "fit_sizing_anxiety",
    "fabric_quality_ambiguity",
    "visual_reality_discrepancy",
    "occasion_timing_delay"
]

for t in themes:
    print(f"\n=======================================================")
    print(f"THEME: {t}")
    print(f"=======================================================")
    res = supabase.table("raw_feedback").select("id, text, platform, rating").eq("theme", t).limit(10).execute()
    for r in res.data:
        print(f"  [ID {r['id']} | {r['platform']} | Rating {r['rating']}]: {r['text']}")
