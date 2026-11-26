
"""
Odhikar BD - Conversation Memory Test

Tests:
1. Initial user question
2. Gemini response
3. Tool execution
4. Follow-up question
5. Conversation history
6. Context retention
7. SQLite checkpoint persistence
"""

from src.odhikar.ormsgpack_compat import install

# Register compatibility before LangGraph imports
install()


import sqlite3

from pathlib import Path
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver

from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    ToolMessage
)

from src.odhikar.graph import graph_builder


# ==========================================
# 1. EXTRACT READABLE TEXT
# ==========================================

def extract_text(content):

    if isinstance(content, str):
        return content

    if isinstance(content, list):

        parts = []

        for block in content:

            if isinstance(block, dict):

                if block.get("type") == "text":
                    parts.append(block.get("text", ""))

            elif hasattr(block, "text"):

                parts.append(block.text)

        return "\n".join(parts).strip()

    if isinstance(content, dict):

        return content.get("text", str(content))

    return str(content)


# ==========================================
# 2. TEST DATABASE
# ==========================================

TEST_DB = Path("test_conversation_memory.sqlite")

connection = sqlite3.connect(
    str(TEST_DB),
    check_same_thread=False,
    timeout=30
)


try:

    checkpointer = SqliteSaver(connection)

    checkpointer.setup()

    app = graph_builder.compile(
        checkpointer=checkpointer
    )


    # ==========================================
    # 3. CREATE UNIQUE THREAD
    # ==========================================

    thread_id = f"memory_{uuid4().hex[:12]}"

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    print("\n======================================")
    print("ODHIKAR BD CONVERSATION MEMORY TEST")
    print("======================================")

    print("Thread ID:", thread_id)


    # ==========================================
    # 4. FIRST QUESTION
    # ==========================================

    print("\n--- FIRST QUESTION ---")

    first_question = (
        "What is the maximum fine for riding "
        "a motorcycle without wearing a helmet "
        "in Bangladesh?"
    )

    result1 = app.invoke(
        {
            "messages": [
                HumanMessage(content=first_question)
            ]
        },
        config=config
    )

    first_message = result1["messages"][-1]

    first_answer = extract_text(
        first_message.content
    )

    print("\nAI Response:")
    print(first_answer)


    # ==========================================
    # 5. FOLLOW-UP QUESTION
    # ==========================================

    print("\n--- FOLLOW-UP QUESTION ---")

    follow_up = (
        "And what is the maximum imprisonment "
        "for that same offence?"
    )

    result2 = app.invoke(
        {
            "messages": [
                HumanMessage(content=follow_up)
            ]
        },
        config=config
    )

    final_message = result2["messages"][-1]

    final_text = extract_text(
        final_message.content
    )

    print("\nFollow-up Response:")
    print(final_text)


    # ==========================================
    # 6. GET CONVERSATION HISTORY
    # ==========================================

    print("\n--- CONVERSATION HISTORY ---")

    snapshot = app.get_state(config)

    messages = snapshot.values.get(
        "messages",
        []
    )

    for message in messages:

        print(
            "\nMessage Type:",
            type(message).__name__
        )

        if isinstance(message, AIMessage):

            if message.tool_calls:
                print("Tool Calls:", message.tool_calls)

            print(
                "Content:",
                extract_text(message.content)
            )

        elif isinstance(message, ToolMessage):

            print("Tool Result:", message.content)

        else:

            print(
                "Content:",
                extract_text(message.content)
            )


    # ==========================================
    # 7. VALIDATE CONVERSATION HISTORY
    # ==========================================

    print("\n--- HISTORY VALIDATION ---")

    human_messages = [
        message
        for message in messages
        if isinstance(message, HumanMessage)
    ]

    ai_messages = [
        message
        for message in messages
        if isinstance(message, AIMessage)
    ]

    tool_messages = [
        message
        for message in messages
        if isinstance(message, ToolMessage)
    ]

    assert len(human_messages) == 2, (
        "Expected exactly two user messages."
    )

    assert human_messages[0].content == first_question

    assert human_messages[1].content == follow_up

    assert len(ai_messages) >= 2, (
        "AI responses missing from conversation history."
    )

    assert len(tool_messages) >= 1, (
        "Tool execution result missing from history."
    )

    print("Conversation History: PASSED")


    # ==========================================
    # 8. VALIDATE FIRST RESPONSE
    # ==========================================

    print("\n--- FIRST RESPONSE VALIDATION ---")

    normalized_first = first_answer.replace(",", "").lower()

    assert "10000" in normalized_first, (
        "Expected maximum fine of 10,000 BDT "
        "was not found in the first response."
    )

    print("First Answer Validation: PASSED")


    # ==========================================
    # 9. VALIDATE FOLLOW-UP RESPONSE
    # ==========================================

    print("\n--- FOLLOW-UP VALIDATION ---")

    assert isinstance(final_message, AIMessage)

    assert final_text.strip(), (
        "AI follow-up response is empty."
    )

    assert "3 months" in final_text.lower(), (
        "Expected imprisonment information "
        "was not found in the follow-up response."
    )

    print("Follow-up Context Understanding: PASSED")

    print("Follow-up Answer Validation: PASSED")


    # ==========================================
    # 10. VERIFY CHECKPOINT
    # ==========================================

    print("\n--- SQLITE CHECKPOINT VALIDATION ---")

    assert snapshot.config["configurable"]["thread_id"] == thread_id

    assert len(messages) >= 5

    print("SQLite Checkpoint: PASSED")


    # ==========================================
    # 11. FINAL RESULT
    # ==========================================

    print("\n======================================")
    print("CONVERSATION MEMORY TEST SUCCESSFUL")
    print("======================================")

    print("User Questions:", len(human_messages))
    print("AI Messages:", len(ai_messages))
    print("Tool Messages:", len(tool_messages))

    print("\nAll Conversation Memory Tests Passed!")


finally:

    # Always close the database connection

    connection.close()

    print("\nDatabase Connection Closed.")
