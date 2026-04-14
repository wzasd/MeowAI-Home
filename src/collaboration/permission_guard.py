from typing import List, Optional

HIGH_RISK_TOOLS = {
    "execute_command": ["shell_exec"],
    "delete_file": ["file_write"],
    "write_file": ["file_write"],
    "git_push": ["git_ops"],
    "edit_file": ["file_write"],
}


def check_permission(cat_permissions: List[str], tool_name: str) -> bool:
    """检查猫是否有权限调用指定工具"""
    if tool_name not in HIGH_RISK_TOOLS:
        return True
    required = HIGH_RISK_TOOLS[tool_name]
    return any(r in cat_permissions for r in required)


def get_missing_permission(tool_name: str) -> Optional[str]:
    """返回缺失的 permission 建议"""
    if tool_name not in HIGH_RISK_TOOLS:
        return None
    return HIGH_RISK_TOOLS[tool_name][0]
