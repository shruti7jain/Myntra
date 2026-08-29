import os
from dotenv import load_dotenv
load_dotenv(r'c:\Users\shrut\Downloads\M\.env')

key = os.getenv('GROQ_API_KEY', '')
print(f'GROQ_API_KEY present: {bool(key)}')
print(f'Starts with gsk_: {key.startswith("gsk_")}')
print(f'Length: {len(key)}')

from groq import Groq
client = Groq(api_key=key)

print('\n--- Testing model: openai/gpt-oss-20b ---')
try:
    resp = client.chat.completions.create(
        model='openai/gpt-oss-20b',
        messages=[{'role':'user','content':'Say HELLO in one word.'}],
        max_tokens=10,
        temperature=0
    )
    print(f'RESPONSE: {resp.choices[0].message.content}')
    print('STATUS: WORKING')
except Exception as e:
    print(f'ERROR: {type(e).__name__}: {e}')

print('\n--- Testing model: llama-3.3-70b-versatile ---')
try:
    resp2 = client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[{'role':'user','content':'Say HELLO in one word.'}],
        max_tokens=10,
        temperature=0
    )
    print(f'RESPONSE: {resp2.choices[0].message.content}')
    print('STATUS: WORKING')
except Exception as e2:
    print(f'ERROR: {type(e2).__name__}: {e2}')

print('\n--- Testing model: llama3-8b-8192 ---')
try:
    resp3 = client.chat.completions.create(
        model='llama3-8b-8192',
        messages=[{'role':'user','content':'Say HELLO in one word.'}],
        max_tokens=10,
        temperature=0
    )
    print(f'RESPONSE: {resp3.choices[0].message.content}')
    print('STATUS: WORKING')
except Exception as e3:
    print(f'ERROR: {type(e3).__name__}: {e3}')
