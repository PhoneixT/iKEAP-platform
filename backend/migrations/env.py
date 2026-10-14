from alembic import context
from app.infrastructure.database import Base, engine
import app.infrastructure.models  # noqa: F401

if context.is_offline_mode():
    from app.core.config import DATABASE_URL

    context.configure(
        url=DATABASE_URL,
        target_metadata=Base.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    with engine.connect() as connection:
        context.configure(
            connection=connection, target_metadata=Base.metadata, compare_type=True
        )
        with context.begin_transaction():
            context.run_migrations()
