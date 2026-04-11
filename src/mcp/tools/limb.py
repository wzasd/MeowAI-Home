"""Limb MCP tools for remote device control."""

from typing import Any, Dict, List, Optional

from src.limb import LimbRegistry, AccessLevel


class LimbTools:
    """MCP tools for limb device management."""

    def __init__(self, limb_registry: LimbRegistry):
        self._registry = limb_registry

    async def limb_list_available(self) -> Dict[str, Any]:
        """List all available (online and paired) limb devices.

        Returns:
            Dict with available devices.
        """
        devices = self._registry.list_available()

        return {
            "devices": [
                {
                    "device_id": d.device_id,
                    "name": d.name,
                    "type": d.device_type,
                    "capabilities": [c.value for c in d.capabilities],
                    "status": d.status.value,
                    "endpoint": d.endpoint,
                }
                for d in devices
            ],
            "count": len(devices),
        }

    async def limb_list_all(self) -> Dict[str, Any]:
        """List all registered limb devices (including offline).

        Returns:
            Dict with all devices.
        """
        devices = self._registry.list_all()

        return {
            "devices": [
                {
                    "device_id": d.device_id,
                    "name": d.name,
                    "type": d.device_type,
                    "capabilities": [c.value for c in d.capabilities],
                    "status": d.status.value,
                    "is_paired": d.is_paired,
                    "last_seen": d.last_seen_at,
                }
                for d in devices
            ],
            "count": len(devices),
        }

    async def limb_invoke(
        self,
        device_id: str,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        user_id: str = "default",
    ) -> Dict[str, Any]:
        """Invoke an action on a limb device.

        Args:
            device_id: Target device ID
            action: Action to perform
            params: Action parameters
            user_id: Invoking user

        Returns:
            Invocation result.
        """
        result = await self._registry.invoke(
            device_id=device_id,
            user_id=user_id,
            action=action,
            params=params,
        )

        return {
            "success": result.success,
            "device_id": result.device_id,
            "action": result.action,
            "result": result.result,
            "error": result.error,
            "execution_time_ms": result.execution_time_ms,
        }

    async def limb_pair_list(self) -> Dict[str, Any]:
        """List pending device pairing requests.

        Returns:
            Dict with unpaired devices.
        """
        all_devices = self._registry.list_all()
        pending = [d for d in all_devices if not d.is_paired]

        return {
            "pending_devices": [
                {
                    "device_id": d.device_id,
                    "name": d.name,
                    "type": d.device_type,
                    "registered_at": d.registered_at,
                }
                for d in pending
            ],
            "count": len(pending),
        }

    async def limb_pair_approve(
        self,
        device_id: str,
    ) -> Dict[str, Any]:
        """Approve pairing for a device.

        Args:
            device_id: Device to approve

        Returns:
            Result of approval.
        """
        device = self._registry.get(device_id)
        if not device:
            return {
                "success": False,
                "error": "Device not found",
            }

        if device.is_paired:
            return {
                "success": False,
                "error": "Device already paired",
            }

        success = self._registry.pair(device_id)

        return {
            "success": success,
            "device_id": device_id,
            "message": f"Device {device.name} is now paired" if success else "Failed to pair",
        }

    async def limb_pair_revoke(
        self,
        device_id: str,
    ) -> Dict[str, Any]:
        """Revoke pairing for a device.

        Args:
            device_id: Device to revoke

        Returns:
            Result of revocation.
        """
        device = self._registry.get(device_id)
        if not device:
            return {
                "success": False,
                "error": "Device not found",
            }

        success = self._registry.unpair(device_id)

        return {
            "success": success,
            "device_id": device_id,
            "message": f"Device {device.name} is now unpaired" if success else "Failed to unpair",
        }

    async def limb_get_status(
        self,
        device_id: str,
    ) -> Dict[str, Any]:
        """Get status of a specific device.

        Args:
            device_id: Device to check

        Returns:
            Device status.
        """
        device = self._registry.get(device_id)
        if not device:
            return {
                "success": False,
                "error": "Device not found",
            }

        return {
            "success": True,
            "device_id": device.device_id,
            "name": device.name,
            "type": device.device_type,
            "status": device.status.value,
            "capabilities": [c.value for c in device.capabilities],
            "is_paired": device.is_paired,
            "is_available": device.is_available,
            "last_seen": device.last_seen_at,
            "endpoint": device.endpoint,
        }

    async def limb_get_logs(
        self,
        device_id: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Get invocation logs.

        Args:
            device_id: Filter by device (None = all)
            limit: Maximum logs to return

        Returns:
            Invocation logs.
        """
        logs = self._registry.get_invocation_logs(device_id=device_id, limit=limit)

        return {
            "logs": [
                {
                    "log_id": log.log_id,
                    "device_id": log.device_id,
                    "user_id": log.user_id,
                    "action": log.action,
                    "success": log.result.success,
                    "execution_time_ms": log.result.execution_time_ms,
                    "timestamp": log.timestamp,
                    "error": log.result.error,
                }
                for log in logs
            ],
            "count": len(logs),
        }


def get_limb_tools(limb_registry: LimbRegistry) -> Dict[str, Any]:
    """Get all limb tool handlers."""
    tools = LimbTools(limb_registry)

    return {
        "limb_list_available": tools.limb_list_available,
        "limb_list_all": tools.limb_list_all,
        "limb_invoke": tools.limb_invoke,
        "limb_pair_list": tools.limb_pair_list,
        "limb_pair_approve": tools.limb_pair_approve,
        "limb_pair_revoke": tools.limb_pair_revoke,
        "limb_get_status": tools.limb_get_status,
        "limb_get_logs": tools.limb_get_logs,
    }
