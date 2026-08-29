import os
from dotenv import load_dotenv
load_dotenv(r'c:\Users\shrut\Downloads\M\.env')
from supabase import create_client

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))

res = supabase.table('insights').select('theme, mention_count').execute()
for r in res.data:
    print(f"{r['theme']}: {r['mention_count']}")
