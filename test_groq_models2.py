import os, json
from dotenv import load_dotenv
load_dotenv(r'c:\Users\shrut\Downloads\M\.env')

from groq import Groq
client = Groq(api_key=os.getenv('GROQ_API_KEY'))

system = """You are an expert E-Commerce VoC Intelligence Classifier for Myntra fashion.
Classify each customer review in the input JSON array into structured friction signals.
Respond ONLY with a raw JSON array. No text before or after.
[{"id":<id>,"theme":"theme_key","intent_type":"intent"}]
Themes: fabric_quality_ambiguity, fit_sizing_anxiety, visual_reality_discrepancy, occasion_timing_delay, styling_pairing_doubt, choice_paralysis_shortlist, social_validation_delay, unrelated_other"""

batch = [
    {"id": 1, "text": "I like this dress but I am not sure about the fabric quality before buying"},
    {"id": 2, "text": "I bought this kurti and the size was wrong"}
]

for model_id in ['openai/gpt-oss-120b', 'qwen/qwen3.6-27b', 'qwen/qwen3.8-27b', 'groq/compound', 'groq/compound-mini']:
    print(f'\n--- Testing: {model_id} ---')
    try:
        resp = client.chat.completions.create(
            model=model_id,
            messages=[
                {'role':'system','content':system},
                {'role':'user','content':json.dumps(batch)}
            ],
            max_tokens=500,
            temperature=0.05
        )
        raw = resp.choices[0].message.content
        finish = resp.choices[0].finish_reason
        usage = resp.usage
        print(f'finish_reason: {finish}')
        print(f'completion_tokens: {usage.completion_tokens}')
        print(f'response: {raw[:300]}')
        # Try parsing
        start = raw.find('[')
        end = raw.rfind(']')
        if start != -1 and end > start:
            try:
                parsed = json.loads(raw[start:end+1])
                print(f'PARSED OK: {len(parsed)} items')
            except Exception as pe:
                print(f'PARSE ERROR: {pe}')
        else:
            print('No JSON array found')
    except Exception as e:
        print(f'ERROR: {type(e).__name__}: {e}')
