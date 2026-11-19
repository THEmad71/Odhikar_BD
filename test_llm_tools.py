
from src.odhikar.llm import llm_with_tools
from src.odhikar.langchain_tools import ODHIKAR_TOOLS

from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    ToolMessage
)


# ==========================================
# 1. DISPLAY AVAILABLE TOOLS
# ==========================================

print("\n--- AVAILABLE TOOLS ---")

for tool in ODHIKAR_TOOLS:
    print(tool.name)


# ==========================================
# 2. PREPARE MESSAGES
# ==========================================

messages = [
    SystemMessage(
        content="""
        You are Odhikar BD.

        For Bangladesh traffic law questions,
        use the relevant available tool.

        Do not invent legal information.
        """
    ),

    HumanMessage(
        content="""
        Find the maximum fine and imprisonment
        for riding a motorcycle without wearing
        a helmet in Bangladesh.
        """
    )
]


# ==========================================
# 3. INVOKE GEMINI
# ==========================================

print("\n--- GEMINI TOOL CALLING TEST ---")

response = llm_with_tools.invoke(messages)

print("\nModel Response:")
print(response.content)


# ==========================================
# 4. CHECK TOOL CALLS
# ==========================================

print("\n--- REQUESTED TOOL CALLS ---")

print(response.tool_calls)


# ==========================================
# 5. EXECUTE TOOLS MANUALLY
# ==========================================

if response.tool_calls:

    print("\n--- EXECUTING TOOLS ---")

    tool_results = []

    for call in response.tool_calls:

        tool = next(
            (
                item for item in ODHIKAR_TOOLS
                if item.name == call["name"]
            ),
            None
        )

        if tool is None:
            print("Tool not found:", call["name"])
            continue

        result = tool.invoke(call["args"])

        tool_message = ToolMessage(
            content=str(result),
            tool_call_id=call["id"],
            name=tool.name
        )

        tool_results.append(tool_message)

        print("\nTool:", tool.name)
        print("Result:", result)


    # ======================================
    # 6. ASK GEMINI TO PROCESS TOOL RESULTS
    # ======================================

    print("\n--- FINAL GEMINI RESPONSE ---")

    final_response = llm_with_tools.invoke(
        messages + [response] + tool_results
    )

    print(final_response.content)

    print("\nGEMINI TOOL TEST SUCCESSFUL!")

else:

    print("\nNo tool call generated.")

    print("Check model response and tool instructions.")
