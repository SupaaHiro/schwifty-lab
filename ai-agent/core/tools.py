
from typing import Callable
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool, BaseTool
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain_core.vectorstores import VectorStoreRetriever
from datetime import datetime


@tool
def get_today_date(format: str = "%Y-%m-%d") -> str:
    """
    Returns today's date in the specified format.

    Args:
      format (str): Date format according to the rules of datetime.strftime.
                    Default: "%Y-%m-%d".

    Returns:
      str: The date in the requested format.
    """

    today = datetime.now()

    if not format:
        format = "%Y-%m-%d"

    return today.strftime(format)


@tool
def get_current_time(format: str = "%H:%M:%S") -> str:
    """
    Returns the current time in the specified format.

    Args:
      format (str): Time format according to the rules of datetime.strftime. 
                    Default: "%H:%M:%S".

    Returns:
      str: The current time in the requested format.
    """
    now = datetime.now()

    if not format:
        format = "%H:%M:%S"

    return now.strftime(format)


def build_query_internal_kb(vectordb_retriever: VectorStoreRetriever) -> BaseTool:
    """
    Creates a tool function for querying an internal knowledge base (vector database) using a provided retriever.

    Args:
      vectordb_retriever (VectorStoreRetriever): An object capable of retrieving documents from the internal KB based on a query string.

    Returns:
      BaseTool: A tool function that can be used to query the internal KB.
    """

    @tool
    def query_internal_kb(query: str) -> str:
        """
        This tool searches and returns the information from the internal KB (vector db).

        Args:
          query (str): The query string to search in the internal KB.
        Returns:
          str: The search results from the internal KB.
        """

        # Debug: print the query being processed
        print(f"🔍 Searching internal KB for: {query}")

        docs = vectordb_retriever.invoke(query)

        if not docs:
            return "I found no relevant documentation in the internal KB (vector db)."

        results = []
        for i, doc in enumerate(docs):
            results.append(f"Document {i+1}:\n{doc.page_content}")

        return "\n\n".join(results)

    return query_internal_kb


def load_all_tools(model: str, vectordb_retriever: VectorStoreRetriever | None) -> list[BaseTool]:
    """
    Loads and returns a list of tools for the AI agent.
    This function initializes the default math tools (which require an LLM),
    and combines them with internal tools for querying a knowledge base,
    retrieving the current date, and retrieving the current time.
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
    memory_tools = [build_query_internal_kb(
        vectordb_retriever)] if vectordb_retriever is not None else []

    return datetime_tools + math_tools + memory_tools
