import os
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), '.env'))

print("Fetching API data...")
try:
    res = requests.get('http://localhost:3000/api/insights')
    data = res.json()
    print("Insights:")
    for theme in data.get('insights', []):
        print(f"  {theme['theme']}: count={theme['count']}, pct={theme['pct']}")
    print(f"Total friction: {data.get('total_friction_count')}")
except Exception as e:
    print(f"Error fetching from API: {e}")
