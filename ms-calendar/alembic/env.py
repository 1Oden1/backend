"""
Alembic env.py — ms-calendar

Utilise la DATABASE_URL de app/config.py (variables d'environnement).
Mode online uniquement : les migrations sont appliquées directement sur la base.
"""

import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Ajoute la racine du projet au path pour pouvoir importer app.*
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import settings
from app.models import Base   # Importe tous les modèles via Base

# Alembic Config object
config = context.config

# Injecte la vraie DATABASE_URL depuis les settings (variables d'env)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Configure le logging si un fichier ini est présent
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Métadonnées cibles pour l'autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Mode offline : génère le SQL sans connexion."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Mode online : connexion directe à la base."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Compare les types de colonnes pour détecter les changements
            compare_type=True,
            # Compare les valeurs par défaut côté serveur
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
