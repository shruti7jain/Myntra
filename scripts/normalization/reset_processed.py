import os
import sys
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), '.env'))

from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

print("Resetting is_processed flags to False...")

# Fetch all ids
all_p = []
offset = 0
while True:
    r = supabase.table("raw_feedback").select("id").range(offset, offset + 999).execute()
    data = r.data or []
    all_p.extend(data)
    if len(data) < 1000:
        break
    offset += 1000

print(f"Updating {len(all_p)} rows...")

# Bulk update in chunks
for i in range(0, len(all_p), 1000):
    chunk = all_p[i:i+1000]
    ids = [item['id'] for item in chunk]
    supabase.table("raw_feedback").update({"is_processed": False, "theme": None}).in_("id", ids).execute()
    print(f"Updated chunk {i} to {i+len(chunk)}")

print("Done resetting!")
