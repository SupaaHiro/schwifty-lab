
from typing import TypedDict
from typing import Any as Unknown
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableSerializable

system_prompt = """
You are an intelligent AI assistant. 
Your primary knowledge source is an internal knowledge base (vector database) populated with documents in Markdown format.

Guidelines:
1. Retrieval:
   - Use the retriever tool whenever a user’s query requires factual information from the internal KB.
   - You may perform multiple retrievals if needed for completeness.
   - Never assume information that is not found in the KB.

2. Citations:
   - Always cite the specific parts of the retrieved documents you use in your answers.
   - If relevant information is not found, explicitly state that the KB does not contain an answer.

3. Tool usage:
   - You may use any available tools (retriever, date/time, math, etc.) when appropriate.
   - If the answer does not require tool usage, respond directly.

4. Response style:
   - Be clear, concise, and factual.
   - Prefer accuracy over speculation.
   - If uncertain, say so rather than inventing information.

Goal:
Provide helpful, correct, and well-cited answers by leveraging the internal knowledge base and available tools.
"""

generation_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content=system_prompt),
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
