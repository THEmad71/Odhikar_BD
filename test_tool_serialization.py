
from src.odhikar.ormsgpack_compat import install

# Register compatibility layer before LangGraph imports
install()

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from langchain_core.messages import (
    AIMessage,
    ToolMessage
)


# ==========================================
# 1. INITIALIZE SERIALIZER
# ==========================================

serializer = JsonPlusSerializer()


# ==========================================
# 2. CREATE AI TOOL CALL MESSAGE
# ==========================================

original_ai_message = AIMessage(
    content="",
    tool_calls=[
        {
            "name": "lookup_traffic_offence",
            "args": {
                "vehicle_type": "motorcycle",
                "offence": "riding without helmet"
            },
            "id": "call_test_001",
            "type": "tool_call"
        }
    ]
)


# ==========================================
# 3. CREATE TOOL RESULT MESSAGE
# ==========================================

original_tool_message = ToolMessage(
    content="Maximum fine: 10,000 BDT",
    tool_call_id="call_test_001",
    name="lookup_traffic_offence"
)


# ==========================================
# 4. TEST AI TOOL CALL SERIALIZATION
# ==========================================

print("\n--- AI TOOL CALL SERIALIZATION ---")

saved_ai = serializer.dumps_typed(
    original_ai_message
)

restored_ai = serializer.loads_typed(
    saved_ai
)

print("Saved Type:", saved_ai[0])
print("Restored Class:", type(restored_ai).__name__)
print("Tool Calls:", restored_ai.tool_calls)

assert isinstance(restored_ai, AIMessage)

assert (
    restored_ai.tool_calls[0]["name"]
    == "lookup_traffic_offence"
)

assert (
    restored_ai.tool_calls[0]["args"]["vehicle_type"]
    == "motorcycle"
)

assert (
    restored_ai.tool_calls[0]["id"]
    == "call_test_001"
)

print("AI Tool Call Serialization PASSED!")


# ==========================================
# 5. TEST TOOL MESSAGE SERIALIZATION
# ==========================================

print("\n--- TOOL MESSAGE SERIALIZATION ---")

saved_tool = serializer.dumps_typed(
    original_tool_message
)

restored_tool = serializer.loads_typed(
    saved_tool
)

print("Saved Type:", saved_tool[0])
print("Restored Class:", type(restored_tool).__name__)
print("Tool Result:", restored_tool.content)
print("Tool Call ID:", restored_tool.tool_call_id)

assert isinstance(restored_tool, ToolMessage)

assert (
    restored_tool.content
    == "Maximum fine: 10,000 BDT"
)

assert (
    restored_tool.tool_call_id
    == "call_test_001"
)

print("Tool Message Serialization PASSED!")


# ==========================================
# 6. FINAL RESULT
# ==========================================

print("\n================================")
print("TOOL SERIALIZATION TEST COMPLETED")
print("================================")
