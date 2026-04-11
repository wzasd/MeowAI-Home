"""LimbRegistry — Device registry for remote IoT/device control."""

import time
import sqlite3
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Coroutine
from uuid import uuid4


class DeviceStatus(str, Enum):
    """Device connection status."""
    OFFLINE = "offline"
    ONLINE = "online"
    BUSY = "busy"
    ERROR = "error"


class DeviceCapability(str, Enum):
    """Common device capabilities."""
    ACTUATOR = "actuator"  # Can perform physical actions
    SENSOR = "sensor"      # Can read physical state
    DISPLAY = "display"    # Can show information
    SPEAKER = "speaker"    # Can play audio
    CAMERA = "camera"      # Can capture images/video


@dataclass
class LimbDevice:
    """A registered remote device (limb)."""
    device_id: str
    name: str
    device_type: str  # e.g., "smart_light", "robot_arm", "sensor_node"
    capabilities: List[DeviceCapability]
    status: DeviceStatus
    endpoint: str  # HTTP/HTTPS URL for device API
    auth_token: Optional[str] = None  # Bearer token for auth
    metadata: Dict[str, Any] = field(default_factory=dict)
    owner_user_id: Optional[str] = None
    registered_at: float = field(default_factory=time.time)
    last_seen_at: Optional[float] = None
    health_check_interval: int = 60  # seconds
    is_paired: bool = False  # Paired with this MeowAI instance

    @property
    def is_available(self) -> bool:
        """Check if device is available for invocation."""
        return self.status == DeviceStatus.ONLINE and self.is_paired

    def update_status(self, status: DeviceStatus) -> None:
        """Update device status."""
        self.status = status
        self.last_seen_at = time.time()


@dataclass
class InvocationResult:
    """Result of a limb invocation."""
    success: bool
    device_id: str
    action: str
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class InvocationLog:
    """Log entry for limb invocation."""
    log_id: str
    device_id: str
    user_id: str
    action: str
    params: Dict[str, Any]
    result: InvocationResult
    timestamp: float


class LimbRegistry:
    """Registry for managing remote devices (limbs)."""

    def __init__(
        self,
        db_path: str = "data/limb_registry.db",
        policy=None,
        lease_manager=None,
    ):
        self._db_path = db_path
        self._policy = policy
        self._lease_manager = lease_manager
        self._devices: Dict[str, LimbDevice] = {}
        self._invocation_handlers: Dict[str, Callable[[LimbDevice, str, Dict], Coroutine]] = {}
        self._init_db()
        self._load_devices()

    def _init_db(self) -> None:
        """Initialize SQLite schema."""
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS limb_devices (
                    device_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    device_type TEXT NOT NULL,
                    capabilities TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'offline',
                    endpoint TEXT NOT NULL,
                    auth_token TEXT,
                    metadata TEXT,
                    owner_user_id TEXT,
                    registered_at REAL NOT NULL,
                    last_seen_at REAL,
                    health_check_interval INTEGER DEFAULT 60,
                    is_paired INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS limb_invocation_logs (
                    log_id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    params TEXT,
                    success INTEGER,
                    result TEXT,
                    error TEXT,
                    execution_time_ms REAL,
                    timestamp REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_devices_status
                ON limb_devices(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_devices_owner
                ON limb_devices(owner_user_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_logs_device
                ON limb_invocation_logs(device_id)
            """)
            conn.commit()

    def _load_devices(self) -> None:
        """Load devices from database."""
        import json
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM limb_devices").fetchall()
            for row in rows:
                device = self._row_to_device(row)
                self._devices[device.device_id] = device

    def _row_to_device(self, row: sqlite3.Row) -> LimbDevice:
        import json
        return LimbDevice(
            device_id=row["device_id"],
            name=row["name"],
            device_type=row["device_type"],
            capabilities=[DeviceCapability(c) for c in json.loads(row["capabilities"])],
            status=DeviceStatus(row["status"]),
            endpoint=row["endpoint"],
            auth_token=row["auth_token"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            owner_user_id=row["owner_user_id"],
            registered_at=row["registered_at"],
            last_seen_at=row["last_seen_at"],
            health_check_interval=row["health_check_interval"],
            is_paired=bool(row["is_paired"]),
        )

    def _device_to_row(self, device: LimbDevice) -> tuple:
        import json
        return (
            device.device_id,
            device.name,
            device.device_type,
            json.dumps([c.value for c in device.capabilities]),
            device.status.value,
            device.endpoint,
            device.auth_token,
            json.dumps(device.metadata) if device.metadata else None,
            device.owner_user_id,
            device.registered_at,
            device.last_seen_at,
            device.health_check_interval,
            1 if device.is_paired else 0,
        )

    def _save_device(self, device: LimbDevice) -> None:
        """Save device to database."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO limb_devices
                (device_id, name, device_type, capabilities, status, endpoint, auth_token,
                 metadata, owner_user_id, registered_at, last_seen_at, health_check_interval, is_paired)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._device_to_row(device),
            )
            conn.commit()

    def register(
        self,
        name: str,
        device_type: str,
        endpoint: str,
        capabilities: List[DeviceCapability],
        auth_token: Optional[str] = None,
        owner_user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LimbDevice:
        """Register a new device.

        Args:
            name: Human-readable name
            device_type: Device type identifier
            endpoint: HTTP endpoint URL
            capabilities: List of device capabilities
            auth_token: Optional bearer token
            owner_user_id: Owner user ID
            metadata: Additional metadata

        Returns:
            Registered LimbDevice
        """
        device_id = f"limb_{uuid4().hex[:12]}"

        device = LimbDevice(
            device_id=device_id,
            name=name,
            device_type=device_type,
            capabilities=capabilities,
            status=DeviceStatus.OFFLINE,
            endpoint=endpoint,
            auth_token=auth_token,
            metadata=metadata or {},
            owner_user_id=owner_user_id,
            is_paired=False,
        )

        self._devices[device_id] = device
        self._save_device(device)

        return device

    def unregister(self, device_id: str) -> bool:
        """Unregister a device.

        Args:
            device_id: Device ID to remove

        Returns:
            True if device was removed
        """
        if device_id not in self._devices:
            return False

        del self._devices[device_id]

        with sqlite3.connect(self._db_path) as conn:
            conn.execute("DELETE FROM limb_devices WHERE device_id = ?", (device_id,))
            conn.commit()

        return True

    def get(self, device_id: str) -> Optional[LimbDevice]:
        """Get device by ID."""
        return self._devices.get(device_id)

    def list_all(self) -> List[LimbDevice]:
        """List all registered devices."""
        return list(self._devices.values())

    def list_available(self) -> List[LimbDevice]:
        """List devices available for invocation."""
        return [d for d in self._devices.values() if d.is_available]

    def list_by_type(self, device_type: str) -> List[LimbDevice]:
        """List devices by type."""
        return [d for d in self._devices.values() if d.device_type == device_type]

    def list_by_capability(self, capability: DeviceCapability) -> List[LimbDevice]:
        """List devices with specific capability."""
        return [d for d in self._devices.values() if capability in d.capabilities]

    def update_status(self, device_id: str, status: DeviceStatus) -> bool:
        """Update device status."""
        if device_id not in self._devices:
            return False

        device = self._devices[device_id]
        device.update_status(status)
        self._save_device(device)
        return True

    def pair(self, device_id: str) -> bool:
        """Pair device with this MeowAI instance."""
        if device_id not in self._devices:
            return False

        device = self._devices[device_id]
        device.is_paired = True
        self._save_device(device)
        return True

    def unpair(self, device_id: str) -> bool:
        """Unpair device."""
        if device_id not in self._devices:
            return False

        device = self._devices[device_id]
        device.is_paired = False
        self._save_device(device)
        return True

    def register_invocation_handler(
        self,
        device_type: str,
        handler: Callable[[LimbDevice, str, Dict], Coroutine],
    ) -> None:
        """Register handler for device type invocations."""
        self._invocation_handlers[device_type] = handler

    async def invoke(
        self,
        device_id: str,
        user_id: str,
        action: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> InvocationResult:
        """Invoke an action on a device.

        Pipeline: check → policy → lease → execute → log

        Args:
            device_id: Target device ID
            user_id: Invoking user ID
            action: Action to perform
            params: Action parameters

        Returns:
            InvocationResult
        """
        params = params or {}
        start_time = time.time()

        # Step 1: Check device exists
        device = self._devices.get(device_id)
        if not device:
            return InvocationResult(
                success=False,
                device_id=device_id,
                action=action,
                error="Device not found",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        # Step 2: Check device is available
        if not device.is_available:
            return InvocationResult(
                success=False,
                device_id=device_id,
                action=action,
                error=f"Device not available (status: {device.status.value})",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        # Step 3: Policy check (if configured)
        if self._policy:
            allowed, reason = self._policy.check_access(user_id, device_id, action)
            if not allowed:
                return InvocationResult(
                    success=False,
                    device_id=device_id,
                    action=action,
                    error=f"Access denied: {reason}",
                    execution_time_ms=(time.time() - start_time) * 1000,
                )

        # Step 4: Lease acquisition (if configured)
        if self._lease_manager:
            lease = self._lease_manager.acquire(user_id, device_id, ttl_seconds=300)
            if not lease:
                return InvocationResult(
                    success=False,
                    device_id=device_id,
                    action=action,
                    error="Could not acquire device lease",
                    execution_time_ms=(time.time() - start_time) * 1000,
                )

        try:
            # Step 5: Execute
            device.status = DeviceStatus.BUSY
            handler = self._invocation_handlers.get(device.device_type)

            if handler:
                result_data = await handler(device, action, params)
                success = True
                error = None
            else:
                # Default: simulate success (actual implementation would HTTP call)
                result_data = {"status": "simulated", "action": action}
                success = True
                error = None

            execution_time_ms = (time.time() - start_time) * 1000

            result = InvocationResult(
                success=success,
                device_id=device_id,
                action=action,
                result=result_data,
                error=error,
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            result = InvocationResult(
                success=False,
                device_id=device_id,
                action=action,
                error=str(e),
                execution_time_ms=execution_time_ms,
            )
        finally:
            # Release lease
            if self._lease_manager:
                self._lease_manager.release(device_id)

            # Update device status
            device.status = DeviceStatus.ONLINE if result.success else DeviceStatus.ERROR
            self._save_device(device)

        # Step 6: Log
        self._log_invocation(user_id, device_id, action, params, result)

        return result

    def _log_invocation(
        self,
        user_id: str,
        device_id: str,
        action: str,
        params: Dict[str, Any],
        result: InvocationResult,
    ) -> None:
        """Log invocation to database."""
        import json
        log_id = f"log_{uuid4().hex[:12]}"

        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO limb_invocation_logs
                (log_id, device_id, user_id, action, params, success, result, error, execution_time_ms, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log_id,
                    device_id,
                    user_id,
                    action,
                    json.dumps(params),
                    1 if result.success else 0,
                    json.dumps(result.result) if result.result else None,
                    result.error,
                    result.execution_time_ms,
                    result.timestamp,
                ),
            )
            conn.commit()

    def get_invocation_logs(
        self,
        device_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[InvocationLog]:
        """Get invocation logs."""
        import json
        logs = []

        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row

            if device_id:
                rows = conn.execute(
                    "SELECT * FROM limb_invocation_logs WHERE device_id = ? ORDER BY timestamp DESC LIMIT ?",
                    (device_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM limb_invocation_logs ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                ).fetchall()

            for row in rows:
                result = InvocationResult(
                    success=bool(row["success"]),
                    device_id=row["device_id"],
                    action=row["action"],
                    result=json.loads(row["result"]) if row["result"] else None,
                    error=row["error"],
                    execution_time_ms=row["execution_time_ms"],
                    timestamp=row["timestamp"],
                )
                logs.append(InvocationLog(
                    log_id=row["log_id"],
                    device_id=row["device_id"],
                    user_id=row["user_id"],
                    action=row["action"],
                    params=json.loads(row["params"]) if row["params"] else {},
                    result=result,
                    timestamp=row["timestamp"],
                ))

        return logs
