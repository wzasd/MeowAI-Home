"""Tests for CatRegistry roster and reviewPolicy features (D1)."""
import pytest
from src.models.cat_registry import CatRegistry


class TestRosterSupport:
    def test_load_roster(self):
        registry = CatRegistry()
        config = {
            "version": 2,
            "roster": {
                "orange": {
                    "family": "orange",
                    "roles": ["developer", "coder"],
                    "lead": True,
                    "available": True,
                    "evaluation": "主力开发者，全能型选手",
                },
                "inky": {
                    "family": "inky",
                    "roles": ["reviewer"],
                    "lead": False,
                    "available": True,
                    "evaluation": "代码审查专家",
                },
            },
            "reviewPolicy": {
                "requireDifferentFamily": True,
                "preferActiveInThread": True,
                "preferLead": True,
                "excludeUnavailable": True,
            },
            "breeds": [
                {
                    "id": "orange",
                    "catId": "orange",
                    "name": "橘猫",
                    "displayName": "阿橘",
                    "provider": "anthropic",
                    "cli": {"command": "claude"},
                }
            ],
        }

        registry.load_from_config(config)

        assert registry.has("orange")
        assert registry.is_available("orange") is True
        assert registry.get_roles("orange") == ["developer", "coder"]
        assert "主力开发者" in registry.get_evaluation("orange")

    def test_is_available_false(self):
        registry = CatRegistry()
        config = {
            "roster": {
                "patch": {
                    "family": "patch",
                    "roles": ["researcher"],
                    "available": False,
                }
            },
            "breeds": [
                {
                    "id": "patch",
                    "catId": "patch",
                    "name": "三花猫",
                    "displayName": "花花",
                    "provider": "anthropic",
                    "cli": {"command": "claude"},
                }
            ],
        }

        registry.load_from_config(config)
        assert registry.is_available("patch") is False

    def test_get_roles_default(self):
        registry = CatRegistry()
        # No roster defined for this cat
        config = {
            "roster": {},  # Empty roster
            "breeds": [
                {
                    "id": "test",
                    "catId": "test",
                    "name": "Test",
                    "provider": "anthropic",
                    "cli": {"command": "claude"},
                }
            ],
        }
        registry.load_from_config(config)
        # Should return empty list when no roster entry
        assert registry.get_roles("test") == []

    def test_get_evaluation_missing(self):
        registry = CatRegistry()
        config = {
            "roster": {"orange": {"available": True}},
            "breeds": [
                {
                    "id": "orange",
                    "catId": "orange",
                    "name": "橘猫",
                    "provider": "anthropic",
                    "cli": {"command": "claude"},
                }
            ],
        }
        registry.load_from_config(config)
        assert registry.get_evaluation("orange") == ""


class TestReviewPolicy:
    def test_load_review_policy(self):
        registry = CatRegistry()
        config = {
            "roster": {},
            "reviewPolicy": {
                "requireDifferentFamily": True,
                "preferActiveInThread": True,
                "preferLead": True,
                "excludeUnavailable": True,
            },
            "breeds": [],
        }

        registry.load_from_config(config)
        policy = registry.get_review_policy()

        assert policy["requireDifferentFamily"] is True
        assert policy["preferLead"] is True

    def test_default_review_policy(self):
        registry = CatRegistry()
        policy = registry.get_review_policy()

        assert policy["requireDifferentFamily"] is False
        assert policy["excludeUnavailable"] is True  # Default


class TestRuntimeOverlay:
    def test_overlay_deep_merge(self):
        registry = CatRegistry()
        # Base config
        config = {
            "roster": {"orange": {"available": True}},
            "breeds": [
                {
                    "id": "orange",
                    "catId": "orange",
                    "name": "橘猫",
                    "provider": "anthropic",
                    "cli": {"command": "claude", "defaultArgs": []},
                }
            ],
        }
        registry.load_from_config(config)

        # Overlay
        overlay = {
            "roster": {"orange": {"available": False}},
            "breeds": [
                {
                    "id": "orange",
                    "cli": {"defaultArgs": ["--model", "opus"]},
                }
            ],
        }
        registry.apply_overlay(overlay)

        # Should merge: available=False, defaultArgs added
        assert registry.is_available("orange") is False
        cat = registry.get("orange")
        assert "--model" in cat.cli_args


