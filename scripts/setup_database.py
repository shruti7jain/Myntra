import os
import sys
import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

SCHEMA_SQL = """
-- 1. Table for Raw Ingested Feedback
CREATE TABLE IF NOT EXISTS raw_feedback (
    id BIGSERIAL PRIMARY KEY,
    external_id TEXT UNIQUE NOT NULL,
    platform TEXT NOT NULL CHECK (platform IN ('playstore', 'reddit', 'appstore', 'youtube')),
    text TEXT NOT NULL,
    url TEXT,
    author TEXT,
    rating INT,
    keyword_matched TEXT,
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    is_processed BOOLEAN DEFAULT FALSE
);

-- Indexes for rapid deduplication and unprocessed batch fetching
CREATE INDEX IF NOT EXISTS idx_raw_feedback_external_id ON raw_feedback(external_id);
CREATE INDEX IF NOT EXISTS idx_raw_feedback_is_processed ON raw_feedback(is_processed);

-- 2. Table for Normalized PM Discovery Insights
CREATE TABLE IF NOT EXISTS insights (
    id BIGSERIAL PRIMARY KEY,
    theme TEXT UNIQUE NOT NULL,
    theme_label TEXT NOT NULL,
    mention_count INT DEFAULT 0 NOT NULL,
    pct_of_total NUMERIC(5, 2) DEFAULT 0.00 NOT NULL,
    sample_quotes TEXT[] DEFAULT '{}',
    segment_breakdown JSONB DEFAULT '{}'::jsonb,
    trend TEXT DEFAULT 'stable',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. Enable Row Level Security (RLS) & Public Read Access
ALTER TABLE insights ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'insights' AND policyname = 'Allow Public Read Access on Insights'
    ) THEN
        CREATE POLICY "Allow Public Read Access on Insights" ON insights FOR SELECT USING (true);
    END IF;
END
$$;
"""

def setup_database():
    print("=" * 60)
    print("MYNTRA DISCOVERY ENGINE - PHASE 2: DATABASE SETUP")
    print("=" * 60)

    if not DATABASE_URL:
        print("[ERROR] DATABASE_URL is not set in .env file.")
        print("Please ensure your postgres connection string is provided.")
        sys.exit(1)

    print(f"Connecting to Supabase PostgreSQL database...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        print("[OK] Connected to Supabase PostgreSQL successfully.")
        
        print("Applying Schema: Creating `raw_feedback` and `insights` tables...")
        cursor.execute(SCHEMA_SQL)
        conn.commit()
        
        # Verify tables exist
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name IN ('raw_feedback', 'insights');
        """)
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()

        print(f"[SUCCESS] Tables verified in Supabase: {', '.join(tables)}")
        print("Phase 2 Database Schema applied successfully!")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to apply schema via direct connection: {e}")
        print("\nFallback: You can copy and paste the SQL directly into the Supabase SQL Editor.")
        return False

if __name__ == "__main__":
    setup_database()
