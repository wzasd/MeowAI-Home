"""EnvRegistry — environment variable metadata registry for Web UI."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class EnvVar:
    """Metadata for an environment variable."""

    name: str
    category: str
    description: str
    default: Optional[str] = None
    required: bool = False
    sensitive: bool = False
    allowed_values: Optional[List[str]] = None
    example: Optional[str] = None


class EnvRegistry:
    """Registry for environment variable metadata."""

    def __init__(self):
        self._vars: Dict[str, EnvVar] = {}

    def register(
        self,
        name: str,
        category: str,
        description: str,
        default: Optional[str] = None,
        required: bool = False,
        sensitive: bool = False,
        allowed_values: Optional[List[str]] = None,
        example: Optional[str] = None,
    ) -> None:
        """Register an environment variable."""
        self._vars[name] = EnvVar(
            name=name,
            category=category,
            description=description,
            default=default,
            required=required,
            sensitive=sensitive,
            allowed_values=allowed_values,
            example=example,
        )

    def has(self, name: str) -> bool:
        """Check if variable is registered."""
        return name in self._vars

    def get(self, name: str) -> Optional[EnvVar]:
        """Get variable metadata."""
        return self._vars.get(name)

    def get_all(self) -> List[EnvVar]:
        """Get all registered variables."""
        return list(self._vars.values())

    def get_by_category(self, category: str) -> List[EnvVar]:
        """Get variables by category."""
        return [v for v in self._vars.values() if v.category == category]

    def get_categories(self) -> Set[str]:
        """Get all categories."""
        return set(v.category for v in self._vars.values())

    def to_dict_for_display(self) -> List[Dict[str, Any]]:
        """Export as list of dicts for Web UI display.

        Sensitive values are masked.
        """
        result = []
        for var in self._vars.values():
            display_default = var.default
            if var.sensitive and display_default:
                display_default = "********"

            result.append({
                "name": var.name,
                "category": var.category,
                "description": var.description,
                "default": display_default,
                "required": var.required,
                "sensitive": var.sensitive,
                "allowed_values": var.allowed_values,
                "example": var.example,
            })
        return result

    def to_dict_for_export(self) -> str:
        """Export as .env format string."""
        lines = []
        by_category: Dict[str, List[EnvVar]] = {}
        for var in self._vars.values():
            by_category.setdefault(var.category, []).append(var)

        for category in sorted(by_category.keys()):
            lines.append(f"# {category.upper()}")
            for var in sorted(by_category[category], key=lambda v: v.name):
                lines.append(f"# {var.description}")
                default = var.default or ""
                lines.append(f"{var.name}={default}")
                lines.append("")

        return "\n".join(lines)

    def validate(self, env: Dict[str, str]) -> List[str]:
        """Validate environment against registry.

        Returns list of missing required variables.
        """
        missing = []
        for var in self._vars.values():
            if var.required and not env.get(var.name):
                missing.append(var.name)
        return missing


# Default registry with all MeowAI environment variables
default_env_registry = EnvRegistry()

# Core
default_env_registry.register(
    name="MEOWAI_ENV",
    category="core",
    description="运行环境: development / production",
    default="development",
    allowed_values=["development", "production", "testing"],
)

default_env_registry.register(
    name="MEOWAI_PORT",
    category="core",
    description="API 服务端口",
    default="3004",
    example="3004",
)

default_env_registry.register(
    name="MEOWAI_LOG_LEVEL",
    category="core",
    description="日志级别",
    default="INFO",
    allowed_values=["DEBUG", "INFO", "WARNING", "ERROR"],
)

# Security
default_env_registry.register(
    name="MEOWAI_SECRET_KEY",
    category="security",
    description="JWT 签名密钥 (生产环境请修改为随机字符串)",
    default="change-me-in-production",
    sensitive=True,
    required=True,
)

default_env_registry.register(
    name="MEOWAI_API_TOKEN",
    category="security",
    description="API 访问令牌 (可选)",
    sensitive=True,
)

# Database
default_env_registry.register(
    name="MEOWAI_DB_PATH",
    category="database",
    description="SQLite 数据库路径",
    default="./data/meowai.db",
    example="./data/meowai.db",
)

# AI Provider
default_env_registry.register(
    name="ANTHROPIC_API_KEY",
    category="ai",
    description="Anthropic API Key (Claude)",
    sensitive=True,
)

default_env_registry.register(
    name="OPENAI_API_KEY",
    category="ai",
    description="OpenAI API Key",
    sensitive=True,
)

default_env_registry.register(
    name="GOOGLE_API_KEY",
    category="ai",
    description="Google API Key (Gemini)",
    sensitive=True,
)

# Connector
default_env_registry.register(
    name="FEISHU_APP_ID",
    category="connector",
    description="飞书 App ID",
)

default_env_registry.register(
    name="FEISHU_APP_SECRET",
    category="connector",
    description="飞书 App Secret",
    sensitive=True,
)

default_env_registry.register(
    name="DINGTALK_APP_KEY",
    category="connector",
    description="钉钉 App Key",
)

default_env_registry.register(
    name="DINGTALK_APP_SECRET",
    category="connector",
    description="钉钉 App Secret",
    sensitive=True,
)

__all__ = ["EnvRegistry", "EnvVar", "default_env_registry"]
