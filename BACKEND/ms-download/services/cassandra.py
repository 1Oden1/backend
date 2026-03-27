from cassandra.cluster import Cluster
from fastapi import HTTPException
from config import settings


def get_session():
    try:
        cluster = Cluster(
            [settings.CASSANDRA_HOST],
            port=settings.CASSANDRA_PORT
        )
        session = cluster.connect(settings.CASSANDRA_KEYSPACE)
        return session
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Cassandra indisponible: {e}")


def get_files_by_cours(cours_id: int) -> list:
    """Récupère tous les fichiers d'un cours depuis Cassandra"""
    session = get_session()
    rows = session.execute(
        "SELECT * FROM file_metadata WHERE cours_id = %s ALLOW FILTERING",
        (cours_id,)
    )
    result = []
    for row in rows:
        result.append({
            "file_id": str(row.file_id),
            "cours_id": row.cours_id,
            "filename": row.filename,
            "original_name": row.original_name,
            "content_type": row.content_type,
            "size": row.size,
            "minio_path": row.minio_path,
            "uploaded_by": row.uploaded_by,
            "uploaded_at": row.uploaded_at,
        })
    return result


def get_file_by_id(file_id: str) -> dict:
    """Récupère les métadonnées d'un fichier par son ID"""
    from cassandra.util import uuid_from_time
    import uuid
    session = get_session()
    try:
        file_uuid = uuid.UUID(file_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="file_id invalide")

    rows = session.execute(
        "SELECT * FROM file_metadata WHERE file_id = %s",
        (file_uuid,)
    )
    row = rows.one()
    if not row:
        raise HTTPException(status_code=404, detail="Fichier non trouvé")

    return {
        "file_id": str(row.file_id),
        "cours_id": row.cours_id,
        "filename": row.filename,
        "original_name": row.original_name,
        "content_type": row.content_type,
        "size": row.size,
        "minio_path": row.minio_path,
        "uploaded_by": row.uploaded_by,
        "uploaded_at": row.uploaded_at,
    }