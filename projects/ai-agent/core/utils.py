from typing import Literal
from langgraph.graph.state import CompiledStateGraph

import warnings
import functools


def deprecated(reason: str = ""):
    """
    Decorator per marcare una funzione come deprecata.
    Mostra un DeprecationWarning quando la funzione viene chiamata.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                f"La funzione {func.__name__} è deprecata. {reason}",
                category=DeprecationWarning,
                stacklevel=2
            )
            return func(*args, **kwargs)
        return wrapper
    return decorator


def print_graph(app: CompiledStateGraph, type: Literal["ascii", "mermaid"]) -> None:
    """
    Prints a visual representation of a compiled state graph in either ASCII or Mermaid format.
    Args:
        app (CompiledStateGraph): The compiled state graph to visualize.
        type (Literal["ascii", "mermaid"]): The format to use for visualization. 
            - "ascii": Prints the graph in ASCII format.
            - "mermaid": Prints the graph in Mermaid diagram format.
    Raises:
        ValueError: If an unsupported graph type is provided.
    """

    graph = app.get_graph()

    if type == "ascii":
        graph.print_ascii()
    elif type == "mermaid":
        print(graph.draw_mermaid())
    else:
        raise ValueError("Unsupported graph type. Use 'ascii' or 'mermaid'.")
