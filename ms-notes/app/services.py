"""
services.py — Calculs des moyennes et classements

Structure académique depuis ms-calendar /internal/...
Notes depuis la base locale ent_notes uniquement.
"""
from decimal import ROUND_HALF_UP, Decimal
from typing import List, Optional, Tuple

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.models import DemandeClassement, Enseignant, Etudiant, Note
from app.schemas import (
    ClassementCompletOut, EntreeClassement,
    ElementNoteOut, MonClassementOut, SemestreNotesOut,
)


def _arrondi(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ── Appels ms-calendar /internal ─────────────────────────────────────────────

def _cal_get(path: str) -> dict:
    url = f"{settings.MS_CALENDAR_URL}/api/v1/calendar/internal/{path}"
    headers = {}
    if settings.INTERNAL_SERVICE_TOKEN:
        headers["Authorization"] = f"Bearer {settings.INTERNAL_SERVICE_TOKEN}"
    try:
        r = httpx.get(url, headers=headers, timeout=5.0)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(404, f"Ressource introuvable dans ms-calendar : {path}")
        raise HTTPException(502, f"Erreur ms-calendar ({exc.response.status_code}) : {path}")
    except Exception as exc:
        raise HTTPException(502, f"ms-calendar inaccessible : {exc}")


def _get_semestre(semestre_id: int) -> dict:
    return _cal_get(f"semestres/{semestre_id}")


def _get_filiere(filiere_id: int) -> dict:
    return _cal_get(f"filieres/{filiere_id}")


# ── Helpers DB locale ─────────────────────────────────────────────────────────

def get_etudiant_by_user_id(db: Session, user_id: str) -> Optional[Etudiant]:
    return db.query(Etudiant).filter(Etudiant.user_id == user_id).first()


def get_enseignant_by_user_id(db: Session, user_id: str) -> Optional[Enseignant]:
    return db.query(Enseignant).filter(Enseignant.user_id == user_id).first()


# ── Notes d'un étudiant pour un semestre ─────────────────────────────────────

def calculer_notes_semestre(
    db: Session, etudiant: Etudiant, semestre_id: int
) -> SemestreNotesOut:
    semestre = _get_semestre(semestre_id)

    if semestre.get("filiere_id") != etudiant.calendar_filiere_id:
        raise HTTPException(403, "Ce semestre n'appartient pas à votre filière.")

    notes_map: dict[int, Decimal] = {
        n.calendar_element_id: Decimal(str(n.note))
        for n in db.query(Note).filter(Note.etudiant_id == etudiant.id).all()
    }

    sem_num = Decimal("0")
    sem_den = Decimal("0")
    notes_out: List[ElementNoteOut] = []

    for module in semestre.get("modules", []):
        credit  = Decimal(str(module["credit"]))
        mod_num = Decimal("0")
        mod_den = Decimal("0")
        for elem in module.get("elements", []):
            eid      = elem["id"]
            coeff    = Decimal(str(elem["coefficient"]))
            note_val = notes_map.get(eid)
            mod_num += (note_val if note_val is not None else Decimal("0")) * coeff
            mod_den += coeff
            notes_out.append(ElementNoteOut(
                calendar_element_id=eid,
                note=_arrondi(note_val) if note_val is not None else None,
            ))
        if mod_den > 0:
            sem_num += (mod_num / mod_den) * credit
            sem_den += credit

    return SemestreNotesOut(
        calendar_semestre_id=semestre_id,
        moyenne_semestre=_arrondi(sem_num / sem_den) if sem_den > 0 else Decimal("0"),
        notes=notes_out,
    )


# ── Moyennes par filière ──────────────────────────────────────────────────────

def _moyennes_semestre_filiere(
    db: Session, semestre_id: int, filiere_id: int
) -> List[Tuple[int, Decimal]]:
    semestre = _get_semestre(semestre_id)

    elem_coeff:    dict[int, Decimal] = {}
    module_elems:  dict[int, list]    = {}
    module_credit: dict[int, Decimal] = {}

    for module in semestre.get("modules", []):
        mid = module["id"]
        module_credit[mid] = Decimal(str(module["credit"]))
        module_elems[mid]  = []
        for elem in module.get("elements", []):
            eid = elem["id"]
            elem_coeff[eid] = Decimal(str(elem["coefficient"]))
            module_elems[mid].append(eid)

    if not elem_coeff:
        return []

    etudiants = db.query(Etudiant).filter(Etudiant.calendar_filiere_id == filiere_id).all()
    if not etudiants:
        return []

    notes_rows = db.query(Note).filter(
        Note.etudiant_id.in_([e.id for e in etudiants]),
        Note.calendar_element_id.in_(list(elem_coeff.keys())),
    ).all()

    notes_by_student: dict[int, dict[int, Decimal]] = {e.id: {} for e in etudiants}
    for n in notes_rows:
        notes_by_student[n.etudiant_id][n.calendar_element_id] = Decimal(str(n.note))

    results = []
    for etudiant in etudiants:
        notes = notes_by_student[etudiant.id]
        if not notes:
            continue
        sem_num = Decimal("0")
        sem_den = Decimal("0")
        for mid, elem_ids in module_elems.items():
            mod_num = Decimal("0")
            mod_den = Decimal("0")
            for eid in elem_ids:
                mod_num += notes.get(eid, Decimal("0")) * elem_coeff[eid]
                mod_den += elem_coeff[eid]
            if mod_den > 0:
                sem_num += (mod_num / mod_den) * module_credit[mid]
                sem_den += module_credit[mid]
        if sem_den > 0:
            results.append((etudiant.id, _arrondi(sem_num / sem_den)))

    return results


# ── Classement filière ────────────────────────────────────────────────────────

def classement_filiere(
    db: Session, filiere_id: int, semestre_id: int
) -> ClassementCompletOut:
    filiere = _get_filiere(filiere_id)
    etudiants_map = {
        e.id: e
        for e in db.query(Etudiant).filter(Etudiant.calendar_filiere_id == filiere_id).all()
    }
    moyennes = sorted(
        _moyennes_semestre_filiere(db, semestre_id, filiere_id),
        key=lambda x: x[1], reverse=True,
    )
    return ClassementCompletOut(
        scope_id=filiere_id,
        scope_nom=filiere["nom"],
        type_classement="filiere",
        calendar_semestre_id=semestre_id,
        total=len(moyennes),
        classement=[
            EntreeClassement(
                rang=rang,
                cne=etudiants_map[eid].cne,
                nom=f"{etudiants_map[eid].prenom} {etudiants_map[eid].nom}",
                moyenne=moy,
            )
            for rang, (eid, moy) in enumerate(moyennes, start=1)
            if eid in etudiants_map
        ],
    )


# ── Classement département ────────────────────────────────────────────────────

def classement_departement(
    db: Session, departement_id: int, semestre_id: int
) -> ClassementCompletOut:
    dept_data   = _cal_get(f"departements/{departement_id}")
    filieres    = _cal_get(f"departements/{departement_id}/filieres")
    filiere_ids = [f["id"] for f in filieres]

    etudiants_map = {
        e.id: e
        for e in db.query(Etudiant).filter(
            Etudiant.calendar_filiere_id.in_(filiere_ids)
        ).all()
    }

    all_moyennes: List[Tuple[int, Decimal]] = []
    for fid in filiere_ids:
        all_moyennes.extend(_moyennes_semestre_filiere(db, semestre_id, fid))
    all_moyennes.sort(key=lambda x: x[1], reverse=True)

    return ClassementCompletOut(
        scope_id=departement_id,
        scope_nom=dept_data["nom"],
        type_classement="departement",
        calendar_semestre_id=semestre_id,
        total=len(all_moyennes),
        classement=[
            EntreeClassement(
                rang=rang,
                cne=etudiants_map[eid].cne,
                nom=f"{etudiants_map[eid].prenom} {etudiants_map[eid].nom}",
                moyenne=moy,
            )
            for rang, (eid, moy) in enumerate(all_moyennes, start=1)
            if eid in etudiants_map
        ],
    )


# ── Mon classement (étudiant) ─────────────────────────────────────────────────

def mon_classement(
    db: Session, etudiant: Etudiant, demande: DemandeClassement
) -> MonClassementOut:
    semestre_id     = demande.calendar_semestre_id
    type_classement = demande.type_classement

    if type_classement == "filiere":
        filiere_id = etudiant.calendar_filiere_id
        scope_nom  = _get_filiere(filiere_id)["nom"]
        moyennes   = _moyennes_semestre_filiere(db, semestre_id, filiere_id)
    else:
        filiere   = _get_filiere(etudiant.calendar_filiere_id)
        dept_id   = filiere["departement_id"]
        scope_nom = _cal_get(f"departements/{dept_id}")["nom"]
        moyennes: List[Tuple[int, Decimal]] = []
        for fid in [f["id"] for f in _cal_get(f"departements/{dept_id}/filieres")]:
            moyennes.extend(_moyennes_semestre_filiere(db, semestre_id, fid))

    moyennes.sort(key=lambda x: x[1], reverse=True)

    mon_rang, ma_moyenne = 0, Decimal("0")
    for rang, (eid, moy) in enumerate(moyennes, start=1):
        if eid == etudiant.id:
            mon_rang, ma_moyenne = rang, moy
            break

    return MonClassementOut(
        demande_id=demande.id,
        type_classement=type_classement,
        calendar_semestre_id=semestre_id,
        scope_nom=scope_nom,
        total=len(moyennes),
        mon_rang=mon_rang,
        ma_moyenne=ma_moyenne,
    )
