from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage

from agent import build_agent, print_graph
from core.config import Config
from core.vectordb import build_embeddings, vdb_builder
from tools import load_all_tools

# Load secrets from .env (OPENAI_API_KEY, optional LangSmith vars)
load_dotenv()

# Load and validate configuration
cfg = Config.load_from_file("config.json")
print("✅ Configuration loaded successfully.")

# Build the chat model from the configured provider
if cfg.provider == "openai":
    from providers.openai import build_chat_model
    assert cfg.openai is not None  # guaranteed by model_validator
    llm = build_chat_model(cfg.openai)
elif cfg.provider == "llamacpp":
    from providers.llamacpp import build_chat_model
    assert cfg.llamacpp is not None  # guaranteed by model_validator
    llm = build_chat_model(cfg.llamacpp)
else:
    raise ValueError(f"Unknown provider '{cfg.provider}'. Check config.json.")

# Build embeddings (configured independently of the chat model provider)
embeddings = build_embeddings(
    embedding_provider=cfg.vectordb.embedding_provider,
    embedding_name=cfg.vectordb.embedding_name,
)

# Build the vector DB retriever closure (lazy — no I/O until first query)
retriever_builder = vdb_builder(
    embeddings=embeddings,
    path=str(cfg.vectordb.docs_path),
    glob=cfg.vectordb.docs_glob,
    db_path=str(cfg.vectordb.db_path),
    collection_name=cfg.vectordb.collection_name,
    recreate=False,
)

# Load all agent tools
all_tools = load_all_tools(
    vdb_builder=retriever_builder,
    memory_path=str(cfg.agent.memory_path),
)

# Compile the LangGraph agent
app = build_agent(llm, all_tools)


def main() -> None:
    """Runs the AI agent in an interactive REPL loop."""

    print("🤖 Welcome to the AI Agent. You can ask questions about the loaded documents.\n")
    print_graph(app, "ascii")
    print("\nType 'exit' or 'quit' to end the conversation.")

    conversation_history = []

    while True:
        try:
            user_input = input("\n🧑‍💻 You: ")
        except KeyboardInterrupt:
            user_input = "exit"

        if user_input.lower() in ("exit", "quit"):
            print("\nExiting the conversation. Goodbye!")
            break

        conversation_history.append(HumanMessage(content=user_input))

        result = app.invoke(
            {"messages": conversation_history[-cfg.agent.history_window:]})
        if not result or "messages" not in result:
            print("🤖 Agent: No response from the agent.")
            continue

        response = result["messages"][-1].content if result["messages"] else ""
        conversation_history.append(AIMessage(content=response))
        print(f"🤖 Agent: {response}")

        if len(conversation_history) > cfg.agent.history_window:
            conversation_history = conversation_history[-cfg.agent.history_window:]


if __name__ == "__main__":
    main()
