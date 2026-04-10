from typing import Dict, List, Optional
from src.models.types import CatConfig, CatId, ContextBudget


class CatRegistry:
    """全局猫配置注册表 — 从 cat-config.json breeds+variants 扁平化"""

    def __init__(self):
        self._cats: Dict[CatId, CatConfig] = {}
        self._mention_index: Dict[str, CatId] = {}  # lowercase mention -> catId
        self._default_id: Optional[CatId] = None

    def load_from_breeds(self, breeds: List[dict]) -> None:
        """从 cat-config.json breeds 数组加载所有猫"""
        for breed in breeds:
            breed_id = breed["id"]
            breed_name = breed.get("name", breed_id)
            default_variant_id = breed.get("defaultVariantId")

            for variant in breed.get("variants", []):
                cat_id = variant.get("catId", breed.get("catId"))
                if not cat_id:
                    continue

                cli_config = variant.get("cli", {})
                budget_data = variant.get("contextBudget", {})
                color_data = breed.get("color", {})

                config = CatConfig(
                    cat_id=cat_id,
                    breed_id=breed_id,
                    name=breed.get("displayName", breed_name),
                    display_name=variant.get("displayName", breed.get("displayName", breed_name)),
                    provider=variant.get("provider", ""),
                    default_model=variant.get("defaultModel", ""),
                    personality=variant.get("personality", ""),
                    mention_patterns=variant.get("mentionPatterns", breed.get("mentionPatterns", [])),
                    avatar=variant.get("avatar", breed.get("avatar")),
                    color_primary=color_data.get("primary", "#666666"),
                    color_secondary=color_data.get("secondary", "#EEEEEE"),
                    cli_command=cli_config.get("command", ""),
                    cli_args=cli_config.get("defaultArgs", []),
                    budget=ContextBudget(
                        max_prompt_tokens=budget_data.get("maxPromptTokens", 100000),
                        max_context_tokens=budget_data.get("maxContextTokens", 60000),
                        max_messages=budget_data.get("maxMessages", 200),
                        max_content_length_per_msg=budget_data.get("maxContentLengthPerMsg", 10000),
                    ),
                    variant_id=variant.get("id"),
                    breed_name=breed_name,
                    role_description=breed.get("roleDescription"),
                    team_strengths=breed.get("teamStrengths"),
                    caution=breed.get("caution"),
                    mcp_support=variant.get("mcpSupport", False),
                    effort=cli_config.get("effort", "high"),
                )
                self._cats[cat_id] = config

                # 索引 mention patterns
                for pattern in config.mention_patterns:
                    self._mention_index[pattern.lower().lstrip("@")] = cat_id
                    self._mention_index[pattern.lower()] = cat_id

            # 设置默认猫（breed 的 defaultVariantId）
            if default_variant_id:
                for variant in breed.get("variants", []):
                    if variant.get("id") == default_variant_id:
                        cid = variant.get("catId", breed.get("catId"))
                        if cid and (self._default_id is None):
                            self._default_id = cid

    def register(self, cat_id: CatId, config: CatConfig) -> None:
        if cat_id in self._cats:
            raise ValueError(f"Cat already registered: {cat_id}")
        self._cats[cat_id] = config

    def get(self, cat_id: CatId) -> CatConfig:
        if cat_id not in self._cats:
            registered = list(self._cats.keys())
            raise KeyError(f"Cat not found: {cat_id}. Registered: {registered}")
        return self._cats[cat_id]

    def try_get(self, cat_id: CatId) -> Optional[CatConfig]:
        return self._cats.get(cat_id)

    def has(self, cat_id: CatId) -> bool:
        return cat_id in self._cats

    def get_all_ids(self) -> List[CatId]:
        return list(self._cats.keys())

    def get_all_configs(self) -> Dict[CatId, CatConfig]:
        return dict(self._cats)

    def get_by_mention(self, mention: str) -> Optional[CatConfig]:
        key = mention.lower().lstrip("@")
        cat_id = self._mention_index.get(key)
        if cat_id:
            return self._cats[cat_id]
        cat_id = self._mention_index.get(mention.lower())
        if cat_id:
            return self._cats[cat_id]
        return None

    def set_default(self, cat_id: CatId) -> None:
        self._default_id = cat_id

    def get_default_id(self) -> Optional[CatId]:
        return self._default_id

    def reset(self) -> None:
        self._cats.clear()
        self._mention_index.clear()
        self._default_id = None


# 全局单例
cat_registry = CatRegistry()
