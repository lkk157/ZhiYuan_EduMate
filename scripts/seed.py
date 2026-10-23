"""Idempotent RBAC seed: roles, permissions and demo accounts.

Usage:
    python scripts/seed.py
    python scripts/seed.py --reset-passwords
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.permissions import (  # noqa: E402
    DEMO_USERS,
    PERMISSION_CATALOG,
    ROLE_DESCRIPTIONS,
    ROLE_PERMISSIONS,
)
from app.core.security import hash_password  # noqa: E402
from app.db.models.rbac import USER_STATUS_ACTIVE, Permission, Role, User  # noqa: E402
from app.db.session import AsyncSessionLocal  # noqa: E402


async def seed(reset_passwords: bool = False) -> None:
    settings = get_settings()
    password = settings.seed_demo_password

    async with AsyncSessionLocal() as session:
        existing_permissions = {
            permission.code: permission
            for permission in (await session.scalars(select(Permission))).all()
        }
        for code, (name, description) in PERMISSION_CATALOG.items():
            if code not in existing_permissions:
                permission = Permission(code=code, name=name, description=description)
                session.add(permission)
                existing_permissions[code] = permission

        await session.flush()

        existing_roles = {role.name: role for role in (await session.scalars(select(Role))).all()}
        for role_name, permission_codes in ROLE_PERMISSIONS.items():
            role = existing_roles.get(role_name)
            if role is None:
                role = Role(name=role_name, description=ROLE_DESCRIPTIONS[role_name])
                session.add(role)
                existing_roles[role_name] = role
            role.permissions = [existing_permissions[code] for code in permission_codes]

        await session.flush()

        for username, email, role_name in DEMO_USERS:
            user = await session.scalar(select(User).where(User.username == username))
            if user is None:
                session.add(
                    User(
                        username=username,
                        email=email,
                        role_id=existing_roles[role_name].id,
                        status=USER_STATUS_ACTIVE,
                        password_hash=hash_password(password),
                    )
                )
            elif reset_passwords:
                user.password_hash = hash_password(password)
                user.token_version += 1
                user.role_id = existing_roles[role_name].id
                user.status = USER_STATUS_ACTIVE

        await session.commit()

    print("Seed complete.")
    print("  roles: admin, teacher, student")
    print(f"  permissions: {len(PERMISSION_CATALOG)}")
    print("  demo accounts: admin, teacher, student")
    if password == "EduMate@2026":
        print("  WARNING: using default demo password; set SEED_DEMO_PASSWORD in .env.")
    print("  password source: SEED_DEMO_PASSWORD (see README / .env.example)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed EduMate RBAC data")
    parser.add_argument(
        "--reset-passwords",
        action="store_true",
        help="reset demo account passwords to SEED_DEMO_PASSWORD",
    )
    args = parser.parse_args()
    asyncio.run(seed(reset_passwords=args.reset_passwords))


if __name__ == "__main__":
    main()
