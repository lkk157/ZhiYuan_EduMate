"""Shared test data factories."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    DEMO_USERS,
    PERMISSION_CATALOG,
    ROLE_DESCRIPTIONS,
    ROLE_PERMISSIONS,
)
from app.core.security import hash_password
from app.db.models.rbac import USER_STATUS_ACTIVE, Permission, Role, User

TEST_PASSWORD = "Secret123!"
# Hash once: bcrypt is intentionally expensive and tests create many users.
TEST_PASSWORD_HASH = hash_password(TEST_PASSWORD)


async def seed_rbac(session: AsyncSession) -> dict:
    permissions: dict[str, Permission] = {}
    for code, (name, description) in PERMISSION_CATALOG.items():
        permission = Permission(code=code, name=name, description=description)
        session.add(permission)
        permissions[code] = permission
    await session.flush()

    roles: dict[str, Role] = {}
    for role_name, codes in ROLE_PERMISSIONS.items():
        role = Role(name=role_name, description=ROLE_DESCRIPTIONS[role_name])
        role.permissions = [permissions[code] for code in codes]
        session.add(role)
        roles[role_name] = role
    await session.flush()

    users: dict[str, User] = {}
    for username, email, role_name in DEMO_USERS:
        user = User(
            username=username,
            email=email,
            role_id=roles[role_name].id,
            status=USER_STATUS_ACTIVE,
            password_hash=TEST_PASSWORD_HASH,
        )
        session.add(user)
        users[role_name] = user
    await session.commit()

    return {
        "password": TEST_PASSWORD,
        "roles": {name: role.id for name, role in roles.items()},
        "users": {name: {"id": user.id, "username": user.username} for name, user in users.items()},
    }
