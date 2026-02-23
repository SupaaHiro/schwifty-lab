# 🤖 Smart AI Agent

An AI agent combining ReAct and Retrieval-Augmented Generation (RAG), powered by **GPT-4o-mini** and **ChromaDB**.
It efficiently retrieves information from internal Markdown documents, enabling smart, context-aware responses.

---

## Key Features

- ReAct + Retrieval-Augmented Generation (RAG) architecture
- Internal vector database powered by **ChromaDB**
- Dynamic memory retrieval and updating
- Maintains conversation history for context
- Tool invocation (date/time, math, KB queries, memory management)

---

## Prerequisites

- **Python 3.13.x**
- **VS Code** (recommended IDE)
- Install dependencies as described below


> **Note:** Python 3.14 is not yet supported by LangChain due to compatibility issues (Pydantic V1 deprecation).

---

## Configuration: Environment Variables

Create a `.env` file in the project root with:

```text
OPENAI_API_KEY=your_openai_api_key_here
```

**How to obtain your OpenAI API key:**
1. Visit OpenAI API Keys and create a new key.
2. Use the OpenAI CLI: `openai api keys create`

> **Never share your API key publicly!**

---

### Quick Setup

1. Create a conda environment:

```bash
conda create -n langchain-python3.13 python=3.13.12
conda activate langchain-python3.13
```

2. Install Poetry:

```bash
conda install -c conda-forge poetry poetry-plugin-export
```

3. Configure Poetry to not create virtual environments:

```bash
poetry config virtualenvs.create false
poetry config --list | grep virtualenvs
```

4. Install dependencies:

```bash
poetry install
```

### Update Dependencies

To check for outdated dependencies and update them:

```bash
poetry show --outdated
poetry update
poetry export -f requirements.txt --output requirements.txt --without-hashes
```

---

## Running the Agent

Start the agent interactively:

```bash
python main.py
```

Example session:

```text
You: Can you tell me the auth code for the 28 January 2025 meeting?
🤖 Asking the agent with 1 messages in the history...
🔍 Searching internal KB for: 28 January 2025 meeting auth code
🤖 Asking the agent with 3 messages in the history...

🛠️ USED TOOL: query_internal_kb
Agent: The auth code for the meeting scheduled on **28 January 2025** is **42**. The meeting will take place from **3:00 PM to 4:00 PM** virtually via **Microsoft Teams**.

You: exit
```

Type your queries to interact with the agent.
Type `exit` or `quit` to end the session.

---

## Example Queries

Try these sample queries:

- **Meeting details:**
  *Can you tell me the auth code for the 28 January 2025 meeting?*
  → Searches the internal knowledge base for relevant info.

- **Personalized responses:**
  *What's my lucky number?*
  → Uses conversation memory or context for a response.

Feel free to experiment with questions related to your documentation or general queries!

---

## Experiment Tracking: LangSmith

To enable LangSmith logging and tracing, add these variables to your `.env` file:

```text
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com
LANGSMITH_API_KEY=<your-api-key>
LANGSMITH_PROJECT=ai-agent
```

Replace `<your-api-key>` with your actual LangSmith API key.

---

## License

This project is licensed under a **No-Commercial License** (see LICENSE file).
It depends on third-party libraries that allow free use for personal, experimental, or research purposes, but may restrict commercial use.
