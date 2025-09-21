
from typing import TypedDict
from typing import Any as Unknown
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableSerializable

from core.constants import SYSTEM_PROMPT

generation_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content=SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
    ]
)


class RunnableChain(TypedDict):
    generate_chain: RunnableSerializable[dict[Unknown, Unknown], BaseMessage]


def load_chains(model: str, tools: list[BaseTool]) -> RunnableChain:
    """
    Initializes and returns a dictionary containing a generation chain for language model interactions.
    Args:
        tools (list[BaseTool]): A list of tool instances to be bound to the language model.
    Returns:
        dict: A dictionary with the key 'generate_chain' mapped to the chained prompt and language model.
    """

    llm = ChatOpenAI(model=model).bind_tools(tools=tools)
    # Note: Using "gpt-4o-mini" for cost efficiency; replace with "gpt-4o" for better performance.

    generate_chain = generation_prompt | llm
    # Note: The '|' operator is used to chain the prompt with the LLM in LangChain.

    return {"generate_chain": generate_chain}
