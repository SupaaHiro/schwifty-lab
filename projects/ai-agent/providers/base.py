"""
LLM Provider interface.

Each provider module must expose a `build_chat_model(config)` function that returns
a LangChain-compatible `BaseChatModel` instance.

Provider modules:
  - providers/openai.py   — OpenAI cloud API (default)
  - providers/llamacpp.py — Local model via an OpenAI-compatible API server

The provider is selected at startup via `config.provider` in config.json.
Embeddings are configured separately in the `vectordb` section and are not
the responsibility of the chat model provider.
"""

from typing import Protocol

from langchain_core.language_models import BaseChatModel


class LLMProvider(Protocol):
    """Structural protocol describing what a provider module must expose."""

    def build_chat_model(self, config: object) -> BaseChatModel:
        """Return a LangChain-compatible chat model built from the given config."""
        ...
