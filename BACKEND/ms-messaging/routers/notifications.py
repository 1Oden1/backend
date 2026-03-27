from fastapi import APIRouter, Header, HTTPException
from typing import List
from models.schemas import NotificationRequest, NotificationResponse, SuccessResponse
from services.auth_client import verify_token
from services.database import get_connection

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def get_current_user(authorization: str = None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant")
    token = authorization.split(" ")[1]
    return verify_token(token)


@router.post(
    "/send",
    response_model=SuccessResponse,
    summary="Envoyer une notification",
    description="Envoie une notification à un utilisateur. Réservé aux admins et enseignants."
)
def send_notification(
    request: NotificationRequest,
    authorization: str = Header(None)
):
    user = get_current_user(authorization)

    if user["role"] not in ["admin", "teacher", "enseignant"]:
        raise HTTPException(status_code=403, detail="Accès réservé aux admins et enseignants")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO notifications (receiver_username, title, message, type) VALUES (%s, %s, %s, %s)",
        (request.receiver_username, request.title, request.message, request.type)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return SuccessResponse(message="Notification envoyée avec succès")


@router.get(
    "/",
    response_model=List[NotificationResponse],
    summary="Mes notifications",
    description="Retourne toutes les notifications de l'utilisateur connecté."
)
def get_notifications(authorization: str = Header(None)):
    user = get_current_user(authorization)
    username = user["username"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM notifications WHERE receiver_username = %s ORDER BY created_at DESC",
        (username,)
    )
    notifications = cursor.fetchall()
    cursor.close()
    conn.close()

    return notifications


@router.put(
    "/{notif_id}/read",
    response_model=SuccessResponse,
    summary="Marquer notification comme lue"
)
def mark_notification_read(notif_id: int, authorization: str = Header(None)):
    user = get_current_user(authorization)
    username = user["username"]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE notifications SET is_read = TRUE WHERE id = %s AND receiver_username = %s",
        (notif_id, username)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return SuccessResponse(message="Notification marquée comme lue")