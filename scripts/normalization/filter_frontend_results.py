import json

with open("number_search_results.json", "r", encoding="utf-8") as f:
    results = json.load(f)

frontend_results = [r for r in results if r['file'].startswith('frontend')]
print(f"Total frontend occurrences: {len(frontend_results)}")
for r in frontend_results:
    print(f"{r['file']}:{r['line_number']} [{r['matched_number']}] -> {r['line_content']}")
