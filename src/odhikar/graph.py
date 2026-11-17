
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


def ask_odhikar_graph(query: str) -> str:

    if not isinstance(query, str) or not query.strip():
        return "Please enter a valid question."

    messages = [
        SystemMessage(
            content="""
            You are Odhikar BD, a Bangladesh traffic-law
            information assistant.

            Use available tools for traffic-law information.

            Do not invent legal information.

            If information is unavailable, explain the limitation.

            Do not claim that user documents have been authenticated.
            """
        ),
        HumanMessage(content=query)
    ]

    result = odhikar_graph.invoke({
        "messages": messages
    })

    final_message = result["messages"][-1]

    content = final_message.content

    if isinstance(content, str):
        return content

    if isinstance(content, list):

        answer = []

        for block in content:

            if isinstance(block, dict) and block.get("type") == "text":
                answer.append(block.get("text", ""))

        return "\n".join(answer)

    return "Unable to generate an answer."
