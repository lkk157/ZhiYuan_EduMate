"""Canonical RBAC catalogue shared by seeding, tests and future admin APIs."""

from __future__ import annotations

from app.db.models.rbac import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER

PERMISSION_CATALOG: dict[str, tuple[str, str]] = {
    "user:manage": ("用户管理", "创建、编辑、禁用用户与分配角色"),
    "role:manage": ("角色权限管理", "维护角色与权限映射"),
    "course:review": ("课程审核", "审核教师提交的课程"),
    "material:review": ("资料审核", "审核课程资料并触发索引"),
    "audit:view": ("审计日志查看", "查看系统关键操作日志"),
    "course:create": ("课程创建", "创建与编辑自己的课程"),
    "material:upload": ("资料上传", "上传课程资料"),
    "qa:ask": ("AI 问答", "使用课程知识库进行带引用问答"),
    "analytics:view": ("学情分析", "查看课程学情看板"),
    "system:config": ("系统配置", "修改系统运行配置"),
    "exercise:manage": ("习题管理", "维护课程题库"),
    "exercise:answer": ("习题作答", "提交习题答案"),
}

ROLE_PERMISSIONS: dict[str, list[str]] = {
    ROLE_ADMIN: list(PERMISSION_CATALOG),
    ROLE_TEACHER: [
        "course:create",
        "material:upload",
        "qa:ask",
        "analytics:view",
        "exercise:manage",
    ],
    ROLE_STUDENT: ["qa:ask", "exercise:answer"],
}

ROLE_DESCRIPTIONS: dict[str, str] = {
    ROLE_ADMIN: "系统管理员，拥有全部治理权限",
    ROLE_TEACHER: "教师，负责课程、资料与学情",
    ROLE_STUDENT: "学生，进行学习、问答与练习",
}

DEMO_USERS: list[tuple[str, str, str]] = [
    ("admin", "admin@edumate.local", ROLE_ADMIN),
    ("teacher", "teacher@edumate.local", ROLE_TEACHER),
    ("student", "student@edumate.local", ROLE_STUDENT),
]
