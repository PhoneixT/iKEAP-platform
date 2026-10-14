USE ikeap_platform;
SET NAMES utf8mb4;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> bf75f8ecfced

CREATE TABLE agents (
    name VARCHAR(120) NOT NULL,
    description TEXT NOT NULL,
    capabilities JSON NOT NULL,
    protocol VARCHAR(30) NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    version VARCHAR(30) NOT NULL,
    id VARCHAR(36) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE kg_documents (
    title VARCHAR(160) NOT NULL,
    content TEXT NOT NULL,
    source VARCHAR(255) NOT NULL,
    entity_ids JSON NOT NULL,
    version INTEGER NOT NULL,
    id VARCHAR(36) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE kg_entities (
    name VARCHAR(120) NOT NULL,
    kind VARCHAR(60) NOT NULL,
    aliases JSON NOT NULL,
    properties JSON NOT NULL,
    description TEXT NOT NULL,
    source VARCHAR(255) NOT NULL,
    id VARCHAR(36) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_entity_name_kind UNIQUE (name, kind)
);

CREATE INDEX ix_kg_entities_name ON kg_entities (name);

CREATE TABLE phm_machines (
    name VARCHAR(120) NOT NULL,
    code VARCHAR(60) NOT NULL,
    component VARCHAR(80) NOT NULL,
    thresholds JSON NOT NULL,
    telemetry JSON NOT NULL,
    id VARCHAR(36) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (code)
);

CREATE TABLE platform_resources (
    name VARCHAR(120) NOT NULL,
    kind VARCHAR(40) NOT NULL,
    status VARCHAR(30) NOT NULL,
    capabilities JSON NOT NULL,
    description TEXT NOT NULL,
    id VARCHAR(36) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE reasoning_runs (
    title VARCHAR(160) NOT NULL,
    task TEXT NOT NULL,
    domain VARCHAR(30) NOT NULL,
    mode VARCHAR(30) NOT NULL,
    evidence JSON NOT NULL,
    candidates JSON NOT NULL,
    service_metadata JSON NOT NULL,
    id VARCHAR(36) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE sys_audit_logs (
    actor VARCHAR(80) NOT NULL,
    action VARCHAR(120) NOT NULL,
    target VARCHAR(120) NOT NULL,
    detail JSON NOT NULL,
    id VARCHAR(36) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE sys_users (
    username VARCHAR(80) NOT NULL,
    display_name VARCHAR(120) NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    `role` VARCHAR(20) NOT NULL,
    active BOOL NOT NULL,
    id VARCHAR(36) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (username)
);

CREATE TABLE validation_reports (
    name VARCHAR(160) NOT NULL,
    scope VARCHAR(30) NOT NULL,
    status VARCHAR(30) NOT NULL,
    input_data JSON NOT NULL,
    findings JSON NOT NULL,
    id VARCHAR(36) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE validation_rules (
    name VARCHAR(120) NOT NULL,
    scope VARCHAR(30) NOT NULL,
    field VARCHAR(80) NOT NULL,
    operator VARCHAR(20) NOT NULL,
    expected JSON NOT NULL,
    unit VARCHAR(30) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    enabled BOOL NOT NULL,
    version INTEGER NOT NULL,
    id VARCHAR(36) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE workflows (
    name VARCHAR(120) NOT NULL,
    description TEXT NOT NULL,
    nodes JSON NOT NULL,
    version INTEGER NOT NULL,
    id VARCHAR(36) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE cam_projects (
    name VARCHAR(160) NOT NULL,
    material VARCHAR(80) NOT NULL,
    description TEXT NOT NULL,
    resource_id VARCHAR(36),
    parameters JSON NOT NULL,
    plan JSON NOT NULL,
    status VARCHAR(30) NOT NULL,
    execution JSON NOT NULL,
    id VARCHAR(36) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(resource_id) REFERENCES platform_resources (id)
);

CREATE TABLE kg_relations (
    source_id VARCHAR(36) NOT NULL,
    target_id VARCHAR(36) NOT NULL,
    kind VARCHAR(60) NOT NULL,
    properties JSON NOT NULL,
    source VARCHAR(255) NOT NULL,
    id VARCHAR(36) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(source_id) REFERENCES kg_entities (id) ON DELETE CASCADE,
    FOREIGN KEY(target_id) REFERENCES kg_entities (id) ON DELETE CASCADE
);

CREATE INDEX ix_kg_relations_source_id ON kg_relations (source_id);

CREATE INDEX ix_kg_relations_target_id ON kg_relations (target_id);

CREATE TABLE phm_anomalies (
    machine_id VARCHAR(36) NOT NULL,
    title VARCHAR(160) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    status VARCHAR(30) NOT NULL,
    measurements JSON NOT NULL,
    diagnosis JSON NOT NULL,
    id VARCHAR(36) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(machine_id) REFERENCES phm_machines (id)
);

CREATE INDEX ix_phm_anomalies_machine_id ON phm_anomalies (machine_id);

CREATE TABLE platform_jobs (
    name VARCHAR(160) NOT NULL,
    module VARCHAR(40) NOT NULL,
    status VARCHAR(30) NOT NULL,
    owner_id VARCHAR(36) NOT NULL,
    input_data JSON NOT NULL,
    result JSON NOT NULL,
    error TEXT NOT NULL,
    progress INTEGER NOT NULL,
    idempotency_key VARCHAR(160),
    id VARCHAR(36) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(owner_id) REFERENCES sys_users (id),
    UNIQUE (idempotency_key)
);

CREATE INDEX ix_platform_jobs_status ON platform_jobs (status);

CREATE TABLE phm_maintenance_orders (
    anomaly_id VARCHAR(36) NOT NULL,
    title VARCHAR(160) NOT NULL,
    assignee VARCHAR(80) NOT NULL,
    status VARCHAR(30) NOT NULL,
    actions JSON NOT NULL,
    feedback TEXT NOT NULL,
    id VARCHAR(36) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(anomaly_id) REFERENCES phm_anomalies (id)
);

CREATE TABLE platform_job_events (
    job_id VARCHAR(36) NOT NULL,
    sequence INTEGER NOT NULL,
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    payload JSON NOT NULL,
    id VARCHAR(36) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(job_id) REFERENCES platform_jobs (id) ON DELETE CASCADE
);

CREATE INDEX ix_platform_job_events_job_id ON platform_job_events (job_id);

INSERT INTO alembic_version (version_num) VALUES ('bf75f8ecfced');

-- Running upgrade bf75f8ecfced -> a92465298fed

CREATE TABLE platform_files (
    name VARCHAR(255) NOT NULL,
    storage_key VARCHAR(80) NOT NULL,
    content_type VARCHAR(120) NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    size INTEGER NOT NULL,
    owner_id VARCHAR(36) NOT NULL,
    id VARCHAR(36) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(owner_id) REFERENCES sys_users (id),
    UNIQUE (storage_key)
);

UPDATE alembic_version SET version_num='a92465298fed' WHERE alembic_version.version_num = 'bf75f8ecfced';

-- Running upgrade a92465298fed -> 702ca790f4df

ALTER TABLE cam_projects ADD COLUMN geometry_file_id VARCHAR(36);

ALTER TABLE cam_projects ADD FOREIGN KEY(geometry_file_id) REFERENCES platform_files (id);

UPDATE alembic_version SET version_num='702ca790f4df' WHERE alembic_version.version_num = 'a92465298fed';
