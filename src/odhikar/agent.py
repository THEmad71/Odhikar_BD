
import json

from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    ToolMessage
)

from src.odhikar.llm import llm_with_tools
from src.odhikar.langchain_tools import ODHIKAR_TOOLS


# 1. Create tool registry
tools_by_name = {
    tool.name: tool
    for tool in ODHIKAR_TOOLS
}


# 2. Extract readable text from Gemini response
def extract_text(content):

    if isinstance(content, str):
        return content

    answer = ""

    if isinstance(content, list):

        for block in content:

            if isinstance(block, dict) and block.get("type") == "text":

                answer += block.get("text", "") + "\n"

    return answer.strip()


# 3. Main Odhikar AI function
def ask_odhikar(
    query: str,
    max_tool_rounds: int = 5
) -> str:

    # Validate input
    if not isinstance(query, str) or not query.strip():
        return "Please enter a valid question."

    if (
        isinstance(max_tool_rounds, bool)
        or not isinstance(max_tool_rounds, int)
        or max_tool_rounds < 1
    ):
        return "max_tool_rounds must be a positive integer."

    # Initialize conversation
    messages = [

        SystemMessage(
            content="""
            You are Odhikar BD, a Bangladesh traffic-law
            information assistant.

            Use the available tools to retrieve traffic
            offence information and check fine claims.

            Do not invent legal information.

            Base legal claims on the tool results.

            If information is unavailable or unclear,
            explain that limitation.

            A recorded maximum fine is not necessarily
            the fixed amount payable in every case.

            Do not claim that receipts or case documents
            have been authenticated by the check_claim tool.
            """
        ),

        HumanMessage(content=query)
    ]

    # 4. Tool execution loop
    for round_number in range(max_tool_rounds + 1):

        # Ask Gemini
        ai_response = llm_with_tools.invoke(messages)

        # If no tool is requested, return final answer
        if not ai_response.tool_calls:

            return extract_text(ai_response.content)

        # Stop if maximum tool rounds reached
        if round_number == max_tool_rounds:

            return (
                "Maximum tool execution limit reached. "
                "Please try a simpler question."
            )

        # Add Gemini's tool-call response
        messages.append(ai_response)

        # Execute requested tools
        for tool_call in ai_response.tool_calls:

            tool_name = tool_call["name"]

            selected_tool = tools_by_name.get(tool_name)

            print(f"\nExecuting tool: {tool_name}")

            if selected_tool is None:

                tool_result = {
                    "error": f"Tool '{tool_name}' not found."
                }

            else:

                try:

                    tool_result = selected_tool.invoke(
                        tool_call["args"]
                    )

                except Exception as e:

                    tool_result = {
                        "error": f"Tool execution failed: {str(e)}"
                    }

            print("Tool result:", tool_result)

            # Send tool result back to Gemini
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

    return "Unable to generate a response."


