import os, json, time
from dotenv import load_dotenv
load_dotenv(r'c:\Users\shrut\Downloads\M\.env')

from groq import Groq
client = Groq(api_key=os.getenv('GROQ_API_KEY'))

# Test 1: What does openai/gpt-oss-20b actually return for a real classification task?
print('=== TEST 1: openai/gpt-oss-20b response inspection ===')
try:
    resp = client.chat.completions.create(
        model='openai/gpt-oss-20b',
        messages=[
            {'role':'system','content':'You are a classifier. Respond ONLY with a raw JSON array.'},
            {'role':'user','content':'[{"id": 1, "text": "I like this dress but not sure about the fabric quality"}]'}
        ],
        max_tokens=200,
        temperature=0.05
    )
    raw = resp.choices[0].message.content
    print(f'Raw response (repr): {repr(raw)}')
    print(f'Length: {len(raw)}')
    print(f'Contains [: {"[" in raw}')
    finish_reason = resp.choices[0].finish_reason
    print(f'Finish reason: {finish_reason}')
    usage = resp.usage
    print(f'Usage - prompt: {usage.prompt_tokens}, completion: {usage.completion_tokens}')
except Exception as e:
    print(f'ERROR: {type(e).__name__}: {e}')

# Test 2: List available models
print('\n=== TEST 2: Available models on this account ===')
try:
    models = client.models.list()
    for m in models.data:
        print(f'  {m.id}')
except Exception as e:
    print(f'ERROR listing models: {type(e).__name__}: {e}')
