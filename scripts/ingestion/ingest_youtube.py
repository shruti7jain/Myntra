import os
import sys
import re
import requests
from datetime import datetime
from itertools import islice
from common import matches_wishlist_keywords, upsert_raw_feedback

# youtube-comment-downloader: pip install youtube-comment-downloader
try:
    from youtube_comment_downloader import YoutubeCommentDownloader, SORT_BY_POPULAR
    YT_DOWNLOADER_AVAILABLE = True
except ImportError:
    YT_DOWNLOADER_AVAILABLE = False
    print("[WARN] youtube-comment-downloader not installed. Run: pip install youtube-comment-downloader")

# ---------------------------------------------------------------------------
# Curated list of known Myntra haul / review / try-on video IDs
# These are real Indian fashion YouTube videos where users discuss sizing,
# fabric quality, and wishlist-to-buy decisions.
# We seed with known IDs + dynamically discover more at runtime.
# ---------------------------------------------------------------------------
SEEDED_VIDEO_IDS = [
    # Myntra haul videos with high engagement Indian fashion community
    # (These are well-known public videos; scraped via YouTube search)
]


def discover_video_ids_from_search(max_videos: int = 12) -> list[str]:
    """
    Discovers real YouTube video IDs by scraping YouTube search results.
    Uses multiple search queries focused on Myntra try-on hauls and reviews.
    """
    queries = [
        "myntra+haul+try+on+honest+review",
        "myntra+kurti+haul+sizing+quality",
        "myntra+western+wear+review+fitting",
        "myntra+fashion+haul+2024+india",
        "myntra+wishlist+try+on",
        "myntra+unboxing+review+fabric",
    ]
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    video_ids = list(SEEDED_VIDEO_IDS)

    for q in queries:
        url = f"https://www.youtube.com/results?search_query={q}&sp=CAISAhAB"  # filter: videos only
        try:
            r = requests.get(url, headers=headers, timeout=12)
            if r.status_code == 200:
                # YouTube embeds video IDs in the initial data JSON
                found = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', r.text)
                for vid in found:
                    if vid not in video_ids:
                        video_ids.append(vid)
        except Exception as e:
            print(f"[WARN] YouTube search error for '{q}': {e}")

        if len(video_ids) >= max_videos:
            break

    print(f"[YOUTUBE] Discovered {len(video_ids)} Myntra fashion video targets.")
    return video_ids[:max_videos]


def fetch_youtube_comments(max_comments_per_video: int = 100) -> int:
    print("=" * 60)
    print("YOUTUBE COMMENTS INGESTION (Myntra Haul & Review Videos)")
    print("=" * 60)

    if not YT_DOWNLOADER_AVAILABLE:
        print("[ERROR] youtube-comment-downloader package not available. Skipping YouTube ingestion.")
        return 0

    video_ids = discover_video_ids_from_search(max_videos=12)
    if not video_ids:
        print("[WARN] No YouTube video IDs found. Skipping.")
        return 0

    downloader = YoutubeCommentDownloader()
    records = []

    for vid in video_ids:
        video_url = f"https://www.youtube.com/watch?v={vid}"
        print(f"[YOUTUBE] Fetching comments: {video_url}")
        try:
            comments_gen = downloader.get_comments(vid, sort_by=SORT_BY_POPULAR)
            count_scanned = 0
            count_matched = 0

            for comment in islice(comments_gen, max_comments_per_video):
                count_scanned += 1
                text = comment.get("text", "").strip()
                cid = comment.get("cid", "")
                if not cid:
                    cid = str(hash(f"{vid}_{text[:50]}"))
                author = comment.get("author", "YouTube Viewer")
                likes = comment.get("votes", 0) or 0

                # Only include comments with meaningful text
                if len(text) < 20:
                    continue

                matched_kw = matches_wishlist_keywords(text)
                if matched_kw:
                    count_matched += 1
                    records.append({
                        "external_id": f"youtube_{cid[:60]}",
                        "platform": "youtube",
                        "text": text,
                        "url": f"https://www.youtube.com/watch?v={vid}&lc={cid}",
                        "author": author,
                        "rating": None,
                        "keyword_matched": matched_kw,
                        "scraped_at": datetime.utcnow().isoformat(),
                        "is_processed": False
                    })

            print(f"[OK] Scanned {count_scanned} comments → {count_matched} matched for video {vid}.")

        except Exception as e:
            print(f"[WARN] Error fetching comments for video {vid}: {e}")

    unique_records = list({r["external_id"]: r for r in records}.values())
    print(f"[FILTER] Total unique wishlist/friction YouTube comments: {len(unique_records)}")

    if unique_records:
        upserted = upsert_raw_feedback(unique_records)
        print(f"[SUCCESS] Upserted {upserted} YouTube rows into Supabase `raw_feedback`.")
        return upserted
    return 0


if __name__ == "__main__":
    fetch_youtube_comments()
