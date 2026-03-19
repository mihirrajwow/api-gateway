"""Initial migration - create users, api_keys, request_logs tables

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # api_keys
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("key", sa.String(64), nullable=False, unique=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False, server_default="Default Key"),
        sa.Column("rate_limit", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("rate_limit_window", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_api_keys_key", "api_keys", ["key"])
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])

    # request_logs
    op.create_table(
        "request_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("api_key_id", sa.String(36), sa.ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False),
        sa.Column("endpoint", sa.String(255), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_request_logs_user_id", "request_logs", ["user_id"])
    op.create_index("ix_request_logs_endpoint", "request_logs", ["endpoint"])
    op.create_index("ix_request_logs_status_code", "request_logs", ["status_code"])
    op.create_index("ix_request_logs_timestamp", "request_logs", ["timestamp"])


def downgrade() -> None:
    op.drop_table("request_logs")
    op.drop_table("api_keys")
    op.drop_table("users")
