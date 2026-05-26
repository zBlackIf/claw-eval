"""user_role_binding.py — 用户绑定多个角色，支持时效与租户隔离。"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Binding:
    user_id: str
    role_name: str
    tenant_id: str  # 多租户隔离
    granted_at: datetime
    expires_at: Optional[datetime] = None
    granted_by: Optional[str] = None


class UserRoleBindingService:
    def __init__(self) -> None:
        self._bindings: list[Binding] = []

    def grant(self, user_id: str, role_name: str, tenant_id: str,
              expires_at: Optional[datetime] = None,
              granted_by: Optional[str] = None) -> Binding:
        # 同租户内同 role 不重复绑定
        for b in self._bindings:
            if (b.user_id == user_id and b.role_name == role_name
                    and b.tenant_id == tenant_id and not self._is_expired(b)):
                raise ValueError(f"user {user_id} already has active binding to {role_name} in {tenant_id}")
        binding = Binding(
            user_id=user_id, role_name=role_name, tenant_id=tenant_id,
            granted_at=datetime.now(timezone.utc),
            expires_at=expires_at, granted_by=granted_by,
        )
        self._bindings.append(binding)
        return binding

    def revoke(self, user_id: str, role_name: str, tenant_id: str) -> int:
        before = len(self._bindings)
        self._bindings = [
            b for b in self._bindings
            if not (b.user_id == user_id and b.role_name == role_name
                    and b.tenant_id == tenant_id)
        ]
        return before - len(self._bindings)

    def list_active_roles(self, user_id: str, tenant_id: str) -> list[str]:
        return [
            b.role_name for b in self._bindings
            if b.user_id == user_id and b.tenant_id == tenant_id
            and not self._is_expired(b)
        ]

    @staticmethod
    def _is_expired(b: Binding) -> bool:
        return b.expires_at is not None and b.expires_at < datetime.now(timezone.utc)
