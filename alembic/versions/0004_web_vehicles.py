"""web vehicles

Revision ID: 0004_web_vehicles
Revises: 0003_mcp_seed_admin
Create Date: 2026-09-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_web_vehicles"
down_revision: Union[str, None] = "0003_mcp_seed_admin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ALL_ACTIONS = ("read", "list", "create", "edit", "delete")


def upgrade() -> None:
    op.create_table(
        "web_vehicles",
        sa.Column("uid", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("brand", sa.String(length=120), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("odometer", sa.Integer(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("sale_status", sa.String(length=32), nullable=False),
        sa.Column("motor_type", sa.String(length=120), nullable=False),
        sa.Column("drive_type", sa.String(length=32), nullable=False),
        sa.Column("fuel_type", sa.String(length=32), nullable=False),
        sa.Column("first_registration_date", sa.Date(), nullable=False),
        sa.Column("images", sa.JSON(), nullable=False),
        sa.Column("rebu", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("uid"),
    )
    op.create_index(op.f("ix_web_vehicles_slug"), "web_vehicles", ["slug"], unique=True)
    op.create_index(op.f("ix_web_vehicles_uuid"), "web_vehicles", ["uuid"], unique=True)

    roles = sa.table(
        "roles",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
    )
    perms = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Integer),
        sa.column("scope", sa.String),
        sa.column("action", sa.String),
    )

    bind = op.get_bind()
    admin_role_id = bind.execute(
        sa.select(roles.c.id).where(roles.c.name == "administrator")
    ).scalar_one_or_none()
    if admin_role_id is not None:
        existing = {
            (row[0], row[1])
            for row in bind.execute(
                sa.select(perms.c.scope, perms.c.action).where(perms.c.role_id == admin_role_id)
            )
        }
        inserts = [
            {"role_id": admin_role_id, "scope": "web_vehicles", "action": action}
            for action in ALL_ACTIONS
            if ("web_vehicles", action) not in existing
        ]
        if inserts:
            op.bulk_insert(perms, inserts)


def downgrade() -> None:
    bind = op.get_bind()
    admin_role_id = bind.execute(
        sa.text("SELECT id FROM roles WHERE name = 'administrator'")
    ).scalar_one_or_none()
    if admin_role_id is not None:
        bind.execute(
            sa.text(
                "DELETE FROM role_permissions WHERE role_id = :role_id AND scope = 'web_vehicles'"
            ),
            {"role_id": admin_role_id},
        )

    op.drop_index(op.f("ix_web_vehicles_uuid"), table_name="web_vehicles")
    op.drop_index(op.f("ix_web_vehicles_slug"), table_name="web_vehicles")
    op.drop_table("web_vehicles")
