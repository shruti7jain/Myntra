"""
Add new audit columns to the Supabase database:
  - insights.last_classified_at  : timestamp of last process_insights.py run
  - raw_feedback.classification_failure_reason : why LLM failed per record (if applicable)
"""
import os, sys
import psycopg2
from dotenv import load_dotenv

load_dotenv(r'c:\Users\shrut\Downloads\M\.env')

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("[ERROR] DATABASE_URL not set")
    sys.exit(1)

SQL = """
ALTER TABLE insights
    ADD COLUMN IF NOT EXISTS last_classified_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE raw_feedback
    ADD COLUMN IF NOT EXISTS classification_failure_reason TEXT;
"""

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(SQL)
    conn.commit()
    cur.close()
    conn.close()
    print("[OK] Database columns added successfully.")
    print("  - insights.last_classified_at")
    print("  - raw_feedback.classification_failure_reason")
except Exception as e:
    print(f"[ERROR] {e}")
    sys.exit(1)
