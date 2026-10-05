"""Align resume_artifacts with the current ORM models.

Revision ID: 0004_schema_alignment
Revises: 0003_streamlit_candidate
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_schema_alignment"
down_revision = "0003_streamlit_candidate"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("resume_artifacts")}

    if "updated_at" not in columns:
        op.add_column(
            "resume_artifacts",
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )

    op.execute(
        """
        UPDATE resume_artifacts
        SET updated_at = created_at
        WHERE updated_at IS NULL
        """
    )

    op.alter_column(
        "resume_artifacts",
        "updated_at",
        existing_type=sa.DateTime(),
        nullable=False,
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("resume_artifacts")}

    if "updated_at" in columns:
        op.drop_column("resume_artifacts", "updated_at")
