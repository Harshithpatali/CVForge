"""Align the production database with the current ORM models.

Revision ID: 0004_schema_alignment
Revises: 0003_streamlit_candidate
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_schema_alignment"
down_revision = "0003_streamlit_candidate"
branch_labels = None
depends_on = None


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade():
    # 0003_streamlit_candidate already creates applications.candidate_json.
    # This migration only aligns resume_artifacts with the current ORM.
    if "updated_at" not in _column_names("resume_artifacts"):
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
    if "updated_at" in _column_names("resume_artifacts"):
        op.drop_column("resume_artifacts", "updated_at")
