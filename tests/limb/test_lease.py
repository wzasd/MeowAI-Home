"""Tests for LeaseManager."""

import pytest
import time

from src.limb.lease import LeaseManager, Lease


@pytest.fixture
def manager():
    """Create fresh lease manager for each test."""
    return LeaseManager(default_ttl=60.0, cleanup_interval=0.1)


class TestLeaseAcquisition:
    """Test lease acquisition."""

    def test_acquire_lease(self, manager):
        """Test basic lease acquisition."""
        lease = manager.acquire("user_123", "device_123")

        assert lease is not None
        assert lease.user_id == "user_123"
        assert lease.device_id == "device_123"
        assert lease.remaining_seconds > 0

    def test_acquire_fails_when_leased(self, manager):
        """Test acquiring already-leased device fails."""
        manager.acquire("user_123", "device_123")

        lease2 = manager.acquire("user_456", "device_123")

        assert lease2 is None

    def test_acquire_succeeds_after_expiry(self, manager):
        """Test lease can be acquired after expiry."""
        manager.acquire("user_123", "device_123", ttl_seconds=0.1)
        time.sleep(0.15)

        lease2 = manager.acquire("user_456", "device_123")

        assert lease2 is not None
        assert lease2.user_id == "user_456"

    def test_custom_ttl(self, manager):
        """Test acquiring with custom TTL."""
        lease = manager.acquire("user_123", "device_123", ttl_seconds=300.0)

        assert lease.remaining_seconds > 290

    def test_multiple_devices_same_user(self, manager):
        """Test user can hold leases on multiple devices."""
        lease1 = manager.acquire("user_123", "device_1")
        lease2 = manager.acquire("user_123", "device_2")

        assert lease1 is not None
        assert lease2 is not None

    def test_lease_uniqueness(self, manager):
        """Test each lease gets unique ID."""
        lease1 = manager.acquire("user_123", "device_1")
        lease2 = manager.acquire("user_123", "device_2")

        assert lease1.lease_id != lease2.lease_id


class TestLeaseRelease:
    """Test lease release."""

    def test_release_lease(self, manager):
        """Test releasing a lease."""
        manager.acquire("user_123", "device_123")

        success = manager.release("device_123")

        assert success is True
        assert manager.is_leased("device_123") is False

    def test_release_nonexistent_lease(self, manager):
        """Test releasing non-existent lease."""
        success = manager.release("device_123")

        assert success is False

    def test_acquire_after_release(self, manager):
        """Test device can be re-leased after release."""
        manager.acquire("user_123", "device_123")
        manager.release("device_123")

        lease = manager.acquire("user_456", "device_123")

        assert lease is not None
        assert lease.user_id == "user_456"


class TestLeaseExtension:
    """Test lease extension."""

    def test_extend_lease(self, manager):
        """Test extending lease time."""
        lease = manager.acquire("user_123", "device_123", ttl_seconds=60.0)
        original_expires = lease.expires_at

        success = manager.extend("device_123", additional_seconds=60.0)

        assert success is True
        assert lease.expires_at > original_expires

    def test_extend_nonexistent_lease(self, manager):
        """Test extending non-existent lease fails."""
        success = manager.extend("device_123", additional_seconds=60.0)

        assert success is False

    def test_extend_expired_lease(self, manager):
        """Test extending expired lease fails."""
        manager.acquire("user_123", "device_123", ttl_seconds=0.1)
        time.sleep(0.15)

        success = manager.extend("device_123", additional_seconds=60.0)

        assert success is False


class TestLeaseQueries:
    """Test lease query methods."""

    def test_get_lease(self, manager):
        """Test getting lease for device."""
        manager.acquire("user_123", "device_123")

        lease = manager.get_lease("device_123")

        assert lease is not None
        assert lease.user_id == "user_123"

    def test_get_lease_returns_none_when_expired(self, manager):
        """Test getting expired lease returns None."""
        manager.acquire("user_123", "device_123", ttl_seconds=0.1)
        time.sleep(0.15)

        lease = manager.get_lease("device_123")

        assert lease is None

    def test_is_leased(self, manager):
        """Test checking if device is leased."""
        manager.acquire("user_123", "device_123")

        assert manager.is_leased("device_123") is True
        assert manager.is_leased("device_456") is False

    def test_get_lease_holder(self, manager):
        """Test getting lease holder user ID."""
        manager.acquire("user_123", "device_123")

        holder = manager.get_lease_holder("device_123")

        assert holder == "user_123"

    def test_get_lease_holder_none(self, manager):
        """Test getting lease holder for unleased device."""
        holder = manager.get_lease_holder("device_123")

        assert holder is None

    def test_list_user_leases(self, manager):
        """Test listing all leases for a user."""
        manager.acquire("user_123", "device_1")
        manager.acquire("user_123", "device_2")
        manager.acquire("user_456", "device_3")

        leases = manager.list_user_leases("user_123")

        assert len(leases) == 2
        assert "device_1" in leases
        assert "device_2" in leases

    def test_list_all_leases(self, manager):
        """Test listing all active leases."""
        manager.acquire("user_123", "device_1")
        manager.acquire("user_456", "device_2")

        leases = manager.list_all_leases()

        assert len(leases) == 2


class TestLeaseCleanup:
    """Test automatic lease cleanup."""

    def test_expired_lease_auto_cleanup(self, manager):
        """Test expired leases are cleaned up automatically."""
        manager.acquire("user_123", "device_123", ttl_seconds=0.1)
        time.sleep(0.15)

        # Querying triggers cleanup
        manager.get_lease("device_123")

        assert manager.is_leased("device_123") is False

    def test_manual_cleanup(self, manager):
        """Test manual cleanup of expired leases."""
        manager.acquire("user_123", "device_123", ttl_seconds=0.1)
        time.sleep(0.15)

        count = manager._cleanup()

        assert count == 1
        assert len(manager.list_all_leases()) == 0

    def test_force_release(self, manager):
        """Test force releasing a lease."""
        manager.acquire("user_123", "device_123")

        success = manager.force_release("device_123")

        assert success is True
        assert manager.is_leased("device_123") is False


class TestLeaseStats:
    """Test lease statistics."""

    def test_get_stats(self, manager):
        """Test getting lease statistics."""
        manager.acquire("user_123", "device_1")
        manager.acquire("user_123", "device_2")
        manager.acquire("user_456", "device_3")

        stats = manager.get_stats()

        assert stats["active_leases"] == 3
        assert stats["unique_users"] == 2
        assert stats["default_ttl"] == 60.0

    def test_get_stats_after_release(self, manager):
        """Test stats update after lease release."""
        manager.acquire("user_123", "device_1")
        manager.release("device_1")

        stats = manager.get_stats()

        assert stats["active_leases"] == 0


class TestLeaseProperties:
    """Test Lease dataclass properties."""

    def test_is_expired_property(self, manager):
        """Test is_expired property."""
        lease = manager.acquire("user_123", "device_123", ttl_seconds=0.1)

        assert lease.is_expired is False

        time.sleep(0.15)

        assert lease.is_expired is True

    def test_remaining_seconds_property(self, manager):
        """Test remaining_seconds property."""
        lease = manager.acquire("user_123", "device_123", ttl_seconds=60.0)

        assert 59 < lease.remaining_seconds <= 60

    def test_remaining_seconds_zero_when_expired(self, manager):
        """Test remaining_seconds returns 0 when expired."""
        lease = manager.acquire("user_123", "device_123", ttl_seconds=0.1)
        time.sleep(0.15)

        assert lease.remaining_seconds == 0
