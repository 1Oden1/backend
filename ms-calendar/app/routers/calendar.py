"""
Router ms-calendar — /api/v1/calendar

1. Endpoints publics (auth requise) : CRUD structure académique + emploi du temps
2. Endpoints internes /internal    : consommés par ms-notes (hors Swagger)
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.auth import get_current_user, require_admin
from app.models import (
    AnneeUniversitaire, Departement, Filiere, Semestre,
    Module, ElementModule, Enseignant, Salle, Seance,
)
from app.schemas import (
    AnneeUniversitaireIn, AnneeUniversitaireRead,
    DepartementIn, DepartementRead,
    FiliereIn, FiliereRead,
    SemestreIn, SemestreRead, DeadlineUpdate,
    ModuleIn, ModuleRead,
    ElementModuleIn, ElementModuleRead,
    EnseignantIn, EnseignantRead,
    SalleIn, SalleRead,
    SeanceIn, SeanceRead, EmploiDuTemps,
)
from app.events import (
    publish_filiere_created, publish_filiere_updated, publish_filiere_deleted,
    publish_teacher_filiere_linked,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── BUG FIX : helper IntegrityError → 409/422 lisibles au lieu de 500 ─────────

def _handle_integrity(exc: IntegrityError) -> HTTPException:
    msg = str(exc.orig) if exc.orig else str(exc)
    if "Duplicate entry" in msg or "UNIQUE" in msg.upper():
        return HTTPException(status.HTTP_409_CONFLICT, f"Valeur déjà existante : {msg}")
    if "FOREIGN KEY" in msg.upper():
        return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Référence invalide : {msg}")
    return HTTPException(status.HTTP_409_CONFLICT, f"Contrainte de base de données : {msg}")


# ══════════════════════════════════════════════════════════════════════════════
# ANNÉES UNIVERSITAIRES
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/annees", response_model=List[AnneeUniversitaireRead])
def list_annees(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.scalars(select(AnneeUniversitaire).order_by(AnneeUniversitaire.label.desc())).all()


@router.post("/annees", response_model=AnneeUniversitaireRead, status_code=201)
def create_annee(body: AnneeUniversitaireIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = AnneeUniversitaire(label=body.label)
    db.add(obj)
    try:
        db.commit(); db.refresh(obj)
    except IntegrityError as exc:
        db.rollback(); raise _handle_integrity(exc)
    return obj


@router.delete("/annees/{annee_id}", status_code=204)
def delete_annee(annee_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = db.get(AnneeUniversitaire, annee_id)
    if not obj: raise HTTPException(404, "Année introuvable")
    db.delete(obj); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# DÉPARTEMENTS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/departements", response_model=List[DepartementRead])
def list_departements(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.scalars(select(Departement).order_by(Departement.nom)).all()


@router.get("/departements/{dept_id}", response_model=DepartementRead)
def get_departement(dept_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = db.get(Departement, dept_id)
    if not obj: raise HTTPException(404, "Département introuvable")
    return obj


@router.post("/departements", response_model=DepartementRead, status_code=201)
def create_departement(body: DepartementIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = Departement(nom=body.nom)
    db.add(obj)
    try:
        db.commit(); db.refresh(obj)
    except IntegrityError as exc:
        db.rollback(); raise _handle_integrity(exc)
    return obj


@router.put("/departements/{dept_id}", response_model=DepartementRead)
def update_departement(dept_id: int, body: DepartementIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = db.get(Departement, dept_id)
    if not obj: raise HTTPException(404, "Département introuvable")
    obj.nom = body.nom
    try:
        db.commit(); db.refresh(obj)
    except IntegrityError as exc:
        db.rollback(); raise _handle_integrity(exc)
    return obj


@router.delete("/departements/{dept_id}", status_code=204)
def delete_departement(dept_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = db.get(Departement, dept_id)
    if not obj: raise HTTPException(404, "Département introuvable")
    db.delete(obj); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# FILIÈRES
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/departements/{dept_id}/filieres", response_model=List[FiliereRead])
def list_filieres(dept_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.scalars(select(Filiere).where(Filiere.departement_id == dept_id).order_by(Filiere.nom)).all()


@router.get("/filieres/{filiere_id}", response_model=FiliereRead)
def get_filiere(filiere_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = db.get(Filiere, filiere_id)
    if not obj: raise HTTPException(404, "Filière introuvable")
    return obj


@router.post("/filieres", response_model=FiliereRead, status_code=201)
async def create_filiere(body: FiliereIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = Filiere(nom=body.nom, departement_id=body.departement_id)
    db.add(obj)
    try:
        db.commit(); db.refresh(obj)
    except IntegrityError as exc:
        db.rollback(); raise _handle_integrity(exc)
    await publish_filiere_created(obj.id, obj.nom)
    return obj


@router.put("/filieres/{filiere_id}", response_model=FiliereRead)
async def update_filiere(filiere_id: int, body: FiliereIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = db.get(Filiere, filiere_id)
    if not obj: raise HTTPException(404, "Filière introuvable")
    obj.nom = body.nom; obj.departement_id = body.departement_id
    try:
        db.commit(); db.refresh(obj)
    except IntegrityError as exc:
        db.rollback(); raise _handle_integrity(exc)
    await publish_filiere_updated(obj.id, obj.nom)
    return obj


@router.delete("/filieres/{filiere_id}", status_code=204)
async def delete_filiere(filiere_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = db.get(Filiere, filiere_id)
    if not obj: raise HTTPException(404, "Filière introuvable")
    db.delete(obj); db.commit()
    await publish_filiere_deleted(filiere_id)


# ══════════════════════════════════════════════════════════════════════════════
# SEMESTRES
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/filieres/{filiere_id}/semestres", response_model=List[SemestreRead])
def list_semestres(
    filiere_id: int,
    annee_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    q = select(Semestre).where(Semestre.filiere_id == filiere_id)
    if annee_id:
        q = q.where(Semestre.annee_id == annee_id)
    return db.scalars(q.order_by(Semestre.nom)).all()


@router.get("/semestres/{semestre_id}", response_model=SemestreRead)
def get_semestre(semestre_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    obj = db.get(Semestre, semestre_id)
    if not obj: raise HTTPException(404, "Semestre introuvable")
    return obj


@router.post("/semestres", response_model=SemestreRead, status_code=201)
def create_semestre(body: SemestreIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = Semestre(**body.model_dump())
    db.add(obj)
    try:
        db.commit(); db.refresh(obj)
    except IntegrityError as exc:
        db.rollback(); raise _handle_integrity(exc)
    return obj


@router.put("/semestres/{semestre_id}", response_model=SemestreRead)
def update_semestre(semestre_id: int, body: SemestreIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = db.get(Semestre, semestre_id)
    if not obj: raise HTTPException(404, "Semestre introuvable")
    for k, v in body.model_dump().items():
        setattr(obj, k, v)
    try:
        db.commit(); db.refresh(obj)
    except IntegrityError as exc:
        db.rollback(); raise _handle_integrity(exc)
    return obj


@router.patch("/semestres/{semestre_id}/deadline", response_model=SemestreRead)
def update_deadline(semestre_id: int, body: DeadlineUpdate, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = db.get(Semestre, semestre_id)
    if not obj: raise HTTPException(404, "Semestre introuvable")
    obj.date_limite_depot = body.date_limite_depot
    db.commit(); db.refresh(obj)
    return obj


@router.delete("/semestres/{semestre_id}", status_code=204)
def delete_semestre(semestre_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = db.get(Semestre, semestre_id)
    if not obj: raise HTTPException(404, "Semestre introuvable")
    db.delete(obj); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# MODULES
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/semestres/{semestre_id}/modules", response_model=List[ModuleRead])
def list_modules(semestre_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.scalars(select(Module).where(Module.semestre_id == semestre_id).order_by(Module.nom)).all()


@router.post("/modules", response_model=ModuleRead, status_code=201)
def create_module(body: ModuleIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = Module(**body.model_dump())
    db.add(obj)
    try:
        db.commit(); db.refresh(obj)
    except IntegrityError as exc:
        db.rollback(); raise _handle_integrity(exc)
    return obj


@router.put("/modules/{module_id}", response_model=ModuleRead)
def update_module(module_id: int, body: ModuleIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = db.get(Module, module_id)
    if not obj: raise HTTPException(404, "Module introuvable")
    for k, v in body.model_dump().items():
        setattr(obj, k, v)
    try:
        db.commit(); db.refresh(obj)
    except IntegrityError as exc:
        db.rollback(); raise _handle_integrity(exc)
    return obj


@router.delete("/modules/{module_id}", status_code=204)
def delete_module(module_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = db.get(Module, module_id)
    if not obj: raise HTTPException(404, "Module introuvable")
    db.delete(obj); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# ÉLÉMENTS DE MODULE
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/modules/{module_id}/elements", response_model=List[ElementModuleRead])
def list_elements(module_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.scalars(select(ElementModule).where(ElementModule.module_id == module_id).order_by(ElementModule.nom)).all()


@router.post("/elements", response_model=ElementModuleRead, status_code=201)
def create_element(body: ElementModuleIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = ElementModule(**body.model_dump())
    db.add(obj)
    try:
        db.commit(); db.refresh(obj)
    except IntegrityError as exc:
        db.rollback(); raise _handle_integrity(exc)
    return obj


@router.put("/elements/{element_id}", response_model=ElementModuleRead)
def update_element(element_id: int, body: ElementModuleIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = db.get(ElementModule, element_id)
    if not obj: raise HTTPException(404, "Élément introuvable")
    for k, v in body.model_dump().items():
        setattr(obj, k, v)
    try:
        db.commit(); db.refresh(obj)
    except IntegrityError as exc:
        db.rollback(); raise _handle_integrity(exc)
    return obj


@router.delete("/elements/{element_id}", status_code=204)
def delete_element(element_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = db.get(ElementModule, element_id)
    if not obj: raise HTTPException(404, "Élément introuvable")
    db.delete(obj); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# ENSEIGNANTS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/enseignants", response_model=List[EnseignantRead])
def list_enseignants(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.scalars(select(Enseignant).order_by(Enseignant.nom)).all()


@router.post("/enseignants", response_model=EnseignantRead, status_code=201)
def create_enseignant(body: EnseignantIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = Enseignant(**body.model_dump())
    db.add(obj)
    try:
        db.commit(); db.refresh(obj)
    except IntegrityError as exc:
        db.rollback(); raise _handle_integrity(exc)
    return obj


@router.put("/enseignants/{ens_id}", response_model=EnseignantRead)
def update_enseignant(ens_id: int, body: EnseignantIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = db.get(Enseignant, ens_id)
    if not obj: raise HTTPException(404, "Enseignant introuvable")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    try:
        db.commit(); db.refresh(obj)
    except IntegrityError as exc:
        db.rollback(); raise _handle_integrity(exc)
    return obj


@router.delete("/enseignants/{ens_id}", status_code=204)
def delete_enseignant(ens_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = db.get(Enseignant, ens_id)
    if not obj: raise HTTPException(404, "Enseignant introuvable")
    db.delete(obj); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# SALLES
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/salles", response_model=List[SalleRead])
def list_salles(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.scalars(select(Salle).order_by(Salle.nom)).all()


@router.post("/salles", response_model=SalleRead, status_code=201)
def create_salle(body: SalleIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = Salle(**body.model_dump())
    db.add(obj)
    try:
        db.commit(); db.refresh(obj)
    except IntegrityError as exc:
        db.rollback(); raise _handle_integrity(exc)
    return obj


@router.put("/salles/{salle_id}", response_model=SalleRead)
def update_salle(salle_id: int, body: SalleIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = db.get(Salle, salle_id)
    if not obj: raise HTTPException(404, "Salle introuvable")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    try:
        db.commit(); db.refresh(obj)
    except IntegrityError as exc:
        db.rollback(); raise _handle_integrity(exc)
    return obj


@router.delete("/salles/{salle_id}", status_code=204)
def delete_salle(salle_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = db.get(Salle, salle_id)
    if not obj: raise HTTPException(404, "Salle introuvable")
    db.delete(obj); db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# SÉANCES & EMPLOI DU TEMPS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/seances", status_code=201)
async def create_seance(body: SeanceIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = Seance(**body.model_dump())
    db.add(obj)
    try:
        db.commit(); db.refresh(obj)
    except IntegrityError as exc:
        db.rollback(); raise _handle_integrity(exc)

    try:
        element    = db.get(ElementModule, obj.element_module_id)
        module     = db.get(Module,        element.module_id)   if element  else None
        semestre   = db.get(Semestre,      module.semestre_id)  if module   else None
        enseignant = db.get(Enseignant,    obj.enseignant_id)
        if semestre and enseignant and enseignant.user_id:
            await publish_teacher_filiere_linked(enseignant.user_id, semestre.filiere_id)
    except Exception as exc:
        logger.warning("Impossible de publier teacher.filiere.linked : %s", exc)

    return {"id": obj.id}


@router.put("/seances/{seance_id}")
def update_seance(seance_id: int, body: SeanceIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = db.get(Seance, seance_id)
    if not obj: raise HTTPException(404, "Séance introuvable")
    for k, v in body.model_dump().items():
        setattr(obj, k, v)
    try:
        db.commit(); db.refresh(obj)
    except IntegrityError as exc:
        db.rollback(); raise _handle_integrity(exc)
    return {"id": obj.id}


@router.delete("/seances/{seance_id}", status_code=204)
def delete_seance(seance_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    obj = db.get(Seance, seance_id)
    if not obj: raise HTTPException(404, "Séance introuvable")
    db.delete(obj); db.commit()


@router.get("/emploi-du-temps/{semestre_id}", response_model=EmploiDuTemps)
def get_emploi_du_temps(semestre_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    semestre = db.scalars(
        select(Semestre)
        .where(Semestre.id == semestre_id)
        .options(
            joinedload(Semestre.filiere).joinedload(Filiere.departement),
            joinedload(Semestre.annee),
        )
    ).first()
    if not semestre:
        raise HTTPException(404, "Semestre introuvable")

    seances = db.scalars(
        select(Seance)
        .join(Seance.element_module)
        .join(ElementModule.module)
        .where(Module.semestre_id == semestre_id)
        .options(
            joinedload(Seance.element_module).joinedload(ElementModule.module),
            joinedload(Seance.enseignant),
            joinedload(Seance.salle),
        )
        .order_by(Seance.jour, Seance.heure_debut)
    ).unique().all()

    rows = [
        SeanceRead(
            id                = s.id,
            jour              = s.jour,
            heure_debut       = s.heure_debut,
            heure_fin         = s.heure_fin,
            element_module    = s.element_module.nom,
            type_seance       = s.element_module.type,
            module            = s.element_module.module.nom,
            enseignant_nom    = s.enseignant.nom,
            enseignant_prenom = s.enseignant.prenom,
            salle             = s.salle.nom,
        )
        for s in seances
    ]

    return EmploiDuTemps(
        departement = semestre.filiere.departement.nom,
        filiere     = semestre.filiere.nom,
        annee       = semestre.annee.label,
        semestre    = semestre.nom,
        seances     = rows,
    )


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS INTERNES — consommés par ms-notes (non exposés dans Swagger)
# ══════════════════════════════════════════════════════════════════════════════

internal_router = APIRouter(prefix="/internal", tags=["Internal"], include_in_schema=False)


@internal_router.get("/departements")
def internal_list_departements(db: Session = Depends(get_db)):
    rows = db.scalars(select(Departement).order_by(Departement.nom)).all()
    return [{"id": d.id, "nom": d.nom} for d in rows]


@internal_router.get("/departements/{dept_id}")
def internal_get_departement(dept_id: int, db: Session = Depends(get_db)):
    obj = db.get(Departement, dept_id)
    if not obj: raise HTTPException(404, "Département introuvable")
    return {"id": obj.id, "nom": obj.nom}


@internal_router.get("/filieres")
def internal_list_filieres(db: Session = Depends(get_db)):
    rows = db.scalars(select(Filiere).order_by(Filiere.nom)).all()
    return [{"id": f.id, "nom": f.nom, "departement_id": f.departement_id} for f in rows]


@internal_router.get("/filieres/{filiere_id}")
def internal_get_filiere(filiere_id: int, db: Session = Depends(get_db)):
    obj = db.get(Filiere, filiere_id)
    if not obj: raise HTTPException(404, "Filière introuvable")
    return {
        "id":              obj.id,
        "nom":             obj.nom,
        "departement_id":  obj.departement_id,
        "departement_nom": obj.departement.nom if obj.departement else "",
    }


@internal_router.get("/departements/{dept_id}/filieres")
def internal_filieres_by_dept(dept_id: int, db: Session = Depends(get_db)):
    rows = db.query(Filiere).filter(Filiere.departement_id == dept_id).all()
    return [{"id": f.id, "nom": f.nom} for f in rows]


@internal_router.get("/semestres/{semestre_id}")
def internal_get_semestre(semestre_id: int, db: Session = Depends(get_db)):
    obj = (
        db.query(Semestre)
        .options(
            joinedload(Semestre.annee),
            joinedload(Semestre.filiere).joinedload(Filiere.departement),
            joinedload(Semestre.modules).joinedload(Module.elements),
        )
        .filter(Semestre.id == semestre_id)
        .first()
    )
    if not obj: raise HTTPException(404, "Semestre introuvable")
    return {
        "id":                obj.id,
        "nom":               obj.nom,
        "annee_id":          obj.annee_id,
        "annee_label":       obj.annee.label                         if obj.annee   else "",
        "filiere_id":        obj.filiere_id,
        "filiere_nom":       obj.filiere.nom                         if obj.filiere else "",
        "departement_id":    obj.filiere.departement_id              if obj.filiere else None,
        "departement_nom":   obj.filiere.departement.nom             if obj.filiere and obj.filiere.departement else "",
        "date_limite_depot": str(obj.date_limite_depot)              if obj.date_limite_depot else None,
        "modules": [
            {
                "id":     m.id,
                "nom":    m.nom,
                "code":   m.code,
                "credit": m.credit,
                "elements": [
                    {
                        "id":          e.id,
                        "nom":         e.nom,
                        "code":        e.code,
                        "coefficient": float(e.coefficient),
                        "type":        e.type,
                    }
                    for e in m.elements
                ],
            }
            for m in obj.modules
        ],
    }


@internal_router.get("/elements/{element_id}")
def internal_get_element(element_id: int, db: Session = Depends(get_db)):
    obj = db.get(ElementModule, element_id)
    if not obj: raise HTTPException(404, "Élément introuvable")
    return {
        "id":          obj.id,
        "nom":         obj.nom,
        "code":        obj.code,
        "type":        obj.type,
        # BUG FIX : coefficient manquant dans la version originale → KeyError dans ms-notes/services.py
        "coefficient": float(obj.coefficient),
        "module_id":   obj.module_id,
        "module_nom":  obj.module.nom  if obj.module else "",
        "module_code": obj.module.code if obj.module else "",
    }


@internal_router.get("/semestres-deadline")
def internal_semestres_deadline(
    date_limite: str = Query(..., description="Date au format YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    from datetime import date as date_type
    try:
        target = date_type.fromisoformat(date_limite)
    except ValueError:
        return {"semestres": []}
    rows = db.query(Semestre).filter(Semestre.date_limite_depot == target).all()
    return {"semestres": [{"id": s.id, "nom": s.nom, "filiere_id": s.filiere_id} for s in rows]}
