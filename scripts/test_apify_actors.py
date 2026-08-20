import os
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("APIFY_API_TOKEN")
client = ApifyClient(token)

actors_to_test = [
    "epctex/reddit-scraper",
    "dtrungtin/reddit-scraper",
    "streamers/reddit-scraper",
    "apify/web-scraper"
]

for act in actors_to_test:
    try:
        actor_info = client.actor(act).get()
        print(f"Actor {act} found: {actor_info.get('title') if actor_info else 'None'}")
    except Exception as e:
        print(f"Actor {act} error: {e}")
