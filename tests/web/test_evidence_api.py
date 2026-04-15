"""Tests for evidence API routes."""

import pytest
import tempfile
import os
from fastapi.testclient import TestClient

from src.web.app import create_app
from src.evidence.store import EvidenceStore, EvidenceDoc


@pytest.fixture
def client():
    """Create authenticated test client."""
    app = create_app()
    with TestClient(app) as c:
        c.post("/api/auth/register", json={"username": "testuser", "password": "testpass", "role": "admin"})
        resp = c.post("/api/auth/login", json={"username": "testuser", "password": "testpass"})
        token = resp.json()["access_token"]
        c.headers["Authorization"] = f"Bearer {token}"
        yield c


@pytest.fixture
def store_with_docs():
    """Create evidence store with test documents."""
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test_evidence.db")
    store = EvidenceStore(db_path=db_path)

    docs = [
        EvidenceDoc(
            title="使用 React Server Components 优化首屏加载",
            anchor="docs/frontend/react-server-components.md",
            summary="通过迁移到 RSC，首屏加载时间减少 60%",
            content="详细分析了 React Server Components 的使用方式和性能优化效果",
            kind="decision",
            source="project-a",
            confidence="high",
        ),
        EvidenceDoc(
            title="API 网关选型: Kong vs Envoy",
            anchor="docs/architecture/api-gateway.md",
            summary="经过性能测试和功能对比，选择 Envoy 作为 API 网关",
            content="对比了 Kong 和 Envoy 在高并发场景下的性能表现",
            kind="discussion",
            source="project-a",
            confidence="mid",
        ),
        EvidenceDoc(
            title="数据库迁移计划 Phase 2",
            anchor="docs/migration/phase2.md",
            summary="将用户表从 MySQL 迁移到 PostgreSQL",
            content="Phase 2 迁移计划包含用户表、订单表和支付记录表的迁移",
            kind="plan",
            source="project-b",
            confidence="high",
        ),
    ]

    for doc in docs:
        store.store(doc)

    return store


class TestEvidenceSearch:
    """Tests for GET /api/evidence/search endpoint."""

    def test_search_empty(self, client):
        """Test search with no documents."""
        response = client.get("/api/evidence/search?q=test")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "degraded" in data
        assert isinstance(data["results"], list)

    def test_search_missing_query(self, client):
        """Test search without query parameter."""
        response = client.get("/api/evidence/search")
        assert response.status_code == 422

    def test_search_with_results(self, client):
        """Test search that returns results."""
        # First create a document
        client.post(
            "/api/evidence/docs",
            json={
                "title": "React 性能优化指南",
                "anchor": "docs/react-perf.md",
                "summary": "React 性能优化的最佳实践",
                "content": "本文介绍了 React 性能优化的各种方法",
                "kind": "decision",
                "confidence": "high",
            },
        )

        # Search for it
        response = client.get("/api/evidence/search?q=React+性能")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) > 0
        assert data["degraded"] is False


class TestEvidenceStatus:
    """Tests for GET /api/evidence/status endpoint."""

    def test_get_status(self, client):
        """Test getting evidence store status."""
        response = client.get("/api/evidence/status")
        assert response.status_code == 200
        data = response.json()
        assert data["backend"] == "sqlite"
        assert data["healthy"] is True
        assert "total" in data
        assert "by_kind" in data


class TestCreateDoc:
    """Tests for POST /api/evidence/docs endpoint."""

    def test_create_doc_minimal(self, client):
        """Test creating document with minimal data."""
        response = client.post(
            "/api/evidence/docs",
            json={"title": "Test Document"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] is not None
        assert data["title"] == "Test Document"

    def test_create_doc_full(self, client):
        """Test creating document with all fields."""
        response = client.post(
            "/api/evidence/docs",
            json={
                "title": "架构决策记录",
                "anchor": "docs/adr-001.md",
                "summary": "选择微服务架构而非单体架构",
                "content": "经过详细分析，团队决定采用微服务架构",
                "kind": "decision",
                "source": "project-alpha",
                "confidence": "high",
                "status": "published",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] is not None


class TestListDocs:
    """Tests for GET /api/evidence/docs endpoint."""

    def test_list_docs(self, client):
        """Test listing documents."""
        response = client.get("/api/evidence/docs")
        assert response.status_code == 200
        data = response.json()
        assert "docs" in data
        assert "total" in data

    def test_list_docs_by_kind(self, client):
        """Test listing documents filtered by kind."""
        response = client.get("/api/evidence/docs?kind=decision")
        assert response.status_code == 200


class TestGetDoc:
    """Tests for GET /api/evidence/docs/{id} endpoint."""

    def test_get_doc_not_found(self, client):
        """Test getting non-existent document."""
        response = client.get("/api/evidence/docs/99999")
        assert response.status_code == 404

    def test_get_doc_success(self, client):
        """Test getting existing document."""
        # Create a document
        create_response = client.post(
            "/api/evidence/docs",
            json={"title": "Get Test Doc"},
        )
        doc_id = create_response.json()["id"]

        # Get it
        response = client.get(f"/api/evidence/docs/{doc_id}")
        assert response.status_code == 200
        assert response.json()["title"] == "Get Test Doc"


class TestDeleteDoc:
    """Tests for DELETE /api/evidence/docs/{id} endpoint."""

    def test_delete_doc_not_found(self, client):
        """Test deleting non-existent document."""
        response = client.delete("/api/evidence/docs/99999")
        assert response.status_code == 404

    def test_delete_doc_success(self, client):
        """Test deleting existing document."""
        # Create a document
        create_response = client.post(
            "/api/evidence/docs",
            json={"title": "Delete Test Doc"},
        )
        doc_id = create_response.json()["id"]

        # Delete it
        response = client.delete(f"/api/evidence/docs/{doc_id}")
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify it's gone
        get_response = client.get(f"/api/evidence/docs/{doc_id}")
        assert get_response.status_code == 404
