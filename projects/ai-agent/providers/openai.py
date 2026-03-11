import os

from langchain_openai import ChatOpenAI

from core.config import OpenAIConfig


def build_chat_model(config: OpenAIConfig) -> ChatOpenAI:
    """
    Builds a ChatOpenAI instance from the given OpenAI provider configuration.

    Reads the API key from the environment variable specified by `config.api_key_env`.
    If `config.base_url` is set, it is passed to ChatOpenAI to support
    OpenAI-compatible local servers (e.g. llama.cpp server, Ollama, LM Studio).

    Args:
      config (OpenAIConfig): The OpenAI provider configuration section.

    Returns:
      ChatOpenAI: A configured chat model instance.
    """

    kwargs: dict = {"model": config.model}

    if config.base_url:
        kwargs["base_url"] = config.base_url

    api_key = os.getenv(config.api_key_env)
    if api_key:
        kwargs["api_key"] = api_key

    return ChatOpenAI(**kwargs)
