from cassandra.cluster import Cluster
from cassandra.policies import DCAwareRoundRobinPolicy
from app.config import settings
import logging

logger = logging.getLogger(__name__)
_session = None


def get_session():
    global _session
    if _session is None:
        cluster = Cluster(
            contact_points=[settings.CASSANDRA_HOST],
            load_balancing_policy=DCAwareRoundRobinPolicy(local_dc="datacenter1"),
        )
        _session = cluster.connect()
    return _session


def init_cassandra():
    session = get_session()

    # ── Keyspace ent_messaging ────────────────────────────────────────────────
    session.execute(f"""
        CREATE KEYSPACE IF NOT EXISTS {settings.CASSANDRA_KEYSPACE}
        WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}}
    """)
    session.set_keyspace(settings.CASSANDRA_KEYSPACE)

    # ── Table notifications ───────────────────────────────────────────────────
    # Partitionnée par recipient_id, triée par date décroissante
    session.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            recipient_id      TEXT,
            created_at        TIMESTAMP,
            notification_id   UUID,
            type              TEXT,
            title             TEXT,
            content           TEXT,
            related_id        TEXT,
            is_read           BOOLEAN,
            PRIMARY KEY ((recipient_id), created_at, notification_id)
        ) WITH CLUSTERING ORDER BY (created_at DESC, notification_id ASC)
    """)

    # ── Table conversations ───────────────────────────────────────────────────
    # Table principale pour récupérer une conversation par son ID
    session.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            conversation_id   UUID PRIMARY KEY,
            type              TEXT,
            participant_ids   LIST<TEXT>,
            created_at        TIMESTAMP,
            last_message_at   TIMESTAMP
        )
    """)

    # ── Table conversations_by_user ───────────────────────────────────────────
    # Index secondaire pour lister les conversations d'un utilisateur
    session.execute("""
        CREATE TABLE IF NOT EXISTS conversations_by_user (
            user_id           TEXT,
            last_message_at   TIMESTAMP,
            conversation_id   UUID,
            other_user_id     TEXT,
            other_user_name   TEXT,
            conv_type         TEXT,
            PRIMARY KEY ((user_id), last_message_at, conversation_id)
        ) WITH CLUSTERING ORDER BY (last_message_at DESC, conversation_id ASC)
    """)

    # ── Table messages ────────────────────────────────────────────────────────
    # Partitionnée par conversation_id, triée par date croissante
    # hidden_for : SET des user_id pour qui le message est masqué (soft delete UI)
    session.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            conversation_id   UUID,
            sent_at           TIMESTAMP,
            message_id        UUID,
            sender_id         TEXT,
            sender_name       TEXT,
            content           TEXT,
            hidden_for        SET<TEXT>,
            PRIMARY KEY ((conversation_id), sent_at, message_id)
        ) WITH CLUSTERING ORDER BY (sent_at ASC, message_id ASC)
    """)

    # ── Cache : utilisateurs par filière (alimenté par événements RabbitMQ) ──
    # Remplace les appels HTTP vers ms-notes et ms-calendar
    session.execute("""
        CREATE TABLE IF NOT EXISTS users_by_filiere (
            filiere_id  INT,
            user_id     TEXT,
            role        TEXT,
            PRIMARY KEY ((filiere_id), user_id)
        )
    """)

    # ── Cache : lookup filière d'un étudiant ──────────────────────────────────
    session.execute("""
        CREATE TABLE IF NOT EXISTS student_filiere (
            user_id    TEXT PRIMARY KEY,
            filiere_id INT
        )
    """)

    # ── Cache : noms des filières ─────────────────────────────────────────────
    session.execute("""
        CREATE TABLE IF NOT EXISTS filieres_cache (
            filiere_id INT PRIMARY KEY,
            nom        TEXT
        )
    """)

    logger.info("Cassandra initialisé (ent_messaging : notifications, conversations, messages, cache).")
