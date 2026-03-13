from cassandra.cluster import Cluster
from cassandra.policies import DCAwareRoundRobinPolicy
from app.config import settings
import logging
import time

logger = logging.getLogger(__name__)
_session = None
_keyspace_ready = False   # True une fois le keyspace créé et sélectionné


def get_session():
    """
    Connexion lazy à Cassandra avec retry exponentiel (3 tentatives).
    Ne lève une exception que si les 3 tentatives échouent.
    """
    global _session
    if _session is not None:
        return _session

    last_err = None
    for attempt in range(3):
        try:
            cluster = Cluster(
                contact_points=[settings.CASSANDRA_HOST],
                load_balancing_policy=DCAwareRoundRobinPolicy(local_dc="datacenter1"),
                connect_timeout=10,
            )
            _session = cluster.connect()
            logger.info("Cassandra connecté (tentative %d).", attempt + 1)
            return _session
        except Exception as e:
            last_err = e
            wait = 2 ** attempt
            logger.warning("Cassandra connexion échouée (tentative %d) : %s — retry dans %ds", attempt + 1, e, wait)
            time.sleep(wait)

    raise RuntimeError(f"Impossible de se connecter à Cassandra après 3 tentatives : {last_err}")


def get_session_with_keyspace():
    """
    Retourne une session Cassandra avec le keyspace ent_messaging prêt.
    Crée le keyspace + les tables si absents (self-healing).
    Utilisé par chat_service et notification_service à la place de get_session().
    """
    global _keyspace_ready
    s = get_session()
    if not _keyspace_ready:
        _ensure_keyspace(s)
    return s


def _ensure_keyspace(s):
    """Crée le keyspace et les tables si absents — idempotent."""
    global _keyspace_ready
    try:
        s.execute(f"""
            CREATE KEYSPACE IF NOT EXISTS {settings.CASSANDRA_KEYSPACE}
            WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}}
        """)
        s.set_keyspace(settings.CASSANDRA_KEYSPACE)
        _create_tables(s)
        _keyspace_ready = True
        logger.info("Keyspace %s prêt.", settings.CASSANDRA_KEYSPACE)
    except Exception as e:
        logger.error("_ensure_keyspace échoué : %s", e)
        raise


def _create_tables(s):
    s.execute("""
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
    s.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            conversation_id   UUID PRIMARY KEY,
            type              TEXT,
            participant_ids   LIST<TEXT>,
            created_at        TIMESTAMP,
            last_message_at   TIMESTAMP
        )
    """)
    s.execute("""
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
    s.execute("""
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
    s.execute("""
        CREATE TABLE IF NOT EXISTS users_by_filiere (
            filiere_id  INT,
            user_id     TEXT,
            role        TEXT,
            PRIMARY KEY ((filiere_id), user_id)
        )
    """)
    s.execute("""
        CREATE TABLE IF NOT EXISTS student_filiere (
            user_id    TEXT PRIMARY KEY,
            filiere_id INT
        )
    """)
    s.execute("""
        CREATE TABLE IF NOT EXISTS filieres_cache (
            filiere_id INT PRIMARY KEY,
            nom        TEXT
        )
    """)


def init_cassandra():
    """Initialisation au démarrage — délègue à get_session_with_keyspace() qui est self-healing."""
    get_session_with_keyspace()
