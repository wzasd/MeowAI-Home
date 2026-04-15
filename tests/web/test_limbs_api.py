"""Tests for limb REST API endpoints."""
import pytest
import tempfile
from pathlib import Path
from httpx import AsyncClient, ASGITransport

from src.auth.store import AuthStore
from src.thread.thread_manager import ThreadManager
from src.web.app import create_app
from src.limb import LimbRegistry, LeaseManager
from tests.web.conftest import authenticate_client


@pytest.fixture
async def app_client():
    """Create a test client with limb registry initialized."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        ThreadManager.reset()

        app = create_app()
        tm = ThreadManager(db_path=db_path, skip_init=True)
        await tm.async_init()
        app.state.thread_manager = tm

        from src.models.cat_registry import CatRegistry
        from src.models.agent_registry import AgentRegistry
        cat_reg = CatRegistry()
        agent_reg = AgentRegistry()
        try:
            from src.models.registry_init import initialize_registries
            cat_reg, agent_reg = initialize_registries("cat-config.json")
        except Exception:
            pass

        app.state.cat_registry = cat_reg
        app.state.agent_registry = agent_reg

        auth_store = AuthStore(db_path=db_path)
        await auth_store.initialize()
        app.state.auth_store = auth_store

        lease_manager = LeaseManager()
        limb_registry = LimbRegistry(
            db_path=str(Path(tmpdir) / "limb_registry.db"),
            lease_manager=lease_manager,
        )
        app.state.limb_registry = limb_registry
        app.state.limb_lease_manager = lease_manager

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await authenticate_client(client)
            yield client, limb_registry, lease_manager

        ThreadManager.reset()
        if hasattr(tm, '_store') and tm._store:
            await tm._store.close()


@pytest.mark.asyncio
async def test_list_devices_empty(app_client):
    """Test listing devices when none exist."""
    client, _, _ = app_client
    response = await client.get("/api/limbs")
    assert response.status_code == 200
    data = response.json()
    assert "devices" in data
    assert data["devices"] == []


@pytest.mark.asyncio
async def test_register_device(app_client):
    """Test registering a new device."""
    client, _, _ = app_client
    response = await client.post("/api/limbs", json={
        "name": "Test Light",
        "device_type": "smart_light",
        "endpoint": "http://localhost:8001",
        "capabilities": ["actuator", "sensor"],
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["device"]["name"] == "Test Light"
    assert data["device"]["device_type"] == "smart_light"
    assert data["device"]["endpoint"] == "http://localhost:8001"
    assert data["device"]["capabilities"] == ["actuator", "sensor"]
    assert data["device"]["status"] == "offline"
    assert data["device"]["is_paired"] is False


@pytest.mark.asyncio
async def test_get_device(app_client):
    """Test getting a single device."""
    client, _, _ = app_client
    create_res = await client.post("/api/limbs", json={
        "name": "Test Camera",
        "device_type": "security_cam",
        "endpoint": "http://localhost:8002",
        "capabilities": ["camera"],
    })
    device_id = create_res.json()["device"]["device_id"]

    response = await client.get(f"/api/limbs/{device_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["device"]["device_id"] == device_id
    assert data["device"]["name"] == "Test Camera"


@pytest.mark.asyncio
async def test_get_device_not_found(app_client):
    """Test getting non-existent device."""
    client, _, _ = app_client
    response = await client.get("/api/limbs/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_device(app_client):
    """Test updating device info."""
    client, _, _ = app_client
    create_res = await client.post("/api/limbs", json={
        "name": "Old Name",
        "device_type": "sensor",
        "endpoint": "http://localhost:8003",
        "capabilities": ["sensor"],
    })
    device_id = create_res.json()["device"]["device_id"]

    response = await client.patch(f"/api/limbs/{device_id}", json={
        "name": "New Name",
        "endpoint": "http://localhost:8004",
        "status": "online",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["device"]["name"] == "New Name"
    assert data["device"]["endpoint"] == "http://localhost:8004"
    assert data["device"]["status"] == "online"


@pytest.mark.asyncio
async def test_update_device_not_found(app_client):
    """Test updating non-existent device."""
    client, _, _ = app_client
    response = await client.patch("/api/limbs/nonexistent", json={
        "name": "New Name",
    })
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_device(app_client):
    """Test deleting a device."""
    client, _, _ = app_client
    create_res = await client.post("/api/limbs", json={
        "name": "To Delete",
        "device_type": "sensor",
        "endpoint": "http://localhost:8005",
        "capabilities": ["sensor"],
    })
    device_id = create_res.json()["device"]["device_id"]

    response = await client.delete(f"/api/limbs/{device_id}")
    assert response.status_code == 200
    assert response.json()["success"] is True

    get_res = await client.get(f"/api/limbs/{device_id}")
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_delete_device_not_found(app_client):
    """Test deleting non-existent device."""
    client, _, _ = app_client
    response = await client.delete("/api/limbs/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_pair_unpair_device(app_client):
    """Test pairing and unpairing a device."""
    client, _, _ = app_client
    create_res = await client.post("/api/limbs", json={
        "name": "Pairable Device",
        "device_type": " actuator",
        "endpoint": "http://localhost:8006",
        "capabilities": ["actuator"],
    })
    device_id = create_res.json()["device"]["device_id"]

    # Pair
    pair_res = await client.post(f"/api/limbs/{device_id}/pair")
    assert pair_res.status_code == 200
    assert pair_res.json()["device"]["is_paired"] is True

    # Unpair
    unpair_res = await client.post(f"/api/limbs/{device_id}/unpair")
    assert unpair_res.status_code == 200
    assert unpair_res.json()["device"]["is_paired"] is False


@pytest.mark.asyncio
async def test_pair_device_not_found(app_client):
    """Test pairing non-existent device."""
    client, _, _ = app_client
    response = await client.post("/api/limbs/nonexistent/pair")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_available_devices(app_client):
    """Test listing available devices."""
    client, _, _ = app_client
    # Register offline device
    offline_res = await client.post("/api/limbs", json={
        "name": "Offline Device",
        "device_type": "sensor",
        "endpoint": "http://localhost:8007",
        "capabilities": ["sensor"],
    })
    offline_id = offline_res.json()["device"]["device_id"]
    await client.post(f"/api/limbs/{offline_id}/pair")

    # Register online + paired device
    online_res = await client.post("/api/limbs", json={
        "name": "Online Device",
        "device_type": "sensor",
        "endpoint": "http://localhost:8008",
        "capabilities": ["sensor"],
    })
    online_id = online_res.json()["device"]["device_id"]
    await client.post(f"/api/limbs/{online_id}/pair")
    await client.patch(f"/api/limbs/{online_id}", json={"status": "online"})

    response = await client.get("/api/limbs/available")
    assert response.status_code == 200
    data = response.json()
    device_ids = [d["device_id"] for d in data["devices"]]
    assert offline_id not in device_ids
    assert online_id in device_ids


@pytest.mark.asyncio
async def test_invoke_device(app_client):
    """Test invoking an action on a device."""
    client, _, _ = app_client
    create_res = await client.post("/api/limbs", json={
        "name": "Invokable Device",
        "device_type": "smart_light",
        "endpoint": "http://localhost:8009",
        "capabilities": ["actuator"],
    })
    device_id = create_res.json()["device"]["device_id"]
    await client.post(f"/api/limbs/{device_id}/pair")
    await client.patch(f"/api/limbs/{device_id}", json={"status": "online"})

    response = await client.post(f"/api/limbs/{device_id}/invoke", json={
        "action": "turn_on",
        "params": {"brightness": 50},
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["device_id"] == device_id
    assert data["action"] == "turn_on"
    assert "result" in data


@pytest.mark.asyncio
async def test_invoke_device_not_found(app_client):
    """Test invoking non-existent device."""
    client, _, _ = app_client
    response = await client.post("/api/limbs/nonexistent/invoke", json={
        "action": "turn_on",
    })
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_device_logs(app_client):
    """Test getting invocation logs."""
    client, _, _ = app_client
    create_res = await client.post("/api/limbs", json={
        "name": "Log Device",
        "device_type": "smart_light",
        "endpoint": "http://localhost:8010",
        "capabilities": ["actuator"],
    })
    device_id = create_res.json()["device"]["device_id"]
    await client.post(f"/api/limbs/{device_id}/pair")
    await client.patch(f"/api/limbs/{device_id}", json={"status": "online"})

    await client.post(f"/api/limbs/{device_id}/invoke", json={
        "action": "turn_on",
    })

    response = await client.get(f"/api/limbs/{device_id}/logs")
    assert response.status_code == 200
    data = response.json()
    assert "logs" in data
    assert len(data["logs"]) >= 1
    assert data["logs"][0]["action"] == "turn_on"


@pytest.mark.asyncio
async def test_lease_lifecycle(app_client):
    """Test acquiring, extending, and releasing a lease."""
    client, _, _ = app_client
    create_res = await client.post("/api/limbs", json={
        "name": "Leased Device",
        "device_type": "smart_light",
        "endpoint": "http://localhost:8011",
        "capabilities": ["actuator"],
    })
    device_id = create_res.json()["device"]["device_id"]

    # Acquire
    acquire_res = await client.post(f"/api/limbs/leases/{device_id}/acquire", json={
        "ttl_seconds": 300,
    })
    assert acquire_res.status_code == 200
    assert acquire_res.json()["success"] is True

    # List leases
    list_res = await client.get("/api/limbs/leases")
    assert list_res.status_code == 200
    leases = list_res.json()["leases"]
    assert any(l["device_id"] == device_id for l in leases)

    # Extend
    extend_res = await client.post(f"/api/limbs/leases/{device_id}/extend", json={
        "additional_seconds": 600,
    })
    assert extend_res.status_code == 200
    assert extend_res.json()["success"] is True

    # Release
    release_res = await client.post(f"/api/limbs/leases/{device_id}/release")
    assert release_res.status_code == 200
    assert release_res.json()["success"] is True

    # Verify released
    list_res2 = await client.get("/api/limbs/leases")
    leases2 = list_res2.json()["leases"]
    assert not any(l["device_id"] == device_id for l in leases2)


@pytest.mark.asyncio
async def test_release_lease_not_found(app_client):
    """Test releasing non-existent lease."""
    client, _, _ = app_client
    response = await client.post("/api/limbs/leases/nonexistent/release")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_extend_lease_not_found(app_client):
    """Test extending non-existent lease."""
    client, _, _ = app_client
    response = await client.post("/api/limbs/leases/nonexistent/extend", json={
        "additional_seconds": 300,
    })
    assert response.status_code == 404
