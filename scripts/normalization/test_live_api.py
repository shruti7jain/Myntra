import requests
import json

try:
    r = requests.get('http://localhost:3000/api/insights')
    data = r.json()
    print("API Response Summary:")
    print(f"Total raw analyzed: {data.get('total_raw_analyzed')}")
    print(f"Total friction count: {data.get('total_friction_count')}")
    print(f"Noise count: {data.get('noise_count')}")
    print(f"Platforms: {data.get('platforms')}")
    print(f"Intents: {data.get('intents')}")
    print(f"Insights: {data.get('insights')}")
except Exception as e:
    print(f"Error connecting to dev server: {e}")
