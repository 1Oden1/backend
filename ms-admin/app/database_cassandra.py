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

    # ── Keyspace ent_files (partagé avec ms-upload / ms-download) ────────────
    session.execute(f"""
        CREATE KEYSPACE IF NOT EXISTS {settings.CASSANDRA_KEYSPACE}
        WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}}
    """)
    session.set_keyspace(settings.CASSANDRA_KEYSPACE)

    # Table files — schéma identique à ms-upload
    session.execute("""
        CREATE TABLE IF NOT EXISTS files (
            file_id      UUID PRIMARY KEY,
            owner_id     TEXT,
            owner_name   TEXT,
            title        TEXT,
            description  TEXT,
            category     TEXT,
            module       TEXT,
            filename     TEXT,
            content_type TEXT,
            size_bytes   BIGINT,
            minio_key    TEXT,
            upload_date  TIMESTAMP,
            is_public    BOOLEAN
        )
    """)
    session.execute("CREATE INDEX IF NOT EXISTS files_owner_idx    ON files (owner_id)")
    session.execute("CREATE INDEX IF NOT EXISTS files_category_idx ON files (category)")
    session.execute("CREATE INDEX IF NOT EXISTS files_module_idx   ON files (module)")

    # ── Table audit_logs (propre au ms-admin) ────────────────────────────────
    session.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            log_id      UUID,
            admin_id    TEXT,
            action      TEXT,
            target_type TEXT,
            target_id   TEXT,
            details     TEXT,
            created_at  TIMESTAMP,
            PRIMARY KEY (log_id, created_at)
        ) WITH CLUSTERING ORDER BY (created_at DESC)
    """)

    logger.info("Cassandra initialisé (ent_files + audit_logs).")
