"""
Router proxy notes — ms-admin

ms-admin NE touche PAS à ent_notes.
Chaque endpoint ici fait un appel HTTP vers ms-notes et retransmet la réponse.

Depuis le passage à l'Option 2 (ms-calendar = source de vérité pour la structure
académique), les routes années/départements/filières/semestres/modules/éléments
ont été supprimées de ce proxy → elles sont désormais dans calendar_proxy.

Routes disponibles ici (données propres à ms-notes) :
  Étudiants   : CRUD
  Enseignants : CRUD
  Notes       : saisie, consultation, publication
  Demandes    : relevés, classements
"""

import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.auth import require_admin, get_current_user
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notes", tags=["Proxy → ms-notes"])


def _notes_url(path: str) -> str:
    return f"{settings.MS_NOTES_URL}/api/v1/notes{path}"


def _token(request: Request) -> str:
    return request.headers.get("Authorization", "").removeprefix("Bearer ").strip()


async def _proxy(method: str, path: str, token: str, body: Any = None, params: dict | None = None) -> JSONResponse:
    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.request(method=method, url=_notes_url(path),
                                        json=body, params=params, headers=headers)
    except httpx.RequestError as exc:
        logger.error("ms-notes inaccessible : %s", exc)
        raise HTTPException(502, "ms-notes est inaccessible.")
    return JSONResponse(content=resp.json() if resp.content else None, status_code=resp.status_code)


# ── Étudiants ─────────────────────────────────────────────────────────────────

@router.post("/admin/etudiants",          status_code=201, summary="[Proxy] Inscrire un étudiant")
async def proxy_create_etudiant(request: Request, _=Depends(require_admin)):
    return await _proxy("POST", "/admin/etudiants", _token(request), await request.json())


@router.get("/admin/etudiants",                            summary="[Proxy] Lister les étudiants")
async def proxy_list_etudiants(request: Request, _=Depends(require_admin)):
    return await _proxy("GET", "/admin/etudiants", _token(request), params=dict(request.query_params))


@router.get("/admin/etudiants/{etudiant_id}",              summary="[Proxy] Détail étudiant")
async def proxy_get_etudiant(etudiant_id: int, request: Request, _=Depends(require_admin)):
    return await _proxy("GET", f"/admin/etudiants/{etudiant_id}", _token(request))


@router.delete("/admin/etudiants/{etudiant_id}", status_code=204, summary="[Proxy] Supprimer un étudiant")
async def proxy_delete_etudiant(etudiant_id: int, request: Request, _=Depends(require_admin)):
    return await _proxy("DELETE", f"/admin/etudiants/{etudiant_id}", _token(request))


# ── Enseignants ───────────────────────────────────────────────────────────────

@router.post("/admin/enseignants",        status_code=201, summary="[Proxy] Enregistrer un enseignant")
async def proxy_create_enseignant(request: Request, _=Depends(require_admin)):
    return await _proxy("POST", "/admin/enseignants", _token(request), await request.json())


@router.get("/admin/enseignants",                          summary="[Proxy] Lister les enseignants (notes)")
async def proxy_list_enseignants(request: Request, _=Depends(require_admin)):
    return await _proxy("GET", "/admin/enseignants", _token(request))


# ── Notes ─────────────────────────────────────────────────────────────────────

@router.post("/admin/notes",              status_code=201, summary="[Proxy] Saisir une note (UPSERT)")
async def proxy_upsert_note(request: Request, _=Depends(require_admin)):
    return await _proxy("POST", "/admin/notes", _token(request), await request.json())


@router.get("/admin/etudiants/{etudiant_id}/notes",        summary="[Proxy] Notes d'un étudiant")
async def proxy_notes_etudiant(etudiant_id: int, request: Request, _=Depends(require_admin)):
    return await _proxy("GET", f"/admin/etudiants/{etudiant_id}/notes", _token(request))


@router.delete("/admin/notes/{note_id}", status_code=204,  summary="[Proxy] Supprimer une note")
async def proxy_delete_note(note_id: int, request: Request, _=Depends(require_admin)):
    return await _proxy("DELETE", f"/admin/notes/{note_id}", _token(request))


@router.post("/admin/semestres/{semestre_id}/filieres/{filiere_id}/publier",
             status_code=202, summary="[Proxy] Publier les notes d'un semestre")
async def proxy_publier_notes(semestre_id: int, filiere_id: int, request: Request, _=Depends(require_admin)):
    return await _proxy("POST", f"/admin/semestres/{semestre_id}/filieres/{filiere_id}/publier",
                        _token(request), params=dict(request.query_params))


# ── Demandes ──────────────────────────────────────────────────────────────────

@router.get("/admin/demandes-releve",                      summary="[Proxy] Demandes de relevé")
async def proxy_list_releve(request: Request, _=Depends(require_admin)):
    return await _proxy("GET", "/admin/demandes-releve", _token(request), params=dict(request.query_params))


@router.patch("/admin/demandes-releve/{demande_id}",       summary="[Proxy] Traiter une demande de relevé")
async def proxy_traiter_releve(demande_id: int, request: Request, _=Depends(require_admin)):
    return await _proxy("PATCH", f"/admin/demandes-releve/{demande_id}", _token(request), await request.json())


@router.get("/admin/demandes-classement",                  summary="[Proxy] Demandes de classement")
async def proxy_list_classement(request: Request, _=Depends(require_admin)):
    return await _proxy("GET", "/admin/demandes-classement", _token(request), params=dict(request.query_params))


@router.patch("/admin/demandes-classement/{demande_id}",   summary="[Proxy] Traiter une demande de classement")
async def proxy_traiter_classement(demande_id: int, request: Request, _=Depends(require_admin)):
    return await _proxy("PATCH", f"/admin/demandes-classement/{demande_id}", _token(request), await request.json())
