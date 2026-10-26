"""Course hierarchy, review workflow, invitation codes and enrollment."""

from __future__ import annotations


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


async def register_student(client, username: str = "student2") -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "password": "StudentPass123!",
            "password_confirm": "StudentPass123!",
        },
    )
    assert response.status_code == 201, response.text
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def create_course(client, headers, title: str = "机器学习基础", **overrides):
    payload = {"title": title, "description": "面向初学者的机器学习课程"}
    payload.update(overrides)
    return await client.post("/api/v1/courses", headers=headers, json=payload)


async def add_chapter(client, headers, course_id: int, title: str, order_no: int = 0):
    return await client.post(
        f"/api/v1/courses/{course_id}/chapters",
        headers=headers,
        json={"title": title, "order_no": order_no},
    )


async def add_knowledge(
    client, headers, course_id: int, chapter_id: int, name: str, difficulty: int = 3
):
    return await client.post(
        f"/api/v1/courses/{course_id}/chapters/{chapter_id}/knowledges",
        headers=headers,
        json={"name": name, "difficulty": difficulty},
    )


async def build_approved_course(client, teacher_headers, admin_headers, title="机器学习基础"):
    created = await create_course(client, teacher_headers, title=title)
    assert created.status_code == 201, created.text
    course = created.json()["data"]
    chapter = await add_chapter(client, teacher_headers, course["id"], "第一章 绪论")
    assert chapter.status_code == 201, chapter.text
    chapter_id = chapter.json()["data"]["id"]
    knowledge = await add_knowledge(client, teacher_headers, course["id"], chapter_id, "监督学习")
    assert knowledge.status_code == 201, knowledge.text

    submitted = await client.post(f"/api/v1/courses/{course['id']}/submit", headers=teacher_headers)
    assert submitted.status_code == 200, submitted.text
    reviewed = await client.post(
        f"/api/v1/courses/{course['id']}/review",
        headers=admin_headers,
        json={"decision": "approve", "comment": "内容完整"},
    )
    assert reviewed.status_code == 200, reviewed.text
    return reviewed.json()["data"]


async def create_second_teacher(client, admin_headers, username="teacher2"):
    response = await client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={
            "username": username,
            "password": "TeacherPass123!",
            "email": f"{username}@example.com",
            "role": "teacher",
        },
    )
    assert response.status_code == 201, response.text
    return await auth_headers(client, username, "TeacherPass123!")


async def test_teacher_course_crud_and_review_workflow(client, seeded):
    teacher = await auth_headers(client, "teacher", seeded["password"])
    admin = await auth_headers(client, "admin", seeded["password"])
    student = await auth_headers(client, "student", seeded["password"])

    forbidden_create = await create_course(client, student, title="学生不能建课")
    assert forbidden_create.status_code == 403

    created = await create_course(client, teacher)
    assert created.status_code == 201
    course = created.json()["data"]
    assert course["status"] == "draft"
    assert course["teacher"]["username"] == "teacher"
    assert len(course["invite_code"]) == 8
    assert course["chapter_count"] == 0
    assert course["knowledge_count"] == 0
    assert course["student_count"] == 0

    second_teacher = await create_second_teacher(client, admin)
    other_read = await client.get(f"/api/v1/courses/{course['id']}", headers=second_teacher)
    assert other_read.status_code == 403
    other_update = await client.put(
        f"/api/v1/courses/{course['id']}",
        headers=second_teacher,
        json={"title": "篡改标题"},
    )
    assert other_update.status_code == 403

    updated = await client.put(
        f"/api/v1/courses/{course['id']}",
        headers=teacher,
        json={"title": "机器学习导论", "description": "更新后的课程简介"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["title"] == "机器学习导论"

    chapter_two = await add_chapter(client, teacher, course["id"], "第二章 模型评估", 2)
    chapter_one = await add_chapter(client, teacher, course["id"], "第一章 绪论", 1)
    assert chapter_two.status_code == 201
    assert chapter_one.status_code == 201
    chapter_id = chapter_one.json()["data"]["id"]

    knowledge = await add_knowledge(
        client, teacher, course["id"], chapter_id, "监督学习", difficulty=2
    )
    assert knowledge.status_code == 201
    assert knowledge.json()["data"]["difficulty"] == 2

    detail = await client.get(f"/api/v1/courses/{course['id']}", headers=teacher)
    assert detail.status_code == 200
    detail_data = detail.json()["data"]
    assert [item["title"] for item in detail_data["chapters"]] == [
        "第一章 绪论",
        "第二章 模型评估",
    ]
    assert detail_data["chapters"][0]["knowledges"][0]["name"] == "监督学习"
    assert detail_data["chapter_count"] == 2
    assert detail_data["knowledge_count"] == 1

    submitted = await client.post(f"/api/v1/courses/{course['id']}/submit", headers=teacher)
    assert submitted.status_code == 200
    assert submitted.json()["data"]["status"] == "pending"

    locked = await client.put(
        f"/api/v1/courses/{course['id']}",
        headers=teacher,
        json={"title": "审核中修改"},
    )
    assert locked.status_code == 409

    resubmit = await client.post(f"/api/v1/courses/{course['id']}/submit", headers=teacher)
    assert resubmit.status_code == 409

    missing_comment = await client.post(
        f"/api/v1/courses/{course['id']}/review",
        headers=admin,
        json={"decision": "reject"},
    )
    assert missing_comment.status_code == 422

    rejected = await client.post(
        f"/api/v1/courses/{course['id']}/review",
        headers=admin,
        json={"decision": "reject", "comment": "请补充课程目标"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["data"]["status"] == "rejected"
    assert rejected.json()["data"]["review_comment"] == "请补充课程目标"

    editable_again = await client.put(
        f"/api/v1/courses/{course['id']}",
        headers=teacher,
        json={"description": "已补充课程目标"},
    )
    assert editable_again.status_code == 200

    resubmitted = await client.post(f"/api/v1/courses/{course['id']}/submit", headers=teacher)
    assert resubmitted.status_code == 200
    approved = await client.post(
        f"/api/v1/courses/{course['id']}/review",
        headers=admin,
        json={"decision": "approve"},
    )
    assert approved.status_code == 200
    assert approved.json()["data"]["status"] == "approved"

    review_again = await client.post(
        f"/api/v1/courses/{course['id']}/review",
        headers=admin,
        json={"decision": "approve"},
    )
    assert review_again.status_code == 409

    unenrolled = await client.get(f"/api/v1/courses/{course['id']}", headers=student)
    assert unenrolled.status_code == 403

    teacher_list = await client.get("/api/v1/courses", headers=teacher)
    assert teacher_list.status_code == 200
    assert [item["id"] for item in teacher_list.json()["data"]["items"]] == [course["id"]]

    admin_list = await client.get("/api/v1/courses?status=approved&keyword=机器学习", headers=admin)
    assert admin_list.status_code == 200
    assert admin_list.json()["data"]["total"] == 1

    student_list = await client.get("/api/v1/courses", headers=student)
    assert student_list.status_code == 200
    assert student_list.json()["data"]["items"] == []


async def test_chapter_and_knowledge_crud_and_cascade(client, seeded):
    teacher = await auth_headers(client, "teacher", seeded["password"])
    admin = await auth_headers(client, "admin", seeded["password"])
    second_teacher = await create_second_teacher(client, admin, username="teacher3")

    created = await create_course(client, teacher, title="数据结构")
    course_id = created.json()["data"]["id"]

    chapter = await add_chapter(client, teacher, course_id, "线性表")
    chapter_id = chapter.json()["data"]["id"]

    forbidden = await add_chapter(client, second_teacher, course_id, "越权章节")
    assert forbidden.status_code == 403

    knowledge = await add_knowledge(client, teacher, course_id, chapter_id, "数组")
    knowledge_id = knowledge.json()["data"]["id"]

    invalid_difficulty = await client.post(
        f"/api/v1/courses/{course_id}/chapters/{chapter_id}/knowledges",
        headers=teacher,
        json={"name": "越界难度", "difficulty": 9},
    )
    assert invalid_difficulty.status_code == 422

    updated_knowledge = await client.put(
        f"/api/v1/courses/{course_id}/chapters/{chapter_id}/knowledges/{knowledge_id}",
        headers=teacher,
        json={"name": "动态数组", "difficulty": 4},
    )
    assert updated_knowledge.status_code == 200
    assert updated_knowledge.json()["data"]["name"] == "动态数组"
    assert updated_knowledge.json()["data"]["difficulty"] == 4

    listed = await client.get(
        f"/api/v1/courses/{course_id}/chapters/{chapter_id}/knowledges",
        headers=teacher,
    )
    assert listed.status_code == 200
    assert [item["name"] for item in listed.json()["data"]["items"]] == ["动态数组"]

    updated_chapter = await client.put(
        f"/api/v1/courses/{course_id}/chapters/{chapter_id}",
        headers=teacher,
        json={"title": "线性结构", "order_no": 5},
    )
    assert updated_chapter.status_code == 200
    assert updated_chapter.json()["data"]["title"] == "线性结构"

    deleted_knowledge = await client.delete(
        f"/api/v1/courses/{course_id}/chapters/{chapter_id}/knowledges/{knowledge_id}",
        headers=teacher,
    )
    assert deleted_knowledge.status_code == 200

    deleted_chapter = await client.delete(
        f"/api/v1/courses/{course_id}/chapters/{chapter_id}", headers=teacher
    )
    assert deleted_chapter.status_code == 200

    detail = await client.get(f"/api/v1/courses/{course_id}", headers=teacher)
    assert detail.json()["data"]["chapters"] == []
    assert detail.json()["data"]["chapter_count"] == 0

    missing = await client.delete(f"/api/v1/courses/{course_id}/chapters/99999", headers=teacher)
    assert missing.status_code == 404

    # Published courses remain editable so teachers can keep content current.
    chapter_again = await add_chapter(client, teacher, course_id, "链表")
    await client.post(f"/api/v1/courses/{course_id}/submit", headers=teacher)
    await client.post(
        f"/api/v1/courses/{course_id}/review",
        headers=admin,
        json={"decision": "approve"},
    )
    chapter_again_id = chapter_again.json()["data"]["id"]
    edited_after_publish = await client.put(
        f"/api/v1/courses/{course_id}/chapters/{chapter_again_id}",
        headers=teacher,
        json={"title": "已发布后修改"},
    )
    assert edited_after_publish.status_code == 200
    assert edited_after_publish.json()["data"]["title"] == "已发布后修改"

    knowledge_after_publish = await add_knowledge(
        client, teacher, course_id, chapter_again_id, "链表节点"
    )
    assert knowledge_after_publish.status_code == 201

    course_after_publish = await client.put(
        f"/api/v1/courses/{course_id}",
        headers=teacher,
        json={"description": "发布后补充课程简介"},
    )
    assert course_after_publish.status_code == 200

    resubmit_approved = await client.post(f"/api/v1/courses/{course_id}/submit", headers=teacher)
    assert resubmit_approved.status_code == 409


async def test_invite_join_roster_and_removal(client, seeded):
    teacher = await auth_headers(client, "teacher", seeded["password"])
    admin = await auth_headers(client, "admin", seeded["password"])
    student = await auth_headers(client, "student", seeded["password"])
    course = await build_approved_course(client, teacher, admin)

    other_course = await create_course(client, teacher, title="另一门课程")
    assert other_course.status_code == 201
    assert other_course.json()["data"]["invite_code"] != course["invite_code"]

    invalid_code = await client.post(
        "/api/v1/courses/join",
        headers=student,
        json={"invite_code": "ZZZZZZZZ"},
    )
    assert invalid_code.status_code == 404

    joined = await client.post(
        "/api/v1/courses/join",
        headers=student,
        json={"invite_code": course["invite_code"].lower()},
    )
    assert joined.status_code == 200
    assert joined.json()["data"]["joined"] is True
    assert joined.json()["data"]["invite_code"] is None
    assert joined.json()["data"]["student_count"] == 1

    again = await client.post(
        "/api/v1/courses/join",
        headers=student,
        json={"invite_code": course["invite_code"]},
    )
    assert again.status_code == 200
    assert again.json()["data"]["joined"] is False
    assert again.json()["data"]["student_count"] == 1

    my_courses = await client.get("/api/v1/courses", headers=student)
    assert [item["id"] for item in my_courses.json()["data"]["items"]] == [course["id"]]
    assert my_courses.json()["data"]["items"][0]["invite_code"] is None

    detail = await client.get(f"/api/v1/courses/{course['id']}", headers=student)
    assert detail.status_code == 200
    assert detail.json()["data"]["invite_code"] is None

    roster = await client.get(f"/api/v1/courses/{course['id']}/students", headers=teacher)
    assert roster.status_code == 200
    assert roster.json()["data"]["total"] == 1
    assert roster.json()["data"]["items"][0]["username"] == "student"
    assert roster.json()["data"]["items"][0]["source"] == "invite_code"

    student_cannot_roster = await client.get(
        f"/api/v1/courses/{course['id']}/students", headers=student
    )
    assert student_cannot_roster.status_code == 403

    second_student = await register_student(client)
    disabled = await client.put(
        f"/api/v1/courses/{course['id']}/invite",
        headers=teacher,
        json={"enabled": False},
    )
    assert disabled.status_code == 200
    assert disabled.json()["data"]["invite_enabled"] is False

    blocked = await client.post(
        "/api/v1/courses/join",
        headers=second_student,
        json={"invite_code": course["invite_code"]},
    )
    assert blocked.status_code == 409

    enabled = await client.put(
        f"/api/v1/courses/{course['id']}/invite",
        headers=teacher,
        json={"enabled": True},
    )
    assert enabled.status_code == 200

    rotated = await client.post(f"/api/v1/courses/{course['id']}/invite/rotate", headers=teacher)
    assert rotated.status_code == 200
    new_code = rotated.json()["data"]["invite_code"]
    assert new_code != course["invite_code"]

    old_code = await client.post(
        "/api/v1/courses/join",
        headers=second_student,
        json={"invite_code": course["invite_code"]},
    )
    assert old_code.status_code == 404

    joined_second = await client.post(
        "/api/v1/courses/join",
        headers=second_student,
        json={"invite_code": new_code},
    )
    assert joined_second.status_code == 200
    assert joined_second.json()["data"]["student_count"] == 2

    removed = await client.delete(
        f"/api/v1/courses/{course['id']}/students/{seeded['users']['student']['id']}",
        headers=teacher,
    )
    assert removed.status_code == 200

    removed_access = await client.get(f"/api/v1/courses/{course['id']}", headers=student)
    assert removed_access.status_code == 403
    removed_list = await client.get("/api/v1/courses", headers=student)
    assert removed_list.json()["data"]["items"] == []


async def test_teacher_adds_and_removes_students_by_username(client, seeded):
    teacher = await auth_headers(client, "teacher", seeded["password"])
    admin = await auth_headers(client, "admin", seeded["password"])
    course = await build_approved_course(client, teacher, admin)

    added = await client.post(
        f"/api/v1/courses/{course['id']}/students",
        headers=teacher,
        json={"username": "STUDENT"},
    )
    assert added.status_code == 201
    assert added.json()["data"]["username"] == "student"
    assert added.json()["data"]["source"] == "teacher_add"
    assert added.json()["data"]["created"] is True

    duplicate = await client.post(
        f"/api/v1/courses/{course['id']}/students",
        headers=teacher,
        json={"username": "student"},
    )
    assert duplicate.status_code == 201
    assert duplicate.json()["data"]["created"] is False

    non_student = await client.post(
        f"/api/v1/courses/{course['id']}/students",
        headers=teacher,
        json={"username": "teacher"},
    )
    assert non_student.status_code == 422

    unknown = await client.post(
        f"/api/v1/courses/{course['id']}/students",
        headers=teacher,
        json={"username": "nobody"},
    )
    assert unknown.status_code == 404

    removed = await client.delete(
        f"/api/v1/courses/{course['id']}/students/{seeded['users']['student']['id']}",
        headers=teacher,
    )
    assert removed.status_code == 200

    removed_again = await client.delete(
        f"/api/v1/courses/{course['id']}/students/{seeded['users']['student']['id']}",
        headers=teacher,
    )
    assert removed_again.status_code == 404


async def test_enrollment_requires_approved_course(client, seeded):
    teacher = await auth_headers(client, "teacher", seeded["password"])
    student = await auth_headers(client, "student", seeded["password"])

    created = await create_course(client, teacher, title="待审核课程")
    course = created.json()["data"]

    not_approved = await client.post(
        "/api/v1/courses/join",
        headers=student,
        json={"invite_code": course["invite_code"]},
    )
    assert not_approved.status_code == 409

    add_before_approval = await client.post(
        f"/api/v1/courses/{course['id']}/students",
        headers=teacher,
        json={"username": "student"},
    )
    assert add_before_approval.status_code == 409


async def test_course_permission_guards_and_audit_trail(client, seeded):
    teacher = await auth_headers(client, "teacher", seeded["password"])
    admin = await auth_headers(client, "admin", seeded["password"])
    student = await auth_headers(client, "student", seeded["password"])

    anonymous = await client.get("/api/v1/courses")
    assert anonymous.status_code == 401

    join_as_teacher = await client.post(
        "/api/v1/courses/join",
        headers=teacher,
        json={"invite_code": "ABCDEFGH"},
    )
    assert join_as_teacher.status_code == 403

    created = await create_course(client, teacher, title="审计课程")
    course_id = created.json()["data"]["id"]
    teacher_review = await client.post(
        f"/api/v1/courses/{course_id}/review",
        headers=teacher,
        json={"decision": "approve"},
    )
    assert teacher_review.status_code == 403

    student_create = await create_course(client, student, title="学生课程")
    assert student_create.status_code == 403

    await client.post(f"/api/v1/courses/{course_id}/submit", headers=teacher)
    await client.post(
        f"/api/v1/courses/{course_id}/review",
        headers=admin,
        json={"decision": "approve"},
    )

    logs = await client.get("/api/v1/admin/audit-logs?page_size=100", headers=admin)
    actions = {item["action"] for item in logs.json()["data"]["items"]}
    assert {"course.create", "course.submit", "course.approve"} <= actions

    filtered = await client.get("/api/v1/admin/audit-logs?action=course.approve", headers=admin)
    assert filtered.json()["data"]["total"] == 1
