"""AccountStore — provider account configuration with credential storage.

Manages AI provider accounts with two-file storage:
- Account metadata in accounts.json
- API key secrets in credentials.json (mode 0o600)

Builtin accounts (seeded on first load, cannot be deleted):
- builtin-anthropic, builtin-openai, builtin-google, builtin-opencode
"""
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

BUILTIN_ACCOUNTS = [
    {
        "id": "builtin-anthropic",
        "displayName": "Anthropic (Subscription)",
        "protocol": "anthropic",
        "authType": "subscription",
        "baseUrl": None,
        "models": [],
        "isBuiltin": True,
    },
    {
        "id": "builtin-openai",
        "displayName": "OpenAI (Subscription)",
        "protocol": "openai",
        "authType": "subscription",
        "baseUrl": None,
        "models": [],
        "isBuiltin": True,
    },
    {
        "id": "builtin-google",
        "displayName": "Google (Subscription)",
        "protocol": "google",
        "authType": "subscription",
        "baseUrl": None,
        "models": [],
        "isBuiltin": True,
    },
    {
        "id": "builtin-opencode",
        "displayName": "OpenCode (Subscription)",
        "protocol": "opencode",
        "authType": "subscription",
        "baseUrl": None,
        "models": [],
        "isBuiltin": True,
    },
]


class AccountStore:
    """Provider account configuration store.

    Follows the same atomic-write and JSON-loading patterns as RuntimeCatalog.
    """

    def __init__(self, accounts_path: Path, credentials_path: Path):
        self.accounts_path = Path(accounts_path)
        self.credentials_path = Path(credentials_path)
        self._accounts: Dict[str, Dict[str, Any]] = {}
        self._load_accounts()
        self._ensure_builtins()

    def _load_accounts(self) -> None:
        """Load account metadata from disk."""
        if not self.accounts_path.exists():
            return

        try:
            with open(self.accounts_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for acc in data.get("accounts", []):
                acc_id = acc.get("id")
                if acc_id:
                    self._accounts[acc_id] = acc
        except (json.JSONDecodeError, IOError):
            self._accounts.clear()

    def _ensure_builtins(self) -> None:
        """Merge builtin accounts on load (non-destructive).

        Existing user modifications to builtin accounts are preserved;
        only missing builtins are added.
        """
        changed = False
        for builtin in BUILTIN_ACCOUNTS:
            if builtin["id"] not in self._accounts:
                self._accounts[builtin["id"]] = dict(builtin)
                changed = True
        if changed:
            self._save_accounts()

    def _save_accounts(self) -> None:
        """Save accounts to disk atomically (temp + rename)."""
        data = {
            "version": 1,
            "accounts": list(self._accounts.values()),
        }

        self.accounts_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.accounts_path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            temp_path.replace(self.accounts_path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    def _load_credentials(self) -> Dict[str, str]:
        """Load credentials from disk."""
        if not self.credentials_path.exists():
            return {}

        try:
            with open(self.credentials_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return dict(data.get("keys", {}))
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_credentials(self, keys: Dict[str, str]) -> None:
        """Save credentials to disk atomically with mode 0o600."""
        data = {"version": 1, "keys": keys}

        self.credentials_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.credentials_path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            temp_path.replace(self.credentials_path)
            os.chmod(self.credentials_path, 0o600)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    @staticmethod
    def _mask_account(account: Dict[str, Any], has_key: bool) -> Dict[str, Any]:
        """Return a copy of account with apiKey removed and hasApiKey added."""
        masked = dict(account)
        masked.pop("apiKey", None)
        masked["hasApiKey"] = has_key
        return masked

    def list_accounts(self) -> List[Dict]:
        """Return all accounts with masked credentials.

        Each account dict has apiKey removed and a hasApiKey boolean added.
        """
        creds = self._load_credentials()
        result = []
        for acc in self._accounts.values():
            has_key = acc["id"] in creds
            result.append(self._mask_account(acc, has_key))
        return result

    def get_account(self, account_id: str) -> Optional[Dict]:
        """Single account lookup, masked."""
        acc = self._accounts.get(account_id)
        if acc is None:
            return None
        creds = self._load_credentials()
        return self._mask_account(acc, account_id in creds)

    def create_account(
        self,
        id: str,
        displayName: str,
        protocol: str,
        authType: str,
        baseUrl: Optional[str] = None,
        models: Optional[List[str]] = None,
        apiKey: Optional[str] = None,
    ) -> Dict:
        """Create a new account.

        Args:
            id: Unique account identifier (must not start with 'builtin-')
            displayName: Human-readable name
            protocol: AI provider protocol (anthropic, openai, google, opencode)
            authType: Authentication type (subscription, api_key, etc.)
            baseUrl: Optional custom base URL
            models: Optional list of model identifiers
            apiKey: Optional API key (stored separately in credentials)

        Returns:
            The created account dict (masked)

        Raises:
            ValueError: If id is duplicate or uses reserved prefix
        """
        if id.startswith("builtin-"):
            raise ValueError("account id cannot start with 'builtin-' prefix")
        if id in self._accounts:
            raise ValueError(f"account with id '{id}' already exists")

        account: Dict[str, Any] = {
            "id": id,
            "displayName": displayName,
            "protocol": protocol,
            "authType": authType,
            "baseUrl": baseUrl,
            "models": models or [],
            "isBuiltin": False,
        }

        self._accounts[id] = account
        self._save_accounts()

        if apiKey:
            self.set_credential(id, apiKey)

        return self._mask_account(account, apiKey is not None)

    def update_account(self, account_id: str, **updates) -> Dict:
        """Update an existing account.

        Accepts displayName, protocol, authType, baseUrl, models, apiKey.
        If apiKey is provided, the credential is updated separately.

        Returns:
            Updated account dict (masked)

        Raises:
            ValueError: If account not found
        """
        if account_id not in self._accounts:
            raise ValueError(f"account with id '{account_id}' not found")

        account = self._accounts[account_id]

        updatable_fields = ["displayName", "protocol", "authType", "baseUrl", "models"]
        for field in updatable_fields:
            if field in updates:
                account[field] = updates[field]

        api_key = updates.pop("apiKey", None)
        # Also remove non-account fields that were consumed
        for f in updatable_fields:
            updates.pop(f, None)

        self._save_accounts()

        if api_key is not None:
            self.set_credential(account_id, api_key)

        creds = self._load_credentials()
        return self._mask_account(account, account_id in creds)

    def delete_account(self, account_id: str) -> None:
        """Delete an account and its credential.

        Raises:
            ValueError: If account is builtin
        """
        acc = self._accounts.get(account_id)
        if acc is None:
            return

        if acc.get("isBuiltin"):
            raise ValueError("cannot delete builtin account")

        del self._accounts[account_id]
        self._save_accounts()
        self.delete_credential(account_id)

    def get_credential(self, account_id: str) -> Optional[str]:
        """Get the API key for an account."""
        creds = self._load_credentials()
        return creds.get(account_id)

    def set_credential(self, account_id: str, api_key: str) -> None:
        """Set the API key for an account."""
        creds = self._load_credentials()
        creds[account_id] = api_key
        self._save_credentials(creds)

    def delete_credential(self, account_id: str) -> None:
        """Remove the API key for an account."""
        creds = self._load_credentials()
        if account_id in creds:
            del creds[account_id]
            self._save_credentials(creds)


# --- Singleton factory ---

_store_instance: Optional[AccountStore] = None


def get_account_store() -> AccountStore:
    """Get or create the singleton AccountStore instance."""
    global _store_instance
    if _store_instance is None:
        home = Path.home()
        _store_instance = AccountStore(
            home / ".meowai" / "accounts.json",
            home / ".meowai" / "credentials.json",
        )
    return _store_instance
