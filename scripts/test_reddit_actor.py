import os
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("APIFY_API_TOKEN")
client = ApifyClient(token)

run_input = {
    "queries": ["myntra sizing", "myntra wishlist"],
    "subreddits": ["IndianFashionAddicts"],
    "maxPosts": 15
}

print("Testing streamers/reddit-scraper...")
try:
    run = client.actor("streamers/reddit-scraper").call(run_input=run_input)
    if run:
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        print(f"streamers/reddit-scraper fetched {len(items)} items!")
except Exception as e:
    print(f"streamers/reddit-scraper error: {e}")
