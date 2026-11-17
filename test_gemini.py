
import time
from google import genai
from google.genai import types
from src.odhikar.config import settings

client = genai.Client(
    api_key=settings.gemini_api_key
)

print("Sending request to Gemini...")

start = time.perf_counter()

response = client.models.generate_content(
    model="gemini-3.1-flash-lite",
    contents="what is the capital of Bangladesh?",
    config=types.GenerateContentConfig(
        max_output_tokens=50
    )
)

elapsed = time.perf_counter() - start

print("Response:", response.text)
print(f"Response time: {elapsed:.2f} seconds")


print("\n--- Token Usage ---")

usage = response.usage_metadata

if usage:
    print("Input tokens:", usage.prompt_token_count)
    print("Output tokens:", usage.candidates_token_count)
    print("Total tokens:", usage.total_token_count)
