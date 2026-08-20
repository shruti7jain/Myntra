import os
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("APIFY_API_TOKEN")
client = ApifyClient(token)

run_input = {
    "queries": "site:reddit.com/r/IndianFashionAddicts \"myntra\" wishlist OR sizing OR fit",
    "maxPagesPerQuery": 1,
    "resultsPerPage": 20,
    "countryCode": "in"
}

print("Testing apify/google-search-scraper for Reddit...")
try:
    run = client.actor("apify/google-search-scraper").call(run_input=run_input)
    if run:
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        print(f"apify/google-search-scraper fetched {len(items)} results!")
        for it in items[:2]:
            print("Sample:", it.get("organicResults", [{}])[0].get("title"))
except Exception as e:
    print(f"Error: {e}")
