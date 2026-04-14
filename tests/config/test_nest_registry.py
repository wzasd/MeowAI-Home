import json
from pathlib import Path

import pytest

from src.config.nest_registry import NestRegistry


@pytest.fixture
def temp_registry(tmp_path):
    index_path = tmp_path / "nest-index.json"
    return NestRegistry(index_path=index_path)


def test_registry_add_and_list(temp_registry):
    temp_registry.register("/foo/bar")
    projects = temp_registry.list_projects()
    assert len(projects) == 1
    assert projects[0]["path"] == "/foo/bar"
    assert "activated_at" in projects[0]
    assert "last_used_at" in projects[0]


def test_registry_is_registered(temp_registry):
    temp_registry.register("/foo/bar")
    assert temp_registry.is_registered("/foo/bar") is True
    assert temp_registry.is_registered("/baz/qux") is False


def test_registry_unregister(temp_registry):
    temp_registry.register("/foo/bar")
    assert temp_registry.unregister("/foo/bar") is True
    assert temp_registry.is_registered("/foo/bar") is False
    assert temp_registry.unregister("/foo/bar") is False


def test_registry_update_last_used(temp_registry):
    temp_registry.register("/foo/bar")
    first = temp_registry.list_projects()[0]["last_used_at"]
    temp_registry.update_last_used("/foo/bar")
    second = temp_registry.list_projects()[0]["last_used_at"]
    assert second >= first


def test_registry_idempotent_register(temp_registry):
    temp_registry.register("/foo/bar")
    temp_registry.register("/foo/bar")
    assert len(temp_registry.list_projects()) == 1


def test_registry_load_corrupt_json(temp_registry, tmp_path):
    index_path = tmp_path / "bad.json"
    index_path.write_text("not json")
    reg = NestRegistry(index_path=index_path)
    assert reg.list_projects() == []
