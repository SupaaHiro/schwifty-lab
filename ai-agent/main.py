from typing import Any, Literal, Final, TypedDict, List, Union, Annotated, Sequence, Iterator
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph.message import add_messages  # Reducer function
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from core.config import Config
from tools import load_all_tools
from core.chains import load_chains
from core.vectordb import get_vdb_builder
from core.utils import print_graph

# Load environment variables from .env file
# Set OPENAI_API_KEY in your .env file for authentication
# See https://platform.openai.com/account/api-keys
load_dotenv()

# Load configuration
cfg = Config.load_from_file("config.json")

# Load embedding model
embeddings = OpenAIEmbeddings(model=cfg.embedding_name)
# Note: It must be compatible with the LLM you are using.

# Lazy builder function for the vector database retriever
vectordb_builder = get_vdb_builder(str(
    cfg.docs_path), cfg.docs_glob, embeddings, str(cfg.db_path), cfg.collection_name)

# Load all tools
all_tools = load_all_tools(
    model=cfg.model, vdb_builder=vectordb_builder, memory_path="../assets/bot_memory.json")

# Load chains
chains = load_chains(model=cfg.model, tools=all_tools)
generate_chain = chains["generate_chain"]


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


def query_agent(state: AgentState) -> AgentState:
    """Function to call the LLM with the current state."""

    print(f"🤖 Querying the agent")

    result = generate_chain.invoke({"messages": state['messages']})

    return {"messages": [AIMessage(content=result.content, tool_calls=result.tool_calls if isinstance(result, AIMessage) else [])]}


# Define the graph nodes
AGENT_NODE: Final = "agent"
TOOLS_NODE: Final = "tools"


def route_from_agent_to_tools(state: AgentState):
    """Conditional edges based on whether the agent made tool calls"""

    result = state['messages'][-1]

    if isinstance(result, AIMessage) and len(result.tool_calls) > 0:
        for tool_call in result.tool_calls:
            print(f"\n🛠️ Agent decided to use tool: {tool_call['name']}")
        return True

    return False


def main():
    """Main function to run the AI agent in a conversation loop."""

    # Build the state graph
    builder = StateGraph(state_schema=AgentState)
    builder.add_node(AGENT_NODE, query_agent)
    builder.add_node(TOOLS_NODE, ToolNode(all_tools))

    builder.add_conditional_edges(
        AGENT_NODE,
        route_from_agent_to_tools,
        {True: TOOLS_NODE, False: END}
    )

    builder.add_edge(TOOLS_NODE, AGENT_NODE)
    builder.set_entry_point(AGENT_NODE)
    app = builder.compile()

    # Start a conversation loop with the agent
    print("🤖 Welcome to the AI Agent. You can ask questions about the loaded documents.\n")
    print_graph(app, "ascii")
    print("\nType 'exit' or 'quit' to end the conversation.")
    conversation_history = []
    while True:
        # Ask for user input
        try:
            user_input = input("\n🧑‍💻 You: ")
        except KeyboardInterrupt:
            user_input = 'exit'

        # Exit the loop if the user types 'exit' or 'quit'
        if user_input.lower() in ['exit', 'quit']:
            print("\nExiting the conversation. Goodbye!")
            break

        # Append user message to conversation history and invoke the agent
        conversation_history.append(HumanMessage(content=user_input))
        result = app.invoke({'messages': conversation_history})
        if not result or 'messages' not in result:
            print("🤖 Agent: No response from the agent.")
            continue

        # Append agent response to conversation history and print it
        response = (result['messages'][-1]
                    ).content if result['messages'] else ""
        conversation_history.append(
            AIMessage(content=response))
        print(f"🤖 Agent: {response}")

        # Limit conversation history to last 10 messages to manage context length
        if len(conversation_history) > 10:
            conversation_history = conversation_history[-10:]


if __name__ == "__main__":
    main()
