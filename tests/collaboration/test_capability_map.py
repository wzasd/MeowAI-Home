import pytest

from src.collaboration.capability_map import (
    get_task_type,
    required_capabilities_for_task,
    cat_can_handle,
    get_config_capabilities,
)


def test_get_task_type_review():
    assert get_task_type("Please review my code", []) == "review"
    assert get_task_type("Audit the changes", []) == "review"
    assert get_task_type("check this file", []) == "review"


def test_get_task_type_research():
    assert get_task_type("Research FastAPI best practices", []) == "research"
    assert get_task_type("Look up the docs", []) == "research"


def test_get_task_type_implement():
    assert get_task_type("Write a function to parse JSON", []) == "implement"
    assert get_task_type("Refactor this module", []) == "implement"
    assert get_task_type("Debug the failing test", []) == "implement"


def test_get_task_type_execute_command():
    assert get_task_type("Run the migration script", []) == "execute_command"
    assert get_task_type("Execute shell command", []) == "execute_command"


def test_get_task_type_general():
    assert get_task_type("Hello", []) == "general"
    assert get_task_type("What's the weather?", []) == "general"


def test_required_capabilities():
    assert "code_gen" in required_capabilities_for_task("implement")
    assert "code_review" in required_capabilities_for_task("review")
    assert "shell_exec" in required_capabilities_for_task("execute_command")
    assert "file_write" in required_capabilities_for_task("write_file")
    assert "git_ops" in required_capabilities_for_task("git_push")


def test_cat_can_handle():
    assert cat_can_handle(["code_gen", "chat"], "implement") is True
    assert cat_can_handle(["code", "chat"], "implement") is True
    assert cat_can_handle(["chat"], "implement") is False
    assert cat_can_handle(["shell_exec"], "execute_command") is True
    assert cat_can_handle(["code"], "execute_command") is False


def test_general_task_no_requirement():
    assert cat_can_handle([], "general") is True
    assert cat_can_handle(["chat"], "general") is True


def test_get_config_capabilities_falls_back_to_roles():
    assert get_config_capabilities({"roles": ["developer"]}) == ["code_gen"]


def test_get_config_capabilities_respects_explicit_empty_capabilities():
    assert get_config_capabilities({"capabilities": [], "roles": ["developer"]}) == []


def test_get_config_capabilities_accepts_string_capability_values():
    assert get_config_capabilities({"capabilities": "code_gen"}) == ["code_gen"]
