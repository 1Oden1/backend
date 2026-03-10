"""
events.py — ms-notes
Publie des événements sur RabbitMQ quand la structure des utilisateurs change.
ms-messaging consomme ces événements pour mettre à jour son cache local.

Routing keys émises :
  user.student.created  → {user_id, filiere_id}
  user.student.deleted  → {user_id, filiere_id}
  user.teacher.created  → {user_id}
  user.teacher.deleted  → {user_id}
"""
import json
import logging

import aio_pika

from app.config import settings

logger = logging.getLogger(__name__)


async def _publish(routing_key: str, payload: dict) -> None:
    try:
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL, timeout=5.0)
        async with connection:
            channel  = await connection.channel()
            exchange = await channel.declare_exchange(
                "ent.events", aio_pika.ExchangeType.TOPIC, durable=True,
            )
            await exchange.publish(
                aio_pika.Message(
                    body=json.dumps(payload).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=routing_key,
            )
            logger.info("Événement publié : %s → %s", routing_key, payload)
    except Exception as exc:
        logger.error("Erreur publication RabbitMQ [%s] : %s", routing_key, exc)


async def publish_student_created(user_id: str, filiere_id: int) -> None:
    await _publish("user.student.created", {"user_id": user_id, "filiere_id": filiere_id})


async def publish_student_deleted(user_id: str, filiere_id: int) -> None:
    await _publish("user.student.deleted", {"user_id": user_id, "filiere_id": filiere_id})


async def publish_teacher_created(user_id: str) -> None:
    await _publish("user.teacher.created", {"user_id": user_id})


async def publish_teacher_deleted(user_id: str) -> None:
    await _publish("user.teacher.deleted", {"user_id": user_id})
