"""
Modèles SQLAlchemy — base ent_notes

ms-notes possède : Etudiant, Note, DemandeReleve, DemandeClassement
ms-notes consomme : structure académique depuis ms-calendar via HTTP /internal

Les colonnes calendar_* sont de simples entiers (pas de FK locale inter-base) :
  Etudiant.calendar_filiere_id          → ent_calendar.filieres.id
  Note.calendar_element_id              → ent_calendar.elements_module.id
  DemandeReleve.calendar_semestre_id    → ent_calendar.semestres.id
  DemandeClassement.calendar_semestre_id
"""
from datetime import datetime

from sqlalchemy import (
    CheckConstraint, Column, DateTime, Enum,
    ForeignKey, Index, Integer, Numeric, String, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ── Utilisateurs ──────────────────────────────────────────────────────────────

class Etudiant(Base):
    __tablename__ = "etudiants"

    id                   = Column(Integer,     primary_key=True, autoincrement=True)
    user_id              = Column(String(100), nullable=False, unique=True)   # Keycloak sub
    cne                  = Column(String(20),  nullable=False, unique=True)
    prenom               = Column(String(100), nullable=False)
    nom                  = Column(String(100), nullable=False)
    calendar_filiere_id  = Column(Integer,     nullable=False)                # ref ms-calendar
    created_at           = Column(DateTime,    default=datetime.utcnow)

    notes               = relationship("Note",         back_populates="etudiant", cascade="all, delete-orphan")
    demandes_releve     = relationship("DemandeReleve",     foreign_keys="DemandeReleve.etudiant_id",
                                       back_populates="etudiant", cascade="all, delete-orphan")
    demandes_classement = relationship("DemandeClassement", back_populates="etudiant",
                                       cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_etudiant_filiere", "calendar_filiere_id"),
    )


# ── Notes ─────────────────────────────────────────────────────────────────────

class Note(Base):
    __tablename__ = "notes"

    id                   = Column(Integer,       primary_key=True, autoincrement=True)
    etudiant_id          = Column(Integer,       ForeignKey("etudiants.id", ondelete="CASCADE"), nullable=False)
    calendar_element_id  = Column(Integer,       nullable=False)              # ref ms-calendar
    note                 = Column(Numeric(5, 2), nullable=False)
    created_at           = Column(DateTime,      default=datetime.utcnow)
    updated_at           = Column(DateTime,      default=datetime.utcnow, onupdate=datetime.utcnow)

    etudiant = relationship("Etudiant", back_populates="notes")

    __table_args__ = (
        UniqueConstraint("etudiant_id", "calendar_element_id", name="uq_note"),
        CheckConstraint("note >= 0 AND note <= 20",             name="chk_note_range"),
        Index("idx_note_etudiant", "etudiant_id"),
        Index("idx_note_element",  "calendar_element_id"),
    )


# ── Demandes ──────────────────────────────────────────────────────────────────

_STATUTS          = ("en_attente", "approuve", "rejete")
_ROLES_DEMANDEUR  = ("etudiant", "enseignant")
_TYPES_CLASSEMENT = ("filiere", "departement")


class DemandeReleve(Base):
    __tablename__ = "demandes_releve"

    id                    = Column(Integer,     primary_key=True, autoincrement=True)
    demandeur_user_id     = Column(String(100), nullable=False)
    role_demandeur        = Column(Enum(*_ROLES_DEMANDEUR),  nullable=False)
    etudiant_id           = Column(Integer,     ForeignKey("etudiants.id", ondelete="CASCADE"), nullable=False)
    calendar_semestre_id  = Column(Integer,     nullable=False)               # ref ms-calendar
    statut                = Column(Enum(*_STATUTS), default="en_attente",     nullable=False)
    motif_rejet           = Column(String(255), nullable=True)
    demande_le            = Column(DateTime,    default=datetime.utcnow)
    traite_le             = Column(DateTime,    nullable=True)

    etudiant = relationship("Etudiant", foreign_keys=[etudiant_id], back_populates="demandes_releve")

    __table_args__ = (
        Index("idx_dr_statut",    "statut"),
        Index("idx_dr_demandeur", "demandeur_user_id"),
        Index("idx_dr_semestre",  "calendar_semestre_id"),
    )


class DemandeClassement(Base):
    __tablename__ = "demandes_classement"

    id                    = Column(Integer,  primary_key=True, autoincrement=True)
    etudiant_id           = Column(Integer,  ForeignKey("etudiants.id", ondelete="CASCADE"), nullable=False)
    calendar_semestre_id  = Column(Integer,  nullable=False)                  # ref ms-calendar
    type_classement       = Column(Enum(*_TYPES_CLASSEMENT), nullable=False)
    statut                = Column(Enum(*_STATUTS), default="en_attente",     nullable=False)
    motif_rejet           = Column(String(255), nullable=True)
    demande_le            = Column(DateTime, default=datetime.utcnow)
    traite_le             = Column(DateTime, nullable=True)

    etudiant = relationship("Etudiant", back_populates="demandes_classement")

    __table_args__ = (
        Index("idx_dc_statut",   "statut"),
        Index("idx_dc_etudiant", "etudiant_id"),
        Index("idx_dc_semestre", "calendar_semestre_id"),
    )
