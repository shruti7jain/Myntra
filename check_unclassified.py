import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.getcwd(), '.env'))
from supabase import create_client
from collections import Counter

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

# Get all records with theme=None (unclassified)
unclassified = []
offset = 0
while True:
    res = supabase.table('raw_feedback').select('id, platform, is_processed, theme, scraped_at').is_('theme', 'null').range(offset, offset + 999).execute()
    data = res.data or []
    unclassified.extend(data)
    if len(data) < 1000:
        break
    offset += 1000

print(f'Total unclassified (theme=NULL): {len(unclassified)}')
print(f'Of those, is_processed=True: {sum(1 for x in unclassified if x["is_processed"] is True)}')
print(f'Of those, is_processed=False: {sum(1 for x in unclassified if x["is_processed"] is False)}')
print(f'Of those, is_processed=NULL: {sum(1 for x in unclassified if x["is_processed"] is None)}')
print()

# Check for records where is_processed=False but theme IS assigned
unproc_with_theme = []
offset = 0
while True:
    res = supabase.table('raw_feedback').select('id, theme, is_processed').eq('is_processed', False).range(offset, offset + 999).execute()
    data = res.data or []
    unproc_with_theme.extend(data)
    if len(data) < 1000:
        break
    offset += 1000

print(f'Total is_processed=False: {len(unproc_with_theme)}')
print(f'Of those with theme=NULL: {sum(1 for x in unproc_with_theme if x["theme"] is None)}')
print(f'Theme distribution for is_processed=False:')
print(Counter([x.get('theme') for x in unproc_with_theme]))
print()

# Breakdown: are the 68 new records in is_processed=False?
# The 264 unprocessed records should account for most of the 68 new ones
# Let's also check if the insights table needs to be rebuilt
print("SUMMARY:")
print(f"1574 total raw_feedback records")
print(f"1310 are marked is_processed=True (have themes assigned)")
print(f"264 are marked is_processed=False (may or may not have themes)")
print(f"78 have theme=NULL (truly unclassified)")
print()
print(f"This suggests that 264 - 78 = {264-78} records have is_processed=False but DO have themes.")
print(f"These {264-78} may be records flagged for re-review or updates.")
