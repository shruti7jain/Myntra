import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ingest_playstore import fetch_playstore_reviews
from ingest_reddit import fetch_reddit_discussions
from ingest_appstore import fetch_appstore_reviews
from ingest_youtube import fetch_youtube_comments
from common import get_supabase_client

def run_pipeline():
    print("=" * 70)
    print("MYNTRA DISCOVERY ENGINE - MULTI-SOURCE INGESTION RUNNER (4 SOURCES)")
    print("=" * 70)

    # 1. Google Play Store
    ps_count = fetch_playstore_reviews()
    print()

    # 2. Reddit via Apify
    rd_count = fetch_reddit_discussions()
    print()

    # 3. Apple App Store
    as_count = fetch_appstore_reviews()
    print()

    # 4. YouTube Comments
    yt_count = fetch_youtube_comments()
    print()

    # 5. Verification from Supabase
    supabase = get_supabase_client()
    res = supabase.table("raw_feedback").select("id", count="exact").execute()
    total_in_db = res.count or 0

    playstore_res = supabase.table("raw_feedback").select("id", count="exact").eq("platform", "playstore").execute()
    reddit_res = supabase.table("raw_feedback").select("id", count="exact").eq("platform", "reddit").execute()
    appstore_res = supabase.table("raw_feedback").select("id", count="exact").eq("platform", "appstore").execute()
    youtube_res = supabase.table("raw_feedback").select("id", count="exact").eq("platform", "youtube").execute()

    print("=" * 70)
    print("INGESTION SUMMARY & SUPABASE VERIFICATION (ALL 4 SOURCES)")
    print("=" * 70)
    print(f"Total Rows in `raw_feedback`: {total_in_db}")
    print(f"  • Google Play Store: {playstore_res.count or 0} reviews")
    print(f"  • Reddit Discussions: {reddit_res.count or 0} posts/threads")
    print(f"  • Apple App Store:   {appstore_res.count or 0} reviews")
    print(f"  • YouTube Comments:  {youtube_res.count or 0} comments")
    print("=" * 70)
    print("All 4 Source Ingestion Connectors executed successfully!")

if __name__ == "__main__":
    run_pipeline()
