import pytest
from src.router import AgentRouter
from src.config import CatConfigLoader


def test_load_real_config():
    """Test loading real cat-config.json"""
    loader = CatConfigLoader(config_path="config/cat-config.json")
    breeds = loader.list_breeds()

    assert len(breeds) == 3
    assert breeds[0]["id"] == "orange"
    assert breeds[1]["id"] == "inky"
    assert breeds[2]["id"] == "patch"


def test_route_to_all_three_cats():
    """Test routing to all three cats by role"""
    router = AgentRouter(config_path="config/cat-config.json")

    # Test @dev -> orange
    results = router.route_message("@dev help")
    assert len(results) == 1
    assert results[0]["breed_id"] == "orange"
    assert results[0]["name"] == "阿橘"

    # Test @review -> inky
    results = router.route_message("@review this code")
    assert len(results) == 1
    assert results[0]["breed_id"] == "inky"
    assert results[0]["name"] == "墨点"

    # Test @research -> patch
    results = router.route_message("@research this topic")
    assert len(results) == 1
    assert results[0]["breed_id"] == "patch"
    assert results[0]["name"] == "花花"


def test_route_by_name():
    """Test routing by cat name"""
    router = AgentRouter(config_path="config/cat-config.json")

    results = router.route_message("@阿橘 help")
    assert len(results) == 1
    assert results[0]["breed_id"] == "orange"

    results = router.route_message("@墨点 check this")
    assert len(results) == 1
    assert results[0]["breed_id"] == "inky"

    results = router.route_message("@花花 research")
    assert len(results) == 1
    assert results[0]["breed_id"] == "patch"


def test_multi_cat_mention():
    """Test mentioning multiple cats"""
    router = AgentRouter(config_path="config/cat-config.json")

    results = router.route_message("@dev and @review please help")

    assert len(results) == 2
    breed_ids = {r["breed_id"] for r in results}
    assert "orange" in breed_ids
    assert "inky" in breed_ids


def test_default_routing():
    """Test default routing when no mentions"""
    router = AgentRouter(config_path="config/cat-config.json")

    results = router.route_message("just a message")

    assert len(results) == 1
    assert results[0]["breed_id"] == "orange"  # Default to @dev
