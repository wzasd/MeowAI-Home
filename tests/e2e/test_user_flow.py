"""End-to-end tests for critical user flows"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.e2e
class TestUserRegistrationFlow:
    """Test user registration and login flow."""

    def test_complete_registration_flow(self, client: TestClient):
        """E2E: User registers, logs in, and accesses protected resource."""
        # 1. Register
        response = client.post("/api/auth/register", json={
            "username": "testuser",
            "password": "SecurePass123!",
        })
        assert response.status_code == 200
        user_id = response.json()["user_id"]

        # 2. Login
        response = client.post("/api/auth/login", json={
            "username": "testuser",
            "password": "SecurePass123!",
        })
        assert response.status_code == 200
        token = response.json()["token"]

        # 3. Access protected resource
        response = client.get(
            "/api/threads",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200


@pytest.mark.e2e
class TestThreadWorkflowFlow:
    """Test complete thread workflow."""

    def test_create_thread_and_send_messages(self, client: TestClient):
        """E2E: Create thread, send messages, archive."""
        # 1. Create thread
        response = client.post("/api/threads", json={"name": "E2E Test Thread"})
        assert response.status_code == 200
        thread_id = response.json()["id"]

        # 2. Send message
        response = client.post(f"/api/threads/{thread_id}/messages", json={
            "content": "Hello @orange!",
            "role": "user",
        })
        assert response.status_code == 200

        # 3. Get messages
        response = client.get(f"/api/threads/{thread_id}/messages")
        assert response.status_code == 200
        messages = response.json()["messages"]
        assert len(messages) >= 1

        # 4. Archive thread
        response = client.post(f"/api/threads/{thread_id}/archive")
        assert response.status_code == 200

        # 5. Verify archived
        response = client.get(f"/api/threads/{thread_id}")
        assert response.json()["is_archived"] is True


@pytest.mark.e2e
class TestSkillExecutionFlow:
    """Test skill execution workflow."""

    def test_install_and_execute_skill(self, client: TestClient):
        """E2E: Install skill and execute it."""
        # 1. List available skills
        response = client.get("/api/skills")
        assert response.status_code == 200
        skills = response.json()

        # 2. Verify tdd skill exists
        tdd_skill = next((s for s in skills if s["name"] == "tdd"), None)
        assert tdd_skill is not None

        # 3. Create thread for skill execution
        response = client.post("/api/threads", json={"name": "TDD Skill Test"})
        thread_id = response.json()["id"]

        # 4. Send skill trigger message
        response = client.post(f"/api/threads/{thread_id}/messages", json={
            "content": "#tdd implement a calculator",
            "role": "user",
        })
        assert response.status_code == 200


@pytest.mark.e2e
class TestMonitoringFlow:
    """Test monitoring and health check flow."""

    def test_health_check_to_metrics(self, client: TestClient):
        """E2E: Health check → Status → Metrics."""
        # 1. Check liveness
        response = client.get("/api/monitoring/health/live")
        assert response.status_code == 200
        assert response.json()["alive"] is True

        # 2. Check readiness
        response = client.get("/api/monitoring/health/ready")
        assert response.status_code == 200

        # 3. Get full status
        response = client.get("/api/monitoring/status")
        assert response.status_code == 200
        status = response.json()
        assert "health" in status
        assert "version" in status

        # 4. Get Prometheus metrics
        response = client.get("/api/monitoring/metrics")
        assert response.status_code == 200
        assert "http_requests_total" in response.text


@pytest.mark.e2e
class TestAgentManagementFlow:
    """Test agent lifecycle management."""

    def test_register_and_use_agent(self, client: TestClient):
        """E2E: Register agent, verify in list, deregister."""
        # 1. Register new agent
        response = client.post("/api/agents", json={
            "cat_id": "test-agent-001",
            "breed": "ragdoll",
            "display_name": "Test Agent",
            "capabilities": ["coding", "review"],
            "provider": "claude",
        })
        assert response.status_code == 200

        # 2. List agents and verify
        response = client.get("/api/agents")
        assert response.status_code == 200
        agents = response.json()["agents"]
        test_agent = next((a for a in agents if a["cat_id"] == "test-agent-001"), None)
        assert test_agent is not None
        assert test_agent["display_name"] == "Test Agent"

        # 3. Deregister agent
        response = client.delete("/api/agents/test-agent-001")
        assert response.status_code == 200

        # 4. Verify removed
        response = client.get("/api/agents")
        agents = response.json()["agents"]
        test_agent = next((a for a in agents if a["cat_id"] == "test-agent-001"), None)
        assert test_agent is None


@pytest.mark.e2e
class TestPackManagementFlow:
    """Test pack activation workflow."""

    def test_activate_and_use_pack(self, client: TestClient):
        """E2E: Activate pack, create thread, use pack skills."""
        # 1. List available packs
        response = client.get("/api/packs")
        assert response.status_code == 200
        packs = response.json()["packs"]

        if not packs:
            pytest.skip("No packs available")

        pack_name = packs[0]["name"]

        # 2. Create thread
        response = client.post("/api/threads", json={"name": "Pack Test Thread"})
        thread_id = response.json()["id"]

        # 3. Activate pack
        response = client.post(f"/api/packs/{pack_name}/activate", json={
            "thread_id": thread_id,
        })
        assert response.status_code == 200

        # 4. Verify pack is active
        response = client.get(f"/api/threads/{thread_id}/packs")
        active_packs = response.json()["active_packs"]
        assert any(p["name"] == pack_name for p in active_packs)
