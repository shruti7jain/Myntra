import os
import re
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# Target high-intent wishlisting, sizing, and consideration keywords
WISHLIST_KEYWORDS = [
    "wishlist", "wish list", "save for later", "saved item", "bookmark",
    "cart", "buy later", "shortlist", "fitting", "size chart", "fabric quality",
    "return", "exchange", "see through", "true to size", "shoulder", "bust",
    "kapda", "fitting loose", "fitting tight"
]

def get_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in environment variables.")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def matches_wishlist_keywords(text: str) -> str | None:
    """Returns the matched keyword if text contains any target keywords, else None."""
    if not text:
        return None
    lower_text = text.lower()
    for kw in WISHLIST_KEYWORDS:
        if kw in lower_text:
            return kw
    return None

def upsert_raw_feedback(records: list[dict]) -> int:
    """
    Upserts a list of raw feedback records into the Supabase raw_feedback table.
    Uses external_id to prevent duplicates on conflict.
    """
    if not records:
        return 0

    supabase = get_supabase_client()
    try:
        # Upsert in batches of 100
        batch_size = 100
        total_upserted = 0
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            response = supabase.table("raw_feedback").upsert(
                batch,
                on_conflict="external_id"
            ).execute()
            total_upserted += len(batch)
            
        return total_upserted
    except Exception as e:
        print(f"[ERROR] Failed to upsert batch to Supabase: {e}")
        return 0
