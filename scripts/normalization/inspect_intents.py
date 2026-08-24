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

insights_res = supabase.table("insights").select("theme, theme_label, mention_count, intent_breakdown").execute()
print("=== INTENT BREAKDOWN IN INSIGHTS TABLE ===")
total_intents = Counter()
for row in insights_res.data:
    print(f"Theme: {row['theme']} ({row['theme_label']}) - Mentions: {row['mention_count']}")
    ib = row.get("intent_breakdown") or {}
    print(f"  Intent breakdown: {ib}")
    for k, v in ib.items():
        total_intents[k] += v

print("\nAggregate intent counts in insights table:")
for k, v in total_intents.items():
    print(f"  {k}: {v}")

total_intent_sum = sum(total_intents.values())
print(f"Total intent count sum: {total_intent_sum}")
if total_intent_sum > 0:
    for k, v in total_intents.items():
        print(f"  {k}: {v} ({round(v / total_intent_sum * 100, 2)}%)")
