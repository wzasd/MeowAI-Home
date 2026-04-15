"""Limb REST API endpoints for device control plane."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.limb import LimbRegistry, LeaseManager, DeviceStatus, DeviceCapability

router = APIRouter(prefix="/limbs", tags=["limbs"])


# === Helpers ===

def _get_registry(request: Request) -> LimbRegistry:
    registry = getattr(request.app.state, "limb_registry", None)
    if not registry:
        raise HTTPException(status_code=503, detail="Limb registry not initialized")
    return registry


def _get_lease_manager(request: Request) -> Optional[LeaseManager]:
    return getattr(request.app.state, "limb_lease_manager", None)


def _device_to_dict(device) -> Dict[str, Any]:
    return {
        "device_id": device.device_id,
        "name": device.name,
        "device_type": device.device_type,
        "capabilities": [c.value for c in device.capabilities],
        "status": device.status.value,
        "endpoint": device.endpoint,
        "metadata": device.metadata,
        "owner_user_id": device.owner_user_id,
        "registered_at": device.registered_at,
        "last_seen_at": device.last_seen_at,
        "health_check_interval": device.health_check_interval,
        "is_paired": device.is_paired,
        "is_available": device.is_available,
    }


def _log_to_dict(log) -> Dict[str, Any]:
    return {
        "log_id": log.log_id,
        "device_id": log.device_id,
        "user_id": log.user_id,
        "action": log.action,
        "params": log.params,
        "result": {
            "success": log.result.success,
            "device_id": log.result.device_id,
            "action": log.result.action,
            "result": log.result.result,
            "error": log.result.error,
            "execution_time_ms": log.result.execution_time_ms,
            "timestamp": log.result.timestamp,
        },
        "timestamp": log.timestamp,
    }


# === Models ===

class RegisterDeviceBody(BaseModel):
    name: str
    device_type: str
    endpoint: str
    capabilities: List[str] = Field(default_factory=list)
    auth_token: Optional[str] = None
    owner_user_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UpdateDeviceBody(BaseModel):
    name: Optional[str] = None
    endpoint: Optional[str] = None
    status: Optional[str] = None
    auth_token: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class InvokeBody(BaseModel):
    action: str
    params: Dict[str, Any] = Field(default_factory=dict)


class LeaseBody(BaseModel):
    ttl_seconds: Optional[float] = None


class ExtendLeaseBody(BaseModel):
    additional_seconds: float = 300.0


# === Endpoints ===

@router.get("")
async def list_devices(request: Request) -> Dict[str, Any]:
    """List all registered devices."""
    registry = _get_registry(request)
    devices = registry.list_all()
    return {"devices": [_device_to_dict(d) for d in devices]}


@router.get("/available")
async def list_available_devices(request: Request) -> Dict[str, Any]:
    """List devices available for invocation."""
    registry = _get_registry(request)
    devices = registry.list_available()
    return {"devices": [_device_to_dict(d) for d in devices]}


@router.get("/leases")
async def list_leases(request: Request) -> Dict[str, Any]:
    """List all active leases."""
    lease_manager = _get_lease_manager(request)
    if not lease_manager:
        return {"leases": []}
    leases = lease_manager.list_all_leases()
    return {
        "leases": [
            {
                "lease_id": l.lease_id,
                "user_id": l.user_id,
                "device_id": l.device_id,
                "acquired_at": l.acquired_at,
                "expires_at": l.expires_at,
                "remaining_seconds": l.remaining_seconds,
            }
            for l in leases.values()
        ]
    }


@router.post("")
async def register_device(body: RegisterDeviceBody, request: Request) -> Dict[str, Any]:
    """Register a new limb device."""
    registry = _get_registry(request)
    capabilities = [DeviceCapability(c) for c in body.capabilities]
    device = registry.register(
        name=body.name,
        device_type=body.device_type,
        endpoint=body.endpoint,
        capabilities=capabilities,
        auth_token=body.auth_token,
        owner_user_id=body.owner_user_id,
        metadata=body.metadata,
    )
    return {"success": True, "device": _device_to_dict(device)}


@router.get("/{device_id}")
async def get_device(device_id: str, request: Request) -> Dict[str, Any]:
    """Get device details."""
    registry = _get_registry(request)
    device = registry.get(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"device": _device_to_dict(device)}


@router.patch("/{device_id}")
async def update_device(device_id: str, body: UpdateDeviceBody, request: Request) -> Dict[str, Any]:
    """Update device info or status."""
    registry = _get_registry(request)
    device = registry.get(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if body.name is not None:
        device.name = body.name
    if body.endpoint is not None:
        device.endpoint = body.endpoint
    if body.auth_token is not None:
        device.auth_token = body.auth_token
    if body.metadata is not None:
        device.metadata = body.metadata
    if body.status is not None:
        status = DeviceStatus(body.status)
        device.update_status(status)

    registry._save_device(device)
    return {"success": True, "device": _device_to_dict(device)}


@router.delete("/{device_id}")
async def delete_device(device_id: str, request: Request) -> Dict[str, Any]:
    """Unregister a device."""
    registry = _get_registry(request)
    success = registry.unregister(device_id)
    if not success:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"success": True}


@router.post("/{device_id}/pair")
async def pair_device(device_id: str, request: Request) -> Dict[str, Any]:
    """Pair a device."""
    registry = _get_registry(request)
    success = registry.pair(device_id)
    if not success:
        raise HTTPException(status_code=404, detail="Device not found")
    device = registry.get(device_id)
    return {"success": True, "device": _device_to_dict(device)}


@router.post("/{device_id}/unpair")
async def unpair_device(device_id: str, request: Request) -> Dict[str, Any]:
    """Unpair a device."""
    registry = _get_registry(request)
    success = registry.unpair(device_id)
    if not success:
        raise HTTPException(status_code=404, detail="Device not found")
    device = registry.get(device_id)
    return {"success": True, "device": _device_to_dict(device)}


@router.post("/{device_id}/invoke")
async def invoke_device(device_id: str, body: InvokeBody, request: Request) -> Dict[str, Any]:
    """Invoke an action on a device."""
    registry = _get_registry(request)
    device = registry.get(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Use a generic user id for now; auth middleware can supply real user later
    user_id = "current_user"
    result = await registry.invoke(device_id, user_id, body.action, body.params)
    return {
        "success": result.success,
        "device_id": result.device_id,
        "action": result.action,
        "result": result.result,
        "error": result.error,
        "execution_time_ms": result.execution_time_ms,
        "timestamp": result.timestamp,
    }


@router.get("/{device_id}/logs")
async def get_device_logs(device_id: str, limit: int = 100, request: Request = None) -> Dict[str, Any]:
    """Get invocation logs for a device."""
    registry = _get_registry(request)
    logs = registry.get_invocation_logs(device_id=device_id, limit=limit)
    return {"logs": [_log_to_dict(l) for l in logs]}


@router.post("/leases/{device_id}/acquire")
async def acquire_lease(device_id: str, body: LeaseBody, request: Request) -> Dict[str, Any]:
    """Acquire a lease for a device."""
    lease_manager = _get_lease_manager(request)
    if not lease_manager:
        raise HTTPException(status_code=503, detail="Lease manager not initialized")
    user_id = "current_user"
    lease = lease_manager.acquire(user_id, device_id, ttl_seconds=body.ttl_seconds)
    if not lease:
        raise HTTPException(status_code=409, detail="Device already leased or not available")
    return {
        "success": True,
        "lease": {
            "lease_id": lease.lease_id,
            "user_id": lease.user_id,
            "device_id": lease.device_id,
            "acquired_at": lease.acquired_at,
            "expires_at": lease.expires_at,
        },
    }


@router.post("/leases/{device_id}/release")
async def release_lease(device_id: str, request: Request) -> Dict[str, Any]:
    """Release a lease."""
    lease_manager = _get_lease_manager(request)
    if not lease_manager:
        raise HTTPException(status_code=503, detail="Lease manager not initialized")
    success = lease_manager.release(device_id)
    if not success:
        raise HTTPException(status_code=404, detail="Lease not found")
    return {"success": True}


@router.post("/leases/{device_id}/extend")
async def extend_lease(device_id: str, body: ExtendLeaseBody, request: Request) -> Dict[str, Any]:
    """Extend a lease."""
    lease_manager = _get_lease_manager(request)
    if not lease_manager:
        raise HTTPException(status_code=503, detail="Lease manager not initialized")
    success = lease_manager.extend(device_id, body.additional_seconds)
    if not success:
        raise HTTPException(status_code=404, detail="Lease not found or expired")
    return {"success": True}
