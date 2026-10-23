"""SQLAlchemy models.

Import every model module here so Alembic and ``Base.metadata.create_all`` see
all tables.
"""

from app.db.models.audit import AuditLog
from app.db.models.course import Chapter, Course, CourseEnrollment, Knowledge
from app.db.models.knowledge_base import KnowledgeBase
from app.db.models.material import Material, MaterialView
from app.db.models.qa import QARecord
from app.db.models.rbac import Permission, Role, User, role_permissions

__all__ = [
    "AuditLog",
    "Chapter",
    "Course",
    "CourseEnrollment",
    "Knowledge",
    "KnowledgeBase",
    "Material",
    "MaterialView",
    "Permission",
    "QARecord",
    "Role",
    "User",
    "role_permissions",
]
