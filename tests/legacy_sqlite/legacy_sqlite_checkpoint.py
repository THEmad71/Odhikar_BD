
from src.odhikar.ormsgpack_compat import install

# IMPORTANT: Install before importing LangGraph
install()

import sqlite3
from pathlib import Path
from uuid import uuid4

from langgraph.graph import (
    StateGraph,
    START,
    MessagesState
)

from langgraph.checkpoint.sqlite import SqliteSaver

from langchain_core.messages import (
    HumanMessage,
    AIMessage
)


# ==========================================
# 1. TEST DATABASE
# ==========================================

TEST_DB = Path("test_odhikar_checkpoint.sqlite")

thread_id = f"sqlite_test_{uuid4().hex}"

config = {
    "configurable": {
        "thread_id": thread_id
    }
}


# ==========================================
# 2. CREATE SIMPLE GRAPH
# ==========================================

def assistant(state: MessagesState):

    last_message = state["messages"][-1]

    return {
        "messages": [
            AIMessage(
                content=f"Echo: {last_message.content}"
            )
        ]
    }


def build_graph(checkpointer):

    builder = StateGraph(MessagesState)

    builder.add_node(
        "assistant",
        assistant
    )

    builder.add_edge(
        START,
        "assistant"
    )

    return builder.compile(
        checkpointer=checkpointer
    )


# ==========================================
# 3. FIRST DATABASE CONNECTION
# ==========================================

print("\n--- FIRST DATABASE CONNECTION ---")

connection = sqlite3.connect(
    str(TEST_DB),
    check_same_thread=False,
    timeout=30
)

checkpointer = SqliteSaver(connection)

checkpointer.setup()

app = build_graph(checkpointer)


# ==========================================
# 4. SAVE CONVERSATION
# ==========================================

print("\n--- SAVE CONVERSATION ---")

result = app.invoke(
    {
        "messages": [
            HumanMessage(
                content="Test SQLite persistence"
            )
        ]
    },
    config=config
)

print("Graph Response:", result["messages"][-1].content)

state = app.get_state(config)

print("Saved Message Count:", len(state.values["messages"]))

assert len(state.values["messages"]) == 2

print("Conversation Saved Successfully!")


# ==========================================
# 5. CLOSE DATABASE CONNECTION
# ==========================================

print("\n--- CLOSE DATABASE ---")

connection.close()

print("First Database Connection Closed!")


# ==========================================
# 6. REOPEN DATABASE
# ==========================================

print("\n--- REOPEN DATABASE ---")

connection2 = sqlite3.connect(
    str(TEST_DB),
    check_same_thread=False,
    timeout=30
)

checkpointer2 = SqliteSaver(connection2)

checkpointer2.setup()

app2 = build_graph(checkpointer2)


# ==========================================
# 7. RESTORE OLD CONVERSATION
# ==========================================

print("\n--- RESTORE CONVERSATION ---")

restored_state = app2.get_state(config)

messages = restored_state.values["messages"]

print("Restored Message Count:", len(messages))

for message in messages:

    print(
        type(message).__name__,
        ":",
        message.content
    )


# ==========================================
# 8. VALIDATION
# ==========================================

assert len(messages) == 2

assert isinstance(messages[0], HumanMessage)

assert isinstance(messages[1], AIMessage)

assert messages[0].content == "Test SQLite persistence"

assert messages[1].content == "Echo: Test SQLite persistence"

print("\nSQLite Persistence Test PASSED!")


# ==========================================
# 9. CLOSE SECOND CONNECTION
# ==========================================

connection2.close()

print("\nAll SQLite Checkpoint Tests Completed!")
print("Test Database:", TEST_DB.resolve())
