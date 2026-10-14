"""cam_geometry"""

from alembic import op
import sqlalchemy as sa

revision = "702ca790f4df"
down_revision = "a92465298fed"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "cam_projects",
        sa.Column("geometry_file_id", sa.String(length=36), nullable=True),
    )
    op.create_foreign_key(
        None, "cam_projects", "platform_files", ["geometry_file_id"], ["id"]
    )


def downgrade():
    op.drop_constraint(None, "cam_projects", type_="foreignkey")
    op.drop_column("cam_projects", "geometry_file_id")
