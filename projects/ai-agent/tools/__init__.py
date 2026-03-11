
from typing import Callable
from langchain_core.tools import BaseTool, tool
from langchain_core.vectorstores import VectorStoreRetriever

from tools.utils import get_today_date, get_current_time
from tools.kb import get_kb_tools
from tools.memory import get_memory_tools


@tool
def calculate(expression: str) -> str:
    """
    Evaluates a mathematical expression and returns the result.

    Uses numexpr for safe evaluation of arithmetic and common math functions.
    Supports operators: +, -, *, /, **, %, and functions like sin, cos, log, sqrt.

    Args:
      expression (str): A mathematical expression string (e.g. "2 ** 10 + sqrt(144)").

    Returns:
      str: The numeric result as a string, or an error message if evaluation fails.
    """

    try:
        import numexpr
        result = numexpr.evaluate(expression)

        # Handle NumPy scalars and arrays without forcing through float(),
        # to avoid precision loss and errors on non-scalar results.
        if hasattr(result, "shape"):
            # NumPy 0-d scalar: extract the underlying Python scalar
            if result.shape == ():
                try:
                    return str(result.item())
                except Exception:
                    return str(result)
            # NumPy array: return its string representation directly
            return str(result)

        # Fallback for plain Python scalars or other types
        return str(result)
    except Exception as e:
        return f"Error evaluating '{expression}': {e}"


def load_all_tools(
    vdb_builder: Callable[[], VectorStoreRetriever],
    memory_path: str,
) -> list[BaseTool]:
    """
    Loads and returns the full list of tools available to the agent.

    Args:
      vdb_builder: A callable returning a VectorStoreRetriever (lazy init closure).
      memory_path (str): Path to the persistent memory JSON file.

    Returns:
      list[BaseTool]: A flat list of initialised tool instances.
    """

    datetime_tools = [get_today_date, get_current_time]
    math_tools = [calculate]
    kb_and_memory_tools = get_kb_tools(vdb_builder) + get_memory_tools(memory_path)

    return datetime_tools + math_tools + kb_and_memory_tools


__all__ = ["load_all_tools"]
