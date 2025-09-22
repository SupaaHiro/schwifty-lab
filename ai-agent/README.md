# 🤖 Smart AI Agent

A ReAct + RAG AI agent powered by **GPT-4o-mini** and **ChromaDB** for internal knowledge retrieval from Markdown documents.

---

## Features

- ReAct + Retrieval-Augmented Generation (RAG) architecture
- Internal vector database powered by **ChromaDB**
- Ability to retrieve and update dinamically memory
- Conversation history maintained to support context.
- Invokes tools when necessary (date/time, math, KB queries, get/update memory)

---

## Requirements

- **Python 3.12.x**  
- **VS Code** recommended as IDE  
- Install dependencies:

## Environment File

Create a .env file in the root directory with the following content:

```text  
OPENAI_API_KEY=your_openai_api_key_here
```

There are **two** ways to obtain your OpenAI API key:

1. Visit OpenAI API Keys and create a new key.
2. Use the OpenAI CLI: openai api keys create

*Never share your API key publicly!*

## Environment Setup (Pip)

If you prefer using `pip` for dependency management, install the required packages with:

```bash
pip install -r requirements.txt
```

## Environment Setup (Poetry)

If you prefer using [Poetry](https://python-poetry.org/) for dependency management, you can restore the environment with:

```bash
poetry install
```

This will create a virtual environment and install all dependencies specified in `pyproject.toml`.

To activate the environment, use:

```bash
poetry shell
```

## Usage Example

Run the agent interactively:

```bash
python main.py
```

```text
You: Can you tell me the auth code for the 28 January 2025 meeting?
🤖 Asking the agent with 1 messages in the history...
🔍 Searching internal KB for: 28 January 2025 meeting auth code
🤖 Asking the agent with 3 messages in the history...

🛠️ USED TOOL: query_internal_kb
Agent: The auth code for the meeting scheduled on **28 January 2025** is **42**. The meeting will take place from **3:00 PM to 4:00 PM** virtually via **Microsoft Teams**.

You: exit
```

You can type your queries and interact with the agent.
Type exit or quit to stop the session.

## Query Examples

Here are some example queries you can use with the agent:

- **Meeting details:**  
  *Can you tell me the auth code for the 28 January 2025 meeting?*  
  → The agent will search the internal knowledge base for relevant information.

- **Personalized responses:**  
  *What's my lucky number?*  
  → The agent can use conversation memory or context to generate a response.

Feel free to experiment with different questions related to your internal documentation or general queries!

## LangSmith Tracking

To enable LangSmith tracking for experiment logging and tracing, set the following environment variables in your `.env` file:

```text
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com
LANGSMITH_API_KEY=<your-api-key>
LANGSMITH_PROJECT=ai-agent
```

This will activate LangSmith tracing for your agent runs. Make sure to replace `<your-api-key>` with your actual LangSmith API key.

## License

This project is licensed under a **No-Commercial License** (see LICENSE file), since it depends on third-party libraries, which allow free use for personal, experimental, or research purposes, but may impose restrictions on commercial use.