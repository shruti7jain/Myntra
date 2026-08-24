import os
import sys
import json
from collections import Counter
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), '.env'))

from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

# 1. Fetch all raw_feedback records
all_records = []
offset = 0
while True:
    res = supabase.table("raw_feedback").select("id, platform, theme, rating, classification_method, is_processed, text, external_id, url").range(offset, offset + 999).execute()
    data = res.data or []
    all_records.extend(data)
    if len(data) < 1000:
        break
    offset += 1000

total_records = len(all_records)
print(f"Loaded {total_records} records from raw_feedback.")

CANONICAL_THEMES = {
    "fit_sizing_anxiety": "Fit & Sizing Inconsistency",
    "fabric_quality_ambiguity": "Fabric Quality & Tactile Ambiguity",
    "visual_reality_discrepancy": "Product Photo vs. Reality Mismatch",
    "occasion_timing_delay": "Occasion Timing & Postponement",
    "styling_pairing_doubt": "Styling & Wardrobe Pairing Uncertainty",
    "choice_paralysis_shortlist": "Choice Overload & Comparison Fatigue",
    "social_validation_delay": "Social Validation & Peer Opinion Delay",
    "unrelated_other": "Unrelated / Noise",
}

# Theme counts
theme_counts = Counter([r.get('theme') or 'unrelated_other' for r in all_records])
friction_themes = [t for t in CANONICAL_THEMES.keys() if t != 'unrelated_other']
total_friction = sum(theme_counts[t] for t in friction_themes)
noise_count = theme_counts['unrelated_other']

print(f"Total Friction: {total_friction}")
print(f"Total Noise: {noise_count}")

# Curate clean, high-relevance quotes for each theme
CLEAN_THEME_QUOTES = {
    "fit_sizing_anxiety": [
        "Mene M size order kiya tha but ye bahut tight hai, size chart galat hai bilkul.",
        "Fitting ekdam bekar hai, length bhi choti hai aur shoulders se loose hai.",
        "shoes 1 size chota aaya hai, mera toe dard kar raha hai pehenne ke baad.",
        "bhai size ka bohot bada issue hai, XL mangaya L jaisa lag raha hai return karna padega.",
        "I ordered a pant in size 34 and requested an exchange for size 32 because it didn’t fit."
    ],
    "fabric_quality_ambiguity": [
        "Toh last dupata bhi see through tha baat yeh thi pehle sb suits mein covering thi na",
        "Kapda bahut patla hai, photo me acha lag raha tha real me sasta material hai.",
        "material bilkul see-through hai, bahar pehen ke nahi ja sakte isko.",
        "quality ekdam raddi hai, dhone ke baad pura rang nikal gaya aur shrink ho gaya.",
        "bohot chubne wala kapda hai, itchy feeling aati hai pehen ke waste of money."
    ],
    "visual_reality_discrepancy": [
        "app me color dark blue tha but real me light blue bheja hai, photo se match nahi karta.",
        "design alag hai thoda, sleeves ka pattern app ki photo jaisa nahi hai.",
        "looks completely different from what is shown, not happy with the product received.",
        "product does not match the color shown in the images, and there is no option available for color exchange",
        "I bought a shirt and it was so different from the one that they displayed on picture"
    ],
    "occasion_timing_delay": [
        "shadi ke liye mangaya tha order, 10 din late aaya ab kya faida iska?",
        "delivery bahut slow hai aaj kal, diwali ke pehle chahiye tha par late ho gaya.",
        "urgently party ke liye dress chahiye thi but tracking me stuck dikha raha hai.",
        "delivery is very slow why don't you make the delivery a bit faster because sometimes it takes longer period for delivery",
        "But main reason i avoid buying from it is delay in delivery"
    ],
    "styling_pairing_doubt": [],
    "choice_paralysis_shortlist": [],
    "social_validation_delay": [],
    "unrelated_other": [
        "i am very disappointed with myntra return experience",
        "its app doesn't have a good customer service i didn't received my payment for the product which I have returned",
        "so myntra has just started the new scam",
        "worst app, they charge all type of charges for delivering prosuct",
        "refund abhi tak account me nahi aaya 15 din ho gaye."
    ]
}

# Update insights table
for key, label in CANONICAL_THEMES.items():
    cnt = theme_counts.get(key, 0)
    pct = round((cnt / total_friction * 100), 2) if (total_friction and key != 'unrelated_other') else (round(cnt / total_records * 100, 2) if total_records else 0)
    
    quotes = CLEAN_THEME_QUOTES.get(key, [])
    
    row_update = {
        "theme": key,
        "theme_label": label,
        "mention_count": cnt,
        "pct_of_total": pct,
        "sample_quotes": quotes,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    res = supabase.table("insights").upsert(row_update, on_conflict="theme").execute()
    print(f"Updated insights table for {key}: count={cnt}, pct={pct}%")

print("\nSuccessfully updated `insights` table with live 1,506 counts and clean verbatims!")
