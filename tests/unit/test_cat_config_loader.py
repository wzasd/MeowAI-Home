import json
import pytest
from pathlib import Path
from src.config import CatConfigLoader


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset CatConfigLoader singleton before each test"""
    CatConfigLoader.reset()
    yield
    CatConfigLoader.reset()


def test_load_config_success(tmp_path):
    """Test loading cat-config.json successfully"""
    config_file = tmp_path / "cat-config.json"
    config_data = {
        "version": 2,
        "breeds": [{"id": "test", "name": "Test"}]
    }
    config_file.write_text(json.dumps(config_data))

    loader = CatConfigLoader(config_path=str(config_file))
    result = loader.load()

    assert result["version"] == 2
    assert len(result["breeds"]) == 1
    assert result["breeds"][0]["id"] == "test"


def test_get_breed_by_id():
    """Test getting breed by ID"""
    loader = CatConfigLoader(config_path="tests/fixtures/cat-config-test.json")
    breed = loader.get_breed("test_orange")

    assert breed is not None
    assert breed["id"] == "test_orange"
    assert breed["displayName"] == "测试阿橘"


def test_get_breed_not_found():
    """Test getting non-existent breed"""
    loader = CatConfigLoader(config_path="tests/fixtures/cat-config-test.json")
    breed = loader.get_breed("nonexistent")

    assert breed is None


def test_get_breed_by_mention_role():
    """Test getting breed by role mention"""
    loader = CatConfigLoader(config_path="tests/fixtures/cat-config-test.json")
    breed = loader.get_breed_by_mention("@test_dev")

    assert breed is not None
    assert breed["id"] == "test_orange"


def test_get_breed_by_mention_name():
    """Test getting breed by name mention"""
    loader = CatConfigLoader(config_path="tests/fixtures/cat-config-test.json")
    breed = loader.get_breed_by_mention("@测试阿橘")

    assert breed is not None
    assert breed["id"] == "test_orange"


def test_get_breed_by_mention_not_found():
    """Test getting breed by non-existent mention"""
    loader = CatConfigLoader(config_path="tests/fixtures/cat-config-test.json")
    breed = loader.get_breed_by_mention("@nonexistent")

    assert breed is None


def test_list_breeds():
    """Test listing all breeds"""
    loader = CatConfigLoader(config_path="tests/fixtures/cat-config-test.json")
    breeds = loader.list_breeds()

    assert len(breeds) == 1
    assert breeds[0]["id"] == "test_orange"
