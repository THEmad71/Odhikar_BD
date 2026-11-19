
import sqlite3
import json
import logging

from pathlib import Path

from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    ToolMessage
)

from langgraph.graph import (
    StateGraph,
    START,
    END,
    MessagesState
)

from langgraph.checkpoint.sqlite import SqliteSaver

from src.odhikar.database import DB_PATH
from src.odhikar.llm import llm_with_tools
from src.odhikar.langchain_tools import ODHIKAR_TOOLS


# ==========================================
# 0. LOGGING
# ==========================================

logger = logging.getLogger(__name__)


# ==========================================
# 1. SYSTEM PROMPT
# ==========================================

SYSTEM_PROMPT = SystemMessage(
    content="""
    You are Odhikar BD, a Bangladesh traffic-law
    information assistant.

    Use available tools to retrieve traffic-law information.

    Do not invent legal information.

    IMPORTANT CONVERSATION MEMORY RULES:

    1. Always consider previous conversation messages.
    2. Understand follow-up questions using previous context.
    3. If the user asks about imprisonment, fine, or punishment
       without naming an offence, identify the offence from
       the previous conversation.
    4. Do not ask the user to repeat information already
       available in conversation history.
    5. Use available tools when additional legal information
       needs to be retrieved.

    If information is unavailable or unclear,
    explain the limitation.

    A recorded maximum fine is not necessarily
    the fixed amount payable in every case.

    Do not claim that user documents have been authenticated.
    """
)


# ==========================================
# 2. TOOL REGISTRY
# ==========================================

TOOL_MAP = {
    tool.name: tool
    for tool in ODHIKAR_TOOLS
}


# ==========================================
# 3. CHATBOT NODE
# ==========================================

def chatbot(state: MessagesState):

    messages = [
        SYSTEM_PROMPT,
        *state["messages"]
    ]

    response = llm_with_tools.invoke(messages)

    return {
        "messages": [response]
    }


# ==========================================
# 4. CUSTOM TOOL EXECUTION NODE
# ==========================================

def execute_tools(state: MessagesState):

    messages = state["messages"]

    if not messages:
        return {"messages": []}

    last_message = messages[-1]

    tool_calls = getattr(
        last_message,
        "tool_calls",
        []
    )

    if not tool_calls:
        return {"messages": []}

    tool_messages = []

    # Execute every requested tool

    for call in tool_calls:

        tool_name = call.get("name")

        tool_call_id = call.get("id")

        tool_args = call.get("args", {})

        # Validate tool call ID

        if not tool_call_id:

            logger.error(
                "Tool call ID missing for %s",
                tool_name
            )

            continue

        # Find requested tool

        tool = TOOL_MAP.get(tool_name)

        if tool is None:

            result_content = json.dumps(
                {
                    "status": "error",
                    "message": "Requested tool is unavailable."
                },
                ensure_ascii=False
            )

        else:

            try:

                # Execute Python tool directly

                if not isinstance(tool_args, dict):
                    raise ValueError(
                        "Tool arguments must be a dictionary."
                    )

                result = tool.invoke(tool_args)

                # Convert result to readable JSON

                if isinstance(result, str):

                    result_content = result

                else:

                    result_content = json.dumps(
                        result,
                        ensure_ascii=False,
                        default=str
                    )

                logger.info(
                    "Tool executed successfully: %s",
                    tool_name
                )

            except Exception:

                logger.exception(
                    "Tool execution failed: %s",
                    tool_name
                )

                result_content = json.dumps(
                    {
                        "status": "error",
                        "message": (
                            "Tool execution failed. "
                            "Do not invent an answer. "
                            "Explain that the information "
                            "could not be retrieved."
                        )
                    },
                    ensure_ascii=False
                )

        # Create ToolMessage

        tool_message = ToolMessage(
            content=result_content,
            tool_call_id=tool_call_id,
            name=tool_name or "unknown_tool"
        )

        tool_messages.append(tool_message)

    return {
        "messages": tool_messages
    }


# ==========================================
# 5. CUSTOM CONDITIONAL ROUTER
# ==========================================

def route_after_chatbot(state: MessagesState):

    messages = state["messages"]

    if not messages:
        return END

    last_message = messages[-1]

    tool_calls = getattr(
        last_message,
        "tool_calls",
        []
    )

    # If Gemini requests a tool,
    # route execution to custom tool node.

    if tool_calls:
        return "tools"

    # Otherwise finish the graph.

    return END


# ==========================================
# 6. CREATE GRAPH BUILDER
# ==========================================

graph_builder = StateGraph(MessagesState)


# ==========================================
# 7. REGISTER NODES
# ==========================================

graph_builder.add_node(
    "chatbot",
    chatbot
)

graph_builder.add_node(
    "tools",
    execute_tools
)


# ==========================================
# 8. DEFINE GRAPH EDGES
# ==========================================

graph_builder.add_edge(
    START,
    "chatbot"
)

graph_builder.add_conditional_edges(
    "chatbot",
    route_after_chatbot
)

graph_builder.add_edge(
    "tools",
    "chatbot"
)


# ==========================================
# 9. CHECKPOINT DATABASE PATH
# ==========================================

CHECKPOINT_DB_PATH = (
    Path(DB_PATH).with_name(
        "odhikar_checkpoints.sqlite"
    )
)

CHECKPOINT_DB_PATH.parent.mkdir(
    parents=True,
    exist_ok=True
)


# ==========================================
# 10. SQLITE CONNECTION
# ==========================================

checkpoint_connection = sqlite3.connect(
    str(CHECKPOINT_DB_PATH),
    check_same_thread=False,
    timeout=30
)


# ==========================================
# 11. INITIALIZE CHECKPOINTER
# ==========================================

checkpointer = SqliteSaver(
    checkpoint_connection
)

checkpointer.setup()


# ==========================================
# 12. COMPILE GRAPH WITH MEMORY
# ==========================================

odhikar_graph = graph_builder.compile(
    checkpointer=checkpointer
)


# ==========================================
# 13. EXTRACT READABLE TEXT
# ==========================================

def extract_text(content):

    if isinstance(content, str):
        return content

    if isinstance(content, list):

        answer = []

        for block in content:

            if isinstance(block, dict):

                if block.get("type") == "text":

                    answer.append(
                        block.get("text", "")
                    )

            elif hasattr(block, "text"):

                answer.append(block.text)

        return "\n".join(answer).strip()

    return str(content)


# ==========================================
# 14. MAIN ODHIKAR GRAPH FUNCTION
# ==========================================

def ask_odhikar_graph(
    query: str,
    thread_id: str
) -> str:

    if not isinstance(query, str) or not query.strip():

        return "Please enter a valid question."

    if not isinstance(thread_id, str) or not thread_id.strip():

        return "A valid thread ID is required."

    config = {
        "configurable": {
            "thread_id": thread_id.strip()
        },
        "recursion_limit": 20
    }

    result = odhikar_graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content=query.strip()
                )
            ]
        },
        config=config
    )

    final_message = result["messages"][-1]

    return extract_text(
        final_message.content
    )


# ==========================================
# 15. GRAPH INFORMATION
# ==========================================

def get_graph_info():

    return {
        "graph_name": "Odhikar BD LangGraph",

        "nodes": [
            "chatbot",
            "tools"
        ],

        "tool_count": len(ODHIKAR_TOOLS),

        "tool_execution": "custom",

        "checkpoint_database": str(
            CHECKPOINT_DB_PATH
        ),

        "memory_enabled": True
    }


# ==========================================
# 16. GET CONVERSATION HISTORY
# ==========================================

def get_conversation_history(thread_id: str):

    if not isinstance(thread_id, str) or not thread_id.strip():
        return []

    config = {
        "configurable": {
            "thread_id": thread_id.strip()
        }
    }

    snapshot = odhikar_graph.get_state(config)

    if not snapshot or not snapshot.values:
        return []

    return snapshot.values.get(
        "messages",
        []
    )
