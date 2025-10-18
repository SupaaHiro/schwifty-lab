
from typing import Callable
from langchain_openai import ChatOpenAI
from langchain_core.tools import BaseTool
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain_core.vectorstores import VectorStoreRetriever

from tools.utils import get_today_date, get_current_time
from tools.kb import get_kb_tools
from tools.memory import get_memory_tools


def load_all_tools(model: str, vdb_builder: Callable[[], VectorStoreRetriever], memory_path: str) -> list[BaseTool]:
    """
    Loads and returns a list of tools for the AI agent.
    Args:
      vectordb_retriever: An object used to retrieve information from a vector database.
    Returns:
      list[BaseTool]: A list of initialized tool instances.
    """

    # Loads the default datetime tools
    datetime_tools = [get_today_date, get_current_time]

    # Loads the default math tools (llm-math requires an llm)
    math_tools = load_tools(
        ["llm-math"], llm=ChatOpenAI(model=model, temperature=0))

    # Builds the internal KB query tool if a retriever is provided
    memory_tools = get_kb_tools(
        vdb_builder) + get_memory_tools(memory_path)

    return datetime_tools + math_tools + memory_tools


__all__ = ["load_all_tools"]
