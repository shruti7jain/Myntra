import os
import sys
from datetime import datetime
from apify_client import ApifyClient
from common import matches_wishlist_keywords, upsert_raw_feedback

APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

def fetch_reddit_discussions():
    print("=" * 60)
    print("FETCHING REDDIT DISCUSSIONS VIA APIFY (Indian Fashion Communities)")
    print("=" * 60)

    if not APIFY_API_TOKEN or "apify_api_" not in APIFY_API_TOKEN:
        print("[ERROR] Missing or invalid APIFY_API_TOKEN in .env.")
        return 0

    client = ApifyClient(APIFY_API_TOKEN)
    
    queries = [
        "\"r/IndianFashionAddicts\" myntra (wishlist OR sizing OR fit OR quality OR return)",
        "\"r/TwoXIndia\" myntra (wishlist OR sizing OR fit OR quality OR return)",
        "\"IndianFashionAddicts\" myntra wishlist buy later"
    ]
    
    run_input = {
        "queries": "\n".join(queries),
        "maxPagesPerQuery": 1,
        "resultsPerPage": 25,
        "countryCode": "in"
    }

    try:
        print("[APIFY] Triggering Google Search Scraper for Reddit Fashion Threads...")
        run = client.actor("apify/google-search-scraper").call(run_input=run_input)
        
        # Access dataset ID safely from dict or object
        dataset_id = run.get("defaultDatasetId") if isinstance(run, dict) else getattr(run, "default_dataset_id", None) or run.get("defaultDatasetId", "")
        
        if not dataset_id:
            print("[ERROR] Could not determine Apify dataset ID.")
            return 0
            
        print(f"[APIFY] Run completed. Fetching dataset items ({dataset_id})...")
        items = list(client.dataset(dataset_id).iterate_items())
        
        records = []
        for it in items:
            organic_results = it.get("organicResults", [])
            for res in organic_results:
                title = res.get("title", "")
                description = res.get("description", "")
                url = res.get("url", "")
                combined_text = f"{title}. {description}".strip()
                
                matched_kw = matches_wishlist_keywords(combined_text)
                if matched_kw and "reddit.com" in url:
                    # Generate stable ID from url
                    url_slug = url.split("comments/")[-1].replace("/", "_") if "comments/" in url else str(hash(url))
                    
                    records.append({
                        "external_id": f"reddit_{url_slug[:60]}",
                        "platform": "reddit",
                        "text": combined_text,
                        "url": url,
                        "author": "Reddit Community",
                        "rating": None,
                        "keyword_matched": matched_kw,
                        "scraped_at": datetime.utcnow().isoformat(),
                        "is_processed": False
                    })
                    
        # In-memory deduplication
        unique_records = list({r["external_id"]: r for r in records}.values())
        print(f"[FILTER] Extracted {len(unique_records)} high-intent Reddit fashion discussion items.")
        
        if unique_records:
            upserted = upsert_raw_feedback(unique_records)
            print(f"[SUCCESS] Upserted {upserted} Reddit rows into Supabase `raw_feedback`.")
            return upserted
        else:
            print("[INFO] No Reddit rows matched criteria in this batch.")
            return 0

    except Exception as e:
        print(f"[WARN] Apify Reddit scraping error: {e}")
        return 0

if __name__ == "__main__":
    fetch_reddit_discussions()
