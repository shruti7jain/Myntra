import os
import sys
import json
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), '.env'))

from supabase import create_client
from groq import Groq
from process_insights import classify_batch_with_llm, is_excluded_by_rating

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# 1. Fetch the 20 synthetic Hinglish records
print("Fetching synthetic Hinglish records...")
res = supabase.table("raw_feedback").select("id, text, platform, rating").like("external_id", "hinglish_synthetic_%").execute()
records = res.data

if not records:
    print("No records found.")
    sys.exit(1)

# Apply rating exclusions first
eligible_records = []
excluded_records = {}
for r in records:
    if is_excluded_by_rating(r.get("platform"), r.get("rating")):
        excluded_records[r["id"]] = {
            "theme": "unrelated_other",
            "intent_type": "noise",
            "classification_method": "heuristic_fallback"
        }
    else:
        eligible_records.append(r)

print(f"Found {len(records)} records. {len(eligible_records)} eligible for LLM, {len(excluded_records)} excluded by rating.")

# 2. Run them through the exact same batch LLM function used in production
print("Processing in batches of 10...")
llm_results = {}
for i in range(0, len(eligible_records), 10):
    batch = eligible_records[i:i+10]
    print(f"Processing batch {i//10 + 1}...")
    batch_res, _ = classify_batch_with_llm(groq_client, batch)
    if batch_res:
        llm_results.update(batch_res)

# 3. Update database and print results nicely
print("\n--- HINGLISH CLASSIFICATION RESULTS ---\n")
for record in records:
    r_id = record["id"]
    text = record["text"]
    if r_id in excluded_records:
        ex = excluded_records[r_id]
        supabase.table("raw_feedback").update({
            "theme": ex["theme"],
            "classification_method": ex["classification_method"],
            "is_processed": True
        }).eq("id", r_id).execute()
        print(f"TEXT: {text}")
        print(f"  -> THEME:  {ex['theme']} (EXCLUDED BY RATING)")
        print(f"  -> INTENT: {ex['intent_type']}")
        print(f"  -> [DB UPDATED]")
        print("-" * 60)
    elif llm_results and r_id in llm_results:
        result = llm_results[r_id]
        theme = result.get("theme", "unrelated_other")
        intent = result.get("intent_type", "noise")
        
        # UPDATE SUPABASE
        supabase.table("raw_feedback").update({
            "theme": theme,
            "classification_method": "llm",
            "is_processed": True
        }).eq("id", r_id).execute()
        
        print(f"TEXT: {text}")
        print(f"  -> THEME:  {theme}")
        print(f"  -> INTENT: {intent}")
        print(f"  -> [DB UPDATED]")
        print("-" * 60)
    else:
        print(f"TEXT: {text}")
        print(f"  -> FAILED TO CLASSIFY (Rate limit or error)")
        print("-" * 60)
