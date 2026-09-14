"""roles, role_permissions, users.role_id

Revision ID: 0002_role_scopes
Revises: 0001_create_users
Create Date: 2026-09-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_role_scopes"
down_revision: Union[str, None] = "0001_create_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ALL_ACTIONS = ("read", "list", "create", "edit", "delete")


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_roles_name"), "roles", ["name"], unique=True)

    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role_id", "scope", "action", name="uq_role_scope_action"),
    )
    op.create_index(op.f("ix_role_permissions_role_id"), "role_permissions", ["role_id"], unique=False)

    roles = sa.table(
        "roles",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("description", sa.String),
    )
    perms = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Integer),
        sa.column("scope", sa.String),
        sa.column("action", sa.String),
    )

    op.bulk_insert(
        roles,
        [
            {"id": 1, "name": "administrator", "description": "Full control"},
            {"id": 2, "name": "common", "description": "Read-limited user"},
        ],
    )

    admin_perms = [{"role_id": 1, "scope": "users", "action": a} for a in ALL_ACTIONS]
    admin_perms += [{"role_id": 1, "scope": "roles", "action": a} for a in ALL_ACTIONS]
    common_perms = [{"role_id": 2, "scope": "users", "action": "read"}]
    op.bulk_insert(perms, admin_perms + common_perms)

    op.add_column("users", sa.Column("role_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_users_role_id"), "users", ["role_id"], unique=False)
    op.create_foreign_key("fk_users_role_id_roles", "users", "roles", ["role_id"], ["id"])

    op.execute(
        sa.text(
            """
            UPDATE users
            SET role_id = CASE
                WHEN role::text = 'administrator' THEN 1
                ELSE 2
            END
            """
        )
    )
    op.alter_column("users", "role_id", nullable=False)
    op.drop_column("users", "role")
    op.execute("DROP TYPE IF EXISTS user_role")


def downgrade() -> None:
    user_role = sa.Enum("administrator", "common", name="user_role")
    user_role.create(op.get_bind(), checkfirst=True)
    op.add_column("users", sa.Column("role", user_role, nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE users
            SET role = CASE
                WHEN role_id = 1 THEN 'administrator'::user_role
                ELSE 'common'::user_role
            END
            """
        )
    )
    op.alter_column("users", "role", nullable=False)
    op.drop_constraint("fk_users_role_id_roles", "users", type_="foreignkey")
    op.drop_index(op.f("ix_users_role_id"), table_name="users")
    op.drop_column("users", "role_id")
    op.drop_index(op.f("ix_role_permissions_role_id"), table_name="role_permissions")
    op.drop_table("role_permissions")
    op.drop_index(op.f("ix_roles_name"), table_name="roles")
    op.drop_table("roles")
