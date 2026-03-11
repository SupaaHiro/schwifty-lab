
from typing import Callable
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_core.tools import tool, BaseTool


def get_kb_tools(vdb_builder: Callable[[], VectorStoreRetriever] | None) -> list[BaseTool]:
    """
    Creates tools for querying the internal knowledge base.

    The retriever is lazily initialised on first use and stored in closure-scoped
    state (not module-level globals), so multiple independent KB tool sets can
    coexist without interfering with each other.

    Args:
      vdb_builder: A callable that returns a VectorStoreRetriever when invoked.
                   Pass None to disable KB tools entirely.

    Returns:
      list[BaseTool]: A list containing query_kb_tool, or an empty list if
                      vdb_builder is None.
    """

    if vdb_builder is None:
        return []

    # Closure-scoped state — no module-level mutable globals.
    state: dict = {"retriever": None}

    def _get_retriever() -> VectorStoreRetriever:
        if state["retriever"] is None:
            print("🔧 Initializing the vector database retriever...")
            state["retriever"] = vdb_builder()
        return state["retriever"]

    @tool
    def query_kb_tool(query: str) -> str:
        """
        Searches and returns information from the internal knowledge base (vector DB).

        Args:
          query (str): The query string to search in the internal KB.

        Returns:
          str: The search results from the internal KB.
        """

        retriever = _get_retriever()

        print(f"🔍 Searching internal KB for: {query}")

        docs = retriever.invoke(query)

        if not docs:
            return "I found no relevant documentation in the internal KB (vector db)."

        results = []
        for i, doc in enumerate(docs):
            results.append(f"Document {i + 1}:\n{doc.page_content}")

        return "\n\n".join(results)

    return [query_kb_tool]
