import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), '.env'))
from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

print("Fetching from insights table...")
insights_res = supabase.table("insights").select("*").execute()
for r in insights_res.data:
    print(f"Theme: {r['theme']}, Count: {r['mention_count']}, Pct: {r['pct_of_total']}")
