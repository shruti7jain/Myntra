import os
import re
import json

TARGET_NUMBERS = ['1506', '1486', '207', '223', '268', '1299', '1283', '1223', '38', '24', '18', '12', '8', '68', '13', '11', '45']

SEARCH_FILES = [
    'frontend/app/page.js',
    'frontend/app/api/insights/route.js',
    'frontend/app/api/chat/route.js',
    'frontend/app/api/verbatims/route.js',
    'frontend/lib/supabase.js'
]

ROOT_DIR = os.getcwd()
findings = []

for relpath in SEARCH_FILES:
    fpath = os.path.join(ROOT_DIR, relpath)
    if not os.path.exists(fpath):
        continue
    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    for idx, line in enumerate(lines):
        for num in TARGET_NUMBERS:
            pattern = r'(?<!\w)' + re.escape(num) + r'(?!\w)'
            if re.search(pattern, line):
                # Classify
                classification = "A. Legitimate static / UI token"
                line_str = line.strip()
                if num in ['1486', '207', '223', '268', '1299', '1283', '1223'] and not line_str.startswith('//'):
                    classification = "B. Hardcoded analytical value"
                elif line_str.startswith('//') or 'comment' in line_str:
                    classification = "D. Historical / commentary text"
                elif 'pct' in line_str or 'count' in line_str:
                    if 'Math.round' in line_str or 'reduce' in line_str or 'sum' in line_str:
                        classification = "C. Calculated value"
                
                findings.append({
                    "file": relpath,
                    "line": idx + 1,
                    "number": num,
                    "classification": classification,
                    "code": line_str
                })

print(f"Total active codebase matches found: {len(findings)}")
for f in findings:
    print(f"[{f['classification']}] {f['file']}:{f['line']} (num: {f['number']}) -> {f['code']}")
