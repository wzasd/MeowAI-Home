"""RuntimeCatalog — runtime CRUD for cat configurations."""
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class ValidationError(Exception):
    """Raised when cat configuration validation fails."""

    pass


class RuntimeCatalog:
    """Runtime catalog for cat CRUD operations.

    Supports atomic writes and deep-merge overlay format.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self._cats: Dict[str, Dict[str, Any]] = {}
        self._mention_index: Dict[str, str] = {}  # mention -> cat_id
        self._load()

    def _load(self) -> None:
        """Load existing catalog from disk."""
        if not self.path.exists():
            return

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)

            cats = data.get("cats", [])
            for cat in cats:
                cat_id = cat.get("id")
                if cat_id:
                    self._cats[cat_id] = cat
                    # Index mentions
                    for mention in cat.get("mentionPatterns", []):
                        self._mention_index[mention.lower()] = cat_id
        except (json.JSONDecodeError, IOError):
            # Start fresh if file is corrupted
            self._cats.clear()
            self._mention_index.clear()

    def _save(self) -> None:
        """Save catalog to disk atomically."""
        data = {"version": 1, "cats": list(self._cats.values())}

        # Write to temp file first, then rename for atomicity
        temp_path = self.path.with_suffix(".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())

            # Atomic rename
            temp_path.replace(self.path)
        except Exception:
            # Clean up temp file on failure
            if temp_path.exists():
                temp_path.unlink()
            raise

    def _rebuild_mention_index(self) -> None:
        """Rebuild mention index from all cats."""
        self._mention_index.clear()
        for cat_id, cat in self._cats.items():
            for mention in cat.get("mentionPatterns", []):
                self._mention_index[mention.lower()] = cat_id

    def _validate_mentions(self, mentions: List[str], exclude_cat_id: Optional[str] = None) -> None:
        """Validate mention patterns are unique and valid."""
        seen: Set[str] = set()

        for mention in mentions:
            if not mention or not mention.strip():
                raise ValidationError("mention alias cannot be empty")

            lower_mention = mention.lower()

            # Check for duplicates in current list
            if lower_mention in seen:
                raise ValidationError(f"duplicate mention alias: {mention}")
            seen.add(lower_mention)

            # Check against existing cats
            existing_cat = self._mention_index.get(lower_mention)
            if existing_cat and existing_cat != exclude_cat_id:
                raise ValidationError(f"mention alias '{mention}' already used by cat '{existing_cat}'")

    def exists(self) -> bool:
        """Check if catalog file exists."""
        return self.path.exists()

    def create_cat(
        self,
        cat_id: str,
        name: str,
        provider: str,
        mention_patterns: Optional[List[str]] = None,
        default_model: Optional[str] = None,
        cli_command: Optional[str] = None,
        cli_args: Optional[List[str]] = None,
        personality: Optional[str] = None,
        **extra_fields,
    ) -> Dict[str, Any]:
        """Create a new cat configuration.

        Args:
            cat_id: Unique identifier for the cat
            name: Display name
            provider: AI provider (anthropic, openai, etc.)
            mention_patterns: List of mention aliases (e.g., ["@cat", "CatName"])
            default_model: Default model identifier
            cli_command: CLI command to invoke
            cli_args: Default CLI arguments
            personality: Personality description
            **extra_fields: Additional cat-specific fields

        Returns:
            The created cat configuration dict

        Raises:
            ValidationError: If validation fails
        """
        # Validate required fields
        if not cat_id or not cat_id.strip():
            raise ValidationError("cat id is required")
        if not name or not name.strip():
            raise ValidationError("cat name is required")
        if not provider or not provider.strip():
            raise ValidationError("cat provider is required")

        # Check for duplicate id
        if cat_id in self._cats:
            raise ValidationError(f"cat with id '{cat_id}' already exists")

        # Validate mentions
        mentions = mention_patterns or []
        self._validate_mentions(mentions)

        # Build cat config
        cat = {
            "id": cat_id,
            "name": name,
            "provider": provider,
            "mentionPatterns": mentions,
        }

        if default_model:
            cat["defaultModel"] = default_model
        if cli_command:
            cat["cli"] = {"command": cli_command}
            if cli_args:
                cat["cli"]["defaultArgs"] = cli_args
        if personality:
            cat["personality"] = personality

        # Add extra fields
        cat.update(extra_fields)

        # Store and persist
        self._cats[cat_id] = cat
        self._rebuild_mention_index()
        self._save()

        return dict(cat)

    def get(self, cat_id: str) -> Optional[Dict[str, Any]]:
        """Get cat configuration by id."""
        cat = self._cats.get(cat_id)
        return dict(cat) if cat else None

    def list_all(self) -> List[Dict[str, Any]]:
        """List all cat configurations."""
        return [dict(cat) for cat in self._cats.values()]

    def update_cat(self, cat_id: str, **updates) -> Dict[str, Any]:
        """Update an existing cat configuration.

        Args:
            cat_id: Cat identifier
            **updates: Fields to update

        Returns:
            Updated cat configuration

        Raises:
            ValidationError: If cat not found or validation fails
        """
        if cat_id not in self._cats:
            raise ValidationError(f"cat with id '{cat_id}' not found")

        cat = self._cats[cat_id]

        # Handle mention pattern updates specially
        if "mention_patterns" in updates:
            new_mentions = updates.pop("mention_patterns")
            if new_mentions is not None:
                self._validate_mentions(new_mentions, exclude_cat_id=cat_id)
                cat["mentionPatterns"] = new_mentions

        # Update other fields
        field_mapping = {
            "name": "name",
            "provider": "provider",
            "default_model": "defaultModel",
            "personality": "personality",
            "displayName": "displayName",
        }

        for py_key, json_key in field_mapping.items():
            if py_key in updates:
                cat[json_key] = updates[py_key]

        # Handle CLI updates
        if "cli_command" in updates or "cli_args" in updates:
            if "cli" not in cat:
                cat["cli"] = {}
            if "cli_command" in updates:
                cat["cli"]["command"] = updates["cli_command"]
            if "cli_args" in updates:
                cat["cli"]["defaultArgs"] = updates["cli_args"]

        # Update any extra fields directly
        for key, value in updates.items():
            if key not in field_mapping and key not in (
                "cli_command",
                "cli_args",
                "mention_patterns",
            ):
                cat[key] = value

        self._rebuild_mention_index()
        self._save()

        return dict(cat)

    def delete_cat(self, cat_id: str) -> None:
        """Delete a cat configuration.

        No-op if cat doesn't exist.
        """
        if cat_id not in self._cats:
            return

        del self._cats[cat_id]
        self._rebuild_mention_index()
        self._save()

    def to_overlay(self) -> Dict[str, Any]:
        """Export catalog as overlay format for deep-merge.

        Returns:
            Overlay dict compatible with CatRegistry.apply_overlay()
        """
        breeds = []
        for cat in self._cats.values():
            breed = {
                "id": cat["id"],
                "catId": cat["id"],
                "name": cat["name"],
                "displayName": cat.get("displayName", cat["name"]),
                "provider": cat.get("provider", ""),
            }

            if "defaultModel" in cat:
                breed["defaultModel"] = cat["defaultModel"]
            if "mentionPatterns" in cat:
                breed["mentionPatterns"] = cat["mentionPatterns"]
            if "personality" in cat:
                breed["personality"] = cat["personality"]
            if "cli" in cat:
                breed["cli"] = cat["cli"]

            breeds.append(breed)

        return {"breeds": breeds}


# Default catalog location
def get_default_catalog_path() -> Path:
    """Get default runtime catalog path.

    Uses ~/.meowai/cat-catalog.json
    """
    home = Path.home()
    return home / ".meowai" / "cat-catalog.json"


def get_runtime_catalog(path: Optional[Path] = None) -> RuntimeCatalog:
    """Get or create runtime catalog.

    Args:
        path: Optional custom path, defaults to ~/.meowai/cat-catalog.json

    Returns:
        RuntimeCatalog instance
    """
    if path is None:
        path = get_default_catalog_path()
    return RuntimeCatalog(path)
