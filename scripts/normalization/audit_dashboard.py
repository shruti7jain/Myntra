import os
import requests

try:
    res = requests.get('http://localhost:3000/api/insights')
    data = res.json()
    
    total_friction = data.get('total_friction_count', 0)
    noise_count = data.get('noise_count', 0)
    total_raw = data.get('total_raw_analyzed', 0)
    
    print(f"Total Source Counts: {total_raw}")
    print(f"Friction + Noise: {total_friction} + {noise_count} = {total_friction + noise_count}")
    
    print("\nFriction Percentages:")
    for theme in data.get('insights', []):
        calc_pct = (theme['count'] / total_friction * 100) if total_friction > 0 else 0
        print(f"Theme: {theme['theme_label']}")
        print(f"Numerator (count): {theme['count']}")
        print(f"Denominator (total_friction): {total_friction}")
        print(f"Displayed pct: {theme['pct']}%")
        print(f"Calculated pct: {round(calc_pct)}%")
        print(f"Pct Exact from DB: {theme['pct_exact']}")
        print("---")
        
    print("\nIntent Percentages:")
    sum_intent = 0
    total_intent_count = sum(intent['count'] for intent in data.get('intents', []))
    for intent in data.get('intents', []):
        print(f"Intent: {intent['label']}")
        print(f"Count: {intent['count']}")
        print(f"Displayed pct: {intent['pct']}%")
        calc_pct = (intent['count'] / total_intent_count * 100) if total_intent_count > 0 else 0
        print(f"Calculated pct: {round(calc_pct)}%")
        sum_intent += intent['pct']
    print(f"Total Intent Pct Sum: {sum_intent}%")
    print(f"Total Intent Count: {total_intent_count}")
    
except Exception as e:
    print(f"Error: {e}")
