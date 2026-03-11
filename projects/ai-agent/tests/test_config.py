from core.config import Config


def test_config_loading() -> None:
    """Smoke test: loads config.json and validates the Pydantic model."""

    cfg = Config.load_from_file("config.json")
    print(cfg)

    assert cfg is not None
    assert cfg.provider in ("openai", "llamacpp")
    assert cfg.vectordb is not None
    assert cfg.agent is not None
