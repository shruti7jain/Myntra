import os
import re
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# ---------------------------------------------------------------------------
# HIGH-INTENT KEYWORD FILTER
# Multi-token patterns to avoid false positives like "returns are fast!" or
# "add to cart worked!" matching as friction signals.
# Uses (primary_token, context_token) pairs - BOTH must be present in text.
# Single-token entries are standalone high-signal terms unlikely to be noise.
# ---------------------------------------------------------------------------
WISHLIST_KEYWORD_PAIRS = [
    # Wishlist / Save behaviour
    ("wishlist", None),
    ("wish list", None),
    ("save for later", None),
    ("saved item", None),
    ("saved it", None),
    ("bookmark", None),
    ("buy later", None),
    ("shortlist", None),

    # Fit & Sizing (require sizing context words)
    ("size chart", None),
    ("true to size", None),
    ("size up", None),
    ("size down", None),
    ("runs small", None),
    ("runs large", None),
    ("fitting tight", None),
    ("fitting loose", None),
    ("shoulder fit", None),
    ("bust size", None),
    ("waist size", None),
    ("size guide", None),

    # Return/Exchange (require friction context — not "hassle free returns")
    ("had to return", None),
    ("returned it", None),
    ("return because", None),
    ("exchange because", None),
    ("return policy made me", None),
    ("afraid to return", None),
    ("return process", None),
    ("return fear", None),

    # Fabric / quality hesitation
    ("see through", None),
    ("see-through", None),
    ("fabric quality", None),
    ("fabric is", None),
    ("material is", None),
    ("material looks", None),
    ("kapda", None),
    ("cloth quality", None),
    ("sheer fabric", None),
    ("transparent fabric", None),
    ("lining missing", None),
    ("no lining", None),

    # Photo / Reality discrepancy
    ("different from photo", None),
    ("different from picture", None),
    ("different in real", None),
    ("color different", None),
    ("colour different", None),
    ("not like image", None),
    ("misleading photo", None),
    ("looks different", None),

    # Comparison / shortlisting
    ("comparing", None),
    ("cant decide", None),
    ("can't decide", None),
    ("confused between", None),
    ("which one to buy", None),

    # Social validation
    ("asked friend", None),
    ("asked my friend", None),
    ("show my friend", None),
    ("getting opinion", None),
    ("whatsapp to decide", None),

    # Occasion / timing hesitation
    ("waiting for occasion", None),
    ("waiting for wedding", None),
    ("delivery before", None),
    ("will it arrive before", None),
    ("need it for", None),
]

# Quick single-token lookup for fast early filtering
WISHLIST_PRIMARY_TOKENS = set()
for pair in WISHLIST_KEYWORD_PAIRS:
    WISHLIST_PRIMARY_TOKENS.add(pair[0])


def sanitize_text(text: str) -> str:
    """Remove PII: phone numbers, order IDs, email addresses."""
    if not text:
        return text
    # Remove Indian mobile numbers (10 digits, optionally +91 prefix)
    text = re.sub(r'(\+91[\-\s]?)?[6-9]\d{9}', '[PHONE]', text)
    # Remove Myntra order IDs (OD followed by digits)
    text = re.sub(r'\bOD\d{9,}\b', '[ORDER_ID]', text, flags=re.IGNORECASE)
    # Remove email addresses
    text = re.sub(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', '[EMAIL]', text)
    return text


def matches_wishlist_keywords(text: str) -> str | None:
    """
    Returns the matched keyword phrase if text contains a high-intent
    wishlist/friction signal. Uses multi-token patterns to avoid false
    positives. Returns None if no relevant signal found.
    """
    if not text or len(text.strip()) < 15:
        return None
    lower_text = text.lower()
    for primary, context in WISHLIST_KEYWORD_PAIRS:
        if primary in lower_text:
            if context is None:
                return primary
            elif context in lower_text:
                return f"{primary}+{context}"
    return None


def get_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in environment variables.")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def upsert_raw_feedback(records: list[dict]) -> int:
    """
    Upserts a list of raw feedback records into the Supabase raw_feedback table.
    Sanitizes PII and enforces text length limits before writing.
    Uses external_id to prevent duplicates on conflict.
    """
    if not records:
        return 0

    MIN_CHARS = 20
    MAX_CHARS = 1500

    # Sanitize and filter
    clean_records = []
    for r in records:
        text = r.get("text", "") or ""
        text = sanitize_text(text.strip())
        # Enforce length bounds
        if len(text) < MIN_CHARS:
            continue
        if len(text) > MAX_CHARS:
            text = text[:MAX_CHARS] + "..."
        r["text"] = text
        clean_records.append(r)

    if not clean_records:
        return 0

    supabase = get_supabase_client()
    try:
        batch_size = 100
        total_upserted = 0
        for i in range(0, len(clean_records), batch_size):
            batch = clean_records[i:i + batch_size]
            supabase.table("raw_feedback").upsert(
                batch,
                on_conflict="external_id"
            ).execute()
            total_upserted += len(batch)
        return total_upserted
    except Exception as e:
        print(f"[ERROR] Failed to upsert batch to Supabase: {e}")
        return 0
