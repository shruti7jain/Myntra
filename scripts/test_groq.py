from dotenv import load_dotenv
import os, json, re
load_dotenv()
from groq import Groq

key = os.getenv('GROQ_API_KEY')
client = Groq(api_key=key)

# Test models WITHOUT response_format (use prompt-based JSON extraction)
test_models = [
    'qwen/qwen3.6-27b',
    'openai/gpt-oss-120b',
    'openai/gpt-oss-20b',
    'groq/compound',
]

system_prompt = """You are a fashion review classifier. Respond with ONLY a valid JSON object, no markdown, no explanation.
Example output: {"theme": "fit_sizing_anxiety", "clearest_quote": "exact text", "category": "Ethnic Wear", "is_relevant_friction": true, "intent_type": "high_intent_blocked"}"""

test_prompt = 'Review: "The kurti looks good but the sizing is completely off — I ordered M and it is way too tight on the shoulders and bust."'

def extract_json(text):
    """Try to parse JSON from model output, handling markdown fences."""
    text = text.strip()
    # Strip markdown code fences
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    # Find JSON object
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return json.loads(text)

for model in test_models:
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': test_prompt}
            ],
            temperature=0.05,
            max_tokens=200,
        )
        raw = resp.choices[0].message.content.strip()
        parsed = extract_json(raw)
        print(f'OK  [{model}]')
        print(f'     theme={parsed.get("theme")}')
        print(f'     quote={parsed.get("clearest_quote","")[:60]}')
        print(f'     intent={parsed.get("intent_type")}')
    except json.JSONDecodeError as e:
        raw_out = resp.choices[0].message.content[:150] if 'resp' in dir() else 'N/A'
        print(f'JSON_ERR [{model}]: {e} | raw: {raw_out}')
    except Exception as e:
        print(f'ERR [{model}]: {str(e)[:120]}')
