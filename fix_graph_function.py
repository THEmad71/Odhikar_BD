
from pathlib import Path
import re

# Locate the actual graph.py file
file_path = Path("src/odhikar/graph.py")

source = file_path.read_text(encoding="utf-8")

# Find all definitions of ask_odhikar_graph
matches = list(
    re.finditer(
        r"(?m)^def ask_odhikar_graph\s*\(",
        source
    )
)

if not matches:
    raise ValueError(
        "ask_odhikar_graph function not found!"
    )

# Replace the last definition and everything after it
start = matches[-1].start()

corrected_function = '''
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

    # Configure conversation
    config = {
        "configurable": {
            "thread_id": thread_id
        },
        "recursion_limit": 20
    }

    # Execute LangGraph
    result = odhikar_graph.invoke(
        {
            "messages": [
                HumanMessage(content=query)
            ]
        },
        config=config
    )

    # Get final response
    final_message = result["messages"][-1]

    return extract_text(final_message.content)
'''

# Save corrected file
file_path.write_text(
    source[:start] + corrected_function,
    encoding="utf-8"
)

print("graph.py successfully updated!")

print("Corrected function signature:")
print("ask_odhikar_graph(query, thread_id)")
