import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIT_FILE = ROOT / 'out_fit.json'
FABRIC_FILE = ROOT / 'out_fabric.json'
OUT_CSV = ROOT / 'audit_classified.csv'

post_re = re.compile(r"\b(order(ed|s)?|ordered|delivered|received|return(ed|s)?|refund(ed|s)?|exchange(d|s|es)?|pickup|picked up|requested|cancel(le|led)|returned|refunded|was delivered|i received|i ordered|i got|got my)\b", re.I)
pre_re = re.compile(r"\b(not sure if|not sure|unsure|hesitat|hesitate|wishlist|wishlisted|wish list|considering|thinking of|thinking about|wonder if|can't decide|can't tell|will it fit|will it)\b", re.I)

def load(path):
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding='utf-8'))

def classify_text(text: str) -> str:
    t = (text or '').lower()
    if post_re.search(t):
        return 'POST-PURCHASE'
    if pre_re.search(t):
        return 'PRE-PURCHASE'
    # fallback heuristics: presence of first-person past/present purchase verbs
    if re.search(r"\b(i ordered|i bought|i purchased|i received|was delivered|delivered|received|got|my order|order was)\b", t):
        return 'POST-PURCHASE'
    # default to POST (most reviews describe experiences)
    return 'POST-PURCHASE'

def main():
    fit = load(FIT_FILE)
    fabric = load(FABRIC_FILE)
    all_rows = fit + fabric

    rows = []
    counts = {'POST-PURCHASE':0, 'PRE-PURCHASE':0}
    for r in all_rows:
        cls = classify_text(r.get('text',''))
        counts[cls] += 1
        rows.append({'id': r.get('id'), 'platform': r.get('platform'), 'theme': r.get('theme'), 'text': r.get('text','').replace('\n',' '), 'class': cls})

    total = len(rows)
    with OUT_CSV.open('w', encoding='utf-8') as f:
        f.write('id,platform,theme,class,text\n')
        for r in rows:
            # naive csv escaping
            text = '"' + r['text'].replace('"','""') + '"'
            f.write(f"{r['id']},{r['platform']},{r['theme']},{r['class']},{text}\n")

    print(f"TOTAL={total}")
    for k in ['POST-PURCHASE','PRE-PURCHASE']:
        v = counts[k]
        pct = (v/total*100) if total>0 else 0
        print(f"{k}: {v} ({pct:.2f}%)")

if __name__ == '__main__':
    main()
