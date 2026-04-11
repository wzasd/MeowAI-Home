"""LimbAccessPolicy — Access control policy for limb devices."""

from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field


class AccessLevel(str, Enum):
    """Access levels for devices."""
    FREE = "free"       # Anyone can use
    LEASED = "leased"   # Requires lease acquisition
    GATED = "gated"     # Requires explicit approval


@dataclass
class AccessRule:
    """Access rule for a device or device type."""
    device_id: Optional[str]       # None means applies to all devices of type
    device_type: Optional[str]     # None means applies to specific device only
    allowed_users: Set[str] = field(default_factory=set)
    allowed_actions: Set[str] = field(default_factory=set)
    require_approval: bool = False


class LimbAccessPolicy:
    """Manages access control for limb devices.

    Supports three levels:
    - FREE: Anyone can invoke
    - LEASED: Requires lease (first-come-first-served)
    - GATED: Requires explicit user approval
    """

    def __init__(self):
        self._device_levels: Dict[str, AccessLevel] = {}  # device_id -> level
        self._type_levels: Dict[str, AccessLevel] = {}    # device_type -> level
        self._default_level = AccessLevel.LEASED
        self._rules: List[AccessRule] = []
        self._user_approvals: Dict[str, Set[str]] = {}  # user_id -> {device_ids}

    def set_device_level(self, device_id: str, level: AccessLevel) -> None:
        """Set access level for a specific device."""
        self._device_levels[device_id] = level

    def set_type_level(self, device_type: str, level: AccessLevel) -> None:
        """Set default access level for a device type."""
        self._type_levels[device_type] = level

    def set_default_level(self, level: AccessLevel) -> None:
        """Set global default access level."""
        self._default_level = level

    def get_level(self, device_id: str, device_type: Optional[str] = None) -> AccessLevel:
        """Get effective access level for a device."""
        # Check device-specific level
        if device_id in self._device_levels:
            return self._device_levels[device_id]

        # Check type level
        if device_type and device_type in self._type_levels:
            return self._type_levels[device_type]

        # Return default
        return self._default_level

    def add_rule(
        self,
        device_id: Optional[str] = None,
        device_type: Optional[str] = None,
        allowed_users: Optional[List[str]] = None,
        allowed_actions: Optional[List[str]] = None,
        require_approval: bool = False,
    ) -> None:
        """Add an access rule.

        Args:
            device_id: Specific device ID (None = all of type)
            device_type: Device type (None = specific device only)
            allowed_users: List of allowed user IDs
            allowed_actions: List of allowed action names
            require_approval: Whether explicit approval is required
        """
        rule = AccessRule(
            device_id=device_id,
            device_type=device_type,
            allowed_users=set(allowed_users or []),
            allowed_actions=set(allowed_actions or []),
            require_approval=require_approval,
        )
        self._rules.append(rule)

    def approve_user(self, user_id: str, device_id: str) -> None:
        """Approve a user for accessing a gated device."""
        if user_id not in self._user_approvals:
            self._user_approvals[user_id] = set()
        self._user_approvals[user_id].add(device_id)

    def revoke_user(self, user_id: str, device_id: str) -> None:
        """Revoke user approval for a device."""
        if user_id in self._user_approvals:
            self._user_approvals[user_id].discard(device_id)

    def check_access(
        self,
        user_id: str,
        device_id: str,
        action: str,
        device_type: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Check if user can access device.

        Returns:
            Tuple of (allowed, reason)
        """
        level = self.get_level(device_id, device_type)

        # FREE level: always allow
        if level == AccessLevel.FREE:
            return True, "Access granted (free level)"

        # Check specific rules
        for rule in self._rules:
            # Check if rule applies
            if rule.device_id and rule.device_id != device_id:
                continue
            if rule.device_type and rule.device_type != device_type:
                continue

            # Check user whitelist
            if rule.allowed_users and user_id not in rule.allowed_users:
                continue

            # Check action whitelist
            if rule.allowed_actions and action not in rule.allowed_actions:
                continue

            # Check approval requirement
            if rule.require_approval:
                user_approved = self._user_approvals.get(user_id, set())
                if device_id not in user_approved:
                    return False, f"User {user_id} not approved for device {device_id}"

            # Rule matched and passed all checks
            return True, "Access granted by rule"

        # GATED level without matching rule requires approval
        if level == AccessLevel.GATED:
            user_approved = self._user_approvals.get(user_id, set())
            if device_id not in user_approved:
                return False, f"Device {device_id} is gated, user not approved"

        # LEASED level: allow (lease acquisition handled separately)
        if level == AccessLevel.LEASED:
            return True, "Access granted (leased level)"

        return True, "Access granted"

    def is_approved(self, user_id: str, device_id: str) -> bool:
        """Check if user is approved for a gated device."""
        return device_id in self._user_approvals.get(user_id, set())

    def list_approved_devices(self, user_id: str) -> List[str]:
        """List devices a user is approved for."""
        return list(self._user_approvals.get(user_id, set()))
