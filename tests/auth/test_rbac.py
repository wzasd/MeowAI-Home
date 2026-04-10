"""RBAC tests"""
import pytest
from src.auth.rbac import check_permission, ROLE_PERMISSIONS, get_role_permissions


class TestCheckPermission:
    def test_admin_has_all_permissions(self):
        assert check_permission("admin", "read") is True
        assert check_permission("admin", "write") is True
        assert check_permission("admin", "delete") is True
        assert check_permission("admin", "manage_users") is True

    def test_member_has_limited_permissions(self):
        assert check_permission("member", "read") is True
        assert check_permission("member", "write") is True
        assert check_permission("member", "delete") is False
        assert check_permission("member", "manage_agents") is True
        assert check_permission("member", "manage_users") is False

    def test_viewer_has_only_read(self):
        assert check_permission("viewer", "read") is True
        assert check_permission("viewer", "write") is False
        assert check_permission("viewer", "delete") is False

    def test_unknown_role_has_no_permissions(self):
        assert check_permission("unknown", "read") is False
        assert check_permission("unknown", "write") is False


class TestGetRolePermissions:
    def test_get_admin_permissions(self):
        perms = get_role_permissions("admin")
        assert "read" in perms
        assert "write" in perms
        assert "delete" in perms

    def test_get_empty_for_unknown_role(self):
        perms = get_role_permissions("nonexistent")
        assert perms == set()

    def test_permissions_are_copied(self):
        perms1 = get_role_permissions("admin")
        perms1.add("new_permission")
        perms2 = get_role_permissions("admin")
        assert "new_permission" not in perms2
