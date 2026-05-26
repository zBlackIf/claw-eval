"""access_check.py — 集成 RoleService + UserRoleBindingService，对外暴露 check_access。"""

from typing import Iterable, Optional


class AccessChecker:
    def __init__(self, role_service, binding_service) -> None:
        self.roles = role_service
        self.bindings = binding_service

    def check_access(self, user_id: str, perm: str, tenant_id: str,
                     deny_overrides: Optional[Iterable[str]] = None) -> bool:
        """
        判定 user 是否有 perm 权限。
        - deny_overrides: 任何匹配的 perm 都立即拒绝（适合敏感操作的 explicit deny）
        - 多租户：tenant_id 严格隔离
        - 角色继承：通过 effective_permissions
        """
        if deny_overrides and perm in set(deny_overrides):
            return False

        active_roles = self.bindings.list_active_roles(user_id, tenant_id)
        if not active_roles:
            return False

        for role_name in active_roles:
            try:
                if self.roles.has_permission(role_name, perm):
                    return True
            except KeyError:
                # role 被删过；忽略此 binding（应清理 stale binding）
                continue
        return False
