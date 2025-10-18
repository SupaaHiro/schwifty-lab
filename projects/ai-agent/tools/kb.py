
from typing import Callable, TypedDict
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_core.tools import tool, BaseTool


class ToolState(TypedDict):
    """Maintains the state of the vector database retriever tool."""
    vectordb_retriever: VectorStoreRetriever | None


toolstate = ToolState(vectordb_retriever=None)


def get_kb_tools(vdb_builder: Callable[[], VectorStoreRetriever] | None) -> list[BaseTool]:
    """
    Creates a tool function for querying a vector database using a provided retriever.

    Args:
      vectordb_retriever: An object used to retrieve information from a vector database.

    Returns:
      list[BaseTool]: A list containing the tool function for querying the vector database.
    """

    # If no retriever builder is provided, return an empty list
    if vdb_builder is None:
        return []

    # Lazy initialization of the vector database retriever
    def _initialize_vdb(force: bool) -> VectorStoreRetriever:
        if force or toolstate['vectordb_retriever'] is None:
            print("🔧 Initializing the vector database retriever...")
            toolstate['vectordb_retriever'] = vdb_builder()
        return toolstate['vectordb_retriever']

    @tool
    def initialize_kb_tool() -> str:
        """
        This tool initializes/loads the internal KB (vector db) retriever.

        Returns:
          str: A message indicating the status of the initialization.
        """

        _initialize_vdb(force=True)

        return "The vector database retriever has been initialized."

    @tool
    def query_kb_tool(query: str) -> str:
        """
        This tool searches and returns the information from the internal KB (vector db).

        Args:
          query (str): The query string to search in the internal KB.
        Returns:
          str: The search results from the internal KB.
        """

        # If not, initialize the vector database retriever
        vectordb_retriever = _initialize_vdb(force=False)

        print(f"🔍 Searching internal KB for: {query}")

        docs = vectordb_retriever.invoke(query)

        if not docs:
            return "I found no relevant documentation in the internal KB (vector db)."

        results = []
        for i, doc in enumerate(docs):
            results.append(f"Document {i+1}:\n{doc.page_content}")

        return "\n\n".join(results)

    @tool
    def is_kb_loaded() -> bool:
        """
        This tool checks if the internal KB (vector db) retriever has been loaded.

        Returns:
          bool: True if the retriever has been loaded, False otherwise.
        """
        return toolstate['vectordb_retriever'] is not None

    return [initialize_kb_tool, query_kb_tool, is_kb_loaded]
