import requests
import json

try:
    r = requests.post('http://localhost:3000/api/chat', json={'message': 'Give me an executive summary of the top friction themes.'})
    data = r.json()
    print("Chat API Response:")
    print(data.get('reply'))
except Exception as e:
    print(f"Error connecting to chat API: {e}")
