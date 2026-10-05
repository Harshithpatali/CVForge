"""initial cvforge schema"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("generation_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("status", sa.String(40), nullable=False, server_default="created"),
        sa.Column("job_title", sa.String(255)),
        sa.Column("role_family", sa.String(80)),
        sa.Column("candidate_json", sa.JSON()),
        sa.Column("jd_json", sa.JSON()),
        sa.Column("questions_json", sa.JSON()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_generation_jobs_role_family", "generation_jobs", ["role_family"])
    op.create_table("resume_artifacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("generation_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_json", sa.JSON(), nullable=False),
        sa.Column("ats_json", sa.JSON(), nullable=False),
        sa.Column("prompt_key", sa.String(255), nullable=False),
        sa.Column("docx_path", sa.Text()),
        sa.Column("pdf_path", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_resume_artifacts_job_id", "resume_artifacts", ["job_id"])

def downgrade():
    op.drop_index("ix_resume_artifacts_job_id", table_name="resume_artifacts")
    op.drop_table("resume_artifacts")
    op.drop_index("ix_generation_jobs_role_family", table_name="generation_jobs")
    op.drop_table("generation_jobs")
