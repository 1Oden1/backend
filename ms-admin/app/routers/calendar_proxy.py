"""
Router proxy calendar — ms-admin

ms-admin NE touche PAS à ent_calendar.
Chaque endpoint ici fait un appel HTTP vers ms-calendar et retransmet la réponse.

Avantages :
  - Séparation stricte des domaines : seul ms-calendar possède ent_calendar.
  - L'admin transmet son token JWT ; ms-calendar valide lui-même le rôle `admin`.
  - En cas d'évolution de ms-calendar, ms-admin n'a pas à être modifié côté modèles.
"""

import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from app.auth import require_admin, get_current_user
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/calendar", tags=["Proxy → ms-calendar"])

# ── Helper ────────────────────────────────────────────────────────────────────

def _calendar_url(path: str) -> str:
    return f"{settings.MS_CALENDAR_URL}/api/v1/calendar{path}"


async def _proxy(
    method: str,
    path: str,
    token: str,
    body: Any = None,
    params: dict | None = None,
) -> JSONResponse:
    """
    Effectue l'appel HTTP vers ms-calendar et retransmet la réponse telle quelle.
    Lève une HTTPException si ms-calendar est inaccessible.
    """
    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.request(
                method=method,
                url=_calendar_url(path),
                json=body,
                params=params,
                headers=headers,
            )
    except httpx.RequestError as exc:
        logger.error("ms-calendar inaccessible : %s", exc)
        raise HTTPException(502, "ms-calendar est inaccessible.")

    return JSONResponse(
        content=resp.json() if resp.content else None,
        status_code=resp.status_code,
    )


# ── Utilitaire pour extraire le token de la requête ──────────────────────────

def _token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    return auth.removeprefix("Bearer ").strip()


# ══════════════════════════════════════════════════════════════════════════════
# LECTURE (GET) — disponibles pour tous les utilisateurs authentifiés
# Redirigés via ms-admin pour centraliser l'audit et le contrôle d'accès.
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/departements",                           summary="[Proxy] Lister les départements")
async def proxy_list_departements(request: Request, _=Depends(get_current_user)):
    return await _proxy("GET", "/departements", _token(request))


@router.get("/departements/{dept_id}",                 summary="[Proxy] Détail département")
async def proxy_get_departement(dept_id: int, request: Request, _=Depends(get_current_user)):
    return await _proxy("GET", f"/departements/{dept_id}", _token(request))


@router.get("/departements/{dept_id}/filieres",        summary="[Proxy] Filières d'un département")
async def proxy_list_filieres(dept_id: int, request: Request, _=Depends(get_current_user)):
    return await _proxy("GET", f"/departements/{dept_id}/filieres", _token(request))


@router.get("/filieres/{filiere_id}",                  summary="[Proxy] Détail filière")
async def proxy_get_filiere(filiere_id: int, request: Request, _=Depends(get_current_user)):
    return await _proxy("GET", f"/filieres/{filiere_id}", _token(request))


@router.get("/filieres/{filiere_id}/semestres",        summary="[Proxy] Semestres d'une filière")
async def proxy_list_semestres(filiere_id: int, request: Request, _=Depends(get_current_user)):
    return await _proxy("GET", f"/filieres/{filiere_id}/semestres", _token(request))


@router.get("/semestres/{semestre_id}/modules",        summary="[Proxy] Modules d'un semestre")
async def proxy_list_modules(semestre_id: int, request: Request, _=Depends(get_current_user)):
    return await _proxy("GET", f"/semestres/{semestre_id}/modules", _token(request))


@router.get("/modules/{module_id}/elements",           summary="[Proxy] Éléments d'un module")
async def proxy_list_elements(module_id: int, request: Request, _=Depends(get_current_user)):
    return await _proxy("GET", f"/modules/{module_id}/elements", _token(request))


@router.get("/enseignants",                            summary="[Proxy] Lister les enseignants")
async def proxy_list_enseignants(request: Request, _=Depends(get_current_user)):
    return await _proxy("GET", "/enseignants", _token(request))


@router.get("/salles",                                 summary="[Proxy] Lister les salles")
async def proxy_list_salles(request: Request, _=Depends(get_current_user)):
    return await _proxy("GET", "/salles", _token(request))




@router.get("/annees",                                 summary="[Proxy] Lister les années universitaires")
async def proxy_list_annees(request: Request, _=Depends(get_current_user)):
    return await _proxy("GET", "/annees", _token(request))

@router.get("/emploi-du-temps/{semestre_id}",          summary="[Proxy] Emploi du temps d'un semestre")
async def proxy_emploi_du_temps(semestre_id: int, request: Request, _=Depends(get_current_user)):
    return await _proxy("GET", f"/emploi-du-temps/{semestre_id}", _token(request))


# ══════════════════════════════════════════════════════════════════════════════
# ÉCRITURE (POST / PUT / DELETE) — rôle admin requis
# ══════════════════════════════════════════════════════════════════════════════


# ── Années universitaires ─────────────────────────────────────────────────────

@router.post("/annees",                  status_code=201, summary="[Proxy] Créer une année universitaire")
async def proxy_create_annee(request: Request, _=Depends(require_admin)):
    return await _proxy("POST", "/annees", _token(request), await request.json())

@router.delete("/annees/{annee_id}",     status_code=204, summary="[Proxy] Supprimer une année universitaire")
async def proxy_delete_annee(annee_id: int, request: Request, _=Depends(require_admin)):
    return await _proxy("DELETE", f"/annees/{annee_id}", _token(request))


# ── Départements ──────────────────────────────────────────────────────────────

@router.post("/departements",            status_code=201, summary="[Proxy] Créer un département")
async def proxy_create_dept(request: Request, _=Depends(require_admin)):
    return await _proxy("POST", "/departements", _token(request), await request.json())

@router.put("/departements/{dept_id}",                  summary="[Proxy] Modifier un département")
async def proxy_update_dept(dept_id: int, request: Request, _=Depends(require_admin)):
    return await _proxy("PUT", f"/departements/{dept_id}", _token(request), await request.json())

@router.delete("/departements/{dept_id}", status_code=204, summary="[Proxy] Supprimer un département")
async def proxy_delete_dept(dept_id: int, request: Request, _=Depends(require_admin)):
    return await _proxy("DELETE", f"/departements/{dept_id}", _token(request))


# ── Filières ──────────────────────────────────────────────────────────────────

@router.post("/filieres",                status_code=201, summary="[Proxy] Créer une filière")
async def proxy_create_filiere(request: Request, _=Depends(require_admin)):
    return await _proxy("POST", "/filieres", _token(request), await request.json())

@router.put("/filieres/{filiere_id}",                   summary="[Proxy] Modifier une filière")
async def proxy_update_filiere(filiere_id: int, request: Request, _=Depends(require_admin)):
    return await _proxy("PUT", f"/filieres/{filiere_id}", _token(request), await request.json())

@router.delete("/filieres/{filiere_id}", status_code=204, summary="[Proxy] Supprimer une filière")
async def proxy_delete_filiere(filiere_id: int, request: Request, _=Depends(require_admin)):
    return await _proxy("DELETE", f"/filieres/{filiere_id}", _token(request))


# ── Semestres ─────────────────────────────────────────────────────────────────

@router.post("/semestres",               status_code=201, summary="[Proxy] Créer un semestre")
async def proxy_create_semestre(request: Request, _=Depends(require_admin)):
    return await _proxy("POST", "/semestres", _token(request), await request.json())

@router.put("/semestres/{semestre_id}",                 summary="[Proxy] Modifier un semestre")
async def proxy_update_semestre(semestre_id: int, request: Request, _=Depends(require_admin)):
    return await _proxy("PUT", f"/semestres/{semestre_id}", _token(request), await request.json())

@router.delete("/semestres/{semestre_id}", status_code=204, summary="[Proxy] Supprimer un semestre")
async def proxy_delete_semestre(semestre_id: int, request: Request, _=Depends(require_admin)):
    return await _proxy("DELETE", f"/semestres/{semestre_id}", _token(request))


# ── Modules ───────────────────────────────────────────────────────────────────

@router.post("/modules",                 status_code=201, summary="[Proxy] Créer un module")
async def proxy_create_module(request: Request, _=Depends(require_admin)):
    return await _proxy("POST", "/modules", _token(request), await request.json())

@router.put("/modules/{module_id}",                     summary="[Proxy] Modifier un module")
async def proxy_update_module(module_id: int, request: Request, _=Depends(require_admin)):
    return await _proxy("PUT", f"/modules/{module_id}", _token(request), await request.json())

@router.delete("/modules/{module_id}",   status_code=204, summary="[Proxy] Supprimer un module")
async def proxy_delete_module(module_id: int, request: Request, _=Depends(require_admin)):
    return await _proxy("DELETE", f"/modules/{module_id}", _token(request))


# ── Éléments de module ────────────────────────────────────────────────────────

@router.post("/elements",                status_code=201, summary="[Proxy] Créer un élément")
async def proxy_create_element(request: Request, _=Depends(require_admin)):
    return await _proxy("POST", "/elements", _token(request), await request.json())

@router.put("/elements/{element_id}",                   summary="[Proxy] Modifier un élément")
async def proxy_update_element(element_id: int, request: Request, _=Depends(require_admin)):
    return await _proxy("PUT", f"/elements/{element_id}", _token(request), await request.json())

@router.delete("/elements/{element_id}", status_code=204, summary="[Proxy] Supprimer un élément")
async def proxy_delete_element(element_id: int, request: Request, _=Depends(require_admin)):
    return await _proxy("DELETE", f"/elements/{element_id}", _token(request))


# ── Enseignants ───────────────────────────────────────────────────────────────

@router.post("/enseignants",             status_code=201, summary="[Proxy] Enregistrer un enseignant")
async def proxy_create_enseignant(request: Request, _=Depends(require_admin)):
    return await _proxy("POST", "/enseignants", _token(request), await request.json())

@router.put("/enseignants/{ens_id}",                    summary="[Proxy] Modifier un enseignant")
async def proxy_update_enseignant(ens_id: int, request: Request, _=Depends(require_admin)):
    return await _proxy("PUT", f"/enseignants/{ens_id}", _token(request), await request.json())

@router.delete("/enseignants/{ens_id}",  status_code=204, summary="[Proxy] Supprimer un enseignant")
async def proxy_delete_enseignant(ens_id: int, request: Request, _=Depends(require_admin)):
    return await _proxy("DELETE", f"/enseignants/{ens_id}", _token(request))


# ── Salles ────────────────────────────────────────────────────────────────────

@router.post("/salles",                  status_code=201, summary="[Proxy] Créer une salle")
async def proxy_create_salle(request: Request, _=Depends(require_admin)):
    return await _proxy("POST", "/salles", _token(request), await request.json())

@router.put("/salles/{salle_id}",                       summary="[Proxy] Modifier une salle")
async def proxy_update_salle(salle_id: int, request: Request, _=Depends(require_admin)):
    return await _proxy("PUT", f"/salles/{salle_id}", _token(request), await request.json())

@router.delete("/salles/{salle_id}",     status_code=204, summary="[Proxy] Supprimer une salle")
async def proxy_delete_salle(salle_id: int, request: Request, _=Depends(require_admin)):
    return await _proxy("DELETE", f"/salles/{salle_id}", _token(request))


# ── Séances ───────────────────────────────────────────────────────────────────

@router.post("/seances",                 status_code=201, summary="[Proxy] Ajouter une séance")
async def proxy_create_seance(request: Request, _=Depends(require_admin)):
    return await _proxy("POST", "/seances", _token(request), await request.json())

@router.put("/seances/{seance_id}",                     summary="[Proxy] Modifier une séance")
async def proxy_update_seance(seance_id: int, request: Request, _=Depends(require_admin)):
    return await _proxy("PUT", f"/seances/{seance_id}", _token(request), await request.json())

@router.delete("/seances/{seance_id}",   status_code=204, summary="[Proxy] Supprimer une séance")
async def proxy_delete_seance(seance_id: int, request: Request, _=Depends(require_admin)):
    return await _proxy("DELETE", f"/seances/{seance_id}", _token(request))
