
import json

from langchain_core.messages import (
    HumanMessage,
    ToolMessage
)

from src.odhikar.llm import llm_with_tools
from src.odhikar.langchain_tools import ODHIKAR_TOOLS


# Helper: Extract readable text from Gemini response
def extract_text(content):

    if isinstance(content, str):
        return content

    answer = ""

    if isinstance(content, list):

        for block in content:

            if isinstance(block, dict) and block.get("type") == "text":
                answer += block.get("text", "") + "\n"

    return answer.strip()


# 1. Create tool registry
tools_by_name = {
    tool.name: tool
    for tool in ODHIKAR_TOOLS
}


# 2. User query
query = """
What is the maximum fine for riding a motorcycle
without wearing a helmet in Bangladesh?
"""


# 3. Send query to Gemini
print("\n--- STEP 1: GEMINI RESPONSE ---")

messages = [
    HumanMessage(content=query)
]

ai_response = llm_with_tools.invoke(messages)

print("Content:", ai_response.content)
print("Tool Calls:", ai_response.tool_calls)


# 4. Execute requested tools
if ai_response.tool_calls:

    # Add Gemini's tool-call message to conversation
    messages.append(ai_response)

    for tool_call in ai_response.tool_calls:

        tool_name = tool_call["name"]

        print("\n--- STEP 2: EXECUTING TOOL ---")
        print("Selected Tool:", tool_name)

        selected_tool = tools_by_name.get(tool_name)

        if selected_tool is None:

            tool_result = {
                "error": f"Tool '{tool_name}' was not found."
            }

        else:

            try:
                tool_result = selected_tool.invoke(
                    tool_call["args"]
                )

            except Exception as e:

                tool_result = {
                    "error": str(e)
                }

        print("Tool Result:", tool_result)

        # Send tool result back to conversation
        messages.append(
            ToolMessage(
                content=json.dumps(
                    tool_result,
                    ensure_ascii=False,
                    default=str
                ),
                tool_call_id=tool_call["id"]
            )
        )


    # 5. Send tool result back to Gemini
    print("\n--- STEP 3: FINAL GEMINI RESPONSE ---")

    final_response = llm_with_tools.invoke(messages)

    # Extract readable answer
    answer = extract_text(final_response.content)

    print("\n--- FINAL RESPONSE DEBUG ---")

    print("Full Response:")
    final_response.pretty_print()

    print("\nTool Calls:")
    print(final_response.tool_calls)

    print("\n--- FINAL ANSWER ---")
    print(answer)


else:

    # Gemini answered without requesting a tool
    answer = extract_text(ai_response.content)

    print("\n--- DIRECT GEMINI ANSWER ---")
    print(answer)


print("\n--- EXECUTION COMPLETED ---")
