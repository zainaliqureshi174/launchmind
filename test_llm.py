import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

print("Testing Groq...")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
response = client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[{"role": "user", "content": "Say hello from LaunchMind in one sentence."}]
)
print(f"Groq: {response.choices[0].message.content}")