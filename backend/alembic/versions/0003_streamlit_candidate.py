"""streamlit candidate evidence
Revision ID: 0003_streamlit_candidate
Revises: 0002_saas_product
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_streamlit_candidate"
down_revision = "0002_saas_product"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("applications", sa.Column("candidate_json", sa.JSON(), nullable=True))

def downgrade():
    op.drop_column("applications", "candidate_json")
