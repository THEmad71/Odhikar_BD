
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
        "Answer clearly and simply. Never invent legal information."
    ),
    (
        "human",
        "User question: {question}"
    )
])


# 3. Insert question into template
messages = prompt.invoke({
    "question": "What is a driving licence?"
})


# 4. Send formatted prompt to Gemini
response = llm.invoke(messages)


# 5. Display answer
print("Gemini Response:")

for block in response.content:
    if block["type"] == "text":
        print(block["text"])
