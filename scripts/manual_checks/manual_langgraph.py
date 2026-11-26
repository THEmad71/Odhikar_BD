
from langchain_core.messages import HumanMessage

from src.odhikar.graph import odhikar_graph


# 1. User Query
query = """
What is the maximum fine for riding a motorcycle
without wearing a helmet in Bangladesh?
"""


# 2. Invoke LangGraph
print("\n--- LANGGRAPH EXECUTION ---")

result = odhikar_graph.invoke({
    "messages": [
        HumanMessage(content=query)
    ]
})


# 3. Display All Messages
print("\n--- CONVERSATION HISTORY ---")

for message in result["messages"]:

    print("\nMessage Type:", type(message).__name__)

    print("Content:", message.content)

    if getattr(message, "tool_calls", None):
        print("Tool Calls:", message.tool_calls)


# 4. Display Final Answer
final_message = result["messages"][-1]

print("\n--- FINAL ANSWER ---")

if isinstance(final_message.content, str):

    print(final_message.content)

elif isinstance(final_message.content, list):

    for block in final_message.content:

        if isinstance(block, dict) and block.get("type") == "text":
            print(block.get("text", ""))


print("\n--- LANGGRAPH TEST COMPLETED ---")
