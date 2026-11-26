
from src.odhikar.ormsgpack_compat import install

# Register compatibility before LangGraph imports
install()

import sqlite3
from pathlib import Path
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import HumanMessage, ToolMessage

from src.odhikar.graph import graph_builder


# ==========================================
# 1. CREATE SEPARATE TEST DATABASE
# ==========================================

TEST_DB = Path("test_odhikar_live_graph.sqlite")

connection = sqlite3.connect(
    str(TEST_DB),
    check_same_thread=False,
    timeout=30
)

checkpointer = SqliteSaver(connection)
checkpointer.setup()

app = graph_builder.compile(
    checkpointer=checkpointer
)


# ==========================================
# 2. CREATE UNIQUE TEST THREAD
# ==========================================

thread_id = f"live_test_{uuid4().hex[:12]}"

config = {
    "configurable": {
        "thread_id": thread_id
    }
}

print("\n--- ODHIKAR BD LIVE GRAPH TEST ---")
print("Thread ID:", thread_id)


# ==========================================
# 3. SEND REAL USER QUESTION
# ==========================================

query = (
    "Use the available traffic offence lookup tool "
    "to retrieve the legal maximum fine and imprisonment "
    "for riding a motorcycle without wearing a helmet "
    "in Bangladesh. Explain the result."
)

print("\n--- USER QUESTION ---")
print(query)


# ==========================================
# 4. EXECUTE GEMINI + LANGGRAPH
# ==========================================

result = app.invoke(
    {
        "messages": [
            HumanMessage(content=query)
        ]
    },
    config=config
)


# ==========================================
# 5. INSPECT GRAPH MESSAGES
# ==========================================

print("\n--- GRAPH EXECUTION HISTORY ---")

messages = result["messages"]

for message in messages:

    print("\nMessage Type:", type(message).__name__)

    if hasattr(message, "tool_calls") and message.tool_calls:
        print("Tool Calls:", message.tool_calls)

    if isinstance(message, ToolMessage):
        print("Tool Result:", message.content)

    elif isinstance(message.content, str):
        print("Content:", message.content[:1000])


# ==========================================
# 6. VERIFY TOOL EXECUTION
# ==========================================

tool_calls = [
    call
    for message in messages
    for call in getattr(message, "tool_calls", [])
]

tool_results = [
    message
    for message in messages
    if isinstance(message, ToolMessage)
]

assert tool_calls, "No AI tool call was recorded!"

assert tool_results, "No ToolMessage was recorded!"

print("\nReal Gemini Tool Calling: PASSED")
print("Tool Execution: PASSED")


# ==========================================
# 7. VERIFY CHECKPOINT
# ==========================================

snapshot = app.get_state(config)

assert snapshot.values.get("messages")

print("SQLite Checkpoint: PASSED")


# ==========================================
# 8. CLOSE DATABASE
# ==========================================

connection.close()

print("\nDatabase connection closed.")


# ==========================================
# 9. REOPEN DATABASE
# ==========================================

connection2 = sqlite3.connect(
    str(TEST_DB),
    check_same_thread=False,
    timeout=30
)

checkpointer2 = SqliteSaver(connection2)
checkpointer2.setup()

app2 = graph_builder.compile(
    checkpointer=checkpointer2
)


# ==========================================
# 10. RESTORE CONVERSATION
# ==========================================

restored_state = app2.get_state(config)

restored_messages = restored_state.values["messages"]

assert len(restored_messages) == len(messages)

assert any(
    isinstance(message, ToolMessage)
    for message in restored_messages
)

print("Conversation Restore: PASSED")
print("Restored Message Count:", len(restored_messages))


# ==========================================
# 11. FINAL RESULT
# ==========================================

connection2.close()

print("\n======================================")
print("ODHIKAR BD LIVE GRAPH TEST SUCCESSFUL")
print("======================================")
