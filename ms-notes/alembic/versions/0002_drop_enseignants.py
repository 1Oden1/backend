"""Suppression de la table enseignants — remplacée par ms-calendar comme source unique.

Revision ID: 0002_drop_enseignants
Revises: 0001_initial_notes
Create Date: 2026-03-31
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0002_drop_enseignants"
down_revision: Union[str, None] = "0001_initial_notes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    return inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    if _table_exists("enseignants"):
        op.drop_index("idx_enseignant_dept", table_name="enseignants")
        op.drop_table("enseignants")


def downgrade() -> None:
    """Recrée la table si besoin de rollback."""
    if not _table_exists("enseignants"):
        op.create_table(
            "enseignants",
            sa.Column("id",                      sa.Integer(),     nullable=False, autoincrement=True),
            sa.Column("user_id",                 sa.String(100),   nullable=False),
            sa.Column("prenom",                  sa.String(100),   nullable=False),
            sa.Column("nom",                     sa.String(100),   nullable=False),
            sa.Column("calendar_departement_id", sa.Integer(),     nullable=False),
            sa.Column("created_at",              sa.DateTime(),    nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", name="uq_enseignant_user_id"),
        )
        op.create_index("idx_enseignant_dept", "enseignants", ["calendar_departement_id"])
