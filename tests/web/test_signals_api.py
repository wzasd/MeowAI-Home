"""Tests for signals API routes."""

import pytest
from fastapi.testclient import TestClient

from src.web.app import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


class TestListArticles:
    """Tests for GET /api/signals/articles endpoint."""

    def test_list_articles_empty(self, client):
        """Test listing articles when none exist."""
        response = client.get("/api/signals/articles")
        assert response.status_code == 200
        data = response.json()
        assert "articles" in data
        assert "total" in data

    def test_list_articles_with_filter(self, client):
        """Test listing articles with status filter."""
        response = client.get("/api/signals/articles?status=unread")
        assert response.status_code == 200
        data = response.json()
        assert "articles" in data

    def test_list_articles_with_tier_filter(self, client):
        """Test listing articles with tier filter."""
        response = client.get("/api/signals/articles?tier=S")
        assert response.status_code == 200
        data = response.json()
        assert "articles" in data


class TestSearchArticles:
    """Tests for GET /api/signals/articles/search endpoint."""

    def test_search_articles(self, client):
        """Test searching articles."""
        response = client.get("/api/signals/articles/search?q=test")
        assert response.status_code == 200
        data = response.json()
        assert "articles" in data
        assert "query" in data
        assert data["query"] == "test"

    def test_search_articles_empty_query(self, client):
        """Test searching with empty query returns error."""
        response = client.get("/api/signals/articles/search?q=")
        assert response.status_code == 422


class TestGetArticle:
    """Tests for GET /api/signals/articles/{id} endpoint."""

    def test_get_article_not_found(self, client):
        """Test getting non-existent article."""
        response = client.get("/api/signals/articles/99999")
        assert response.status_code == 404

    def test_get_article_invalid_id(self, client):
        """Test getting article with invalid ID."""
        response = client.get("/api/signals/articles/invalid")
        assert response.status_code == 400


class TestUpdateArticleStatus:
    """Tests for PATCH /api/signals/articles/{id}/status endpoint."""

    def test_update_status_not_found(self, client):
        """Test updating status of non-existent article."""
        response = client.patch(
            "/api/signals/articles/99999/status",
            json={"status": "read"}
        )
        assert response.status_code == 404

    def test_update_status_invalid_id(self, client):
        """Test updating status with invalid ID."""
        response = client.patch(
            "/api/signals/articles/invalid/status",
            json={"status": "read"}
        )
        assert response.status_code == 400


class TestStarArticle:
    """Tests for POST /api/signals/articles/{id}/star endpoint."""

    def test_star_article_not_found(self, client):
        """Test starring non-existent article."""
        response = client.post("/api/signals/articles/99999/star")
        assert response.status_code == 404


class TestListSources:
    """Tests for GET /api/signals/sources endpoint."""

    def test_list_sources(self, client):
        """Test listing all sources."""
        response = client.get("/api/signals/sources")
        assert response.status_code == 200
        data = response.json()
        assert "sources" in data
        assert isinstance(data["sources"], list)


class TestRefreshSource:
    """Tests for POST /api/signals/sources/{id}/refresh endpoint."""

    def test_refresh_source_not_found(self, client):
        """Test refreshing non-existent source."""
        response = client.post("/api/signals/sources/nonexistent/refresh")
        assert response.status_code == 404

    def test_refresh_source_success(self, client):
        """Test refreshing existing source."""
        # First get a source ID
        response = client.get("/api/signals/sources")
        data = response.json()
        if data["sources"]:
            source_id = data["sources"][0]["id"]
            response = client.post(f"/api/signals/sources/{source_id}/refresh")
            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True


class TestGetStats:
    """Tests for GET /api/signals/stats endpoint."""

    def test_get_stats(self, client):
        """Test getting signal statistics."""
        response = client.get("/api/signals/stats")
        assert response.status_code == 200
        data = response.json()
        assert "articles" in data
        assert "sources" in data
