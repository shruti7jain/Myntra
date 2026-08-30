import sys
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), '.env'))
from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')

if not url or not key:
    print("Error: Supabase credentials not found.")
    sys.exit(1)

supabase = create_client(url, key)

hinglish_reviews = [
    # Fit & Sizing
    {"text": "Mene M size order kiya tha but ye bahut tight hai, size chart galat hai bilkul.", "platform": "appstore"},
    {"text": "Fitting ekdam bekar hai, length bhi choti hai aur shoulders se loose hai.", "platform": "playstore"},
    {"text": "shoes 1 size chota aaya hai, mera toe dard kar raha hai pehenne ke baad.", "platform": "appstore"},
    {"text": "bhai size ka bohot bada issue hai, XL mangaya L jaisa lag raha hai return karna padega.", "platform": "playstore"},
    {"text": "size exchange ka option kyu nahi dikha raha? mujhe bada size chahiye ye fit nahi aa raha.", "platform": "appstore"},
    
    # Fabric Quality
    {"text": "Kapda bahut patla hai, photo me acha lag raha tha real me sasta material hai.", "platform": "playstore"},
    {"text": "quality ekdam raddi hai, dhone ke baad pura rang nikal gaya aur shrink ho gaya.", "platform": "appstore"},
    {"text": "material bilkul see-through hai, bahar pehen ke nahi ja sakte isko.", "platform": "playstore"},
    {"text": "bohot chubne wala kapda hai, itchy feeling aati hai pehen ke waste of money.", "platform": "appstore"},
    
    # Visual Reality / Mismatch
    {"text": "app me color dark blue tha but real me light blue bheja hai, photo se match nahi karta.", "platform": "playstore"},
    {"text": "design alag hai thoda, sleeves ka pattern app ki photo jaisa nahi hai.", "platform": "appstore"},
    {"text": "looks completely different from what is shown, not happy with the product received.", "platform": "playstore"},
    {"text": "dikhte kuch aur hai bhejte kuch aur hai, total scam.", "platform": "appstore"},
    
    # Occasion Timing / Delivery
    {"text": "shadi ke liye mangaya tha order, 10 din late aaya ab kya faida iska?", "platform": "playstore"},
    {"text": "delivery bahut slow hai aaj kal, diwali ke pehle chahiye tha par late ho gaya.", "platform": "appstore"},
    {"text": "urgently party ke liye dress chahiye thi but tracking me stuck dikha raha hai.", "platform": "playstore"},
    
    # Noise / Unrelated / General
    {"text": "return policy bahut kharab hai myntra ki aajkal, customer care walo ko kuch nahi pata.", "platform": "playstore"},
    {"text": "app hamesha crash ho jata hai jab payment page aata hai, fix this bug.", "platform": "appstore"},
    {"text": "refund abhi tak account me nahi aaya 15 din ho gaye.", "platform": "playstore"},
    {"text": "bahut badhiya app hai, delivery fast hoti hai generally.", "platform": "appstore"},
]

print(f"Injecting {len(hinglish_reviews)} Hinglish reviews into `raw_feedback`...")

inserted_count = 0
for idx, review in enumerate(hinglish_reviews):
    payload = {
        "external_id": f"hinglish_synthetic_{idx+1}",
        "text": review["text"],
        "platform": review["platform"],
        "is_processed": False, # Important: So it gets picked up by process_insights.py
        "classification_method": None,
        "theme": None,
        "rating": 1
    }
    
    try:
        # Upsert based on external_id
        supabase.table("raw_feedback").upsert(payload, on_conflict="external_id").execute()
        inserted_count += 1
    except Exception as e:
        print(f"Failed to insert: {e}")

print(f"Successfully injected {inserted_count} Hinglish records.")
print("Run `python scripts/normalization/process_insights.py` next to process these with the LLM!")
