"""
Router : /api/v1/messaging/chat

Endpoints :
  GET    /conversations                          → mes conversations
  POST   /conversations                          → démarrer/récupérer une conv directe
  GET    /conversations/{id}/messages            → historique de la conversation
  POST   /conversations/{id}/messages            → envoyer un message
  DELETE /conversations/{id}/messages/{msg_id}  → soft-delete UI (masquer pour moi)
  POST   /broadcast                              → [admin] message à tous les enseignants

Matrice des permissions :
  delegue    → enseignants de sa filière uniquement
  enseignant → admin + délégués
  admin      → enseignants uniquement  |  broadcast vers tous les enseignants
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from datetime import datetime

from app.auth import (
    get_current_user, require_admin, require_any, get_user_roles,
)
from app.schemas import (
    ConversationStartIn, ConversationRead, MessageIn,
    MessageListResponse, MessageRead, BroadcastIn, AckResponse,
)
from app.services.chat_service import (
    check_chat_permission,
    get_or_create_conversation,
    list_conversations,
    send_message,
    get_messages,
    soft_delete_message,
    send_broadcast,
)

router = APIRouter(prefix="/chat", tags=["Chat"])


# ── Utilitaire interne ────────────────────────────────────────────────────────

def _display_name(user: dict) -> str:
    """Reconstruit le nom affiché depuis le token Keycloak."""
    return (
        f"{user.get('given_name', '')} {user.get('family_name', '')}".strip()
        or user.get("preferred_username", user["sub"])
    )


def _get_target_roles(target_user_id: str, caller_token: str = "") -> list[str]:
    """
    Récupère les rôles d'un utilisateur cible via ms-admin (qui interroge Keycloak).
    Utilise le token JWT de l'appelant pour s'authentifier auprès de ms-admin.

    En cas d'erreur (ms-admin indisponible, user introuvable), retourne ["unknown"]
    pour ne pas bloquer la messagerie : la permission sera accordée par défaut à l'admin.
    """
    import httpx
    from app.config import settings

    if not caller_token:
        # Pas de token → impossible de vérifier → on laisse passer (admin a déjà son JWT validé)
        return ["unknown"]

    try:
        resp = httpx.get(
            f"{settings.MS_ADMIN_URL}/api/v1/admin/users/{target_user_id}",
            headers={"Authorization": f"Bearer {caller_token}"},
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            roles = data.get("roles", [])
            # Si roles vide mais user existe → on met "unknown" pour ne pas bloquer
            return roles if roles else ["unknown"]
        # User non trouvé dans ms-admin → peut être un user valide sans profil admin
        return ["unknown"]
    except Exception:
        # ms-admin indisponible → on ne bloque pas
        return ["unknown"]


# ── Conversations ─────────────────────────────────────────────────────────────

@router.get(
    "/conversations",
    response_model=list[ConversationRead],
    summary="Lister mes conversations (les plus récentes en premier)",
)
def my_conversations(
    limit: int  = Query(30, ge=1, le=100),
    user:  dict = Depends(require_any),
):
    return list_conversations(user["sub"], limit=limit)


@router.post(
    "/conversations",
    response_model=ConversationRead,
    status_code=201,
    summary="Démarrer ou récupérer une conversation directe",
)
def start_conversation(
    body:    ConversationStartIn,
    request: Request,
    user:    dict = Depends(require_any),
):
    """
    Vérifie les permissions de discussion selon la matrice métier,
    puis crée ou retourne la conversation existante.
    """
    sender_roles = get_user_roles(user)

    # Récupérer les rôles du destinataire de façon robuste
    caller_token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    target_roles = _get_target_roles(body.target_user_id, caller_token)

    # Si les rôles sont fournis dans la requête (frontend enrichi), les utiliser directement
    if hasattr(body, 'target_user_roles') and body.target_user_roles:
        target_roles = body.target_user_roles

    # Si on n'a pas pu récupérer les rôles, utiliser ["unknown"]
    # L'admin peut toujours initier une conversation
    if not target_roles:
        target_roles = ["unknown"]

    allowed, reason = check_chat_permission(
        sender_roles   = sender_roles,
        sender_user_id = user["sub"],
        target_user_id = body.target_user_id,
        target_roles   = target_roles,
    )
    if not allowed:
        raise HTTPException(403, reason)

    sender_name = _display_name(user)
    conv_id = get_or_create_conversation(
        user_a_id   = user["sub"],
        user_a_name = sender_name,
        user_b_id   = body.target_user_id,
        user_b_name = body.target_user_name,
        conv_type   = "direct",
    )

    return {
        "conversation_id": conv_id,
        "type":            "direct",
        "other_user_id":   body.target_user_id,
        "other_user_name": body.target_user_name,
        "last_message_at": None,
    }


# ── Messages ──────────────────────────────────────────────────────────────────

@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=MessageListResponse,
    summary="Récupérer l'historique complet d'une conversation",
)
def get_history(
    conversation_id: str,
    limit:           int  = Query(100, ge=1, le=500),
    user:            dict = Depends(require_any),
):
    """
    Retourne tous les messages visibles par l'utilisateur courant.
    Les messages soft-deletés (hidden_for contient user_id) sont marqués is_hidden=True
    mais inclus dans la réponse (visibles côté serveur, masqués côté UI).
    """
    messages = get_messages(conversation_id, user["sub"], limit=limit)
    return {"conversation_id": conversation_id, "messages": messages}


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageRead,
    status_code=201,
    summary="Envoyer un message dans une conversation",
)
def post_message(
    conversation_id: str,
    body:            MessageIn,
    user:            dict = Depends(require_any),
):
    """
    Insère le message en Cassandra et envoie une notification au(x) destinataire(s).
    """
    sender_name = _display_name(user)
    msg = send_message(
        conversation_id = conversation_id,
        sender_id       = user["sub"],
        sender_name     = sender_name,
        content         = body.content,
        recipients      = [],   # déduit depuis la table conversations
    )
    return msg


@router.delete(
    "/conversations/{conversation_id}/messages/{message_id}",
    response_model=AckResponse,
    summary="Masquer un message pour moi (soft delete — le message reste en base)",
)
def delete_message(
    conversation_id: str,
    message_id:      str,
    sent_at_iso:     str  = Query(
        ..., description="Timestamp ISO 8601 du message (clé de clustering Cassandra)"
    ),
    user:            dict = Depends(require_any),
):
    """
    Le message est masqué UNIQUEMENT sur l'interface de l'utilisateur courant.
    Il reste stocké dans Cassandra et visible pour les autres participants.
    """
    try:
        sent_at = datetime.fromisoformat(sent_at_iso)
    except ValueError:
        raise HTTPException(400, "Format de sent_at invalide. Utilisez ISO 8601.")

    ok = soft_delete_message(conversation_id, sent_at, message_id, user["sub"])
    if not ok:
        raise HTTPException(500, "Impossible de masquer le message.")
    return {"detail": "Message masqué pour vous. Il reste visible pour les autres participants."}


# ── Broadcast ─────────────────────────────────────────────────────────────────

@router.post(
    "/broadcast",
    response_model=AckResponse,
    status_code=202,
    summary="[Admin] Diffuser un message à tous les enseignants",
)
def broadcast_to_all_teachers(
    body:   BroadcastIn,
    admin:  dict = Depends(require_admin),
):
    """
    L'administrateur peut envoyer un message à TOUS les enseignants simultanément.
    Chaque enseignant reçoit le message dans sa conversation individuelle avec l'admin,
    ainsi qu'une notification push.
    """
    admin_name = _display_name(admin)
    result = send_broadcast(
        admin_id   = admin["sub"],
        admin_name = admin_name,
        content    = body.content,
    )
    return {"detail": result["detail"], "count": result["count"]}
