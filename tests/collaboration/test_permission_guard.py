import pytest

from src.collaboration.permission_guard import (
    check_permission,
    get_missing_permission,
)


def test_low_risk_allowed():
    assert check_permission([], "read_file") is True
    assert check_permission([], "list_directory") is True
    assert check_permission(["shell_exec"], "read_file") is True


def test_execute_command_requires_shell_exec():
    assert check_permission(["shell_exec"], "execute_command") is True
    assert check_permission(["file_write"], "execute_command") is False
    assert check_permission([], "execute_command") is False


def test_write_file_requires_file_write():
    assert check_permission(["file_write"], "write_file") is True
    assert check_permission(["shell_exec"], "write_file") is False
    assert check_permission([], "write_file") is False


def test_git_push_requires_git_ops():
    assert check_permission(["git_ops"], "git_push") is True
    assert check_permission(["file_write"], "git_push") is False
    assert check_permission([], "git_push") is False


def test_missing_permission_hint():
    assert get_missing_permission("execute_command") == "shell_exec"
    assert get_missing_permission("write_file") == "file_write"
    assert get_missing_permission("git_push") == "git_ops"
    assert get_missing_permission("read_file") is None
