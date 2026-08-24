import os
import sys
import json
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), '.env'))

from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

insights_res = supabase.table("insights").select("*").execute()

for row in insights_res.data:
    theme = row['theme']
    label = row['theme_label']
    count = row['mention_count']
    pct = row['pct_of_total']
    quotes = row.get('sample_quotes') or []
    
    print(f"\n=======================================================")
    print(f"THEME: {label} ({theme}) | Mentions: {count} | Pct: {pct}%")
    print(f"=======================================================")
    for idx, q in enumerate(quotes):
        print(f"  [{idx+1}] \"{q}\"")

