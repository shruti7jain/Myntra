import requests

subreddits = ["IndianFashionAddicts", "TwoXIndia"]
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

for sub in subreddits:
    url = f"https://www.reddit.com/r/{sub}/new.json?limit=50"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"r/{sub} new.json status: {r.status_code}, length: {len(r.json().get('data', {}).get('children', []))}")
    except Exception as e:
        print(f"Error: {e}")
