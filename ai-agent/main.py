from typing import Any, Literal, Final, TypedDict, List, Union, Annotated, Sequence, Iterator
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph.message import add_messages  # Reducer function
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from core.tools import load_all_tools
from core.chains import load_chains
from core.vectordb import load_and_split_documents, initialize_vectordb
from core.utils import print_graph

# Load environment variables from .env file
# Set OPENAI_API_KEY in your .env file for authentication
# See https://platform.openai.com/account/api-keys
load_dotenv()


# Load documents from a folder containing Markdown files
docs_chunks = load_and_split_documents("../assets/docs", "**/*.md")
print(f"Markdowns have been split into {len(docs_chunks)} chunks")

model = "gpt-4o-mini"
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
# Note: The embedding model must be compatible with the LLM you are using.

# Initialize the vector database (ChromaDB) and create a retriever
vectordb_retriever = initialize_vectordb(
    embeddings, r"../chroma_db", "internal_kb", docs_chunks)

# Load all tools
all_tools = load_all_tools(model=model, vectordb_retriever=vectordb_retriever)

# Load chains
chains = load_chains(model=model, tools=all_tools)
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
    print("Building the state graph...")
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
    print("State graph built successfully.")

    # Start a conversation loop with the agent
    print("Welcome to the AI Agent. You can ask questions about the loaded documents.\n")
    print_graph(app, "ascii")
    print("\nType 'exit' or 'quit' to end the conversation.")
    conversation_history = []
    while True:
        # Ask for user input
        user_input = input("\nYou: ")
        if user_input.lower() in ['exit', 'quit']:
            break

        # Append user message to conversation history and invoke the agent
        conversation_history.append(HumanMessage(content=user_input))
        result = app.invoke({'messages': conversation_history})
        if not result or 'messages' not in result:
            print("Agent: No response from the agent.")
            continue

        # Append agent response to conversation history and print it
        response = (result['messages'][-1]
                    ).content if result['messages'] else ""
        conversation_history.append(
            AIMessage(content=response))
        print(f"Agent: {response}")


if __name__ == "__main__":
    main()
