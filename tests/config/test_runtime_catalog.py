"""Tests for RuntimeCatalog (D3)."""
import json
import os
import pytest
import tempfile
import shutil
from pathlib import Path

from src.config.runtime_catalog import RuntimeCatalog, ValidationError


class TestRuntimeCatalogBasics:
    def test_catalog_creation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog_path = Path(tmpdir) / "catalog.json"
            catalog = RuntimeCatalog(catalog_path)

            assert catalog.path == catalog_path
            assert catalog.exists() is False

    def test_create_cat(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog_path = Path(tmpdir) / "catalog.json"
            catalog = RuntimeCatalog(catalog_path)

            cat = catalog.create_cat(
                cat_id="test-cat",
                name="测试猫",
                provider="anthropic",
                mention_patterns=["@test", "测试猫"],
            )

            assert cat["id"] == "test-cat"
            assert cat["name"] == "测试猫"
            assert cat["provider"] == "anthropic"
            assert cat["mentionPatterns"] == ["@test", "测试猫"]

    def test_create_duplicate_id_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog_path = Path(tmpdir) / "catalog.json"
            catalog = RuntimeCatalog(catalog_path)

            catalog.create_cat(cat_id="test", name="Test", provider="anthropic")

            with pytest.raises(ValidationError, match="already exists"):
                catalog.create_cat(cat_id="test", name="Another", provider="openai")

    def test_create_duplicate_mention_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog_path = Path(tmpdir) / "catalog.json"
            catalog = RuntimeCatalog(catalog_path)

            catalog.create_cat(
                cat_id="cat1",
                name="Cat1",
                provider="anthropic",
                mention_patterns=["@shared"],
            )

            with pytest.raises(ValidationError, match="mention alias"):
                catalog.create_cat(
                    cat_id="cat2",
                    name="Cat2",
                    provider="openai",
                    mention_patterns=["@shared"],
                )

    def test_get_cat(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog_path = Path(tmpdir) / "catalog.json"
            catalog = RuntimeCatalog(catalog_path)

            catalog.create_cat(cat_id="test", name="Test", provider="anthropic")

            cat = catalog.get("test")
            assert cat is not None
            assert cat["id"] == "test"

    def test_get_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog_path = Path(tmpdir) / "catalog.json"
            catalog = RuntimeCatalog(catalog_path)

            assert catalog.get("nonexistent") is None

    def test_list_cats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog_path = Path(tmpdir) / "catalog.json"
            catalog = RuntimeCatalog(catalog_path)

            catalog.create_cat(cat_id="cat1", name="Cat1", provider="anthropic")
            catalog.create_cat(cat_id="cat2", name="Cat2", provider="openai")

            cats = catalog.list_all()
            assert len(cats) == 2
            ids = {c["id"] for c in cats}
            assert ids == {"cat1", "cat2"}


class TestRuntimeCatalogUpdate:
    def test_update_cat(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog_path = Path(tmpdir) / "catalog.json"
            catalog = RuntimeCatalog(catalog_path)

            catalog.create_cat(cat_id="test", name="Old", provider="anthropic")
            updated = catalog.update_cat(cat_id="test", name="New")

            assert updated["name"] == "New"
            assert updated["provider"] == "anthropic"  # Unchanged

    def test_update_nonexistent_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog_path = Path(tmpdir) / "catalog.json"
            catalog = RuntimeCatalog(catalog_path)

            with pytest.raises(ValidationError, match="not found"):
                catalog.update_cat(cat_id="nonexistent", name="New")

    def test_update_mention_alias_conflict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog_path = Path(tmpdir) / "catalog.json"
            catalog = RuntimeCatalog(catalog_path)

            catalog.create_cat(
                cat_id="cat1", name="Cat1", provider="anthropic", mention_patterns=["@cat1"]
            )
            catalog.create_cat(
                cat_id="cat2", name="Cat2", provider="openai", mention_patterns=["@cat2"]
            )

            # Try to update cat2 with cat1's mention pattern
            with pytest.raises(ValidationError, match="mention alias"):
                catalog.update_cat(cat_id="cat2", mention_patterns=["@cat1"])


class TestRuntimeCatalogDelete:
    def test_delete_cat(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog_path = Path(tmpdir) / "catalog.json"
            catalog = RuntimeCatalog(catalog_path)

            catalog.create_cat(cat_id="test", name="Test", provider="anthropic")
            assert catalog.get("test") is not None

            catalog.delete_cat("test")
            assert catalog.get("test") is None

    def test_delete_nonexistent_silent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog_path = Path(tmpdir) / "catalog.json"
            catalog = RuntimeCatalog(catalog_path)

            # Should not raise
            catalog.delete_cat("nonexistent")


class TestRuntimeCatalogValidation:
    def test_validate_mention_alias_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog_path = Path(tmpdir) / "catalog.json"
            catalog = RuntimeCatalog(catalog_path)

            # Empty mention should fail
            with pytest.raises(ValidationError, match="mention"):
                catalog.create_cat(
                    cat_id="test", name="Test", provider="anthropic", mention_patterns=[""]
                )

            # Duplicate in same patterns should fail
            with pytest.raises(ValidationError, match="duplicate"):
                catalog.create_cat(
                    cat_id="test2",
                    name="Test2",
                    provider="anthropic",
                    mention_patterns=["@dup", "@dup"],
                )

    def test_validate_required_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog_path = Path(tmpdir) / "catalog.json"
            catalog = RuntimeCatalog(catalog_path)

            with pytest.raises(ValidationError, match="id"):
                catalog.create_cat(cat_id="", name="Test", provider="anthropic")

            with pytest.raises(ValidationError, match="name"):
                catalog.create_cat(cat_id="test", name="", provider="anthropic")

            with pytest.raises(ValidationError, match="provider"):
                catalog.create_cat(cat_id="test", name="Test", provider="")


class TestRuntimeCatalogPersistence:
    def test_atomic_write(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog_path = Path(tmpdir) / "catalog.json"
            catalog = RuntimeCatalog(catalog_path)

            catalog.create_cat(cat_id="test", name="Test", provider="anthropic")

            # File should exist
            assert catalog_path.exists()

            # Content should be valid JSON
            with open(catalog_path) as f:
                data = json.load(f)
                assert "cats" in data
                assert len(data["cats"]) == 1

    def test_load_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog_path = Path(tmpdir) / "catalog.json"

            # Pre-populate file
            with open(catalog_path, "w") as f:
                json.dump(
                    {
                        "version": 1,
                        "cats": [
                            {
                                "id": "existing",
                                "name": "Existing",
                                "provider": "anthropic",
                                "mentionPatterns": ["@existing"],
                            }
                        ],
                    },
                    f,
                )

            catalog = RuntimeCatalog(catalog_path)
            cat = catalog.get("existing")
            assert cat is not None
            assert cat["name"] == "Existing"

    def test_corrupted_file_handling(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog_path = Path(tmpdir) / "catalog.json"

            # Write invalid JSON
            with open(catalog_path, "w") as f:
                f.write("not valid json")

            # Should start fresh
            catalog = RuntimeCatalog(catalog_path)
            assert catalog.list_all() == []


class TestRuntimeCatalogAsOverlay:
    def test_to_overlay_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog_path = Path(tmpdir) / "catalog.json"
            catalog = RuntimeCatalog(catalog_path)

            catalog.create_cat(
                cat_id="overlay-cat",
                name="Overlay",
                provider="anthropic",
                mention_patterns=["@overlay"],
                cli_command="claude",
                cli_args=["--model", "opus"],
            )

            overlay = catalog.to_overlay()
            assert "breeds" in overlay
            assert len(overlay["breeds"]) == 1

            breed = overlay["breeds"][0]
            assert breed["id"] == "overlay-cat"
            assert breed["cli"]["command"] == "claude"
