import os
import sys

# Add the scripts/ingestion directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ingestion'))

from ingestion.ingest_playstore import fetch_playstore_reviews
from ingestion.ingest_reddit import fetch_reddit_discussions
from ingestion.ingest_appstore import fetch_appstore_reviews
from ingestion.ingest_youtube import fetch_youtube_comments
from ingestion.common import get_supabase_client


def run_pipeline():
    print("=" * 70)
    print("MYNTRA DISCOVERY ENGINE - MULTI-SOURCE INGESTION RUNNER (4 SOURCES)")
    print("=" * 70)

    # 1. Google Play Store
    ps_count = fetch_playstore_reviews()
    print()

    # 2. Reddit via Apify (real posts + comments)
    rd_count = fetch_reddit_discussions()
    print()

    # 3. Apple App Store
    as_count = fetch_appstore_reviews()
    print()

    # 4. YouTube Comments
    yt_count = fetch_youtube_comments()
    print()

    # 5. Summary from Supabase
    supabase = get_supabase_client()
    total_res = supabase.table("raw_feedback").select("id", count="exact").execute()
    total_in_db = total_res.count or 0

    ps_res = supabase.table("raw_feedback").select("id", count="exact").eq("platform", "playstore").execute()
    rd_res = supabase.table("raw_feedback").select("id", count="exact").eq("platform", "reddit").execute()
    as_res = supabase.table("raw_feedback").select("id", count="exact").eq("platform", "appstore").execute()
    yt_res = supabase.table("raw_feedback").select("id", count="exact").eq("platform", "youtube").execute()

    print("=" * 70)
    print("INGESTION SUMMARY & SUPABASE VERIFICATION (ALL 4 SOURCES)")
    print("=" * 70)
    print(f"Total Rows in `raw_feedback`: {total_in_db:,}")
    print(f"  • Google Play Store : {ps_res.count or 0:,} reviews")
    print(f"  • Reddit            : {rd_res.count or 0:,} posts/comments (REAL Reddit data)")
    print(f"  • Apple App Store   : {as_res.count or 0:,} reviews")
    print(f"  • YouTube Comments  : {yt_res.count or 0:,} comments")
    print("=" * 70)
    print("All 4 source ingestion connectors executed.")
    print("Run scripts/normalization/process_insights.py to classify and tag all records.")
    print()


if __name__ == "__main__":
    run_pipeline()
