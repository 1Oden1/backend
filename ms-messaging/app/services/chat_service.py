"""
Service de chat — ent_messaging.

Matrice des permissions de discussion :
  ┌────────────┬──────────────────────────────────────────────┐
  │ Émetteur   │ Peut discuter avec                           │
  ├────────────┼──────────────────────────────────────────────┤
  │ delegue    │ enseignants de SA filière uniquement         │
  │ enseignant │ admin  +  délégués (de toute filière)        │
  │ admin      │ enseignants uniquement                       │
  └────────────┴──────────────────────────────────────────────┘

Règles supplémentaires :
  - Historique complet visible à chaque accès.
  - La suppression d'un message est UNIQUEMENT côté UI (hidden_for en Cassandra).
  - Le destinataire reçoit une notification "new_message".
  - L'admin peut diffuser un message à TOUS les enseignants (broadcast).
"""

import uuid
import logging
from datetime import datetime, timezone

from app.database_cassandra import get_session_with_keyspace
from app.config import settings
from app.services.notification_service import notify_new_message

logger = logging.getLogger(__name__)

# ── Helpers Cassandra ─────────────────────────────────────────────────────────

def _session():
    """Retourne une session Cassandra avec keyspace prêt (self-healing)."""
    return get_session_with_keyspace()


# ── Permissions ───────────────────────────────────────────────────────────────

def check_chat_permission(
    sender_roles:    list[str],
    sender_user_id:  str,
    target_user_id:  str,
    target_roles:    list[str],
) -> tuple[bool, str]:
    """
    Vérifie si l'émetteur a le droit de démarrer/envoyer un message au destinataire.
    Retourne (autorisé: bool, raison: str).
    """
    from app.http_clients import get_filiere_id_of_student, get_teachers_of_filiere

    sender_is_admin      = "admin"      in sender_roles
    sender_is_enseignant = "enseignant" in sender_roles
    sender_is_delegue    = "delegue"    in sender_roles
    sender_is_etudiant   = "etudiant"   in sender_roles and not sender_is_delegue

    target_is_admin      = "admin"      in target_roles
    target_is_enseignant = "enseignant" in target_roles
    target_is_delegue    = "delegue"    in target_roles

    # Les étudiants non-délégués n'ont pas accès au chat
    if sender_is_etudiant and not sender_is_delegue:
        return False, "Les étudiants non délégués n'ont pas accès au chat."

    # ── Admin → tous les utilisateurs avec un rôle reconnu ───────────────────
    if sender_is_admin:
        # "unknown" = on n'a pas pu récupérer les rôles, on laisse passer
        if "unknown" in target_roles:
            return True, "ok"
        if target_is_enseignant or target_is_admin or target_is_delegue:
            return True, "ok"
        return False, "L'admin ne peut discuter qu'avec les enseignants ou délégués."

    # ── Enseignant → Admin ou Délégué ─────────────────────────────────────────
    if sender_is_enseignant:
        if target_is_admin or target_is_delegue:
            return True, "ok"
        return False, "L'enseignant ne peut discuter qu'avec l'admin ou un délégué."

    # ── Délégué → Enseignants de SA filière uniquement ────────────────────────
    if sender_is_delegue:
        if not target_is_enseignant:
            return False, "Le délégué ne peut discuter qu'avec les enseignants de sa filière."

        # Vérifier que l'enseignant appartient à la filière du délégué
        filiere_id = get_filiere_id_of_student(sender_user_id)
        if filiere_id is None:
            # Délégué non inscrit dans ms-notes → on laisse passer (dégradé)
            logger.warning("Filière du délégué %s introuvable — permission accordée par défaut", sender_user_id)
            return True, "ok"

        teachers_of_filiere = get_teachers_of_filiere(filiere_id)
        if not teachers_of_filiere:
            # Aucun enseignant trouvé (séances pas encore créées) → laisser passer
            logger.warning("Aucun enseignant pour filière %s — permission accordée par défaut", filiere_id)
            return True, "ok"

        if target_user_id not in teachers_of_filiere:
            return False, "Ce délégué ne peut contacter que les enseignants de sa filière."

        return True, "ok"

    return False, "Rôle expéditeur non reconnu pour le chat."


# ── Conversations ─────────────────────────────────────────────────────────────

def get_or_create_conversation(
    user_a_id:   str,
    user_a_name: str,
    user_b_id:   str,
    user_b_name: str,
    conv_type:   str = "direct",
) -> str:
    """
    Cherche une conversation directe existante entre deux utilisateurs.
    Si elle n'existe pas, la crée.
    Retourne le conversation_id (str UUID).
    """
    s = _session()

    # Cherche dans conversations_by_user
    existing = s.execute(
        "SELECT conversation_id, other_user_id FROM conversations_by_user "
        "WHERE user_id = %s ALLOW FILTERING",
        (user_a_id,),
    )
    for row in existing:
        if str(row.other_user_id) == user_b_id:
            return str(row.conversation_id)

    # Création nouvelle conversation
    conv_id = uuid.uuid4()
    now     = datetime.now(timezone.utc)

    s.execute(
        """
        INSERT INTO conversations
               (conversation_id, type, participant_ids, created_at, last_message_at)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (conv_id, conv_type, [user_a_id, user_b_id], now, now),
    )

    # Index pour user_a
    s.execute(
        """
        INSERT INTO conversations_by_user
               (user_id, last_message_at, conversation_id, other_user_id, other_user_name, conv_type)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (user_a_id, now, conv_id, user_b_id, user_b_name, conv_type),
    )

    # Index pour user_b
    s.execute(
        """
        INSERT INTO conversations_by_user
               (user_id, last_message_at, conversation_id, other_user_id, other_user_name, conv_type)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (user_b_id, now, conv_id, user_a_id, user_a_name, conv_type),
    )

    return str(conv_id)


def list_conversations(user_id: str, limit: int = 30) -> list[dict]:
    """Retourne les conversations récentes d'un utilisateur (limit messages)."""
    s = _session()
    rows = s.execute(
        "SELECT last_message_at, conversation_id, other_user_id, other_user_name, conv_type "
        "FROM conversations_by_user WHERE user_id = %s LIMIT %s",
        (user_id, limit),
    )
    return [
        {
            "conversation_id": str(r.conversation_id),
            "type":            r.conv_type,
            "other_user_id":   r.other_user_id,
            "other_user_name": r.other_user_name,
            "last_message_at": r.last_message_at,
        }
        for r in rows
    ]


# ── Messages ──────────────────────────────────────────────────────────────────

def send_message(
    conversation_id: str,
    sender_id:       str,
    sender_name:     str,
    content:         str,
    recipients:      list[str],   # pour la notification
) -> dict:
    """
    Insère un message dans la conversation et envoie une notification
    à tous les participants sauf l'émetteur.
    """
    s        = _session()
    conv_uuid = uuid.UUID(conversation_id)
    msg_id   = uuid.uuid4()
    sent_at  = datetime.now(timezone.utc)

    s.execute(
        """
        INSERT INTO messages
               (conversation_id, sent_at, message_id, sender_id, sender_name, content, hidden_for)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (conv_uuid, sent_at, msg_id, sender_id, sender_name, content, set()),
    )

    # Mise à jour last_message_at dans conversations_by_user pour chaque participant
    conv_row = s.execute(
        "SELECT participant_ids FROM conversations WHERE conversation_id = %s",
        (conv_uuid,),
    ).one()

    participants = conv_row.participant_ids if conv_row else recipients + [sender_id]

    for uid in participants:
        # Récupérer la ligne existante pour connaître other_user_id/name
        try:
            existing = s.execute(
                "SELECT other_user_id, other_user_name, conv_type, last_message_at "
                "FROM conversations_by_user WHERE user_id = %s ALLOW FILTERING",
                (uid,),
            )
            for row in existing:
                if str(row.other_user_id) in participants:
                    # Supprimer l'ancienne entrée (clustering key changed)
                    s.execute(
                        "DELETE FROM conversations_by_user "
                        "WHERE user_id = %s AND last_message_at = %s AND conversation_id = %s",
                        (uid, row.last_message_at, conv_uuid),
                    )
                    # Réinsérer avec last_message_at mis à jour
                    s.execute(
                        """
                        INSERT INTO conversations_by_user
                               (user_id, last_message_at, conversation_id,
                                other_user_id, other_user_name, conv_type)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (uid, sent_at, conv_uuid,
                         row.other_user_id, row.other_user_name, row.conv_type),
                    )
                    break
        except Exception as exc:
            logger.warning("Erreur MAJ conversations_by_user pour %s : %s", uid, exc)

    # Notification aux destinataires (hors expéditeur)
    for uid in participants:
        if uid != sender_id:
            notify_new_message(uid, sender_name, conversation_id, content)

    return {
        "message_id":      str(msg_id),
        "conversation_id": conversation_id,
        "sender_id":       sender_id,
        "sender_name":     sender_name,
        "content":         content,
        "sent_at":         sent_at,
        "is_hidden":       False,
    }


def get_messages(conversation_id: str, current_user_id: str, limit: int = 100) -> list[dict]:
    """
    Retourne l'historique des messages d'une conversation.
    Les messages soft-deletés par l'utilisateur courant sont marqués is_hidden=True.
    """
    s = _session()
    rows = s.execute(
        "SELECT message_id, sender_id, sender_name, content, sent_at, hidden_for "
        "FROM messages WHERE conversation_id = %s LIMIT %s",
        (uuid.UUID(conversation_id), limit),
    )
    return [
        {
            "message_id":      str(r.message_id),
            "conversation_id": conversation_id,
            "sender_id":       r.sender_id,
            "sender_name":     r.sender_name,
            "content":         r.content,
            "sent_at":         r.sent_at,
            "is_hidden":       (r.hidden_for is not None and current_user_id in r.hidden_for),
        }
        for r in rows
    ]


def soft_delete_message(
    conversation_id: str,
    sent_at:         datetime,
    message_id:      str,
    user_id:         str,
) -> bool:
    """
    Masque un message uniquement pour l'utilisateur courant (soft delete UI).
    Le message reste en Cassandra avec hidden_for mis à jour.
    """
    s = _session()
    try:
        s.execute(
            """
            UPDATE messages
            SET hidden_for = hidden_for + %s
            WHERE conversation_id = %s AND sent_at = %s AND message_id = %s
            """,
            ({user_id}, uuid.UUID(conversation_id), sent_at, uuid.UUID(message_id)),
        )
        return True
    except Exception as exc:
        logger.error("Erreur soft_delete_message : %s", exc)
        return False


# ── Broadcast admin ───────────────────────────────────────────────────────────

def send_broadcast(
    admin_id:   str,
    admin_name: str,
    content:    str,
) -> dict:
    """
    L'admin diffuse un message à TOUS les enseignants.
    Crée une conversation broadcast par enseignant cible
    et insère un message dans chacune.
    Retourne le nombre d'enseignants notifiés.
    """
    from app.http_clients import get_all_teachers_user_ids

    teachers = get_all_teachers_user_ids()
    count    = 0

    for teacher_id in teachers:
        try:
            conv_id = get_or_create_conversation(
                user_a_id   = admin_id,
                user_a_name = admin_name,
                user_b_id   = teacher_id,
                user_b_name = "Enseignant",
                conv_type   = "broadcast",
            )
            send_message(
                conversation_id = conv_id,
                sender_id       = admin_id,
                sender_name     = admin_name,
                content         = content,
                recipients      = [teacher_id],
            )
            count += 1
        except Exception as exc:
            logger.error("Erreur broadcast pour enseignant %s : %s", teacher_id, exc)

    logger.info("Broadcast admin → %d enseignants notifiés", count)
    return {"count": count, "detail": f"Message diffusé à {count} enseignant(s)."}
