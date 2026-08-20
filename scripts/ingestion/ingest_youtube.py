import os
import sys
import re
import requests
from datetime import datetime
from itertools import islice
from youtube_comment_downloader import YoutubeCommentDownloader, SORT_BY_POPULAR
from common import matches_wishlist_keywords, upsert_raw_feedback

def get_myntra_haul_video_ids():
    """Dynamically finds real, public YouTube video IDs for Myntra Hauls."""
    queries = [
        "myntra+haul+try+on+sizing", 
        "myntra+honest+review+fitting", 
        "myntra+kurti+haul+quality", 
        "myntra+western+wear+try+on"
    ]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    video_ids = []
    
    for q in queries:
        url = f"https://www.youtube.com/results?search_query={q}"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                found = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', r.text)
                for vid in found:
                    if vid not in video_ids:
                        video_ids.append(vid)
        except Exception as e:
            print(f"[WARN] Error searching YouTube for {q}: {e}")
            
    print(f"[YOUTUBE] Found {len(video_ids)} real Myntra fashion video targets.")
    return video_ids[:15] # Target top 15 videos for large batch ingestion

def fetch_youtube_comments(max_comments_per_video=100):
    print("=" * 60)
    print("SCALING YOUTUBE COMMENTS INGESTION (15 Active Myntra Hauls)")
    print("=" * 60)

    video_ids = get_myntra_haul_video_ids()
    downloader = YoutubeCommentDownloader()
    records = []

    for vid in video_ids:
        print(f"[YOUTUBE] Downloading comments for video: https://youtube.com/watch?v={vid} ...")
        try:
            comments = downloader.get_comments(vid, sort_by=SORT_BY_POPULAR)
            count_scanned = 0
            
            for comment in islice(comments, max_comments_per_video):
                count_scanned += 1
                text = comment.get("text", "")
                cid = comment.get("cid", str(hash(text)))
                author = comment.get("author", "YouTube Viewer")
                
                matched_kw = matches_wishlist_keywords(text)
                if matched_kw:
                    records.append({
                        "external_id": f"youtube_{cid}",
                        "platform": "youtube",
                        "text": text.strip(),
                        "url": f"https://www.youtube.com/watch?v={vid}&lc={cid}",
                        "author": author,
                        "rating": None,
                        "keyword_matched": matched_kw,
                        "scraped_at": datetime.utcnow().isoformat(),
                        "is_processed": False
                    })
            print(f"[OK] Scanned {count_scanned} comments for video {vid}.")
        except Exception as e:
            print(f"[WARN] Error on video {vid}: {e}")

    unique_records = list({r["external_id"]: r for r in records}.values())
    print(f"[FILTER] Matched {len(unique_records)} wishlist/sizing relevant YouTube comments.")

    if unique_records:
        upserted = upsert_raw_feedback(unique_records)
        print(f"[SUCCESS] Upserted {upserted} YouTube rows into Supabase `raw_feedback`.")
        return upserted
    return 0

if __name__ == "__main__":
    fetch_youtube_comments()
