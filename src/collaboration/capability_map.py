from typing import Any, List

CAPABILITY_TASK_MAP = {
    "chat": ["conversation"],
    "code_gen": ["implement", "write_code", "refactor", "debug"],
    "code_review": ["review", "audit", "inspect"],
    "research": ["research", "design", "brainstorm"],
    "shell_exec": ["execute_command", "run_script"],
    "file_write": ["write_file", "edit_file", "delete_file"],
    "git_ops": ["git_commit", "git_push", "git_branch"],
}

CAPABILITY_ALIASES = {
    "code": "code_gen",
    "coding": "code_gen",
    "review": "code_review",
    "audit": "code_review",
    "inspect": "code_review",
    "conversation": "chat",
}

ROLE_CAPABILITY_MAP = {
    "developer": ["code_gen"],
    "coder": ["code_gen"],
    "implementer": ["code_gen"],
    "reviewer": ["code_review"],
    "auditor": ["code_review"],
    "inspector": ["code_review"],
    "researcher": ["research"],
    "designer": ["research"],
    "creative": ["research"],
}


def get_task_type(intent: str, mentions: List[str]) -> str:
    """根据 intent 和 mention 推断任务类型"""
    intent_lower = intent.lower()
    if any(k in intent_lower for k in ("review", "audit", "check")):
        return "review"
    if any(k in intent_lower for k in ("research", "find", "look up", "design")):
        return "research"
    if any(
        k in intent_lower for k in ("write", "code", "implement", "refactor", "debug")
    ):
        return "implement"
    if any(k in intent_lower for k in ("run", "execute", "command", "shell")):
        return "execute_command"
    return "general"


def required_capabilities_for_task(task_type: str) -> List[str]:
    """返回执行某任务类型所需的 capability 列表"""
    caps = []
    for cap, tasks in CAPABILITY_TASK_MAP.items():
        if task_type in tasks:
            caps.append(cap)
    return caps


def cat_can_handle(cat_capabilities: List[str], task_type: str) -> bool:
    """检查猫的 capabilities 是否覆盖任务类型"""
    required = required_capabilities_for_task(task_type)
    if not required:
        return True
    normalized = normalize_capabilities(cat_capabilities)
    return any(r in normalized for r in required)


def normalize_capabilities(capabilities: List[str]) -> List[str]:
    normalized = []
    seen = set()
    for capability in capabilities or []:
        lowered = str(capability).lower()
        canonical = CAPABILITY_ALIASES.get(lowered, lowered)
        if canonical not in seen:
            seen.add(canonical)
            normalized.append(canonical)
    return normalized


def get_config_capabilities(config: Any) -> List[str]:
    """Read capabilities from runtime CatConfig objects or legacy dict configs."""
    if isinstance(config, dict) and "capabilities" in config:
        return normalize_capabilities(_get_config_list(config, "capabilities"))

    declared = _get_config_list(config, "capabilities")
    if declared:
        return normalize_capabilities(declared)

    roles = _get_config_list(config, "roles")
    derived = []
    for role in roles:
        derived.extend(ROLE_CAPABILITY_MAP.get(str(role).lower(), []))
    return normalize_capabilities(derived)


def _get_config_list(config: Any, key: str) -> List[str]:
    if config is None:
        return []
    if isinstance(config, dict):
        value = config.get(key, [])
    else:
        value = getattr(config, key, [])
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)
