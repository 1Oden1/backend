"""
events.py — ms-calendar

Publie des événements sur RabbitMQ quand la structure académique change.
ms-messaging consomme ces événements pour mettre à jour son cache Cassandra.

Routing keys émises :
  filiere.created          → {filiere_id, nom}
  filiere.updated          → {filiere_id, nom}
  filiere.deleted          → {filiere_id}
  teacher.filiere.linked   → {user_id, filiere_id}
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
                "ent.events", aio_pika.ExchangeType.TOPIC, durable=True
            )
            await exchange.publish(
                aio_pika.Message(
                    body=json.dumps(payload).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=routing_key,
            )
            logger.info("Evenement publie : %s → %s", routing_key, payload)
    except Exception as exc:
        logger.error("Erreur publication [%s] : %s", routing_key, exc)


async def publish_filiere_created(filiere_id: int, nom: str) -> None:
    await _publish("filiere.created", {"filiere_id": filiere_id, "nom": nom})


async def publish_filiere_updated(filiere_id: int, nom: str) -> None:
    await _publish("filiere.updated", {"filiere_id": filiere_id, "nom": nom})


async def publish_filiere_deleted(filiere_id: int) -> None:
    await _publish("filiere.deleted", {"filiere_id": filiere_id})


async def publish_teacher_filiere_linked(user_id: str, filiere_id: int) -> None:
    await _publish("teacher.filiere.linked", {"user_id": user_id, "filiere_id": filiere_id})
