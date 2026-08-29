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
#
# AUDIT NOTE (2026-08-29): Bare "return" and "exchange" were previously the
# top 2 matched keywords (65.4% + 9.7% = 75.2% of all ingested records) and
# produced almost exclusively post-purchase complaint content classified as
# unrelated_other. They have been REMOVED from this list and replaced with
# friction-context-qualified variants that require a pre-purchase signal.
# ---------------------------------------------------------------------------
WISHLIST_KEYWORD_PAIRS = [
    # -----------------------------------------------------------------------
    # Wishlist / Save / Shortlist behaviour (direct evidence of pre-purchase intent)
    # -----------------------------------------------------------------------
    ("wishlist", None),
    ("wish list", None),
    ("save for later", None),
    ("saved item", None),
    ("saved it", None),
    ("bookmark", None),
    ("buy later", None),
    ("shortlist", None),
    ("shortlisted", None),
    ("considering buying", None),
    ("thinking of buying", None),
    ("want to buy but", None),
    ("planning to buy", None),
    ("baad mein kharidna", None),          # Hindi: will buy later
    ("baad mein dekhna", None),            # Hindi: will check later
    ("kharidunga baad mein", None),        # Hindi: will buy later

    # -----------------------------------------------------------------------
    # Fit & Sizing PRE-PURCHASE uncertainty
    # -----------------------------------------------------------------------
    ("size chart", None),
    ("size guide", None),
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
    ("size small", None),
    ("wrong size", None),
    ("not fit", None),
    ("size issue", None),
    ("which size", None),
    ("what size", None),
    ("size confusion", None),
    ("unsure about size", None),
    ("size mismatch", None),

    # -----------------------------------------------------------------------
    # Return/Exchange — ONLY friction-context-qualified variants
    # (Requires a pre-purchase signal; bare "return"/"exchange" removed)
    # -----------------------------------------------------------------------
    ("afraid to return", None),
    ("return fear", None),
    ("return policy made me", None),
    ("hesitant to buy because return", None),
    ("no return policy", None),
    ("non-returnable", None),

    # -----------------------------------------------------------------------
    # Fabric / quality PRE-PURCHASE hesitation
    # -----------------------------------------------------------------------
    ("see through", None),
    ("see-through", None),
    ("fabric quality", None),
    ("fabric is", None),
    ("material is", None),
    ("material looks", None),
    ("kapda", None),                        # Hindi: fabric/cloth
    ("cloth quality", None),
    ("sheer fabric", None),
    ("transparent fabric", None),
    ("lining missing", None),
    ("no lining", None),
    ("thin material", None),
    ("cheap fabric", None),
    ("material kaisa", None),              # Hindi: how is the material
    ("kapda kaisa", None),                 # Hindi: how is the cloth

    # -----------------------------------------------------------------------
    # Photo / Reality discrepancy (pre-purchase fear)
    # -----------------------------------------------------------------------
    ("different from photo", None),
    ("different from picture", None),
    ("different in real", None),
    ("color different", None),
    ("colour different", None),
    ("not like image", None),
    ("misleading photo", None),
    ("looks different", None),
    ("photo pe alag", None),               # Hindi: different from photo
    ("image se alag", None),               # Hindi: different from image
    ("real mein", None),                   # Hindi: in real life

    # -----------------------------------------------------------------------
    # Price / Deal timing (waiting for a better price — explicit pre-purchase)
    # -----------------------------------------------------------------------
    ("wait for sale", None),
    ("wait for discount", None),
    ("price drop", None),
    ("price too high", None),
    ("out of budget", None),
    ("too expensive", None),
    ("wait for offer", None),
    ("discount pe", None),                  # Hindi: at a discount
    ("sale mein lena", None),              # Hindi: will buy in sale
    ("coupon chahiye", None),              # Hindi: need a coupon

    # -----------------------------------------------------------------------
    # Comparison / shortlisting (choice paralysis)
    # -----------------------------------------------------------------------
    ("comparing", None),
    ("cant decide", None),
    ("can't decide", None),
    ("confused between", None),
    ("which one to buy", None),
    ("dono mein se", None),               # Hindi: from both of these
    ("ek choose karna", None),            # Hindi: choosing one

    # -----------------------------------------------------------------------
    # Social validation (seeking external opinion before buying)
    # -----------------------------------------------------------------------
    ("asked friend", None),
    ("asked my friend", None),
    ("show my friend", None),
    ("getting opinion", None),
    ("whatsapp to decide", None),
    ("friend se poochna", None),          # Hindi: will ask friend
    ("family se poochna", None),          # Hindi: will ask family

    # -----------------------------------------------------------------------
    # Occasion / timing hesitation (saving for a specific event)
    # -----------------------------------------------------------------------
    ("waiting for occasion", None),
    ("waiting for wedding", None),
    ("will it arrive before", None),
    ("need it for", None),
    ("buy for wedding", None),
    ("buy for party", None),
    ("saving for trip", None),
    ("shaadi ke liye", None),             # Hindi: for the wedding
    ("function ke liye", None),           # Hindi: for the function
    ("event ke liye", None),              # Hindi: for the event

    # -----------------------------------------------------------------------
    # Styling / pairing uncertainty
    # -----------------------------------------------------------------------
    ("how to style", None),
    ("what to pair", None),
    ("pair with", None),
    ("match with", None),
    ("outfit ideas", None),
    ("styling suggestions", None),
    ("kya pehnu", None),                  # Hindi: what should I wear
    ("kiske saath match", None),          # Hindi: what does it match with
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
