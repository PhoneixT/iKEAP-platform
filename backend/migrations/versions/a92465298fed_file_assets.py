"""file_assets"""

from alembic import op
import sqlalchemy as sa

revision = "a92465298fed"
down_revision = "bf75f8ecfced"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "platform_files",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=80), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["sys_users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )


def downgrade():
    op.drop_table("platform_files")
