import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("No API key found in .env")
    exit()

print("Using API Key:", api_key[:10] + "...(hidden)")
genai.configure(api_key=api_key)

try:
    print("\n--- Available Models ---")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"Name: {m.name}")
            
    print("\n✅ API Key is working and has access to the above models.")
except Exception as e:
    print("❌ Failed to list models. Error:", str(e))
