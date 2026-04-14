"""Tests for AccountStore — provider account configuration and credential storage."""
import json
import os
import pytest
from pathlib import Path
from src.config.account_store import AccountStore


@pytest.fixture
def store_dir(tmp_path):
    return tmp_path / ".meowai"


@pytest.fixture
def store(store_dir):
    store_dir.mkdir(parents=True, exist_ok=True)
    return AccountStore(store_dir / "accounts.json", store_dir / "credentials.json")


def test_creates_builtin_accounts_on_first_load(store):
    accounts = store.list_accounts()
    ids = [a["id"] for a in accounts]
    assert "builtin-anthropic" in ids
    assert "builtin-openai" in ids
    assert "builtin-google" in ids
    assert "builtin-opencode" in ids


def test_builtin_accounts_cannot_be_deleted(store):
    with pytest.raises(ValueError, match="builtin"):
        store.delete_account("builtin-anthropic")


def test_create_custom_account(store):
    acc = store.create_account(
        id="my-key",
        displayName="My Key",
        protocol="anthropic",
        authType="api_key",
        apiKey="sk-test-123",
    )
    assert acc["id"] == "my-key"
    assert acc["isBuiltin"] is False
    assert store.get_credential("my-key") == "sk-test-123"


def test_credential_file_permissions(store, store_dir):
    store.set_credential("test", "sk-abc")
    cred_path = store_dir / "credentials.json"
    mode = os.stat(cred_path).st_mode & 0o777
    assert mode == 0o600


def test_update_account(store):
    store.create_account(
        id="test1",
        displayName="Test",
        protocol="anthropic",
        authType="api_key",
        apiKey="sk-1",
    )
    updated = store.update_account("test1", displayName="Updated", apiKey="sk-2")
    assert updated["displayName"] == "Updated"
    assert store.get_credential("test1") == "sk-2"


def test_delete_account_removes_credential(store):
    store.create_account(
        id="temp",
        displayName="Temp",
        protocol="openai",
        authType="api_key",
        apiKey="sk-del",
    )
    store.delete_account("temp")
    assert store.get_account("temp") is None
    assert store.get_credential("temp") is None


def test_list_masks_credentials(store):
    store.create_account(
        id="masked",
        displayName="M",
        protocol="anthropic",
        authType="api_key",
        apiKey="sk-secret",
    )
    accounts = store.list_accounts()
    for acc in accounts:
        assert "apiKey" not in acc
        if acc["id"] == "masked":
            assert acc["hasApiKey"] is True
        elif acc["authType"] == "subscription":
            assert acc["hasApiKey"] is False


def test_reject_duplicate_id(store):
    # builtin- prefix is rejected before duplicate check
    with pytest.raises(ValueError, match="builtin-"):
        store.create_account(
            id="builtin-anthropic",
            displayName="Dup",
            protocol="anthropic",
            authType="subscription",
        )

    # non-builtin duplicate is caught by the duplicate check
    store.create_account(id="my-acc", displayName="First", protocol="anthropic", authType="api_key")
    with pytest.raises(ValueError, match="already exists"):
        store.create_account(id="my-acc", displayName="Dup", protocol="anthropic", authType="api_key")
