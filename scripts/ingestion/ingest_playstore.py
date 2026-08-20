import os
import sys
from datetime import datetime
from google_play_scraper import Sort, reviews
from common import matches_wishlist_keywords, upsert_raw_feedback

MYNTRA_APP_ID = "com.myntra.android"

def fetch_playstore_reviews(target_count=600):
    print("=" * 60)
    print(f"SCALING PLAY STORE INGESTION (Target: {target_count}+ relevant reviews)")
    print("=" * 60)
    
    records = []
    
    # Scrape across both NEWEST and MOST_RELEVANT sorts to maximize diversity
    for sort_type in [Sort.NEWEST, Sort.MOST_RELEVANT]:
        sort_name = "NEWEST" if sort_type == Sort.NEWEST else "MOST_RELEVANT"
        print(f"[PLAY STORE] Scraping 4,000 reviews with sort={sort_name}...")
        
        try:
            result, _ = reviews(
                MYNTRA_APP_ID,
                lang='en',
                country='in',
                sort=sort_type,
                count=4000
            )
            print(f"[OK] Downloaded {len(result)} raw reviews from Play Store ({sort_name}).")
            
            for r in result:
                text = r.get("content", "")
                matched_kw = matches_wishlist_keywords(text)
                
                if matched_kw:
                    review_id = r.get("reviewId")
                    at_time = r.get("at")
                    scraped_at = at_time.isoformat() if isinstance(at_time, datetime) else datetime.utcnow().isoformat()
                    
                    records.append({
                        "external_id": f"playstore_{review_id}",
                        "platform": "playstore",
                        "text": text.strip(),
                        "url": f"https://play.google.com/store/apps/details?id={MYNTRA_APP_ID}&reviewId={review_id}",
                        "author": r.get("userName", "Anonymous"),
                        "rating": r.get("score"),
                        "keyword_matched": matched_kw,
                        "scraped_at": scraped_at,
                        "is_processed": False
                    })
        except Exception as e:
            print(f"[WARN] Error during Play Store scrape ({sort_name}): {e}")

    # Deduplicate in-memory by external_id
    unique_records = list({r["external_id"]: r for r in records}.values())
    print(f"[FILTER] Total unique wishlist/sizing relevant Play Store reviews: {len(unique_records)}")
    
    if unique_records:
        upserted = upsert_raw_feedback(unique_records)
        print(f"[SUCCESS] Upserted {upserted} Play Store rows into Supabase `raw_feedback`.")
        return upserted
    return 0

if __name__ == "__main__":
    fetch_playstore_reviews(target_count=600)
