"""Administrator governance: users, roles and audit trail."""

from __future__ import annotations

import json

from sqlalchemy import select

from app.db.models.audit import AuditLog
from app.db.models.rbac import Permission, Role, User
from tests.factories import TEST_PASSWORD, TEST_PASSWORD_HASH


async def login(client, username: str, password: str):
    return await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )


async def auth_headers(client, username: str, password: str) -> dict[str, str]:
    response = await login(client, username, password)
    assert response.status_code == 200, response.text
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def create_user(client, headers, **overrides):
    payload = {
        "username": "newteacher",
        "password": "CreatePass123!",
        "email": "newteacher@example.com",
        "role": "teacher",
    }
    payload.update(overrides)
    return await client.post("/api/v1/admin/users", headers=headers, json=payload)


async def test_user_list_supports_pagination_search_and_filters(client, seeded):
    headers = await auth_headers(client, "admin", seeded["password"])

    page = await client.get("/api/v1/admin/users?page=1&page_size=2", headers=headers)
    assert page.status_code == 200
    assert page.json()["data"]["total"] == 3
    assert len(page.json()["data"]["items"]) == 2

    searched = await client.get("/api/v1/admin/users?keyword=teach", headers=headers)
    assert [item["username"] for item in searched.json()["data"]["items"]] == ["teacher"]

    by_role = await client.get("/api/v1/admin/users?role=student", headers=headers)
    assert [item["username"] for item in by_role.json()["data"]["items"]] == ["student"]

    by_status = await client.get("/api/v1/admin/users?status=active", headers=headers)
    assert by_status.json()["data"]["total"] == 3

    invalid_status = await client.get("/api/v1/admin/users?status=banned", headers=headers)
    assert invalid_status.status_code == 422


async def test_user_management_requires_admin_permission(client, seeded):
    teacher = await auth_headers(client, "teacher", seeded["password"])
    student = await auth_headers(client, "student", seeded["password"])

    for headers in (teacher, student):
        response = await client.get("/api/v1/admin/users", headers=headers)
        assert response.status_code == 403
        assert response.json()["code"] == 1003


async def test_create_user_validates_duplicates_role_and_password(client, seeded):
    headers = await auth_headers(client, "admin", seeded["password"])

    created = await create_user(client, headers, email="NewTeacher@Example.com")
    assert created.status_code == 201
    data = created.json()["data"]
    assert data["username"] == "newteacher"
    assert data["email"] == "newteacher@example.com"
    assert data["role"] == "teacher"
    assert data["status"] == "active"
    assert "course:create" in data["permissions"]
    assert "user:manage" not in data["permissions"]

    duplicate_name = await create_user(client, headers, email="other@example.com")
    assert duplicate_name.status_code == 409

    duplicate_email = await create_user(
        client, headers, username="another", email="newteacher@example.com"
    )
    assert duplicate_email.status_code == 409

    invalid_role = await create_user(
        client, headers, username="badrole", email="badrole@example.com", role="superuser"
    )
    assert invalid_role.status_code == 422
    assert invalid_role.json()["code"] == 1001

    weak_password = await create_user(
        client, headers, username="weakuser", password="short", email="weak@example.com"
    )
    assert weak_password.status_code == 422

    login_response = await login(client, "NEWTEACHER", "CreatePass123!")
    assert login_response.status_code == 200
    assert login_response.json()["data"]["user"]["role"] == "teacher"


async def test_role_change_invalidates_tokens_and_updates_permissions(client, seeded):
    headers = await auth_headers(client, "admin", seeded["password"])
    created = await create_user(client, headers)
    user_id = created.json()["data"]["id"]

    teacher_headers = await auth_headers(client, "newteacher", "CreatePass123!")
    before = await client.get("/api/v1/auth/me", headers=teacher_headers)
    assert "course:create" in before.json()["data"]["permissions"]

    updated = await client.put(
        f"/api/v1/admin/users/{user_id}",
        headers=headers,
        json={"role": "student", "email": "changed@example.com"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["role"] == "student"
    assert updated.json()["data"]["email"] == "changed@example.com"
    assert "course:create" not in updated.json()["data"]["permissions"]

    stale = await client.get("/api/v1/auth/me", headers=teacher_headers)
    assert stale.status_code == 401
    assert "失效" in stale.json()["message"]

    refreshed = await login(client, "newteacher", "CreatePass123!")
    assert refreshed.json()["data"]["user"]["role"] == "student"

    invalid = await client.put(
        f"/api/v1/admin/users/{user_id}",
        headers=headers,
        json={"role": "superuser"},
    )
    assert invalid.status_code == 422


async def test_email_update_rejects_duplicates_and_can_be_cleared(client, seeded):
    headers = await auth_headers(client, "admin", seeded["password"])
    first = await create_user(client, headers, username="firstuser", email="first@example.com")
    second = await create_user(client, headers, username="seconduser", email="second@example.com")
    second_id = second.json()["data"]["id"]

    duplicate = await client.put(
        f"/api/v1/admin/users/{second_id}",
        headers=headers,
        json={"email": "first@example.com"},
    )
    assert duplicate.status_code == 409

    cleared = await client.put(
        f"/api/v1/admin/users/{second_id}",
        headers=headers,
        json={"email": ""},
    )
    assert cleared.status_code == 200
    assert cleared.json()["data"]["email"] is None
    assert first.status_code == 201


async def test_disable_and_enable_user_with_self_protection(client, seeded):
    headers = await auth_headers(client, "admin", seeded["password"])
    created = await create_user(client, headers)
    user_id = created.json()["data"]["id"]
    teacher_headers = await auth_headers(client, "newteacher", "CreatePass123!")

    disabled = await client.put(
        f"/api/v1/admin/users/{user_id}/status",
        headers=headers,
        json={"status": "disabled"},
    )
    assert disabled.status_code == 200
    assert disabled.json()["data"]["status"] == "disabled"

    stale = await client.get("/api/v1/auth/me", headers=teacher_headers)
    assert stale.status_code == 401
    assert "禁用" in stale.json()["message"]

    blocked_login = await login(client, "newteacher", "CreatePass123!")
    assert blocked_login.status_code == 401

    enabled = await client.put(
        f"/api/v1/admin/users/{user_id}/status",
        headers=headers,
        json={"status": "active"},
    )
    assert enabled.status_code == 200
    assert (await login(client, "newteacher", "CreatePass123!")).status_code == 200

    self_disable = await client.put(
        f"/api/v1/admin/users/{seeded['users']['admin']['id']}/status",
        headers=headers,
        json={"status": "disabled"},
    )
    assert self_disable.status_code == 409
    assert "自己" in self_disable.json()["message"]

    invalid_status = await client.put(
        f"/api/v1/admin/users/{user_id}/status",
        headers=headers,
        json={"status": "banned"},
    )
    assert invalid_status.status_code == 422


async def test_last_admin_is_protected_from_demotion_and_disable(client, seeded, session_factory):
    async with session_factory() as session:
        permission = await session.scalar(
            select(Permission).where(Permission.code == "user:manage")
        )
        moderator_role = Role(name="moderator", description="user manager without admin role")
        moderator_role.permissions = [permission]
        session.add(moderator_role)
        await session.flush()
        session.add(
            User(
                username="moderator",
                email="moderator@example.com",
                password_hash=TEST_PASSWORD_HASH,
                role_id=moderator_role.id,
                status="active",
            )
        )
        await session.commit()

    moderator_headers = await auth_headers(client, "moderator", TEST_PASSWORD)
    admin_id = seeded["users"]["admin"]["id"]

    disabled = await client.put(
        f"/api/v1/admin/users/{admin_id}/status",
        headers=moderator_headers,
        json={"status": "disabled"},
    )
    assert disabled.status_code == 409
    assert "管理员" in disabled.json()["message"]

    demoted = await client.put(
        f"/api/v1/admin/users/{admin_id}",
        headers=moderator_headers,
        json={"role": "student"},
    )
    assert demoted.status_code == 409


async def test_reset_password_invalidates_old_credentials(client, seeded):
    headers = await auth_headers(client, "admin", seeded["password"])
    student_id = seeded["users"]["student"]["id"]
    student_headers = await auth_headers(client, "student", seeded["password"])

    reset = await client.post(
        f"/api/v1/admin/users/{student_id}/reset-password",
        headers=headers,
        json={"new_password": "ResetPass123!"},
    )
    assert reset.status_code == 200
    assert reset.json()["data"]["reset"] is True

    assert (await login(client, "student", seeded["password"])).status_code == 401
    assert (await login(client, "student", "ResetPass123!")).status_code == 200
    stale = await client.get("/api/v1/auth/me", headers=student_headers)
    assert stale.status_code == 401

    too_short = await client.post(
        f"/api/v1/admin/users/{student_id}/reset-password",
        headers=headers,
        json={"new_password": "short"},
    )
    assert too_short.status_code == 422


async def test_roles_overview_returns_permission_matrix(client, seeded):
    headers = await auth_headers(client, "admin", seeded["password"])

    response = await client.get("/api/v1/admin/roles", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    roles = {role["name"]: role for role in data["roles"]}

    assert set(roles) == {"admin", "teacher", "student"}
    assert len(data["permissions"]) == 12
    assert len(roles["admin"]["permissions"]) == 12
    assert "course:create" in roles["teacher"]["permissions"]
    assert set(roles["student"]["permissions"]) == {"qa:ask", "exercise:answer"}
    assert roles["admin"]["user_count"] == 1

    teacher_headers = await auth_headers(client, "teacher", seeded["password"])
    forbidden = await client.get("/api/v1/admin/roles", headers=teacher_headers)
    assert forbidden.status_code == 403


async def test_audit_trail_records_login_and_governance_actions(client, seeded):
    failed = await login(client, "nobody", "WrongPass123!")
    assert failed.status_code == 401

    headers = await auth_headers(client, "admin", seeded["password"])
    created = await create_user(client, headers)
    user_id = created.json()["data"]["id"]
    await client.put(
        f"/api/v1/admin/users/{user_id}/status",
        headers=headers,
        json={"status": "disabled"},
    )

    logs = await client.get("/api/v1/admin/audit-logs?page_size=100", headers=headers)
    assert logs.status_code == 200
    data = logs.json()["data"]
    actions = {item["action"] for item in data["items"]}
    assert {
        "auth.login.failed",
        "auth.login.success",
        "user.create",
        "user.disable",
    } <= actions
    assert data["total"] >= 4

    create_entry = next(item for item in data["items"] if item["action"] == "user.create")
    assert create_entry["username"] == "admin"
    assert create_entry["target_type"] == "user"
    assert create_entry["target_id"] == str(user_id)
    assert "CreatePass123!" not in json.dumps(create_entry["detail"], ensure_ascii=False)
    assert "password" not in create_entry["detail"]

    failures = await client.get("/api/v1/admin/audit-logs?status=failure", headers=headers)
    assert failures.json()["data"]["total"] == 1
    assert failures.json()["data"]["items"][0]["action"] == "auth.login.failed"

    creates = await client.get("/api/v1/admin/audit-logs?action=user.create", headers=headers)
    assert creates.json()["data"]["total"] == 1

    by_username = await client.get("/api/v1/admin/audit-logs?username=admin", headers=headers)
    assert by_username.json()["data"]["total"] >= 1

    student_headers = await auth_headers(client, "student", seeded["password"])
    forbidden = await client.get("/api/v1/admin/audit-logs", headers=student_headers)
    assert forbidden.status_code == 403


async def test_audit_detail_is_redacted_on_read(client, seeded, session_factory):
    async with session_factory() as session:
        session.add(
            AuditLog(
                username="admin",
                action="test.leak",
                detail={
                    "new_password": "leaked-password",
                    "profile": {"api_key": "leaked-key", "display_name": "Admin"},
                },
                status="success",
            )
        )
        await session.commit()

    headers = await auth_headers(client, "admin", seeded["password"])
    response = await client.get("/api/v1/admin/audit-logs?action=test.leak", headers=headers)
    assert response.status_code == 200
    detail = response.json()["data"]["items"][0]["detail"]
    assert detail["new_password"] == "***"
    assert detail["profile"]["api_key"] == "***"
    assert detail["profile"]["display_name"] == "Admin"


async def test_audit_pagination_and_keyword_filter(client, seeded):
    headers = await auth_headers(client, "admin", seeded["password"])
    await login(client, "teacher", seeded["password"])

    first_page = await client.get("/api/v1/admin/audit-logs?page=1&page_size=1", headers=headers)
    assert first_page.status_code == 200
    data = first_page.json()["data"]
    assert len(data["items"]) == 1
    assert data["total"] >= 2

    second_page = await client.get("/api/v1/admin/audit-logs?page=2&page_size=1", headers=headers)
    assert second_page.json()["data"]["items"][0]["id"] != data["items"][0]["id"]

    keyword = await client.get("/api/v1/admin/audit-logs?keyword=login", headers=headers)
    assert keyword.json()["data"]["total"] >= 2


async def test_admin_stats_returns_user_and_audit_totals(client, seeded):
    headers = await auth_headers(client, "admin", seeded["password"])
    stats = await client.get("/api/v1/admin/stats", headers=headers)

    assert stats.status_code == 200
    data = stats.json()["data"]
    assert data["total_users"] == 3
    assert data["active_users"] == 3
    assert data["role_counts"] == {"admin": 1, "teacher": 1, "student": 1}
    assert data["today_audits"] >= 1

    student_headers = await auth_headers(client, "student", seeded["password"])
    forbidden = await client.get("/api/v1/admin/stats", headers=student_headers)
    assert forbidden.status_code == 403
