
import sqlite3
from pathlib import Path

from langchain_core.messages import (
    HumanMessage,
    SystemMessage
)

from langgraph.graph import (
    StateGraph,
    START,
    MessagesState
)

from langgraph.prebuilt import (
    ToolNode,
    tools_condition
)

from langgraph.checkpoint.sqlite import SqliteSaver

from src.odhikar.database import DB_PATH
from src.odhikar.llm import llm_with_tools
from src.odhikar.langchain_tools import ODHIKAR_TOOLS


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

    1. Always consider the previous conversation messages.
    2. Understand follow-up questions using previous context.
    3. If the user asks about imprisonment, fine, or punishment
       without naming an offence, identify the offence from
       the previous conversation.
    4. Do not ask the user to repeat information already
       available in the conversation history.
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
# 2. CHATBOT NODE
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
# 3. CREATE GRAPH BUILDER
# ==========================================

graph_builder = StateGraph(MessagesState)


# ==========================================
# 4. REGISTER NODES
# ==========================================

graph_builder.add_node(
    "chatbot",
    chatbot
)

graph_builder.add_node(
    "tools",
    ToolNode(ODHIKAR_TOOLS)
)


# ==========================================
# 5. DEFINE GRAPH EDGES
# ==========================================

# START -> CHATBOT

graph_builder.add_edge(
    START,
    "chatbot"
)


# CHATBOT -> TOOLS OR END

graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition
)


# TOOLS -> CHATBOT

graph_builder.add_edge(
    "tools",
    "chatbot"
)


# ==========================================
# 6. CHECKPOINT DATABASE PATH
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
# 7. SQLITE CONNECTION
# ==========================================

checkpoint_connection = sqlite3.connect(
    str(CHECKPOINT_DB_PATH),
    check_same_thread=False,
    timeout=30
)


# ==========================================
# 8. INITIALIZE CHECKPOINTER
# ==========================================

checkpointer = SqliteSaver(
    checkpoint_connection
)

checkpointer.setup()


# ==========================================
# 9. COMPILE GRAPH WITH MEMORY
# ==========================================

odhikar_graph = graph_builder.compile(
    checkpointer=checkpointer
)


# ==========================================
# 10. EXTRACT READABLE TEXT
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
# 11. MAIN ODHIKAR GRAPH FUNCTION
# ==========================================

def ask_odhikar_graph(
    query: str,
    thread_id: str
) -> str:

    # Validate query
    if not isinstance(query, str) or not query.strip():

        return "Please enter a valid question."

    # Validate thread ID
    if not isinstance(thread_id, str) or not thread_id.strip():

        return "A valid thread ID is required."

    # Configure conversation thread
    config = {
        "configurable": {
            "thread_id": thread_id.strip()
        },
        "recursion_limit": 20
    }

    # Execute LangGraph
    result = odhikar_graph.invoke(
        {
            "messages": [
                HumanMessage(content=query.strip())
            ]
        },
        config=config
    )

    # Get final message
    final_message = result["messages"][-1]

    # Extract readable answer
    return extract_text(
        final_message.content
    )


# ==========================================
# 12. GRAPH INFORMATION
# ==========================================

def get_graph_info():

    return {
        "graph_name": "Odhikar BD LangGraph",

        "nodes": [
            "chatbot",
            "tools"
        ],

        "checkpoint_database": str(
            CHECKPOINT_DB_PATH
        ),

        "memory_enabled": True
    }


# ==========================================
# 13. GET CONVERSATION HISTORY
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

    return snapshot.values.get("messages", [])
