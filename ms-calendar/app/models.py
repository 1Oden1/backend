"""
Modèles ms-calendar — ent_calendar
Source de vérité pour toute la structure académique.
"""
from sqlalchemy import (
    Column, Integer, String, Numeric, Time, Enum, Date,
    ForeignKey, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship, DeclarativeBase


class Base(DeclarativeBase):
    pass


# ── Structure académique ──────────────────────────────────────────────────────

class AnneeUniversitaire(Base):
    __tablename__ = "annees_universitaires"

    id    = Column(Integer,    primary_key=True, autoincrement=True)
    label = Column(String(20), nullable=False, unique=True)

    semestres = relationship("Semestre", back_populates="annee")


class Departement(Base):
    __tablename__ = "departements"

    id  = Column(Integer,     primary_key=True, autoincrement=True)
    nom = Column(String(150), nullable=False, unique=True)

    filieres = relationship("Filiere", back_populates="departement", cascade="all, delete-orphan")


class Filiere(Base):
    __tablename__ = "filieres"

    id             = Column(Integer,     primary_key=True, autoincrement=True)
    nom            = Column(String(150), nullable=False)
    departement_id = Column(Integer, ForeignKey("departements.id", ondelete="CASCADE"), nullable=False)

    departement = relationship("Departement", back_populates="filieres")
    semestres   = relationship("Semestre",    back_populates="filiere", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("nom", "departement_id", name="uq_filiere_dept"),
        Index("idx_filiere_dept", "departement_id"),
    )


class Semestre(Base):
    __tablename__ = "semestres"

    id                = Column(Integer,    primary_key=True, autoincrement=True)
    nom               = Column(String(20), nullable=False)
    annee_id          = Column(Integer, ForeignKey("annees_universitaires.id", ondelete="CASCADE"), nullable=False)
    filiere_id        = Column(Integer, ForeignKey("filieres.id",              ondelete="CASCADE"), nullable=False)
    date_limite_depot = Column(Date, nullable=True)

    annee   = relationship("AnneeUniversitaire", back_populates="semestres")
    filiere = relationship("Filiere",            back_populates="semestres")
    modules = relationship("Module",             back_populates="semestre", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("nom", "annee_id", "filiere_id", name="uq_semestre"),
        Index("idx_semestre_filiere", "filiere_id"),
        Index("idx_semestre_annee",   "annee_id"),
    )


class Module(Base):
    __tablename__ = "modules"

    id          = Column(Integer,     primary_key=True, autoincrement=True)
    nom         = Column(String(150), nullable=False)
    code        = Column(String(30),  nullable=False, unique=True)
    credit      = Column(Integer,     nullable=False, default=2)
    semestre_id = Column(Integer, ForeignKey("semestres.id", ondelete="CASCADE"), nullable=False)

    semestre = relationship("Semestre",      back_populates="modules")
    elements = relationship("ElementModule", back_populates="module", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_module_semestre", "semestre_id"),
    )


class ElementModule(Base):
    __tablename__ = "elements_module"

    id          = Column(Integer,      primary_key=True, autoincrement=True)
    nom         = Column(String(150),  nullable=False)
    code        = Column(String(30),   nullable=False)
    # BUG FIX #1 : coefficient était absent → AttributeError dans internal_get_semestre
    coefficient = Column(Numeric(4,2), nullable=False, default=1)
    type        = Column(Enum("Cours", "TD", "TP"), nullable=False, default="Cours")
    module_id   = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)

    # BUG FIX #2 : back_populates au lieu de backref + relation seances ajoutée ici
    module  = relationship("Module",  back_populates="elements")
    seances = relationship("Seance",  back_populates="element_module", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("code", "module_id", name="uq_element_module"),
        Index("idx_element_module", "module_id"),
    )


# ── Emploi du temps ───────────────────────────────────────────────────────────

class Enseignant(Base):
    __tablename__ = "enseignants"

    id      = Column(Integer,     primary_key=True, autoincrement=True)
    user_id = Column(String(36),  nullable=True, unique=True)
    nom     = Column(String(100), nullable=False)
    prenom  = Column(String(100), nullable=False)
    email   = Column(String(200), nullable=False, unique=True)

    seances = relationship("Seance", back_populates="enseignant")


class Salle(Base):
    __tablename__ = "salles"

    id       = Column(Integer,    primary_key=True, autoincrement=True)
    nom      = Column(String(50), nullable=False, unique=True)
    capacite = Column(Integer,    nullable=True)
    type     = Column(Enum("Amphithéâtre", "Salle TD", "Salle TP", "Salle Info"), nullable=True)

    seances = relationship("Seance", back_populates="salle")


JOURS = ("Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi")


class Seance(Base):
    __tablename__ = "seances"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    jour              = Column(Enum(*JOURS), nullable=False)
    heure_debut       = Column(Time, nullable=False)
    heure_fin         = Column(Time, nullable=False)
    element_module_id = Column(Integer, ForeignKey("elements_module.id", ondelete="CASCADE"),  nullable=False)
    enseignant_id     = Column(Integer, ForeignKey("enseignants.id",     ondelete="RESTRICT"), nullable=False)
    salle_id          = Column(Integer, ForeignKey("salles.id",          ondelete="RESTRICT"), nullable=False)

    # BUG FIX #2 : back_populates cohérent (backref supprimé)
    element_module = relationship("ElementModule", back_populates="seances")
    enseignant     = relationship("Enseignant",    back_populates="seances")
    salle          = relationship("Salle",         back_populates="seances")

    __table_args__ = (
        UniqueConstraint("jour", "heure_debut", "salle_id",      name="uq_salle_creneau"),
        UniqueConstraint("jour", "heure_debut", "enseignant_id", name="uq_enseignant_creneau"),
        Index("idx_seance_element",    "element_module_id"),
        Index("idx_seance_enseignant", "enseignant_id"),
        Index("idx_seance_salle",      "salle_id"),
    )
