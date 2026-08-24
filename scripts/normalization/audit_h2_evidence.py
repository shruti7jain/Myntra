import os
import sys
import json
import re
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), '.env'))

from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

all_raw = []
offset = 0
while True:
    res = supabase.table("raw_feedback").select("id, platform, text, theme, keyword_matched").range(offset, offset + 999).execute()
    data = res.data or []
    all_raw.extend(data)
    if len(data) < 1000:
        break
    offset += 1000

print(f"Loaded {len(all_raw)} records.")

# Check platform sources
from collections import Counter
print("\nPlatform distribution:")
plat_c = Counter([r['platform'] for r in all_raw])
for p, c in plat_c.items():
    print(f"  {p}: {c} ({round(c/len(all_raw)*100, 2)}%)")

# Search for external platform mentions in text
keywords = [
    'reddit', 'youtube', 'yt', 'instagram', 'insta', 'whatsapp', 'google', 
    'unboxing', 'haul', 'influencer', 'external', 'friend', 'friends', 
    'sister', 'mother', 'mom', 'asked', 'opinion', 'poll', 'story'
]

matches = {kw: [] for kw in keywords}
for r in all_raw:
    text_lower = r['text'].lower()
    for kw in keywords:
        # word boundary match
        if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
            matches[kw].append(r)

print("\nKeywords found in text:")
for kw, rows in matches.items():
    print(f"  '{kw}': {len(rows)} mentions")

print("\n--- SAMPLE MATCHES FOR EXTERNAL RESEARCH ---")
for kw in ['reddit', 'youtube', 'instagram', 'unboxing', 'haul', 'whatsapp', 'friend', 'friends']:
    if matches[kw]:
        print(f"\nMatches for '{kw}':")
        for r in matches[kw][:3]:
            print(f"  [ID {r['id']} | {r['platform']} | Theme: {r['theme']}]: {r['text']}")

# Check Reddit records specifically (only 5 records in entire DB!)
reddit_records = [r for r in all_raw if r['platform'] == 'reddit']
print(f"\n--- ALL REDDIT RECORDS ({len(reddit_records)}) ---")
for r in reddit_records:
    print(f"  ID {r['id']} | Theme: {r['theme']} | Text: {r['text']}")

# Check YouTube records specifically (only 8 records in entire DB!)
yt_records = [r for r in all_raw if r['platform'] == 'youtube']
print(f"\n--- ALL YOUTUBE RECORDS ({len(yt_records)}) ---")
for r in yt_records:
    print(f"  ID {r['id']} | Theme: {r['theme']} | Text: {r['text']}")
