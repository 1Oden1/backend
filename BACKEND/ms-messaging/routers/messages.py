from fastapi import APIRouter, Header, HTTPException
from typing import List
from models.schemas import SendMessageRequest, MessageResponse, SuccessResponse
from services.auth_client import verify_token
from services.database import get_connection

router = APIRouter(prefix="/messages", tags=["Messages"])


def get_current_user(authorization: str = None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant")
    token = authorization.split(" ")[1]
    return verify_token(token)


@router.post(
    "/send",
    response_model=SuccessResponse,
    summary="Envoyer un message",
    description="Envoie un message à un autre utilisateur."
)
def send_message(
    request: SendMessageRequest,
    authorization: str = Header(None)
):
    user = get_current_user(authorization)
    sender = user["username"]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (sender_username, receiver_username, content) VALUES (%s, %s, %s)",
        (sender, request.receiver_username, request.content)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return SuccessResponse(message="Message envoyé avec succès")


@router.get(
    "/inbox",
    response_model=List[MessageResponse],
    summary="Messages reçus",
    description="Retourne tous les messages reçus par l'utilisateur connecté."
)
def get_inbox(authorization: str = Header(None)):
    user = get_current_user(authorization)
    username = user["username"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM messages WHERE receiver_username = %s ORDER BY created_at DESC",
        (username,)
    )
    messages = cursor.fetchall()
    cursor.close()
    conn.close()

    return messages


@router.get(
    "/sent",
    response_model=List[MessageResponse],
    summary="Messages envoyés",
    description="Retourne tous les messages envoyés par l'utilisateur connecté."
)
def get_sent(authorization: str = Header(None)):
    user = get_current_user(authorization)
    username = user["username"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM messages WHERE sender_username = %s ORDER BY created_at DESC",
        (username,)
    )
    messages = cursor.fetchall()
    cursor.close()
    conn.close()

    return messages


@router.put(
    "/{message_id}/read",
    response_model=SuccessResponse,
    summary="Marquer comme lu"
)
def mark_as_read(message_id: int, authorization: str = Header(None)):
    user = get_current_user(authorization)
    username = user["username"]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE messages SET is_read = TRUE WHERE id = %s AND receiver_username = %s",
        (message_id, username)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return SuccessResponse(message="Message marqué comme lu")