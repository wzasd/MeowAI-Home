from typing import List

CAPABILITY_TASK_MAP = {
    "chat": ["conversation"],
    "code": ["implement", "write_code", "refactor", "debug"],
    "code_review": ["review", "audit", "inspect"],
    "research": ["research", "design", "brainstorm"],
    "shell_exec": ["execute_command", "run_script"],
    "file_write": ["write_file", "edit_file", "delete_file"],
    "git_ops": ["git_commit", "git_push", "git_branch"],
}


def get_task_type(intent: str, mentions: List[str]) -> str:
    """根据 intent 和 mention 推断任务类型"""
    intent_lower = intent.lower()
    if any(k in intent_lower for k in ("review", "audit", "check")):
        return "review"
    if any(k in intent_lower for k in ("research", "find", "look up", "design")):
        return "research"
    if any(k in intent_lower for k in ("write", "code", "implement", "refactor", "debug")):
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
    return any(r in cat_capabilities for r in required)
