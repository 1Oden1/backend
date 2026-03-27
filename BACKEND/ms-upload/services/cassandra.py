from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from fastapi import HTTPException
from config import settings
import uuid
from datetime import datetime


def get_session():
    try:
        cluster = Cluster(
            [settings.CASSANDRA_HOST],
            port=settings.CASSANDRA_PORT
        )
        session = cluster.connect()
        session.set_keyspace(settings.CASSANDRA_KEYSPACE)
        return session
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Cassandra indisponible: {e}")


def init_cassandra():
    """Crée le keyspace et la table si nécessaire"""
    try:
        cluster = Cluster(
            [settings.CASSANDRA_HOST],
            port=settings.CASSANDRA_PORT
        )
        session = cluster.connect()

        # Créer le keyspace
        session.execute(f"""
            CREATE KEYSPACE IF NOT EXISTS {settings.CASSANDRA_KEYSPACE}
            WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}}
        """)

        session.set_keyspace(settings.CASSANDRA_KEYSPACE)

        # Créer la table des métadonnées
        session.execute("""
            CREATE TABLE IF NOT EXISTS file_metadata (
                file_id UUID PRIMARY KEY,
                cours_id INT,
                filename TEXT,
                original_name TEXT,
                content_type TEXT,
                size BIGINT,
                minio_path TEXT,
                uploaded_by TEXT,
                uploaded_at TIMESTAMP
            )
        """)

        cluster.shutdown()
    except Exception as e:
        print(f"[WARNING] Cassandra init: {e}")


def save_metadata(cours_id: int, filename: str, original_name: str,
                  content_type: str, size: int, minio_path: str,
                  uploaded_by: str) -> str:
    """Sauvegarde les métadonnées d'un fichier dans Cassandra"""
    session = get_session()
    file_id = uuid.uuid4()

    session.execute("""
        INSERT INTO file_metadata
        (file_id, cours_id, filename, original_name, content_type, size, minio_path, uploaded_by, uploaded_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (file_id, cours_id, filename, original_name, content_type, size, minio_path, uploaded_by, datetime.utcnow()))

    return str(file_id)


def get_files_by_cours(cours_id: int) -> list:
    """Récupère tous les fichiers d'un cours"""
    session = get_session()
    rows = session.execute(
        "SELECT * FROM file_metadata WHERE cours_id = %s ALLOW FILTERING",
        (cours_id,)
    )
    return [dict(row._asdict()) for row in rows]