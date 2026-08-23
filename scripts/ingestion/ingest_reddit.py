import os
import sys
from datetime import datetime
from apify_client import ApifyClient
from common import matches_wishlist_keywords, upsert_raw_feedback

APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

# Target subreddits for Myntra Indian fashion communities
TARGET_SUBREDDITS = [
    "IndianFashionAddicts",
    "TwoXIndia",
    "IndianBeautyDeals",
    "india",
    "AskIndia",
]

# Search queries focused on wishlist/save behaviour and purchase hesitation
SEARCH_QUERIES = [
    "myntra wishlist",
    "myntra sizing chart",
    "myntra fabric quality",
    "myntra return",
    "myntra save later",
    "myntra fit",
    "myntra size",
    "myntra review quality",
]


def fetch_reddit_discussions():
    print("=" * 60)
    print("FETCHING REDDIT DISCUSSIONS VIA APIFY (Real Reddit Posts & Comments)")
    print("=" * 60)

    if not APIFY_API_TOKEN or "apify_api_" not in APIFY_API_TOKEN:
        print("[ERROR] Missing or invalid APIFY_API_TOKEN in .env.")
        return 0

    client = ApifyClient(APIFY_API_TOKEN)
    records = []

    # -----------------------------------------------------------------------
    # Strategy 1: Reddit Scraper by Subreddit (apify/reddit-scraper)
    # Fetches actual post bodies + top comments from target subreddits
    # -----------------------------------------------------------------------
    print("[APIFY] Triggering Reddit Scraper actor for subreddit posts + comments...")
    try:
        run_input_sr = {
            "startUrls": [
                {"url": f"https://www.reddit.com/r/{sr}/search/?q=myntra&sort=relevance&t=year"}
                for sr in TARGET_SUBREDDITS
            ],
            "maxItems": 60,
            "includeComments": True,
            "maxComments": 15,
            "proxy": {"useApifyProxy": True, "apifyProxyGroups": ["RESIDENTIAL"]}
        }

        run = client.actor("trudax/reddit-scraper").call(run_input=run_input_sr)
        dataset_id = (
            run.get("defaultDatasetId") if isinstance(run, dict)
            else getattr(run, "default_dataset_id", None) or run.get("defaultDatasetId", "")
        )

        if dataset_id:
            items = list(client.dataset(dataset_id).iterate_items())
            print(f"[APIFY] Reddit Scraper returned {len(items)} items.")
            for item in items:
                # Each item can be a post or a comment
                post_id = item.get("id") or item.get("postId") or str(hash(str(item)))
                url = item.get("url") or item.get("postUrl") or ""
                author = item.get("author") or item.get("username") or "Reddit User"
                subreddit = item.get("subreddit") or item.get("communityName") or ""

                # Try multiple text field names from different actor versions
                body = (
                    item.get("body")
                    or item.get("text")
                    or item.get("selftext")
                    or item.get("comment")
                    or ""
                )
                title = item.get("title") or ""
                combined_text = f"{title}. {body}".strip(" .")
                if not combined_text:
                    continue

                matched_kw = matches_wishlist_keywords(combined_text)
                if matched_kw:
                    records.append({
                        "external_id": f"reddit_{str(post_id)[:60]}",
                        "platform": "reddit",
                        "text": combined_text,
                        "url": url,
                        "author": author,
                        "rating": None,
                        "keyword_matched": matched_kw,
                        "scraped_at": datetime.utcnow().isoformat(),
                        "is_processed": False
                    })
        else:
            print("[WARN] Could not get dataset ID from Reddit Scraper actor.")

    except Exception as e:
        print(f"[WARN] Reddit Scraper actor error: {e}")

    # -----------------------------------------------------------------------
    # Strategy 2: Apify Reddit Search Scraper (searches specific queries)
    # -----------------------------------------------------------------------
    print("[APIFY] Triggering Reddit search for specific Myntra queries...")
    try:
        run_input_search = {
            "searches": [
                {"query": q, "sort": "relevance", "time": "year"}
                for q in SEARCH_QUERIES[:4]  # Limit to 4 to stay within free tier
            ],
            "maxPostCount": 15,
            "includeComments": True,
            "maxComments": 10,
        }

        run2 = client.actor("apify/reddit-scraper").call(run_input=run_input_search)
        dataset_id2 = (
            run2.get("defaultDatasetId") if isinstance(run2, dict)
            else getattr(run2, "default_dataset_id", None) or run2.get("defaultDatasetId", "")
        )

        if dataset_id2:
            items2 = list(client.dataset(dataset_id2).iterate_items())
            print(f"[APIFY] Reddit Search returned {len(items2)} items.")
            for item in items2:
                post_id = item.get("id") or item.get("postId") or str(hash(str(item)))
                url = item.get("url") or item.get("postUrl") or ""
                author = item.get("author") or item.get("username") or "Reddit User"
                body = (
                    item.get("body")
                    or item.get("text")
                    or item.get("selftext")
                    or ""
                )
                title = item.get("title") or ""
                combined_text = f"{title}. {body}".strip(" .")
                if not combined_text:
                    continue

                matched_kw = matches_wishlist_keywords(combined_text)
                if matched_kw:
                    records.append({
                        "external_id": f"reddit_{str(post_id)[:60]}",
                        "platform": "reddit",
                        "text": combined_text,
                        "url": url,
                        "author": author,
                        "rating": None,
                        "keyword_matched": matched_kw,
                        "scraped_at": datetime.utcnow().isoformat(),
                        "is_processed": False
                    })

    except Exception as e:
        print(f"[WARN] Reddit search scraper error (actor may differ): {e}")

    # Deduplicate in-memory by external_id
    unique_records = list({r["external_id"]: r for r in records}.values())
    # Filter out deleted/removed posts
    unique_records = [
        r for r in unique_records
        if r.get("text", "") not in ("[deleted]", "[removed]", "", ".")
        and len(r.get("text", "")) > 20
    ]
    print(f"[FILTER] Extracted {len(unique_records)} real Reddit posts/comments matching wishlist friction.")

    if unique_records:
        upserted = upsert_raw_feedback(unique_records)
        print(f"[SUCCESS] Upserted {upserted} Reddit rows into Supabase `raw_feedback`.")
        return upserted
    else:
        print("[INFO] No Reddit rows matched criteria in this batch.")
        return 0


if __name__ == "__main__":
    fetch_reddit_discussions()
