"""
RabbitMQ — Publisher + Consumer asynchrone (aio_pika).

Exchange : ent.events  (topic)
Queue    : ms_messaging_queue

Routing keys consommées :
  Notifications :
    filiere.event           → notifier étudiants + enseignants de la filière
    schedule.update         → notifier l'enseignant concerné
    grades.reminder         → notifier les enseignants pour dépôt des notes
    grades.available        → notifier étudiants + enseignants de la filière

  Cache (alimentent le cache Cassandra local — élimine les appels HTTP) :
    user.student.created    → ajouter étudiant au cache
    user.student.deleted    → supprimer étudiant du cache
    user.teacher.created    → enregistrer enseignant (pas de filière à ce stade)
    user.teacher.deleted    → supprimer enseignant du cache
    teacher.filiere.linked  → associer enseignant à une filière
    filiere.created         → ajouter filière au cache
    filiere.updated         → mettre à jour le nom de la filière
    filiere.deleted         → supprimer filière du cache
"""

import json
import asyncio
import logging
import aio_pika
from app.config import settings

logger = logging.getLogger(__name__)


# ── Publisher synchrone (utilisé par les autres MS via HTTP) ─────────────────
# Ce MS n'a pas besoin de publier lui-même, mais on expose la fonction
# pour pouvoir la réutiliser en cas d'extension future.

async def publish_event(routing_key: str, payload: dict) -> None:
    """Publie un événement sur l'exchange ent.events."""
    try:
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        async with connection:
            channel = await connection.channel()
            exchange = await channel.declare_exchange(
                settings.RABBITMQ_EXCHANGE,
                aio_pika.ExchangeType.TOPIC,
                durable=True,
            )
            await exchange.publish(
                aio_pika.Message(
                    body=json.dumps(payload).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=routing_key,
            )
            logger.info("Événement publié : %s", routing_key)
    except Exception as exc:
        logger.error("Erreur publication RabbitMQ [%s] : %s", routing_key, exc)


# ── Consumer asynchrone ───────────────────────────────────────────────────────

async def start_consumer() -> None:
    """
    Lance le consumer RabbitMQ en arrière-plan.
    S'exécute dans le contexte de démarrage FastAPI (lifespan).
    Reconnexion automatique via connect_robust.
    """
    # Import ici pour éviter les imports circulaires
    from app.services.notification_service import (
        notify_filiere_event,
        notify_schedule_update,
        notify_grade_reminder,
        notify_grades_available,
    )
    from app.cache import (
        cache_student_created, cache_student_deleted,
        cache_teacher_linked,  cache_teacher_deleted,
        cache_filiere_upsert,  cache_filiere_deleted,
    )

    async def _handle_student_created(payload: dict):
        cache_student_created(payload["user_id"], payload["filiere_id"])

    async def _handle_student_deleted(payload: dict):
        cache_student_deleted(payload["user_id"], payload["filiere_id"])

    async def _handle_teacher_linked(payload: dict):
        cache_teacher_linked(payload["user_id"], payload["filiere_id"])

    async def _handle_teacher_deleted(payload: dict):
        cache_teacher_deleted(payload["user_id"])

    async def _handle_filiere_upsert(payload: dict):
        cache_filiere_upsert(payload["filiere_id"], payload["nom"])

    async def _handle_filiere_deleted(payload: dict):
        cache_filiere_deleted(payload["filiere_id"])

    handlers = {
        # ── Notifications ──────────────────────────────────────────────────
        "filiere.event":           notify_filiere_event,
        "schedule.update":         notify_schedule_update,
        "grades.reminder":         notify_grade_reminder,
        "grades.available":        notify_grades_available,
        # ── Cache utilisateurs ─────────────────────────────────────────────
        "user.student.created":    _handle_student_created,
        "user.student.deleted":    _handle_student_deleted,
        "user.teacher.created":    lambda p: None,   # enregistrement simple, pas de filière
        "user.teacher.deleted":    _handle_teacher_deleted,
        "teacher.filiere.linked":  _handle_teacher_linked,
        # ── Cache filières ─────────────────────────────────────────────────
        "filiere.created":         _handle_filiere_upsert,
        "filiere.updated":         _handle_filiere_upsert,
        "filiere.deleted":         _handle_filiere_deleted,
    }

    try:
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        channel    = await connection.channel()
        await channel.set_qos(prefetch_count=10)

        exchange = await channel.declare_exchange(
            settings.RABBITMQ_EXCHANGE,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )

        queue = await channel.declare_queue(
            settings.RABBITMQ_QUEUE,
            durable=True,
        )

        # Liaison sur toutes les routing keys gérées
        for rk in handlers:
            await queue.bind(exchange, routing_key=rk)

        logger.info("Consumer RabbitMQ démarré — en attente d'événements.")

        async with queue.iterator() as q_iter:
            async for message in q_iter:
                async with message.process(ignore_processed=True):
                    try:
                        payload  = json.loads(message.body.decode())
                        rk       = message.routing_key or ""
                        handler  = handlers.get(rk)
                        if handler:
                            await handler(payload)
                        else:
                            logger.warning("Routing key non gérée : %s", rk)
                        await message.ack()
                    except Exception as exc:
                        logger.error(
                            "Erreur traitement message [%s] : %s",
                            message.routing_key, exc,
                        )
                        await message.nack(requeue=True)

    except Exception as exc:
        logger.error("Erreur consumer RabbitMQ : %s", exc)
        # Tentative de reconnexion après délai
        await asyncio.sleep(5)
        asyncio.create_task(start_consumer())
