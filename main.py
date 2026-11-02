from itertools import count
from typing import Literal

from langchain_core.messages import ToolMessage, AIMessage
from langgraph.constants import END,START
from langgraph.graph import MessagesState, StateGraph

from chains import first_responder, reviser_responder
from tool_executor import execute_tools

MAX_INTERACTION = 2


def draft_node(state: MessagesState):
    """Draft the initial response."""
    response = first_responder.invoke(input={"messages": state["messages"] })
    return  {"messages": [response]}

def revise_node(state: MessagesState):
    """Revise the answer based on tool results."""
    response = reviser_responder.invoke(input={"messages": state["messages"] })
    return  {"messages": [response]}

def event_loop(state: MessagesState) -> Literal["execute_tools", END]:
    """Determine whether to continue or end based on iteration count."""
    count_tools_visit = sum(
        isinstance(item, ToolMessage) for item in state["messages"]
    )
    if count_tools_visit > MAX_INTERACTION:
        return END
    return "execute_tools"


builder = StateGraph(MessagesState)
builder.add_node("draft", draft_node)
builder.add_node("execute_tools",execute_tools)
builder.add_node("revise", revise_node)
builder.add_edge(START,"draft") #substitui o set_entry_point, que nao existe mais, por add_edge
builder.add_edge("draft","execute_tools")
builder.add_edge("execute_tools","revise")
builder.add_conditional_edges("revise", event_loop, ["execute_tools", END])
graph = builder.compile()


graph.get_graph().draw_mermaid_png(output_file_path="flow.png")


res = graph.invoke(input={"messages": [
    {
        "role": "user",
        "content": "Write about AI-Powered SOC / autonomous soc problem domain, list startups that do that and raised"
    }

]})

last_message = res["messages"][-1]
if isinstance(last_message,AIMessage) and last_message.tool_calls:
    print(last_message.tool_calls[0]["args"]["answer"]) #a resposta esta aqui porque e um AIMessage, mas se fosse um ToolMessage, a resposta estaria em last_message.content

print(res)
