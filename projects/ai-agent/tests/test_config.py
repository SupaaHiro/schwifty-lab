from core.config import Config


def test_config_loading() -> None:
    """
    Test function to load configuration from a JSON file and print its contents.
    """

    # Prepare
    config_path = "config.json"

    # Act
    cfg = Config.load_from_file(config_path)
    print(cfg)

    # Assert
    assert cfg is not None, ValueError("Failed to load configuration")
