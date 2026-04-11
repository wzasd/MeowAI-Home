"""LeaseManager — TTL-based lease management for limb devices."""

import time
import threading
from dataclasses import dataclass
from typing import Dict, Optional, Set
from uuid import uuid4


@dataclass
class Lease:
    """A lease for device access."""
    lease_id: str
    user_id: str
    device_id: str
    acquired_at: float
    expires_at: float

    @property
    def is_expired(self) -> bool:
        """Check if lease has expired."""
        return time.time() > self.expires_at

    @property
    def remaining_seconds(self) -> float:
        """Get remaining lease time."""
        return max(0, self.expires_at - time.time())


class LeaseManager:
    """Manages TTL-based leases for device access.

    Features:
    - First-come-first-served lease acquisition
    - Automatic expiration
    - Crash cleanup (detect stale leases)
    - Lease extension
    """

    def __init__(
        self,
        default_ttl: float = 300.0,  # 5 minutes
        cleanup_interval: float = 60.0,  # Cleanup every minute
    ):
        self._default_ttl = default_ttl
        self._cleanup_interval = cleanup_interval
        self._leases: Dict[str, Lease] = {}  # device_id -> Lease
        self._user_leases: Dict[str, Set[str]] = {}  # user_id -> {device_ids}
        self._lock = threading.RLock()
        self._last_cleanup = time.time()

    def acquire(
        self,
        user_id: str,
        device_id: str,
        ttl_seconds: Optional[float] = None,
    ) -> Optional[Lease]:
        """Acquire a lease for a device.

        Args:
            user_id: User requesting the lease
            device_id: Target device
            ttl_seconds: Lease TTL (default: 5 minutes)

        Returns:
            Lease if acquired, None if device already leased
        """
        self._maybe_cleanup()

        ttl = ttl_seconds or self._default_ttl

        with self._lock:
            # Check if device is already leased
            if device_id in self._leases:
                existing = self._leases[device_id]
                if not existing.is_expired:
                    return None

            # Create new lease
            now = time.time()
            lease = Lease(
                lease_id=f"lease_{uuid4().hex[:12]}",
                user_id=user_id,
                device_id=device_id,
                acquired_at=now,
                expires_at=now + ttl,
            )

            self._leases[device_id] = lease

            # Track user's leases
            if user_id not in self._user_leases:
                self._user_leases[user_id] = set()
            self._user_leases[user_id].add(device_id)

            return lease

    def release(self, device_id: str) -> bool:
        """Release a lease.

        Args:
            device_id: Device to release

        Returns:
            True if lease was released
        """
        with self._lock:
            if device_id not in self._leases:
                return False

            lease = self._leases[device_id]

            # Remove from tracking
            del self._leases[device_id]

            user_id = lease.user_id
            if user_id in self._user_leases:
                self._user_leases[user_id].discard(device_id)
                if not self._user_leases[user_id]:
                    del self._user_leases[user_id]

            return True

    def extend(self, device_id: str, additional_seconds: float) -> bool:
        """Extend an existing lease.

        Args:
            device_id: Device to extend
            additional_seconds: Time to add

        Returns:
            True if lease was extended
        """
        with self._lock:
            if device_id not in self._leases:
                return False

            lease = self._leases[device_id]
            if lease.is_expired:
                return False

            lease.expires_at += additional_seconds
            return True

    def get_lease(self, device_id: str) -> Optional[Lease]:
        """Get current lease for a device."""
        self._maybe_cleanup()

        with self._lock:
            lease = self._leases.get(device_id)
            if lease and lease.is_expired:
                # Auto-cleanup expired lease
                self.release(device_id)
                return None
            return lease

    def is_leased(self, device_id: str) -> bool:
        """Check if device is currently leased."""
        return self.get_lease(device_id) is not None

    def get_lease_holder(self, device_id: str) -> Optional[str]:
        """Get user ID of current lease holder."""
        lease = self.get_lease(device_id)
        return lease.user_id if lease else None

    def list_user_leases(self, user_id: str) -> Dict[str, Lease]:
        """List all leases held by a user."""
        self._maybe_cleanup()

        with self._lock:
            device_ids = self._user_leases.get(user_id, set())
            return {
                device_id: self._leases[device_id]
                for device_id in device_ids
                if device_id in self._leases
            }

    def list_all_leases(self) -> Dict[str, Lease]:
        """List all active leases."""
        self._maybe_cleanup()

        with self._lock:
            return dict(self._leases)

    def force_release(self, device_id: str) -> bool:
        """Force release a lease (admin override).

        Args:
            device_id: Device to release

        Returns:
            True if lease was released
        """
        return self.release(device_id)

    def _maybe_cleanup(self) -> None:
        """Run cleanup if interval has passed."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        self._cleanup()
        self._last_cleanup = now

    def _cleanup(self) -> int:
        """Clean up expired leases.

        Returns:
            Number of leases cleaned up
        """
        expired = []

        with self._lock:
            for device_id, lease in self._leases.items():
                if lease.is_expired:
                    expired.append(device_id)

            for device_id in expired:
                self.release(device_id)

        return len(expired)

    def get_stats(self) -> Dict:
        """Get lease manager statistics."""
        self._maybe_cleanup()

        with self._lock:
            return {
                "active_leases": len(self._leases),
                "unique_users": len(self._user_leases),
                "default_ttl": self._default_ttl,
            }
