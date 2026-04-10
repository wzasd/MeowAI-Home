"""Web API completion tests"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.web.routes.packs import router as packs_router
from src.web.routes.agents import router as agents_router
from src.web.routes.governance import router as governance_router
from src.web.routes.workflow import router as workflow_router


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(packs_router)
    app.include_router(agents_router)
    app.include_router(governance_router)
    app.include_router(workflow_router)
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestPacksAPI:
    def test_list_packs_not_initialized(self, client):
        response = client.get("/api/packs")
        assert response.status_code == 500

    def test_get_pack_not_initialized(self, client):
        response = client.get("/api/packs/test")
        assert response.status_code == 500


class TestAgentsAPI:
    def test_list_agents_not_initialized(self, client):
        response = client.get("/api/agents")
        assert response.status_code == 500

    def test_get_agent_not_initialized(self, client):
        response = client.get("/api/agents/test-1")
        assert response.status_code == 500

    def test_register_agent_not_initialized(self, client):
        response = client.post("/api/agents", json={"cat_id": "test"})
        assert response.status_code == 500


class TestGovernanceAPI:
    def test_get_iron_laws(self, client):
        response = client.get("/api/governance/iron-laws")
        assert response.status_code == 200
        data = response.json()
        assert "laws" in data
        assert len(data["laws"]) > 0
        assert "title" in data["laws"][0]


class TestWorkflowAPI:
    def test_list_templates(self, client):
        response = client.get("/api/workflow/templates")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert "tdd" in [t["id"] for t in data]

    def test_list_active_workflows(self, client):
        response = client.get("/api/workflow/active")
        assert response.status_code == 200
