"""Tests for EnvRegistry (D2)."""
import pytest
from src.config.env_registry import EnvRegistry, EnvVar


class TestEnvVar:
    def test_env_var_creation(self):
        var = EnvVar(
            name="MEOWAI_ENV",
            category="core",
            description="运行环境",
            default="development",
        )
        assert var.name == "MEOWAI_ENV"
        assert var.category == "core"
        assert var.sensitive is False  # Default

    def test_env_var_sensitive(self):
        var = EnvVar(
            name="MEOWAI_SECRET_KEY",
            category="security",
            description="JWT密钥",
            sensitive=True,
        )
        assert var.sensitive is True


class TestEnvRegistry:
    def test_register_env_var(self):
        registry = EnvRegistry()
        registry.register(
            name="MEOWAI_ENV",
            category="core",
            description="运行环境",
            default="development",
        )

        assert registry.has("MEOWAI_ENV")

    def test_get_env_var(self):
        registry = EnvRegistry()
        registry.register(
            name="MEOWAI_ENV",
            category="core",
            description="运行环境",
            default="development",
        )

        var = registry.get("MEOWAI_ENV")
        assert var.name == "MEOWAI_ENV"
        assert var.default == "development"

    def test_get_all_vars(self):
        registry = EnvRegistry()
        registry.register("VAR1", "core", "Desc 1")
        registry.register("VAR2", "security", "Desc 2")
        registry.register("VAR3", "core", "Desc 3")

        all_vars = registry.get_all()
        assert len(all_vars) == 3

    def test_get_by_category(self):
        registry = EnvRegistry()
        registry.register("VAR1", "core", "Desc 1")
        registry.register("VAR2", "security", "Desc 2")
        registry.register("VAR3", "core", "Desc 3")

        core_vars = registry.get_by_category("core")
        assert len(core_vars) == 2
        assert all(v.category == "core" for v in core_vars)

    def test_get_nonexistent(self):
        registry = EnvRegistry()
        assert registry.get("NONEXISTENT") is None

    def test_to_dict_for_display(self):
        registry = EnvRegistry()
        registry.register(
            name="MEOWAI_ENV",
            category="core",
            description="运行环境",
            default="development",
        )
        registry.register(
            name="MEOWAI_SECRET_KEY",
            category="security",
            description="JWT密钥",
            sensitive=True,
            default="change-me",
        )

        display = registry.to_dict_for_display()

        assert display[0]["name"] == "MEOWAI_ENV"
        assert display[0]["default"] == "development"
        # Sensitive values should be masked
        secret = next(v for v in display if v["name"] == "MEOWAI_SECRET_KEY")
        assert secret["default"] == "********"

    def test_to_dict_for_export(self):
        registry = EnvRegistry()
        registry.register(
            name="MEOWAI_ENV",
            category="core",
            description="运行环境",
            default="development",
        )

        export = registry.to_dict_for_export()

        assert "MEOWAI_ENV=development" in export

    def test_validate_required(self):
        registry = EnvRegistry()
        registry.register(
            name="REQUIRED_VAR",
            category="core",
            description="Required",
            required=True,
        )
        registry.register(
            name="OPTIONAL_VAR",
            category="core",
            description="Optional",
            required=False,
        )

        # Mock environment with only optional var
        env = {"OPTIONAL_VAR": "value"}
        missing = registry.validate(env)

        assert "REQUIRED_VAR" in missing
        assert "OPTIONAL_VAR" not in missing


class TestDefaultRegistry:
    def test_default_registry_populated(self):
        from src.config.env_registry import default_env_registry

        assert default_env_registry.has("MEOWAI_ENV")
        assert default_env_registry.has("MEOWAI_SECRET_KEY")
        assert default_env_registry.has("MEOWAI_DB_PATH")

    def test_get_all_categories(self):
        from src.config.env_registry import default_env_registry

        cats = default_env_registry.get_categories()
        assert "core" in cats
        assert "security" in cats
