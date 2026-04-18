from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


# Brand type for cat IDs
CatId = str


class ProviderType(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    DARE = "dare"
    ANTIGRAVITY = "antigravity"
    OPENCODE = "opencode"
    A2A = "a2a"


class AgentMessageType(str, Enum):
    TEXT = "text"
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    DONE = "done"
    USAGE = "usage"
    STATUS = "status"


@dataclass
class ContextBudget:
    max_prompt_tokens: int = 100000
    max_context_tokens: int = 60000
    max_messages: int = 200
    max_content_length_per_msg: int = 10000


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    cost_usd: float = 0.0

    def merge(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            input_tokens=other.input_tokens or self.input_tokens,
            output_tokens=self.output_tokens + (other.output_tokens or 0),
            cache_read_tokens=self.cache_read_tokens + (other.cache_read_tokens or 0),
            cache_creation_tokens=self.cache_creation_tokens + (other.cache_creation_tokens or 0),
            cost_usd=self.cost_usd + (other.cost_usd or 0.0),
        )


@dataclass
class VariantConfig:
    id: str
    cat_id: CatId
    provider: str
    default_model: str
    personality: str = ""
    cli_command: str = ""
    cli_args: List[str] = field(default_factory=list)
    mention_patterns: List[str] = field(default_factory=list)
    avatar: Optional[str] = None
    color_primary: str = "#666666"
    color_secondary: str = "#EEEEEE"
    budget: ContextBudget = field(default_factory=ContextBudget)
    mcp_support: bool = False
    effort: str = "high"


@dataclass
class CatConfig:
    cat_id: CatId
    breed_id: str
    name: str
    display_name: str
    provider: str
    default_model: str
    personality: str = ""
    mention_patterns: List[str] = field(default_factory=list)
    avatar: Optional[str] = None
    color_primary: str = "#666666"
    color_secondary: str = "#EEEEEE"
    cli_command: str = ""
    cli_args: List[str] = field(default_factory=list)
    budget: ContextBudget = field(default_factory=ContextBudget)
    variant_id: Optional[str] = None
    breed_name: Optional[str] = None
    role_description: Optional[str] = None
    team_strengths: Optional[str] = None
    caution: Optional[str] = None
    mcp_support: bool = False
    effort: str = "high"
    account_ref: Optional[str] = None
    capabilities: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)


@dataclass
class AgentMessage:
    type: AgentMessageType
    content: str = ""
    cat_id: Optional[CatId] = None
    tool_name: Optional[str] = None
    tool_params: Optional[Dict[str, Any]] = None
    usage: Optional[TokenUsage] = None
    session_id: Optional[str] = None


@dataclass
class InvocationOptions:
    system_prompt: Optional[str] = None
    timeout: float = 300.0
    session_id: Optional[str] = None
    effort: Optional[str] = None
    mcp_config: Optional[Dict[str, Any]] = None
    extra_args: List[str] = field(default_factory=list)
    cwd: Optional[str] = None
