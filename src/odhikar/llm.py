
from langchain_google_genai import ChatGoogleGenerativeAI

from src.odhikar.config import settings

from src.odhikar.langchain_tools import ODHIKAR_TOOLS


# 1. Initialize Gemini model
llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite",
    google_api_key=settings.gemini_api_key,
    temperature=0
)


# 2. Bind Odhikar BD tools with Gemini
llm_with_tools = llm.bind_tools(ODHIKAR_TOOLS)
