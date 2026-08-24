import os
import sys
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), '.env'))

from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

# Count where is_processed is True
c_true = supabase.table("raw_feedback").select("id", count="exact", head=True).eq("is_processed", True).execute().count
print(f"is_processed == True: {c_true}")

# Count where is_processed is False or null
c_false = supabase.table("raw_feedback").select("id", count="exact", head=True).eq("is_processed", False).execute().count
print(f"is_processed == False: {c_false}")

c_null = supabase.table("raw_feedback").select("id", count="exact", head=True).is_("is_processed", "null").execute().count
print(f"is_processed is null: {c_null}")

# Check theme distribution for is_processed == True
from collections import Counter
all_p = []
offset = 0
while True:
    r = supabase.table("raw_feedback").select("theme, is_processed").range(offset, offset + 999).execute()
    data = r.data or []
    all_p.extend(data)
    if len(data) < 1000:
        break
    offset += 1000

print(f"Total fetched: {len(all_p)}")
print(f"is_processed values: {Counter([x.get('is_processed') for x in all_p])}")
print(f"Themes for is_processed=True: {Counter([x.get('theme') for x in all_p if x.get('is_processed') is True])}")
print(f"Themes for all: {Counter([x.get('theme') for x in all_p])}")
