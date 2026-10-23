"""SQLAlchemy models.

Import every model module here so Alembic and ``Base.metadata.create_all`` see
all tables.
"""

from app.db.models.rbac import Permission, Role, User, role_permissions

__all__ = ["Permission", "Role", "User", "role_permissions"]
