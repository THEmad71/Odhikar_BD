
# ==========================================
# ODHIKAR BD - LANGGRAPH + LANGSMITH
# ==========================================

# 0. ORMSGPACK COMPATIBILITY

from src.odhikar.ormsgpack_compat import (
    install as install_ormsgpack_compat
)

install_ormsgpack_compat()


# ==========================================
# 1. STANDARD IMPORTS
# ==========================================

import os
import sqlite3
import json
import logging
import hashlib

from pathlib import Path


# ==========================================
# 2. CONFIGURATION
# ==========================================

from src.odhikar.config import settings


# ==========================================
# 3. LOGGING
# ==========================================

logger = logging.getLogger(__name__)


# ==========================================
# 4. LANGSMITH CONFIGURATION
# ==========================================

LANGSMITH_TRACING_ENABLED = bool(
    settings.langsmith_tracing
    and settings.langsmith_api_key
)

if settings.langsmith_api_key:

    os.environ["LANGSMITH_API_KEY"] = (
        settings.langsmith_api_key
    )

os.environ["LANGSMITH_TRACING"] = (
    "true"
    if LANGSMITH_TRACING_ENABLED
    else "false"
)

os.environ["LANGSMITH_PROJECT"] = (
    settings.langsmith_project
)

if settings.langsmith_tracing and not settings.langsmith_api_key:

    logger.warning(
        "LangSmith tracing requested but API key is missing."
    )

if LANGSMITH_TRACING_ENABLED:

    logger.info(
        "LangSmith tracing enabled. Project: %s",
        settings.langsmith_project
    )

else:

    logger.info(
        "LangSmith tracing disabled."
    )


# ==========================================
# 5. LANGCHAIN IMPORTS
# ==========================================

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


# ==========================================
# 6. ODHIKAR IMPORTS
# ==========================================

from src.odhikar.database import DB_PATH

from src.odhikar.llm import (
    llm_with_tools
)

from src.odhikar.langchain_tools import (
    ODHIKAR_TOOLS
)


# ==========================================
# 7. SYSTEM PROMPT
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
# 8. TOOL REGISTRY
# ==========================================

TOOL_MAP = {
    tool.name: tool
    for tool in ODHIKAR_TOOLS
}


# ==========================================
# 9. CHATBOT NODE
# ==========================================

def chatbot(state: MessagesState):

    messages = [
        SYSTEM_PROMPT,
        *state["messages"]
    ]

    logger.info(
        "Chatbot node started."
    )

    response = llm_with_tools.invoke(
        messages,
        config={
            "run_name": "odhikar_gemini_call",

            "tags": [
                "odhikar-bd",
                "gemini",
                "legal-assistant"
            ],

            "metadata": {
                "application": "odhikar-bd",
                "environment": settings.app_env,
                "component": "chatbot"
            }
        }
    )

    logger.info(
        "Chatbot node completed."
    )

    return {
        "messages": [response]
    }


# ==========================================
# 10. CUSTOM TOOL EXECUTION NODE
# ==========================================

def execute_tools(state: MessagesState):

    messages = state["messages"]

    if not messages:

        return {
            "messages": []
        }

    last_message = messages[-1]

    tool_calls = getattr(
        last_message,
        "tool_calls",
        []
    )

    if not tool_calls:

        return {
            "messages": []
        }

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

            logger.error(
                "Unknown tool requested: %s",
                tool_name
            )

            result_content = json.dumps(
                {
                    "status": "error",
                    "message": "Requested tool is unavailable."
                },
                ensure_ascii=False
            )

        else:

            try:

                # Validate arguments

                if not isinstance(tool_args, dict):

                    raise ValueError(
                        "Tool arguments must be a dictionary."
                    )

                # Execute tool with tracing metadata

                tool_result = tool.invoke(
                    tool_args,
                    config={
                        "run_name": (
                            f"odhikar_tool_{tool_name}"
                        ),

                        "tags": [
                            "odhikar-bd",
                            "legal-tool"
                        ],

                        "metadata": {
                            "application": "odhikar-bd",
                            "environment": settings.app_env,
                            "tool_name": str(tool_name)
                        }
                    }
                )

                # Convert result to readable JSON

                if isinstance(tool_result, str):

                    result_content = tool_result

                else:

                    result_content = json.dumps(
                        tool_result,
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

        tool_messages.append(
            tool_message
        )

    return {
        "messages": tool_messages
    }


# ==========================================
# 11. CONDITIONAL ROUTER
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

    if tool_calls:

        return "tools"

    return END


# ==========================================
# 12. CREATE GRAPH BUILDER
# ==========================================

graph_builder = StateGraph(
    MessagesState
)


# ==========================================
# 13. REGISTER NODES
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
# 14. DEFINE GRAPH EDGES
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
# 15. CENTRAL CHECKPOINT DATABASE
# ==========================================

CHECKPOINT_DB_PATH = Path(DB_PATH)

CHECKPOINT_DB_PATH.parent.mkdir(
    parents=True,
    exist_ok=True
)


# ==========================================
# 16. SQLITE CONNECTION
# ==========================================

checkpoint_connection = sqlite3.connect(
    str(CHECKPOINT_DB_PATH),
    check_same_thread=False,
    timeout=30
)

checkpoint_connection.execute(
    "PRAGMA foreign_keys = ON"
)

checkpoint_connection.execute(
    "PRAGMA busy_timeout = 30000"
)


# ==========================================
# 17. INITIALIZE CHECKPOINTER
# ==========================================

checkpointer = SqliteSaver(
    checkpoint_connection
)

# Preserve existing checkpoint data.

checkpointer.setup()


# ==========================================
# 18. COMPILE GRAPH
# ==========================================

odhikar_graph = graph_builder.compile(
    checkpointer=checkpointer
)


# ==========================================
# 19. EXTRACT READABLE TEXT
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

                answer.append(
                    block.text
                )

        return "\n".join(answer).strip()

    return str(content)


# ==========================================
# 20. MAIN ODHIKAR GRAPH FUNCTION
# ==========================================

def ask_odhikar_graph(
    query: str,
    thread_id: str
) -> str:

    if not isinstance(query, str) or not query.strip():

        return "Please enter a valid question."

    if not isinstance(thread_id, str) or not thread_id.strip():

        return "A valid thread ID is required."

    clean_thread_id = thread_id.strip()

    # Create a non-reversible trace identifier.
    # Do not expose the original session/thread ID
    # as custom LangSmith metadata.

    thread_hash = hashlib.sha256(
        clean_thread_id.encode("utf-8")
    ).hexdigest()[:20]

    # LangGraph invocation configuration

    config = {

        "run_name": "odhikar_bd_request",

        "tags": [
            "odhikar-bd",
            "legal-assistant",
            settings.app_env
        ],

        "metadata": {

            "application": "odhikar-bd",

            "environment": settings.app_env,

            "thread_id": thread_hash,

            "thread_id_hash": thread_hash
        },

        "configurable": {

            "thread_id": clean_thread_id
        },

        "recursion_limit": 20
    }

    logger.info(
        "Starting Odhikar BD graph execution."
    )

    try:

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

        messages = result.get(
            "messages",
            []
        )

        if not messages:

            logger.warning(
                "Graph returned no messages."
            )

            return (
                "Sorry, I could not generate a response. "
                "Please try again."
            )

        final_message = messages[-1]

        answer = extract_text(
            final_message.content
        )

        logger.info(
            "Odhikar BD graph execution completed."
        )

        return answer

    except Exception:

        logger.exception(
            "Odhikar BD graph execution failed."
        )

        raise


# ==========================================
# 21. GRAPH INFORMATION
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

        "memory_enabled": True,

        "langsmith_tracing_enabled": (
            LANGSMITH_TRACING_ENABLED
        ),

        "langsmith_project": (
            settings.langsmith_project
            if LANGSMITH_TRACING_ENABLED
            else None
        )
    }


# ==========================================
# 22. GET CONVERSATION HISTORY
# ==========================================

def get_conversation_history(thread_id: str):

    if not isinstance(thread_id, str) or not thread_id.strip():

        return []

    config = {

        "configurable": {

            "thread_id": thread_id.strip()
        }
    }

    snapshot = odhikar_graph.get_state(
        config
    )

    if not snapshot or not snapshot.values:

        return []

    return snapshot.values.get(
        "messages",
        []
    )
