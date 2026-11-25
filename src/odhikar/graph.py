
# ============================================================
# ODHIKAR BD - LANGGRAPH ENGINE
# Neon PostgreSQL Persistent Checkpointing
# ============================================================


# ============================================================
# 0. MSGPACK COMPATIBILITY
# ============================================================

from src.odhikar.ormsgpack_compat import (
    install as install_ormsgpack_compat
)

install_ormsgpack_compat()


# ============================================================
# 1. IMPORTS
# ============================================================

import os
import json
import logging
import atexit

from dotenv import load_dotenv

from psycopg_pool import ConnectionPool

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

from langgraph.checkpoint.postgres import PostgresSaver

from src.odhikar.config import settings

from src.odhikar.llm import (
    llm_with_tools
)

from src.odhikar.langchain_tools import (
    ODHIKAR_TOOLS
)


# ============================================================
# 2. ENVIRONMENT CONFIGURATION
# ============================================================

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = (
    os.getenv("NEON_DATABASE_URL")
    or os.getenv("DATABASE_URL")
    or os.getenv("POSTGRES_URL")
)

if not DATABASE_URL:
    raise RuntimeError(
        "PostgreSQL connection URL is missing. "
        "Set DATABASE_URL in your .env file."
    )


# ============================================================
# 3. POSTGRESQL CONNECTION POOL
# ============================================================

connection_kwargs = {
    "autocommit": True,
    "prepare_threshold": 0
}

checkpoint_pool = ConnectionPool(
    conninfo=DATABASE_URL,
    min_size=1,
    max_size=10,
    kwargs=connection_kwargs,
    open=False
)

# Open and verify the connection pool.

checkpoint_pool.open(wait=True)

logger.info(
    "Neon PostgreSQL connection pool initialized."
)


# ============================================================
# 4. POSTGRESQL CHECKPOINTER
# ============================================================

checkpointer = PostgresSaver(
    checkpoint_pool
)

# Create checkpoint tables if they do not exist.
# Existing checkpoint data is preserved.

checkpointer.setup()

logger.info(
    "PostgreSQL checkpoint tables initialized."
)


# ============================================================
# 5. SYSTEM PROMPT
# ============================================================

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


# ============================================================
# 6. TOOL REGISTRY
# ============================================================

TOOL_MAP = {
    tool.name: tool
    for tool in ODHIKAR_TOOLS
}


# ============================================================
# 7. CHATBOT NODE
# ============================================================

def chatbot(state: MessagesState):

    messages = [
        SYSTEM_PROMPT,
        *state["messages"]
    ]

    response = llm_with_tools.invoke(
        messages
    )

    return {
        "messages": [response]
    }


# ============================================================
# 8. CUSTOM TOOL EXECUTION NODE
# ============================================================

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

    for call in tool_calls:

        tool_name = call.get("name")

        tool_call_id = call.get("id")

        tool_args = call.get("args", {})

        # Validate tool call ID.

        if not tool_call_id:

            logger.error(
                "Tool call ID missing for %s",
                tool_name
            )

            continue

        # Find requested tool.

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

                if not isinstance(tool_args, dict):

                    raise ValueError(
                        "Tool arguments must be a dictionary."
                    )

                # Execute tool with tracing metadata.

                tool_result = tool.invoke(
                    tool_args,
                    config={
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

                # Convert result into readable JSON.

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

        # Create ToolMessage.

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


# ============================================================
# 9. CONDITIONAL ROUTER
# ============================================================

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


# ============================================================
# 10. CREATE GRAPH BUILDER
# ============================================================

graph_builder = StateGraph(
    MessagesState
)


# ============================================================
# 11. REGISTER GRAPH NODES
# ============================================================

graph_builder.add_node(
    "chatbot",
    chatbot
)

graph_builder.add_node(
    "tools",
    execute_tools
)


# ============================================================
# 12. DEFINE GRAPH EDGES
# ============================================================

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


# ============================================================
# 13. COMPILE GRAPH WITH POSTGRESQL MEMORY
# ============================================================

odhikar_graph = graph_builder.compile(
    checkpointer=checkpointer
)

logger.info(
    "Odhikar BD LangGraph compiled successfully."
)


# ============================================================
# 14. EXTRACT READABLE TEXT
# ============================================================

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


# ============================================================
# 15. MAIN ODHIKAR GRAPH FUNCTION
# ============================================================

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

    messages = result.get(
        "messages",
        []
    )

    if not messages:
        return "No response was generated."

    final_message = messages[-1]

    return extract_text(
        final_message.content
    )


# ============================================================
# 16. GRAPH INFORMATION
# ============================================================

def get_graph_info():

    return {
        "graph_name": "Odhikar BD LangGraph",

        "nodes": [
            "chatbot",
            "tools"
        ],

        "tool_count": len(ODHIKAR_TOOLS),

        "tool_execution": "custom",

        "checkpoint_database": "Neon PostgreSQL",

        "connection_pool": True,

        "memory_enabled": True
    }


# ============================================================
# 17. GET CONVERSATION HISTORY
# ============================================================

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


# ============================================================
# 18. CLOSE POSTGRESQL CONNECTION POOL
# ============================================================

def close_checkpoint_pool():

    if checkpoint_pool.closed:
        return

    checkpoint_pool.close()

    logger.info(
        "Neon PostgreSQL checkpoint pool closed."
    )


atexit.register(
    close_checkpoint_pool
)


# ============================================================
# END OF ODHIKAR BD GRAPH ENGINE
# ============================================================
