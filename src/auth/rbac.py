"""Role-Based Access Control (RBAC) system"""
from typing import Set, Dict

# Role to permissions mapping
ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "admin": {
        "read", "write", "delete",
        "manage_users", "manage_agents", "manage_packs",
        "manage_system", "view_audit_logs"
    },
    "member": {
        "read", "write",
        "manage_agents", "use_packs"
    },
    "viewer": {
        "read"
    },
}


def check_permission(role: str, action: str) -> bool:
    """Check if a role has permission to perform an action."""
    return action in ROLE_PERMISSIONS.get(role, set())


def get_role_permissions(role: str) -> Set[str]:
    """Get all permissions for a role."""
    return ROLE_PERMISSIONS.get(role, set()).copy()
