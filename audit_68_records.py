import os
from dotenv import load_dotenv
load_dotenv(r'c:\Users\shrut\Downloads\M\.env')
from supabase import create_client
from collections import Counter

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))

# The 68 gap = records in raw_feedback with classification_method=NULL
null_method = []
offset = 0
while True:
    res = supabase.table('raw_feedback').select(
        'id, platform, theme, rating, classification_method, is_processed, scraped_at, keyword_matched, text'
    ).is_('classification_method', 'null').range(offset, offset + 999).execute()
    data = res.data or []
    null_method.extend(data)
    if len(data) < 1000:
        break
    offset += 1000

print(f'Records with classification_method=NULL: {len(null_method)}')

print('\nTheme distribution:')
for t, c in Counter([r.get('theme') for r in null_method]).most_common():
    print(f'  theme={repr(t)}: {c}')

print('\nis_processed distribution:')
for v, c in Counter([r.get('is_processed') for r in null_method]).most_common():
    print(f'  is_processed={v}: {c}')

print('\nPlatform distribution:')
for p, c in Counter([r.get('platform') for r in null_method]).most_common():
    print(f'  platform={p}: {c}')

print('\nKeyword_matched distribution (top 10):')
for k, c in Counter([r.get('keyword_matched') for r in null_method]).most_common(10):
    print(f'  keyword={repr(k)}: {c}')

processed_among = [r for r in null_method if r.get('is_processed') is True]
print(f'\nis_processed=True among null-method records: {len(processed_among)}')
theme_set = [r for r in processed_among if r.get('theme') is not None]
print(f'  ...with a theme set: {len(theme_set)}')

dates = [str(r.get('scraped_at') or '')[:10] for r in null_method]
print('\nscraped_at date distribution:')
for d, c in Counter(dates).most_common():
    print(f'  {d}: {c}')

print('\nSAMPLE RECORDS (first 5):')
for r in null_method[:5]:
    rid = r.get('id')
    plat = r.get('platform')
    theme = r.get('theme')
    proc = r.get('is_processed')
    kw = r.get('keyword_matched')
    dt = str(r.get('scraped_at') or '')[:10]
    txt = str(r.get('text') or '')[:120]
    print(f'  ID={rid} plat={plat} theme={theme} processed={proc} kw={kw} date={dt}')
    print(f'  text: {txt}')
    print()
