"""initial_schema"""

from alembic import op
import sqlalchemy as sa

revision = "bf75f8ecfced"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "agents",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("protocol", sa.String(length=30), nullable=False),
        sa.Column("endpoint", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=30), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "kg_documents",
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("entity_ids", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "kg_entities",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("kind", sa.String(length=60), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=False),
        sa.Column("properties", sa.JSON(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "kind", name="uq_entity_name_kind"),
    )
    op.create_index(op.f("ix_kg_entities_name"), "kg_entities", ["name"], unique=False)
    op.create_table(
        "phm_machines",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=60), nullable=False),
        sa.Column("component", sa.String(length=80), nullable=False),
        sa.Column("thresholds", sa.JSON(), nullable=False),
        sa.Column("telemetry", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "platform_resources",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "reasoning_runs",
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("task", sa.Text(), nullable=False),
        sa.Column("domain", sa.String(length=30), nullable=False),
        sa.Column("mode", sa.String(length=30), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("candidates", sa.JSON(), nullable=False),
        sa.Column("service_metadata", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "sys_audit_logs",
        sa.Column("actor", sa.String(length=80), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("target", sa.String(length=120), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "sys_users",
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=256), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_table(
        "validation_reports",
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("scope", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("input_data", sa.JSON(), nullable=False),
        sa.Column("findings", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "validation_rules",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("scope", sa.String(length=30), nullable=False),
        sa.Column("field", sa.String(length=80), nullable=False),
        sa.Column("operator", sa.String(length=20), nullable=False),
        sa.Column("expected", sa.JSON(), nullable=False),
        sa.Column("unit", sa.String(length=30), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "workflows",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("nodes", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "cam_projects",
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("material", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("resource_id", sa.String(length=36), nullable=True),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("plan", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("execution", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["resource_id"],
            ["platform_resources.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "kg_relations",
        sa.Column("source_id", sa.String(length=36), nullable=False),
        sa.Column("target_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=60), nullable=False),
        sa.Column("properties", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["kg_entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["kg_entities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_kg_relations_source_id"), "kg_relations", ["source_id"], unique=False
    )
    op.create_index(
        op.f("ix_kg_relations_target_id"), "kg_relations", ["target_id"], unique=False
    )
    op.create_table(
        "phm_anomalies",
        sa.Column("machine_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("measurements", sa.JSON(), nullable=False),
        sa.Column("diagnosis", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["machine_id"],
            ["phm_machines.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_phm_anomalies_machine_id"),
        "phm_anomalies",
        ["machine_id"],
        unique=False,
    )
    op.create_table(
        "platform_jobs",
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("module", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("input_data", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["sys_users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index(
        op.f("ix_platform_jobs_status"), "platform_jobs", ["status"], unique=False
    )
    op.create_table(
        "phm_maintenance_orders",
        sa.Column("anomaly_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("assignee", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("actions", sa.JSON(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["anomaly_id"],
            ["phm_anomalies.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "platform_job_events",
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["platform_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_platform_job_events_job_id"),
        "platform_job_events",
        ["job_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f("ix_platform_job_events_job_id"), table_name="platform_job_events"
    )
    op.drop_table("platform_job_events")
    op.drop_table("phm_maintenance_orders")
    op.drop_index(op.f("ix_platform_jobs_status"), table_name="platform_jobs")
    op.drop_table("platform_jobs")
    op.drop_index(op.f("ix_phm_anomalies_machine_id"), table_name="phm_anomalies")
    op.drop_table("phm_anomalies")
    op.drop_index(op.f("ix_kg_relations_target_id"), table_name="kg_relations")
    op.drop_index(op.f("ix_kg_relations_source_id"), table_name="kg_relations")
    op.drop_table("kg_relations")
    op.drop_table("cam_projects")
    op.drop_table("workflows")
    op.drop_table("validation_rules")
    op.drop_table("validation_reports")
    op.drop_table("sys_users")
    op.drop_table("sys_audit_logs")
    op.drop_table("reasoning_runs")
    op.drop_table("platform_resources")
    op.drop_table("phm_machines")
    op.drop_index(op.f("ix_kg_entities_name"), table_name="kg_entities")
    op.drop_table("kg_entities")
    op.drop_table("kg_documents")
    op.drop_table("agents")
