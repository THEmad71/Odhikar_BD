
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from src.odhikar.config import settings


# 1. Create Gemini model
llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite",
    google_api_key=settings.gemini_api_key,
    temperature=0
)


# 2. Create prompt template
prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are Odhikar BD, a helpful legal information assistant. "
        "Answer in simple language."
    ),
    (
        "human",
        "{question}"
    )
])


# 3. Connect prompt and model
chain = prompt | llm


# 4. Invoke the complete chain
response = chain.invoke({
    "question": "What is a driving licence?"
})


# 5. Display response
print("\nOdhikar BD Response:")

if isinstance(response.content, str):
    print(response.content)
else:
    for block in response.content:
        if isinstance(block, dict) and block.get("type") == "text":
            print(block["text"])


# 6. Display token usage
print("\nToken Usage:")
print(response.usage_metadata)
