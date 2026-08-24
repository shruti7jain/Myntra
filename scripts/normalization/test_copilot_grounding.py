import requests
import json

BASE_URL = 'http://localhost:3000'

queries = [
    "How many conversations were analyzed?",
    "What is the top friction theme?",
    "What percentage is Fit & Sizing?",
    "What is the second-largest theme?"
]

print("=== TESTING COPILOT GROUNDING QUERIES ===")
for q in queries:
    print(f"\n--- QUERY: '{q}' ---")
    try:
        res = requests.post(f"{BASE_URL}/api/chat", json={"message": q})
        data = res.json()
        print("REPLY:")
        print(data.get("reply"))
    except Exception as e:
        print(f"Error: {e}")
