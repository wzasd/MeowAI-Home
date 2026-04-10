import pytest
from src.models.cat_registry import CatRegistry, cat_registry
from src.models.types import CatConfig


@pytest.fixture
def sample_breeds():
    return [
        {
            "id": "ragdoll",
            "catId": "opus",
            "name": "布偶猫",
            "displayName": "布偶猫",
            "nickname": "宪宪",
            "avatar": "/avatars/opus.png",
            "color": {"primary": "#9B7EBD", "secondary": "#E8DFF5"},
            "mentionPatterns": ["@opus", "@布偶猫", "@宪宪"],
            "roleDescription": "主架构师",
            "defaultVariantId": "opus-default",
            "variants": [
                {
                    "id": "opus-default",
                    "catId": "opus",
                    "provider": "anthropic",
                    "defaultModel": "claude-opus-4-6",
                    "personality": "温柔但有主见",
                    "cli": {"command": "claude", "outputFormat": "stream-json", "defaultArgs": ["--output-format", "stream-json"]},
                    "contextBudget": {"maxPromptTokens": 180000, "maxContextTokens": 160000, "maxMessages": 200, "maxContentLengthPerMsg": 10000},
                },
                {
                    "id": "opus-sonnet",
                    "catId": "sonnet",
                    "variantLabel": "Sonnet",
                    "displayName": "布偶猫",
                    "mentionPatterns": ["@sonnet"],
                    "provider": "anthropic",
                    "defaultModel": "claude-sonnet-4-6",
                    "personality": "快速灵活",
                    "cli": {"command": "claude", "outputFormat": "stream-json", "defaultArgs": ["--output-format", "stream-json", "--model", "claude-sonnet-4-6"]},
                    "contextBudget": {"maxPromptTokens": 180000, "maxContextTokens": 160000, "maxMessages": 200, "maxContentLengthPerMsg": 10000},
                },
            ],
        }
    ]


class TestCatRegistry:
    def test_register_and_get(self, sample_breeds):
        reg = CatRegistry()
        reg.load_from_breeds(sample_breeds)
        config = reg.get("opus")
        assert config.cat_id == "opus"
        assert config.provider == "anthropic"
        assert config.default_model == "claude-opus-4-6"

    def test_register_multiple_variants(self, sample_breeds):
        reg = CatRegistry()
        reg.load_from_breeds(sample_breeds)
        assert reg.has("opus")
        assert reg.has("sonnet")
        sonnet = reg.get("sonnet")
        assert sonnet.default_model == "claude-sonnet-4-6"

    def test_get_not_found_raises(self):
        reg = CatRegistry()
        with pytest.raises(KeyError, match="nonexistent"):
            reg.get("nonexistent")

    def test_try_get_returns_none(self):
        reg = CatRegistry()
        assert reg.try_get("nonexistent") is None

    def test_get_all_ids(self, sample_breeds):
        reg = CatRegistry()
        reg.load_from_breeds(sample_breeds)
        ids = reg.get_all_ids()
        assert "opus" in ids
        assert "sonnet" in ids

    def test_get_by_mention(self, sample_breeds):
        reg = CatRegistry()
        reg.load_from_breeds(sample_breeds)
        config = reg.get_by_mention("@布偶猫")
        assert config is not None
        assert config.cat_id == "opus"

    def test_get_by_mention_case_insensitive(self, sample_breeds):
        reg = CatRegistry()
        reg.load_from_breeds(sample_breeds)
        config = reg.get_by_mention("@OPUS")
        assert config is not None
        assert config.cat_id == "opus"

    def test_reset(self, sample_breeds):
        reg = CatRegistry()
        reg.load_from_breeds(sample_breeds)
        reg.reset()
        assert reg.has("opus") is False

    def test_default_cat(self, sample_breeds):
        reg = CatRegistry()
        reg.load_from_breeds(sample_breeds)
        assert reg.get_default_id() == "opus"

    def test_manual_register(self):
        reg = CatRegistry()
        config = CatConfig(cat_id="test", breed_id="test", name="test", display_name="test", provider="anthropic", default_model="test")
        reg.register("test", config)
        assert reg.get("test").cat_id == "test"

    def test_register_duplicate_raises(self):
        reg = CatRegistry()
        config = CatConfig(cat_id="test", breed_id="test", name="test", display_name="test", provider="anthropic", default_model="test")
        reg.register("test", config)
        with pytest.raises(ValueError, match="already registered"):
            reg.register("test", config)
