import os
import sys
import json
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), '.env'))

from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

all_raw = []
offset = 0
while True:
    res = supabase.table("raw_feedback").select("id, platform, theme, rating, classification_method, is_processed, text").range(offset, offset + 999).execute()
    data = res.data or []
    all_raw.extend(data)
    if len(data) < 1000:
        break
    offset += 1000

print(f"Total records in raw_feedback: {len(all_raw)}")

# Simulate /api/insights/route.js
total_friction_count = 0
noise_count = 0
theme_counts = {}
excluded_by_rating = []

for row in all_raw:
    theme = row.get("theme")
    rating = row.get("rating")
    
    if not theme or theme == "unrelated_other" or (rating is not None and rating >= 4):
        noise_count += 1
        if theme and theme != "unrelated_other" and rating is not None and rating >= 4:
            excluded_by_rating.append(row)
    else:
        total_friction_count += 1
        theme_counts[theme] = theme_counts.get(theme, 0) + 1

print(f"\nLive API calculation simulation:")
print(f"Total analyzed: {len(all_raw)}")
print(f"Total friction count: {total_friction_count}")
print(f"Noise count: {noise_count}")
print(f"Friction themes counted in API:")
for t, c in sorted(theme_counts.items(), key=lambda x: -x[1]):
    pct = round((c / total_friction_count) * 100)
    print(f"  {t}: count={c}, pct={pct}% ({c}/{total_friction_count})")

print(f"\nFriction records excluded ONLY because rating >= 4: {len(excluded_by_rating)}")
for r in excluded_by_rating[:5]:
    print(f"  ID {r['id']}, Rating={r['rating']}, Theme={r['theme']}: {r['text'][:80]}...")
