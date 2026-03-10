"""Migration — schéma complet ent_calendar (ms-calendar = source de vérité structure académique)

Revision ID: 0001_initial_calendar
Revises:
Create Date: 2025-01-01 00:00:00.000000

Tables :
  Structure académique : annees_universitaires, departements, filieres,
                         semestres, modules, elements_module
  Emploi du temps      : enseignants, salles, seances
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy import inspect
from alembic import op
from sqlalchemy.engine.reflection import Inspector

revision: str = "0001_initial_calendar"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    return inspect(op.get_bind()).has_table(name)

def _column_exists(table: str, column: str) -> bool:
    return any(c["name"] == column for c in inspect(op.get_bind()).get_columns(table))


def upgrade() -> None:

    # ── annees_universitaires ─────────────────────────────────────────────────
    if not _table_exists("annees_universitaires"):
        op.create_table(
            "annees_universitaires",
            sa.Column("id",    sa.Integer(),    autoincrement=True, nullable=False),
            sa.Column("label", sa.String(20),   nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("label"),
        )

    # ── departements ──────────────────────────────────────────────────────────
    if not _table_exists("departements"):
        op.create_table(
            "departements",
            sa.Column("id",  sa.Integer(),    autoincrement=True, nullable=False),
            sa.Column("nom", sa.String(150),  nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("nom"),
        )

    # ── filieres ──────────────────────────────────────────────────────────────
    if not _table_exists("filieres"):
        op.create_table(
            "filieres",
            sa.Column("id",             sa.Integer(),   autoincrement=True, nullable=False),
            sa.Column("nom",            sa.String(150), nullable=False),
            sa.Column("departement_id", sa.Integer(),   nullable=False),
            sa.ForeignKeyConstraint(["departement_id"], ["departements.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("nom", "departement_id", name="uq_filiere_dept"),
        )
        op.create_index("idx_filiere_dept", "filieres", ["departement_id"])

    # ── semestres ─────────────────────────────────────────────────────────────
    if not _table_exists("semestres"):
        op.create_table(
            "semestres",
            sa.Column("id",                sa.Integer(),  autoincrement=True, nullable=False),
            sa.Column("nom",               sa.String(20), nullable=False),
            sa.Column("annee_id",          sa.Integer(),  nullable=False),
            sa.Column("filiere_id",        sa.Integer(),  nullable=False),
            sa.Column("date_limite_depot", sa.Date(),     nullable=True),
            sa.ForeignKeyConstraint(["annee_id"],   ["annees_universitaires.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["filiere_id"], ["filieres.id"],              ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("nom", "annee_id", "filiere_id", name="uq_semestre"),
        )
        op.create_index("idx_semestre_filiere", "semestres", ["filiere_id"])
        op.create_index("idx_semestre_annee",   "semestres", ["annee_id"])
    else:
        # Migration depuis ancienne version sans annee_id
        if not _column_exists("semestres", "annee_id"):
            op.add_column("semestres", sa.Column("annee_id", sa.Integer(), nullable=True))
        if not _column_exists("semestres", "date_limite_depot"):
            op.add_column("semestres", sa.Column("date_limite_depot", sa.Date(), nullable=True))

    # ── modules ───────────────────────────────────────────────────────────────
    if not _table_exists("modules"):
        op.create_table(
            "modules",
            sa.Column("id",          sa.Integer(),    autoincrement=True, nullable=False),
            sa.Column("nom",         sa.String(150),  nullable=False),
            sa.Column("code",        sa.String(30),   nullable=False),
            sa.Column("credit",      sa.Integer(),    nullable=False, server_default="2"),
            sa.Column("semestre_id", sa.Integer(),    nullable=False),
            sa.ForeignKeyConstraint(["semestre_id"], ["semestres.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("code"),
        )
        op.create_index("idx_module_semestre", "modules", ["semestre_id"])
    else:
        if not _column_exists("modules", "code"):
            op.add_column("modules", sa.Column("code", sa.String(30), nullable=True))
        if not _column_exists("modules", "credit"):
            op.add_column("modules", sa.Column("credit", sa.Integer(), nullable=False, server_default="2"))

    # ── elements_module ───────────────────────────────────────────────────────
    if not _table_exists("elements_module"):
        op.create_table(
            "elements_module",
            sa.Column("id",          sa.Integer(),      autoincrement=True, nullable=False),
            sa.Column("nom",         sa.String(150),    nullable=False),
            sa.Column("code",        sa.String(30),     nullable=False),
            # BUG FIX #3 : coefficient était absent de la migration
            sa.Column("coefficient", sa.Numeric(4, 2),  nullable=False, server_default="1"),
            sa.Column("type",        sa.Enum("Cours", "TD", "TP"), nullable=False, server_default="Cours"),
            sa.Column("module_id",   sa.Integer(),      nullable=False),
            sa.ForeignKeyConstraint(["module_id"], ["modules.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("code", "module_id", name="uq_element_module"),
        )
        op.create_index("idx_element_module", "elements_module", ["module_id"])
    else:
        if not _column_exists("elements_module", "code"):
            op.add_column("elements_module", sa.Column("code", sa.String(30), nullable=True))
        # BUG FIX #3 : ajouter coefficient si la table existe déjà sans cette colonne
        if not _column_exists("elements_module", "coefficient"):
            op.add_column("elements_module", sa.Column("coefficient", sa.Numeric(4, 2), nullable=False, server_default="1"))

    # ── enseignants ───────────────────────────────────────────────────────────
    if not _table_exists("enseignants"):
        op.create_table(
            "enseignants",
            sa.Column("id",      sa.Integer(),    autoincrement=True, nullable=False),
            sa.Column("user_id", sa.String(36),   nullable=True),
            sa.Column("nom",     sa.String(100),  nullable=False),
            sa.Column("prenom",  sa.String(100),  nullable=False),
            sa.Column("email",   sa.String(200),  nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("email"),
            sa.UniqueConstraint("user_id"),
        )
    else:
        if not _column_exists("enseignants", "user_id"):
            op.add_column("enseignants", sa.Column("user_id", sa.String(36), nullable=True))
            op.create_unique_constraint("uq_enseignant_user_id", "enseignants", ["user_id"])

    # ── salles ────────────────────────────────────────────────────────────────
    if not _table_exists("salles"):
        op.create_table(
            "salles",
            sa.Column("id",       sa.Integer(),  autoincrement=True, nullable=False),
            sa.Column("nom",      sa.String(50), nullable=False),
            sa.Column("capacite", sa.Integer(),  nullable=True),
            sa.Column("type",     sa.Enum("Amphithéâtre", "Salle TD", "Salle TP", "Salle Info"), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("nom"),
        )

    # ── seances ───────────────────────────────────────────────────────────────
    if not _table_exists("seances"):
        op.create_table(
            "seances",
            sa.Column("id",                sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("jour",              sa.Enum("Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"), nullable=False),
            sa.Column("heure_debut",       sa.Time(),    nullable=False),
            sa.Column("heure_fin",         sa.Time(),    nullable=False),
            sa.Column("element_module_id", sa.Integer(), nullable=False),
            sa.Column("enseignant_id",     sa.Integer(), nullable=False),
            sa.Column("salle_id",          sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["element_module_id"], ["elements_module.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["enseignant_id"],     ["enseignants.id"],     ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["salle_id"],          ["salles.id"],          ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("jour", "heure_debut", "salle_id",      name="uq_salle_creneau"),
            sa.UniqueConstraint("jour", "heure_debut", "enseignant_id", name="uq_enseignant_creneau"),
        )
        op.create_index("idx_seance_element",    "seances", ["element_module_id"])
        op.create_index("idx_seance_enseignant", "seances", ["enseignant_id"])
        op.create_index("idx_seance_salle",      "seances", ["salle_id"])


def downgrade() -> None:
    for table in ["seances", "salles", "enseignants", "elements_module",
                  "modules", "semestres", "filieres", "departements", "annees_universitaires"]:
        if _table_exists(table):
            op.drop_table(table)
