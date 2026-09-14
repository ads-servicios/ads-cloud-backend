"""must_change_password + seed first admin

Revision ID: 0003_mcp_seed_admin
Revises: 0002_role_scopes
Create Date: 2026-09-04
"""

from typing import Sequence, Union

import bcrypt
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0003_mcp_seed_admin"
down_revision: Union[str, None] = "0002_role_scopes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEED_EMAIL = "ads.serviciosintegrales@gmail.com"
SEED_PASSWORD = "admin123456"


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = {col["name"] for col in inspector.get_columns("users")}
    if "must_change_password" not in columns:
        op.add_column(
            "users",
            sa.Column("must_change_password", sa.Boolean(), server_default="false", nullable=False),
        )

    existing = conn.execute(
        sa.text("SELECT id FROM users WHERE email = :email"),
        {"email": SEED_EMAIL},
    ).fetchone()
    if existing is not None:
        return

    role_row = conn.execute(
        sa.text("SELECT id FROM roles WHERE name = 'administrator'")
    ).fetchone()
    if role_row is None:
        raise RuntimeError("administrator role missing; run 0002_role_scopes first")

    hashed = bcrypt.hashpw(SEED_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    conn.execute(
        sa.text(
            """
            INSERT INTO users (email, hashed_password, role_id, is_active, must_change_password)
            VALUES (:email, :hashed_password, :role_id, true, true)
            """
        ),
        {
            "email": SEED_EMAIL,
            "hashed_password": hashed,
            "role_id": role_row[0],
        },
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM users WHERE email = :email"),
        {"email": SEED_EMAIL},
    )
    inspector = inspect(conn)
    columns = {col["name"] for col in inspector.get_columns("users")}
    if "must_change_password" in columns:
        op.drop_column("users", "must_change_password")
