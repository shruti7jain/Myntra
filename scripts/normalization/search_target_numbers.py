import os
import re
import json

TARGET_NUMBERS = ['1506', '1486', '207', '223', '268', '68%', '13%', '11%', '8%', '18%', '12%', '38%', '24%', '38', '24', '18', '12', '68', '13', '11', '8']

SEARCH_DIRS = ['frontend', 'scripts']
ROOT_DIR = os.getcwd()

results = []

for sdir in SEARCH_DIRS:
    full_sdir = os.path.join(ROOT_DIR, sdir)
    for root, dirs, files in os.walk(full_sdir):
        # skip node_modules and .next
        if 'node_modules' in root or '.next' in root or '__pycache__' in root:
            continue
        for file in files:
            if file.endswith(('.js', '.jsx', '.ts', '.tsx', '.py', '.json', '.sql')):
                fpath = os.path.join(root, file)
                relpath = os.path.relpath(fpath, ROOT_DIR)
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                    for idx, line in enumerate(lines):
                        for num in TARGET_NUMBERS:
                            # check if num appears as distinct word / token
                            pattern = r'(?<!\w)' + re.escape(num) + r'(?!\w)'
                            if re.search(pattern, line):
                                results.append({
                                    "file": relpath,
                                    "line_number": idx + 1,
                                    "matched_number": num,
                                    "line_content": line.strip()
                                })
                except Exception as e:
                    pass

with open("number_search_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print(f"Found {len(results)} occurrences across repository.")
