"""
Local LLM provider via an OpenAI-compatible API server.

Instead of using the `langchain-community` ChatLlamaCpp bindings (which do not
reliably support structured tool calling), this provider targets any local runtime
that exposes an OpenAI-compatible `/v1/chat/completions` endpoint.

Supported runtimes (all expose an OpenAI-compatible API with tool calling support):
  - llama.cpp server  — start with: `llama-server --jinja -m model.gguf`
  - Ollama            — https://ollama.com
  - LM Studio         — https://lmstudio.ai

Configuration example (config.json):
  {
    "provider": "llamacpp",
    "llamacpp": {
      "model": "qwen2.5-35b-instruct",
      "base_url": "http://localhost:8080/v1"
    }
  }

NOTE: The local server must support tool/function calling. Verify that your chosen
runtime and model support the `tools` field in the chat completions request.
"""

from langchain_openai import ChatOpenAI

from core.config import LlamaCppConfig


def build_chat_model(config: LlamaCppConfig) -> ChatOpenAI:
    """
    Builds a ChatOpenAI instance pointed at a local OpenAI-compatible server.

    Args:
      config (LlamaCppConfig): The llama-cpp provider configuration section.

    Returns:
      ChatOpenAI: A chat model instance targeting the local API server.
    """

    kwargs: dict = {
        "model": config.model,
        "base_url": config.base_url,
        "api_key": "not-needed",
    }

    if config.extra_body:
        kwargs["model_kwargs"] = {"extra_body": config.extra_body}

    return ChatOpenAI(**kwargs)
