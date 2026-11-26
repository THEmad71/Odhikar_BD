
from langchain_google_genai import ChatGoogleGenerativeAI
from src.odhikar.config import settings

# Check API key
if not settings.gemini_api_key:
    raise ValueError("Gemini API key not found!")

# Create Gemini model
llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite",
    google_api_key=settings.gemini_api_key,
    temperature=0
)

# Send a question
response = llm.invoke(
    "What is the capital of Bangladesh?"
)

# Display answer
print("Gemini Response:")
print(response.content)

# Display token usage
print("\nToken Usage:")
print(response.usage_metadata)
