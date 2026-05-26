"""role_service.py — RBAC core: roles, permissions, hierarchy."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Role:
    name: str
    permissions: set[str] = field(default_factory=set)
    parents: list[str] = field(default_factory=list)  # 角色继承


class RoleService:
    def __init__(self) -> None:
        self._roles: dict[str, Role] = {}

    def create_role(self, name: str, permissions: list[str] | None = None,
                    parents: list[str] | None = None) -> Role:
        if name in self._roles:
            raise ValueError(f"role {name!r} already exists")
        if parents:
            for p in parents:
                if p not in self._roles:
                    raise ValueError(f"parent role {p!r} not found")
        role = Role(name=name, permissions=set(permissions or []),
                    parents=list(parents or []))
        self._roles[name] = role
        return role

    def delete_role(self, name: str) -> None:
        if name not in self._roles:
            raise KeyError(name)
        # 检查是否有其他角色继承自它
        children = [r for r in self._roles.values() if name in r.parents]
        if children:
            raise ValueError(f"role {name!r} has {len(children)} children, cannot delete")
        del self._roles[name]

    def get_role(self, name: str) -> Optional[Role]:
        return self._roles.get(name)

    def effective_permissions(self, name: str) -> set[str]:
        """计算角色的有效权限（含父角色继承）。检测循环继承。"""
        if name not in self._roles:
            raise KeyError(name)
        visited: set[str] = set()
        perms: set[str] = set()

        def _walk(role_name: str) -> None:
            if role_name in visited:
                raise ValueError(f"cyclic inheritance detected at {role_name!r}")
            visited.add(role_name)
            r = self._roles.get(role_name)
            if not r:
                return
            perms.update(r.permissions)
            for p in r.parents:
                _walk(p)

        _walk(name)
        return perms

    def has_permission(self, role_name: str, perm: str) -> bool:
        return perm in self.effective_permissions(role_name)
