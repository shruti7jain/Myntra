import os
import sys
import requests
from datetime import datetime
from common import matches_wishlist_keywords, upsert_raw_feedback

MYNTRA_APP_STORE_ID = "907394059"  # Myntra iOS App in India Store
MYNTRA_APP_STORE_ID_ALT = "id907394059"  # alternate format

# Apple App Store RSS (India) - pages 1-10 cover the most recent ~500 reviews
RSS_BASE = "https://itunes.apple.com/in/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"

# Backup: older RSS format Apple sometimes still serves
RSS_BASE_ALT = "https://itunes.apple.com/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"


def _parse_rss_entry(entry: dict) -> dict | None:
    """Safely parse a single RSS entry dict into a flat review dict."""
    try:
        review_id = (entry.get("id") or {}).get("label") or ""
        title = (entry.get("title") or {}).get("label", "") or ""
        content = (entry.get("content") or {}).get("label", "") or ""
        author = (
            (entry.get("author") or {})
            .get("name", {})
            .get("label", "iOS Shopper")
        ) or "iOS Shopper"
        rating_val = (entry.get("im:rating") or {}).get("label")
        rating = int(rating_val) if rating_val and str(rating_val).isdigit() else None

        full_text = f"{title}. {content}".strip(". ")
        if not full_text or len(full_text) < 15:
            return None

        return {
            "id": review_id or str(hash(full_text[:80])),
            "text": full_text,
            "author": author,
            "rating": rating,
            "url": f"https://apps.apple.com/in/app/myntra-fashion-shopping-app/id{MYNTRA_APP_STORE_ID}"
        }
    except Exception:
        return None


def fetch_appstore_reviews() -> int:
    print("=" * 60)
    print(f"APPLE APP STORE INGESTION (App ID: {MYNTRA_APP_STORE_ID}, India Store)")
    print("=" * 60)

    raw_reviews = []

    for page in range(1, 11):
        fetched = False

        # Try primary India RSS URL
        for url_template in [RSS_BASE, RSS_BASE_ALT]:
            url = url_template.format(page=page, app_id=MYNTRA_APP_STORE_ID)
            try:
                res = requests.get(url, timeout=15, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; MyntraDiscoveryBot/1.0)"
                })
                if res.status_code == 200:
                    data = res.json()
                    entries = data.get("feed", {}).get("entry", [])

                    # Skip the first entry on page 1 (it's the app metadata, not a review)
                    if page == 1 and entries and isinstance(entries[0], dict):
                        entries = entries[1:]

                    if not entries:
                        print(f"[OK] Page {page}: No entries — reached end of reviews.")
                        break

                    parsed_count = 0
                    for entry in entries:
                        if not isinstance(entry, dict):
                            continue
                        r = _parse_rss_entry(entry)
                        if r:
                            raw_reviews.append(r)
                            parsed_count += 1

                    print(f"[OK] Page {page}: Downloaded {parsed_count} reviews.")
                    fetched = True
                    break
                elif res.status_code == 404:
                    print(f"[INFO] Page {page}: 404 — reached end of RSS pages.")
                    break
                else:
                    print(f"[WARN] Page {page}: HTTP {res.status_code} from {url_template[:50]}")
            except requests.exceptions.Timeout:
                print(f"[WARN] Page {page}: Request timeout. Skipping.")
            except Exception as e:
                print(f"[WARN] Page {page}: Error — {e}")

        if not fetched:
            break

    print(f"[OK] Fetched {len(raw_reviews)} raw reviews from Apple App Store (India).")

    records = []
    for r in raw_reviews:
        text = r.get("text", "")
        matched_kw = matches_wishlist_keywords(text)
        if matched_kw:
            review_id = r.get("id") or str(hash(text[:80]))
            records.append({
                "external_id": f"appstore_{review_id}",
                "platform": "appstore",
                "text": text.strip(),
                "url": r.get("url", f"https://apps.apple.com/in/app/id{MYNTRA_APP_STORE_ID}"),
                "author": r.get("author", "iOS Shopper"),
                "rating": r.get("rating"),
                "keyword_matched": matched_kw,
                "scraped_at": datetime.utcnow().isoformat(),
                "is_processed": False
            })

    unique_records = list({r["external_id"]: r for r in records}.values())
    print(f"[FILTER] Matched {len(unique_records)} wishlist/friction relevant App Store reviews.")

    if unique_records:
        upserted = upsert_raw_feedback(unique_records)
        print(f"[SUCCESS] Upserted {upserted} App Store rows into Supabase `raw_feedback`.")
        return upserted
    return 0


if __name__ == "__main__":
    fetch_appstore_reviews()
