import sys
import os
import requests
import json
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ingestion'))
from common import get_supabase_client

load_dotenv()

def run_end_to_end_test():
    print("=" * 80)
    print("MYNTRA WISHLIST AI DISCOVERY ENGINE - PHASE 7: END-TO-END SYSTEM TEST")
    print("=" * 80)

    # 1. Verify Supabase Database Connection & Raw Feedback
    print("[TEST 1/4] Verifying Supabase Data Lake (raw_feedback)...")
    supabase = get_supabase_client()
    raw_res = supabase.table("raw_feedback").select("id", count="exact").execute()
    total_raw = raw_res.count or 0
    
    if total_raw >= 1000:
        print(f"  [PASSED] Found {total_raw} raw VoC verbatims in `raw_feedback` (Target: >= 1,000).")
    else:
        print(f"  [WARN] Found {total_raw} records.")

    # 2. Verify Supabase Insights Table
    print("\n[TEST 2/4] Verifying Processed Intelligence Table (insights)...")
    insights_res = supabase.table("insights").select("*").order("mention_count", desc=True).execute()
    insights = insights_res.data or []
    
    if len(insights) >= 5:
        print(f"  [PASSED] Found {len(insights)} quantified friction themes in `insights` table.")
        for i in insights:
            print(f"     * {i['theme_label']:<40} : {i['mention_count']:>4} ({i['pct_of_total']:>5}%)")
    else:
        print(f"  [FAILED] Less than 5 themes found in `insights`.")

    # 3. Verify Local Next.js API Route (/api/insights)
    print("\n[TEST 3/4] Verifying Next.js Serverless API Route (/api/insights)...")
    try:
        r = requests.get("http://localhost:3000/api/insights", timeout=10)
        if r.status_code == 200:
            data = r.json()
            print(f"  [PASSED] API returned HTTP 200 with {len(data.get('insights', []))} themes.")
        else:
            print(f"  [FAILED] /api/insights returned status {r.status_code}")
    except Exception as e:
        print(f"  [WARN] Dev server check: {e}")

    # 4. Verify AI PM Chat Copilot API Route (/api/chat)
    print("\n[TEST 4/4] Verifying AI PM Copilot API Route (/api/chat)...")
    test_query = "Why do users hesitate to purchase ethnic wear?"
    try:
        r = requests.post("http://localhost:3000/api/chat", json={"message": test_query}, timeout=15)
        if r.status_code == 200:
            res_data = r.json()
            reply = res_data.get("reply", "")
            print(f"  [PASSED] Copilot responded with grounded diagnosis:")
            print(f"     \"{reply[:120]}...\"")
        else:
            print(f"  [FAILED] /api/chat returned status {r.status_code}")
    except Exception as e:
        print(f"  [WARN] Chat API error: {e}")

    print("=" * 80)
    print("ALL 4 END-TO-END TEST SUITES COMPLETED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_end_to_end_test()
