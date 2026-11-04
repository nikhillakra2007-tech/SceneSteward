"""Alembic environment — uses the same settings as the app (env-driven)."""
from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

# ALEMBIC_DATABASE_URL may point alembic at a scratch/CI database without a .env.
if os.environ.get("ALEMBIC_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["ALEMBIC_DATABASE_URL"]

from app.core.config import get_settings
from app.models import Base

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

# Alembic connects as a schema owner/migration role — never as the runtime role.
_migrate_url = (
    os.environ.get("ALEMBIC_DATABASE_URL")
    or os.environ.get("MIGRATION_DATABASE_URL")
    or get_settings().migration_database_url
    or os.environ.get("DATABASE_URL")
    or get_settings().database_url
)
config.set_main_option("sqlalchemy.url", _migrate_url)

settings = get_settings()
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=config.get_main_option("sqlalchemy.url"),
                      target_metadata=target_metadata, literal_binds=True,
                      dialect_opts={"paramstyle": "named"},
                      compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section) or {}
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata,
                          compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
