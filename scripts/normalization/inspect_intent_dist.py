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

insights_res = supabase.table("insights").select("*").execute()

total_intents = Counter()
for row in insights_res.data:
    ib = row.get("intent_breakdown") or {}
    for k, v in ib.items():
        total_intents[k] += v

print("=== INTENT COUNTS FROM INSIGHTS TABLE ===")
for k, v in total_intents.most_common():
    print(f"  {k}: {v}")

# Non-noise intents
non_noise_intents = {k: v for k, v in total_intents.items() if k not in ['noise', 'no_clear_intent']}
total_non_noise = sum(non_noise_intents.values())
print(f"\nTotal non-noise intent signals: {total_non_noise}")
for k, v in non_noise_intents.items():
    pct = round(v / total_non_noise * 100, 1)
    print(f"  {k}: {v} ({pct}%)")

