from ingestion.common import get_supabase_client
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ingestion'))
from common import get_supabase_client

s = get_supabase_client()
rows = s.table('insights').select('theme_label, mention_count, pct_of_total, sample_quotes').order('mention_count', desc=True).execute().data

print("=" * 80)
print(f"LIVE VERIFICATION: {len(rows)} THEMES IN SUPABASE `insights` TABLE")
print("=" * 80)
for r in rows:
    quote = r['sample_quotes'][0][:75] if r.get('sample_quotes') else "No quote"
    print(f"  • {r['theme_label']:<40} : {r['mention_count']:>4} ({r['pct_of_total']:>5}%) | \"{quote}...\"")
print("=" * 80)
