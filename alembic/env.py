from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from backend.database import Base
from backend.models.dataset import Dataset  # noqa: F401
from backend.models.example import Example  # noqa: F401
from backend.models.score import Score  # noqa: F401
from backend.models.bucket import Bucket  # noqa: F401
from backend.models.review import Review  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        # Use synchronous URL for Alembic
    )
    # Replace async URL with sync for Alembic
    url = config.get_main_option("sqlalchemy.url")
    if url:
        url = url.replace("sqlite+aiosqlite", "sqlite")
        connectable = engine_from_config(
            {"sqlalchemy.url": url},
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
