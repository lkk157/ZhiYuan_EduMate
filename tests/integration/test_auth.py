from __future__ import annotations

from sqlalchemy import select

from app.core.security import create_access_token
from app.db.models.rbac import USER_STATUS_DISABLED, User


async def login(client, username: str, password: str):
    return await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )


async def auth_header(client, username: str, password: str) -> dict[str, str]:
    response = await login(client, username, password)
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_login_success_returns_token_and_permissions(client, seeded):
    response = await login(client, "admin", seeded["password"])

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "admin"
    assert "user:manage" in data["user"]["permissions"]


async def test_login_wrong_password_and_unknown_user_share_message(client, seeded):
    wrong = await login(client, "admin", "wrong-pass")
    unknown = await login(client, "nobody", "wrong-pass")

    assert wrong.status_code == 401
    assert unknown.status_code == 401
    assert wrong.json()["code"] == 1002
    assert wrong.json()["message"] == unknown.json()["message"]


async def test_disabled_user_cannot_login(client, seeded, session_factory):
    async with session_factory() as session:
        user = await session.scalar(select(User).where(User.username == "student"))
        user.status = USER_STATUS_DISABLED
        await session.commit()

    response = await login(client, "student", seeded["password"])

    assert response.status_code == 401
    assert "禁用" in response.json()["message"]


async def test_me_requires_token(client, seeded):
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["code"] == 1002


async def test_me_returns_current_user(client, seeded):
    headers = await auth_header(client, "student", seeded["password"])

    response = await client.get("/api/v1/auth/me", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["username"] == "student"
    assert data["role"] == "student"
    assert "qa:ask" in data["permissions"]
    assert "user:manage" not in data["permissions"]


async def test_invalid_and_expired_tokens_are_rejected(client, seeded):
    invalid = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert invalid.status_code == 401

    expired_token = create_access_token(
        user_id=seeded["users"]["student"]["id"],
        username="student",
        role="student",
        token_version=0,
        expires_minutes=-1,
    )
    expired = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert expired.status_code == 401


async def test_password_change_invalidates_old_token(client, seeded):
    old_headers = await auth_header(client, "student", seeded["password"])

    changed = await client.put(
        "/api/v1/auth/password",
        headers=old_headers,
        json={
            "old_password": seeded["password"],
            "new_password": "NewSecret123!",
        },
    )
    assert changed.status_code == 200
    assert changed.json()["data"]["relogin_required"] is True

    old_token = await client.get("/api/v1/auth/me", headers=old_headers)
    assert old_token.status_code == 401

    old_login = await login(client, "student", seeded["password"])
    assert old_login.status_code == 401

    new_login = await login(client, "student", "NewSecret123!")
    assert new_login.status_code == 200


async def test_password_change_rejects_wrong_old_password(client, seeded):
    headers = await auth_header(client, "student", seeded["password"])

    response = await client.put(
        "/api/v1/auth/password",
        headers=headers,
        json={
            "old_password": "WrongSecret1!",
            "new_password": "NewSecret123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["message"] == "原密码不正确"


async def test_admin_permission_guard(client, seeded):
    student_headers = await auth_header(client, "student", seeded["password"])
    teacher_headers = await auth_header(client, "teacher", seeded["password"])
    admin_headers = await auth_header(client, "admin", seeded["password"])

    student = await client.get("/api/v1/admin/ping", headers=student_headers)
    teacher = await client.get("/api/v1/admin/ping", headers=teacher_headers)
    admin = await client.get("/api/v1/admin/ping", headers=admin_headers)

    assert student.status_code == 403
    assert teacher.status_code == 403
    assert admin.status_code == 200
    assert admin.json()["data"]["pong"] is True


async def test_token_version_mismatch_invalidates_token(client, seeded, session_factory):
    headers = await auth_header(client, "student", seeded["password"])

    async with session_factory() as session:
        user = await session.scalar(select(User).where(User.username == "student"))
        user.token_version += 1
        await session.commit()

    response = await client.get("/api/v1/auth/me", headers=headers)

    assert response.status_code == 401
    assert "失效" in response.json()["message"]


async def test_disabling_user_invalidates_existing_token(client, seeded, session_factory):
    headers = await auth_header(client, "student", seeded["password"])

    async with session_factory() as session:
        user = await session.scalar(select(User).where(User.username == "student"))
        user.status = USER_STATUS_DISABLED
        await session.commit()

    response = await client.get("/api/v1/auth/me", headers=headers)

    assert response.status_code == 401
    assert "禁用" in response.json()["message"]


async def test_student_self_registration_returns_token_and_student_role(client, seeded):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "NewStudent",
            "password": "NewSecret123!",
            "password_confirm": "NewSecret123!",
            "email": "new.student@example.com",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["access_token"]
    assert data["user"]["username"] == "newstudent"
    assert data["user"]["role"] == "student"
    assert data["user"]["email"] == "new.student@example.com"
    assert "qa:ask" in data["user"]["permissions"]
    assert "user:manage" not in data["user"]["permissions"]

    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["data"]["username"] == "newstudent"

    # Username lookups are case-insensitive.
    login_response = await login(client, "NEWSTUDENT", "NewSecret123!")
    assert login_response.status_code == 200


async def test_duplicate_username_registration_is_rejected(client, seeded):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "student",
            "password": "NewSecret123!",
            "password_confirm": "NewSecret123!",
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == 1005


async def test_duplicate_email_registration_is_rejected(client, seeded):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "anotherstudent",
            "password": "NewSecret123!",
            "password_confirm": "NewSecret123!",
            "email": "student@edumate.local",
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == 1005


async def test_registration_validates_password_confirmation_and_strength(client, seeded):
    mismatch = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "mismatchuser",
            "password": "NewSecret123!",
            "password_confirm": "Different123!",
        },
    )
    weak = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "weakuser",
            "password": "short",
            "password_confirm": "short",
        },
    )

    assert mismatch.status_code == 422
    assert mismatch.json()["code"] == 1001
    assert weak.status_code == 422
    assert weak.json()["code"] == 1001


async def test_registration_validates_email_format(client, seeded):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "bademailuser",
            "password": "NewSecret123!",
            "password_confirm": "NewSecret123!",
            "email": "not-an-email",
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == 1001
