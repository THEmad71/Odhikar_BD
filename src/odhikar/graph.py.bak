
from langgraph.graph import (
    StateGraph,
    START,
    END,
    MessagesState
)

from langgraph.prebuilt import (
    ToolNode,
    tools_condition
)

from src.odhikar.llm import llm_with_tools

from src.odhikar.langchain_tools import ODHIKAR_TOOLS


# 1. Define the LLM Node
def chatbot(state: MessagesState):

    response = llm_with_tools.invoke(
        state["messages"]
    )

    return {
        "messages": [response]
    }


# 2. Create Graph Builder
graph_builder = StateGraph(MessagesState)


# 3. Register Nodes
graph_builder.add_node(
    "chatbot",
    chatbot
)

graph_builder.add_node(
    "tools",
    ToolNode(ODHIKAR_TOOLS)
)


# 4. Define Starting Edge
graph_builder.add_edge(
    START,
    "chatbot"
)


# 5. Define Conditional Edge
graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition
)


# 6. Return from Tool Node to Chatbot
graph_builder.add_edge(
    "tools",
    "chatbot"
)


# 7. Compile the Graph
odhikar_graph = graph_builder.compile()


from langchain_core.messages import HumanMessage, SystemMessage



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
