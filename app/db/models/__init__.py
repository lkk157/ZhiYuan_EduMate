"""SQLAlchemy models.

Import every model module here so Alembic and ``Base.metadata.create_all`` see
all tables.
"""

from app.db.models.audit import AuditLog
from app.db.models.course import Chapter, Course, CourseEnrollment, Knowledge
from app.db.models.rbac import Permission, Role, User, role_permissions

__all__ = [
    "AuditLog",
    "Chapter",
    "Course",
    "CourseEnrollment",
    "Knowledge",
    "Permission",
    "Role",
    "User",
    "role_permissions",
]
