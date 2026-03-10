"""Schéma initial ent_notes — migration unique et définitive.

Toutes les tables sont créées directement avec les bons noms de colonnes
(calendar_*). Aucune migration de renommage ne sera nécessaire.

Revision ID: 0001_initial_notes
Revises:
Create Date: 2025-01-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision: str = "0001_initial_notes"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    return inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    conn = op.get_bind()

    # ── etudiants ─────────────────────────────────────────────────────────────
    if not _table_exists("etudiants"):
        op.create_table(
            "etudiants",
            sa.Column("id",                  sa.Integer(),   autoincrement=True, nullable=False),
            sa.Column("user_id",             sa.String(100), nullable=False),
            sa.Column("cne",                 sa.String(20),  nullable=False),
            sa.Column("prenom",              sa.String(100), nullable=False),
            sa.Column("nom",                 sa.String(100), nullable=False),
            sa.Column("calendar_filiere_id", sa.Integer(),   nullable=False),
            sa.Column("created_at",          sa.DateTime(),  nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", name="uq_etudiant_user_id"),
            sa.UniqueConstraint("cne",     name="uq_etudiant_cne"),
        )
        op.create_index("idx_etudiant_filiere", "etudiants", ["calendar_filiere_id"])
    else:
        # Table existante avec ancienne architecture → forcer le renommage en SQL brut
        for old, new in [("filiere_id", "calendar_filiere_id")]:
            try:
                conn.execute(text(
                    f"ALTER TABLE `etudiants` CHANGE COLUMN `{old}` `{new}` INT NOT NULL"
                ))
            except Exception as e:
                if "1054" not in str(e) and "1060" not in str(e):
                    raise

    # ── enseignants ───────────────────────────────────────────────────────────
    if not _table_exists("enseignants"):
        op.create_table(
            "enseignants",
            sa.Column("id",                      sa.Integer(),   autoincrement=True, nullable=False),
            sa.Column("user_id",                 sa.String(100), nullable=False),
            sa.Column("prenom",                  sa.String(100), nullable=False),
            sa.Column("nom",                     sa.String(100), nullable=False),
            sa.Column("calendar_departement_id", sa.Integer(),   nullable=False),
            sa.Column("created_at",              sa.DateTime(),  nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", name="uq_enseignant_user_id"),
        )
        op.create_index("idx_enseignant_dept", "enseignants", ["calendar_departement_id"])
    else:
        for old, new in [("departement_id", "calendar_departement_id")]:
            try:
                conn.execute(text(
                    f"ALTER TABLE `enseignants` CHANGE COLUMN `{old}` `{new}` INT NOT NULL"
                ))
            except Exception as e:
                if "1054" not in str(e) and "1060" not in str(e):
                    raise

    # ── notes ─────────────────────────────────────────────────────────────────
    if not _table_exists("notes"):
        op.create_table(
            "notes",
            sa.Column("id",                  sa.Integer(),     autoincrement=True, nullable=False),
            sa.Column("etudiant_id",         sa.Integer(),     nullable=False),
            sa.Column("calendar_element_id", sa.Integer(),     nullable=False),
            sa.Column("note",                sa.Numeric(5, 2), nullable=False),
            sa.Column("created_at",          sa.DateTime(),    nullable=True),
            sa.Column("updated_at",          sa.DateTime(),    nullable=True),
            sa.ForeignKeyConstraint(["etudiant_id"], ["etudiants.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("etudiant_id", "calendar_element_id", name="uq_note"),
            sa.CheckConstraint("note >= 0 AND note <= 20",              name="chk_note_range"),
        )
        op.create_index("idx_note_etudiant", "notes", ["etudiant_id"])
        op.create_index("idx_note_element",  "notes", ["calendar_element_id"])
    else:
        for old, new in [("element_id", "calendar_element_id")]:
            try:
                conn.execute(text(
                    f"ALTER TABLE `notes` CHANGE COLUMN `{old}` `{new}` INT NOT NULL"
                ))
            except Exception as e:
                if "1054" not in str(e) and "1060" not in str(e):
                    raise

    # ── demandes_releve ───────────────────────────────────────────────────────
    if not _table_exists("demandes_releve"):
        op.create_table(
            "demandes_releve",
            sa.Column("id",                   sa.Integer(),   autoincrement=True, nullable=False),
            sa.Column("demandeur_user_id",    sa.String(100), nullable=False),
            sa.Column("role_demandeur",       sa.Enum("etudiant", "enseignant"), nullable=False),
            sa.Column("etudiant_id",          sa.Integer(),   nullable=False),
            sa.Column("calendar_semestre_id", sa.Integer(),   nullable=False),
            sa.Column("statut",               sa.Enum("en_attente", "approuve", "rejete"),
                      nullable=False, server_default="en_attente"),
            sa.Column("motif_rejet",          sa.String(255), nullable=True),
            sa.Column("demande_le",           sa.DateTime(),  nullable=True),
            sa.Column("traite_le",            sa.DateTime(),  nullable=True),
            sa.ForeignKeyConstraint(["etudiant_id"], ["etudiants.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_dr_statut",    "demandes_releve", ["statut"])
        op.create_index("idx_dr_demandeur", "demandes_releve", ["demandeur_user_id"])
        op.create_index("idx_dr_semestre",  "demandes_releve", ["calendar_semestre_id"])
    else:
        for old, new in [("semestre_id", "calendar_semestre_id")]:
            try:
                conn.execute(text(
                    f"ALTER TABLE `demandes_releve` CHANGE COLUMN `{old}` `{new}` INT NOT NULL"
                ))
            except Exception as e:
                if "1054" not in str(e) and "1060" not in str(e):
                    raise

    # ── demandes_classement ───────────────────────────────────────────────────
    if not _table_exists("demandes_classement"):
        op.create_table(
            "demandes_classement",
            sa.Column("id",                   sa.Integer(),  autoincrement=True, nullable=False),
            sa.Column("etudiant_id",          sa.Integer(),  nullable=False),
            sa.Column("calendar_semestre_id", sa.Integer(),  nullable=False),
            sa.Column("type_classement",      sa.Enum("filiere", "departement"), nullable=False),
            sa.Column("statut",               sa.Enum("en_attente", "approuve", "rejete"),
                      nullable=False, server_default="en_attente"),
            sa.Column("motif_rejet",          sa.String(255), nullable=True),
            sa.Column("demande_le",           sa.DateTime(),  nullable=True),
            sa.Column("traite_le",            sa.DateTime(),  nullable=True),
            sa.ForeignKeyConstraint(["etudiant_id"], ["etudiants.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_dc_statut",   "demandes_classement", ["statut"])
        op.create_index("idx_dc_etudiant", "demandes_classement", ["etudiant_id"])
        op.create_index("idx_dc_semestre", "demandes_classement", ["calendar_semestre_id"])
    else:
        for old, new in [("semestre_id", "calendar_semestre_id")]:
            try:
                conn.execute(text(
                    f"ALTER TABLE `demandes_classement` CHANGE COLUMN `{old}` `{new}` INT NOT NULL"
                ))
            except Exception as e:
                if "1054" not in str(e) and "1060" not in str(e):
                    raise


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
    for table in ["demandes_classement", "demandes_releve", "notes", "enseignants", "etudiants"]:
        if _table_exists(table):
            op.drop_table(table)
    conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
