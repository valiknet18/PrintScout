"""init

Revision ID: 0001
Revises:
Create Date: 2026-05-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tg_user_id", sa.BigInteger(), nullable=False),
        sa.Column("tg_username", sa.String(length=64)),
        sa.Column("first_name", sa.String(length=128)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("tg_user_id", name="uq_users_tg_user_id"),
    )
    op.create_index("ix_users_tg_user_id", "users", ["tg_user_id"])

    op.create_table(
        "printers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("build_x_mm", sa.Float(), nullable=False),
        sa.Column("build_y_mm", sa.Float(), nullable=False),
        sa.Column("build_z_mm", sa.Float(), nullable=False),
        sa.Column("nozzle_mm", sa.Float()),
        sa.Column("materials", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_printers_user_id", "printers", ["user_id"])

    op.create_table(
        "cached_models",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("thumbnail_url", sa.Text()),
        sa.Column("is_free", sa.Boolean(), nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("raw_meta", postgresql.JSONB(), nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("source", "source_id", name="uq_cached_model"),
    )
    op.create_index("ix_cached_models_source", "cached_models", ["source"])
    op.create_index("ix_cached_models_source_id", "cached_models", ["source_id"])

    op.create_table(
        "model_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "cached_model_id",
            sa.Integer(),
            sa.ForeignKey("cached_models.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_id", sa.String(length=128), nullable=False),
        sa.Column("file_url", sa.Text(), nullable=False),
        sa.Column("fmt", sa.String(length=8), nullable=False),
        sa.Column("bbox_x_mm", sa.Float()),
        sa.Column("bbox_y_mm", sa.Float()),
        sa.Column("bbox_z_mm", sa.Float()),
        sa.Column("parsed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("cached_model_id", "file_id", name="uq_model_file"),
    )
    op.create_index("ix_model_files_cached_model_id", "model_files", ["cached_model_id"])


def downgrade() -> None:
    op.drop_table("model_files")
    op.drop_table("cached_models")
    op.drop_table("printers")
    op.drop_table("users")
