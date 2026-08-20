import os
import sys
import requests
from datetime import datetime
from common import matches_wishlist_keywords, upsert_raw_feedback

MYNTRA_APP_STORE_ID = "907394059" # Myntra iOS App ID in India Store

def fetch_appstore_reviews():
    print("=" * 60)
    print(f"SCALING APPLE APP STORE INGESTION (Target App ID: {MYNTRA_APP_STORE_ID})")
    print("=" * 60)

    raw_reviews = []
    
    # Apple App Store customer reviews RSS endpoint for India (pages 1 to 10)
    for page in range(1, 11):
        url = f"https://itunes.apple.com/in/rss/customerreviews/page={page}/id={MYNTRA_APP_STORE_ID}/sortby=mostrecent/json"
        try:
            res = requests.get(url, timeout=15)
            if res.status_code == 200:
                data = res.json()
                entries = data.get("feed", {}).get("entry", [])
                for entry in entries:
                    review_id = entry.get("id", {}).get("label")
                    title = entry.get("title", {}).get("label", "")
                    content = entry.get("content", {}).get("label", "")
                    author = entry.get("author", {}).get("name", {}).get("label", "iOS User")
                    rating_val = entry.get("im:rating", {}).get("label")
                    rating = int(rating_val) if rating_val and rating_val.isdigit() else None
                    
                    full_text = f"{title}. {content}".strip()
                    raw_reviews.append({
                        "id": review_id,
                        "text": full_text,
                        "author": author,
                        "rating": rating,
                        "url": f"https://apps.apple.com/in/app/myntra-fashion-shopping-app/id{MYNTRA_APP_STORE_ID}"
                    })
        except Exception as e:
            print(f"[WARN] App Store RSS page {page} fetch error: {e}")
            
    print(f"[OK] Fetched {len(raw_reviews)} raw reviews directly from Apple App Store.")

    records = []
    for r in raw_reviews:
        text = r.get("text", "")
        matched_kw = matches_wishlist_keywords(text)
        
        if matched_kw:
            review_id = r.get("id") or str(hash(text))
            rating = r.get("rating")
            
            records.append({
                "external_id": f"appstore_{review_id}",
                "platform": "appstore",
                "text": text.strip(),
                "url": r.get("url", f"https://apps.apple.com/in/app/id{MYNTRA_APP_STORE_ID}"),
                "author": r.get("author", "iOS Shopper"),
                "rating": int(rating) if rating is not None and str(rating).isdigit() else None,
                "keyword_matched": matched_kw,
                "scraped_at": datetime.utcnow().isoformat(),
                "is_processed": False
            })

    unique_records = list({r["external_id"]: r for r in records}.values())
    print(f"[FILTER] Matched {len(unique_records)} wishlist/sizing relevant App Store reviews.")
    
    if unique_records:
        upserted = upsert_raw_feedback(unique_records)
        print(f"[SUCCESS] Upserted {upserted} App Store rows into Supabase `raw_feedback`.")
        return upserted
    return 0

if __name__ == "__main__":
    fetch_appstore_reviews()
