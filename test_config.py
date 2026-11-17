
from src.odhikar.config import settings

print("Odhikar BD Configuration Test")
print("--------------------------------")

print("App Environment:", settings.app_env)
print("LangSmith Project:", settings.langsmith_project)
print("LangSmith Tracing:", settings.langsmith_tracing)

print("Gemini API key configured:", bool(settings.gemini_api_key))

print("--------------------------------")
print("Configuration loaded successfully!")
