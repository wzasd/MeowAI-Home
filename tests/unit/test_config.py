from src.utils.config import load_config, get_cat_config


def test_load_config():
    config = load_config("config/cat-config.yaml")
    assert "cats" in config
    assert len(config["cats"]) == 3


def test_get_cat_config():
    config = load_config("config/cat-config.yaml")
    orange = config["cats"][0]
    assert orange["name"] == "阿橘"
    assert orange["model"] == "glm-5.0"
