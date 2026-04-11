"""Tests for LimbRegistry."""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, timezone

from src.limb.registry import (
    LimbRegistry,
    LimbDevice,
    DeviceStatus,
    DeviceCapability,
    InvocationResult,
)


@pytest.fixture
def temp_db_path():
    """Create temporary database file."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def registry(temp_db_path):
    """Create fresh registry for each test."""
    return LimbRegistry(db_path=temp_db_path)


@pytest.fixture
def sample_device(registry):
    """Create a sample device."""
    return registry.register(
        name="Test Light",
        device_type="smart_light",
        endpoint="http://192.168.1.100:8080",
        capabilities=[DeviceCapability.ACTUATOR],
        auth_token="test-token-123",
        owner_user_id="user_123",
        metadata={"room": "living_room"},
    )


class TestDeviceRegistration:
    """Test device registration functionality."""

    def test_register_device(self, registry):
        """Test basic device registration."""
        device = registry.register(
            name="Smart Bulb",
            device_type="smart_light",
            endpoint="http://192.168.1.100:8080",
            capabilities=[DeviceCapability.ACTUATOR],
        )

        assert device.device_id.startswith("limb_")
        assert device.name == "Smart Bulb"
        assert device.device_type == "smart_light"
        assert device.status == DeviceStatus.OFFLINE
        assert device.is_paired is False
        assert DeviceCapability.ACTUATOR in device.capabilities

    def test_register_with_all_fields(self, registry):
        """Test registration with all optional fields."""
        device = registry.register(
            name="Test Light",
            device_type="smart_light",
            endpoint="http://192.168.1.100:8080",
            capabilities=[DeviceCapability.ACTUATOR, DeviceCapability.SENSOR],
            auth_token="secret-token",
            owner_user_id="user_123",
            metadata={"room": "living_room"},
        )

        assert device.auth_token == "secret-token"
        assert device.owner_user_id == "user_123"
        assert device.metadata == {"room": "living_room"}

    def test_register_creates_unique_ids(self, registry):
        """Test that each device gets a unique ID."""
        device1 = registry.register(
            name="Device 1",
            device_type="light",
            endpoint="http://localhost:8001",
            capabilities=[DeviceCapability.ACTUATOR],
        )
        device2 = registry.register(
            name="Device 2",
            device_type="light",
            endpoint="http://localhost:8002",
            capabilities=[DeviceCapability.ACTUATOR],
        )

        assert device1.device_id != device2.device_id

    def test_persistence_on_registration(self, registry, temp_db_path):
        """Test device is saved to database on registration."""
        device = registry.register(
            name="Persistent Device",
            device_type="sensor",
            endpoint="http://localhost:8000",
            capabilities=[DeviceCapability.SENSOR],
        )

        # Check database directly
        with sqlite3.connect(temp_db_path) as conn:
            row = conn.execute(
                "SELECT * FROM limb_devices WHERE device_id = ?",
                (device.device_id,),
            ).fetchone()

        assert row is not None
        assert row[1] == "Persistent Device"


class TestDeviceRetrieval:
    """Test device retrieval operations."""

    def test_get_device(self, registry, sample_device):
        """Test getting device by ID."""
        retrieved = registry.get(sample_device.device_id)

        assert retrieved is not None
        assert retrieved.device_id == sample_device.device_id
        assert retrieved.name == sample_device.name

    def test_get_nonexistent_device(self, registry):
        """Test getting non-existent device returns None."""
        result = registry.get("limb_nonexistent")
        assert result is None

    def test_list_all(self, registry):
        """Test listing all devices."""
        registry.register(
            name="Device 1",
            device_type="light",
            endpoint="http://localhost:8001",
            capabilities=[DeviceCapability.ACTUATOR],
        )
        registry.register(
            name="Device 2",
            device_type="sensor",
            endpoint="http://localhost:8002",
            capabilities=[DeviceCapability.SENSOR],
        )

        devices = registry.list_all()
        assert len(devices) == 2

    def test_list_available(self, registry):
        """Test listing available (online and paired) devices."""
        # Create offline device
        device1 = registry.register(
            name="Offline Device",
            device_type="light",
            endpoint="http://localhost:8001",
            capabilities=[DeviceCapability.ACTUATOR],
        )

        # Create online but not paired device
        device2 = registry.register(
            name="Online Unpaired",
            device_type="light",
            endpoint="http://localhost:8002",
            capabilities=[DeviceCapability.ACTUATOR],
        )
        registry.update_status(device2.device_id, DeviceStatus.ONLINE)

        # Create online and paired device
        device3 = registry.register(
            name="Available Device",
            device_type="light",
            endpoint="http://localhost:8003",
            capabilities=[DeviceCapability.ACTUATOR],
        )
        registry.update_status(device3.device_id, DeviceStatus.ONLINE)
        registry.pair(device3.device_id)

        available = registry.list_available()
        assert len(available) == 1
        assert available[0].device_id == device3.device_id

    def test_list_by_type(self, registry):
        """Test filtering devices by type."""
        registry.register(
            name="Light 1",
            device_type="smart_light",
            endpoint="http://localhost:8001",
            capabilities=[DeviceCapability.ACTUATOR],
        )
        registry.register(
            name="Light 2",
            device_type="smart_light",
            endpoint="http://localhost:8002",
            capabilities=[DeviceCapability.ACTUATOR],
        )
        registry.register(
            name="Camera",
            device_type="security_camera",
            endpoint="http://localhost:8003",
            capabilities=[DeviceCapability.CAMERA],
        )

        lights = registry.list_by_type("smart_light")
        assert len(lights) == 2

    def test_list_by_capability(self, registry):
        """Test filtering devices by capability."""
        registry.register(
            name="Actuator Device",
            device_type="light",
            endpoint="http://localhost:8001",
            capabilities=[DeviceCapability.ACTUATOR],
        )
        registry.register(
            name="Sensor Device",
            device_type="sensor",
            endpoint="http://localhost:8002",
            capabilities=[DeviceCapability.SENSOR],
        )
        registry.register(
            name="Multi Device",
            device_type="smart_hub",
            endpoint="http://localhost:8003",
            capabilities=[DeviceCapability.ACTUATOR, DeviceCapability.SENSOR],
        )

        actuators = registry.list_by_capability(DeviceCapability.ACTUATOR)
        assert len(actuators) == 2


class TestDeviceStatus:
    """Test device status management."""

    def test_update_status(self, registry, sample_device):
        """Test updating device status."""
        success = registry.update_status(sample_device.device_id, DeviceStatus.ONLINE)

        assert success is True

        device = registry.get(sample_device.device_id)
        assert device.status == DeviceStatus.ONLINE
        assert device.last_seen_at is not None

    def test_update_nonexistent_device(self, registry):
        """Test updating status of non-existent device."""
        success = registry.update_status("limb_fake", DeviceStatus.ONLINE)
        assert success is False

    def test_is_available_property(self, registry, sample_device):
        """Test is_available property."""
        # Initially offline and unpaired
        assert sample_device.is_available is False

        # Online but not paired
        registry.update_status(sample_device.device_id, DeviceStatus.ONLINE)
        device = registry.get(sample_device.device_id)
        assert device.is_available is False

        # Online and paired
        registry.pair(sample_device.device_id)
        device = registry.get(sample_device.device_id)
        assert device.is_available is True


class TestDevicePairing:
    """Test device pairing operations."""

    def test_pair_device(self, registry, sample_device):
        """Test pairing a device."""
        success = registry.pair(sample_device.device_id)

        assert success is True

        device = registry.get(sample_device.device_id)
        assert device.is_paired is True

    def test_unpair_device(self, registry, sample_device):
        """Test unpairing a device."""
        registry.pair(sample_device.device_id)

        success = registry.unpair(sample_device.device_id)
        assert success is True

        device = registry.get(sample_device.device_id)
        assert device.is_paired is False

    def test_pair_nonexistent_device(self, registry):
        """Test pairing non-existent device."""
        success = registry.pair("limb_fake")
        assert success is False

    def test_unpair_nonexistent_device(self, registry):
        """Test unpairing non-existent device."""
        success = registry.unpair("limb_fake")
        assert success is False


class TestDeviceUnregistration:
    """Test device unregistration."""

    def test_unregister_device(self, registry, sample_device):
        """Test unregistering a device."""
        success = registry.unregister(sample_device.device_id)

        assert success is True
        assert registry.get(sample_device.device_id) is None

    def test_unregister_nonexistent_device(self, registry):
        """Test unregistering non-existent device."""
        success = registry.unregister("limb_fake")
        assert success is False

    def test_unregister_deletes_from_db(self, registry, sample_device, temp_db_path):
        """Test unregistration removes from database."""
        device_id = sample_device.device_id
        registry.unregister(device_id)

        with sqlite3.connect(temp_db_path) as conn:
            row = conn.execute(
                "SELECT * FROM limb_devices WHERE device_id = ?",
                (device_id,),
            ).fetchone()

        assert row is None


class TestInvocation:
    """Test device invocation."""

    async def test_invoke_device_not_found(self, registry):
        """Test invoking non-existent device."""
        result = await registry.invoke(
            device_id="limb_nonexistent",
            user_id="user_123",
            action="turn_on",
        )

        assert result.success is False
        assert result.error == "Device not found"

    async def test_invoke_device_not_available(self, registry, sample_device):
        """Test invoking offline device."""
        result = await registry.invoke(
            device_id=sample_device.device_id,
            user_id="user_123",
            action="turn_on",
        )

        assert result.success is False
        assert "not available" in result.error.lower()

    async def test_invoke_with_handler(self, registry):
        """Test invoking with registered handler."""
        device = registry.register(
            name="Test Device",
            device_type="test_type",
            endpoint="http://localhost:8000",
            capabilities=[DeviceCapability.ACTUATOR],
        )
        registry.update_status(device.device_id, DeviceStatus.ONLINE)
        registry.pair(device.device_id)

        # Register test handler
        async def test_handler(device, action, params):
            return {"action": action, "params": params}

        registry.register_invocation_handler("test_type", test_handler)

        result = await registry.invoke(
            device_id=device.device_id,
            user_id="user_123",
            action="test_action",
            params={"key": "value"},
        )

        assert result.success is True
        assert result.result["action"] == "test_action"

    async def test_invoke_without_handler_simulates(self, registry):
        """Test invoking without handler returns simulated response."""
        device = registry.register(
            name="Test Device",
            device_type="unhandled_type",
            endpoint="http://localhost:8000",
            capabilities=[DeviceCapability.ACTUATOR],
        )
        registry.update_status(device.device_id, DeviceStatus.ONLINE)
        registry.pair(device.device_id)

        result = await registry.invoke(
            device_id=device.device_id,
            user_id="user_123",
            action="test_action",
        )

        assert result.success is True
        assert result.result["status"] == "simulated"


class TestInvocationLogs:
    """Test invocation logging."""

    async def test_invocation_logged(self, registry, temp_db_path):
        """Test successful invocation is logged."""
        device = registry.register(
            name="Test Device",
            device_type="test_type",
            endpoint="http://localhost:8000",
            capabilities=[DeviceCapability.ACTUATOR],
        )
        registry.update_status(device.device_id, DeviceStatus.ONLINE)
        registry.pair(device.device_id)

        await registry.invoke(
            device_id=device.device_id,
            user_id="user_123",
            action="test_action",
            params={"key": "value"},
        )

        # Check logs
        logs = registry.get_invocation_logs(device_id=device.device_id)
        assert len(logs) == 1
        assert logs[0].action == "test_action"
        assert logs[0].user_id == "user_123"

    def test_get_logs_with_limit(self, registry, temp_db_path):
        """Test getting logs with limit."""
        device = registry.register(
            name="Test Device",
            device_type="test_type",
            endpoint="http://localhost:8000",
            capabilities=[DeviceCapability.ACTUATOR],
        )

        # Insert multiple logs manually for testing
        import json
        with sqlite3.connect(temp_db_path) as conn:
            for i in range(10):
                conn.execute(
                    """
                    INSERT INTO limb_invocation_logs
                    (log_id, device_id, user_id, action, params, success, result, error, execution_time_ms, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"log_{i}",
                        device.device_id,
                        "user_123",
                        f"action_{i}",
                        json.dumps({}),
                        1,
                        json.dumps({}),
                        None,
                        100.0,
                        1234567890.0 + i,
                    ),
                )
            conn.commit()

        logs = registry.get_invocation_logs(device_id=device.device_id, limit=5)
        assert len(logs) == 5
