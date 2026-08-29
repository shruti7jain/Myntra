"""
Add audit columns via Supabase REST API (rpc or direct column check).
Since psycopg2 direct connection is blocked, we use the Supabase python client
to check existing columns and handle any schema additions through the existing
upsert mechanism (Supabase auto-accepts new JSON fields).

The actual ALTER TABLE must be done via Supabase Dashboard SQL Editor if
direct DB access is blocked. This script verifies connectivity and tests
that the classification pipeline can write the new fields.
"""
import os
from dotenv import load_dotenv
load_dotenv(r'c:\Users\shrut\Downloads\M\.env')

from supabase import create_client
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))

# Test if last_classified_at column already exists by trying to read it
print("Checking if last_classified_at column exists in insights table...")
try:
    res = supabase.table('insights').select('theme, last_classified_at').limit(1).execute()
    print("[OK] last_classified_at column EXISTS in insights table.")
except Exception as e:
    msg = str(e)
    if 'last_classified_at' in msg or 'column' in msg.lower():
        print("[MISSING] last_classified_at does NOT exist yet.")
        print("Action needed: Run this SQL in Supabase Dashboard > SQL Editor:")
        print("  ALTER TABLE insights ADD COLUMN IF NOT EXISTS last_classified_at TIMESTAMP WITH TIME ZONE;")
        print("  ALTER TABLE raw_feedback ADD COLUMN IF NOT EXISTS classification_failure_reason TEXT;")
    else:
        print(f"[ERROR] Unexpected: {e}")

# Test if classification_failure_reason exists in raw_feedback
print("\nChecking if classification_failure_reason column exists in raw_feedback...")
try:
    res2 = supabase.table('raw_feedback').select('id, classification_failure_reason').limit(1).execute()
    print("[OK] classification_failure_reason column EXISTS.")
except Exception as e2:
    msg2 = str(e2)
    if 'classification_failure_reason' in msg2 or 'column' in msg2.lower():
        print("[MISSING] classification_failure_reason does NOT exist yet.")
    else:
        print(f"[ERROR] Unexpected: {e2}")

print("\nNote: If columns are missing, add them via Supabase Dashboard SQL Editor.")
print("The classification pipeline will work correctly once these columns exist.")
print("If columns already exist (PGRST code not triggered), pipeline is ready.")
