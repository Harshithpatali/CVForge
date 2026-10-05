"""Align the production database with the current ORM models.

Revision ID: 0003_schema_alignment
Revises: 0002_saas_product
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_schema_alignment"
down_revision = "0002_saas_product"
branch_labels = None
depends_on = None


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade():
    # Some deployments may already contain candidate_json from an earlier
    # schema revision. Make this migration safe for both cases.
    if "candidate_json" not in _column_names("applications"):
        op.add_column(
            "applications",
            sa.Column("candidate_json", sa.JSON(), nullable=True),
        )

    # The current ResumeArtifact ORM includes updated_at, but 0001/0002 did
    # not create it. Add it in a backfillable form for existing rows.
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

    if "candidate_json" in _column_names("applications"):
        op.drop_column("applications", "candidate_json")
