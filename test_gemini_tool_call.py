
import json

from langchain_core.messages import (
    HumanMessage,
    ToolMessage
)

from src.odhikar.llm import llm_with_tools

from src.odhikar.langchain_tools import ODHIKAR_TOOLS


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

    messages.append(ai_response)

    for tool_call in ai_response.tool_calls:

        tool_name = tool_call["name"]

        print("\n--- STEP 2: EXECUTING TOOL ---")
        print("Selected Tool:", tool_name)

        selected_tool = tools_by_name.get(tool_name)

        if selected_tool is None:

            tool_result = {
                "error": "Requested tool was not found."
            }

        else:

            tool_result = selected_tool.invoke(
                tool_call["args"]
            )

        print("Tool Result:", tool_result)

        # Send tool result back to conversation
        messages.append(
            ToolMessage(
                content=json.dumps(
                    tool_result,
                    ensure_ascii=False
                ),
                tool_call_id=tool_call["id"]
            )
        )


    # 5. Send tool result back to Gemini
    print("\n--- STEP 3: FINAL GEMINI RESPONSE ---")

    final_response = llm_with_tools.invoke(messages)



    print("\n--- FINAL RESPONSE DEBUG ---")

    print("Full Response:")
    final_response.pretty_print()

    print("\nContent:")
    # Extract readable text from Gemini response

    answer = ""

    if isinstance(final_response.content, str):

        answer = final_response.content

    elif isinstance(final_response.content, list):

        for block in final_response.content:

            if isinstance(block, dict) and block.get("type") == "text":

                answer += block.get("text", "") + "\n"


print("\n--- FINAL ANSWER ---")
print(answer.strip())

    print("\nTool Calls:")
    print(final_response.tool_calls)




else:

    print("Gemini did not request any tool.")

print("\n--- EXECUTION COMPLETED ---")
