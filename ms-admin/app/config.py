from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Cassandra — pour les logs d'audit UNIQUEMENT ───────────────────────────
    CASSANDRA_HOST:     str = "ent_cassandra"
    CASSANDRA_KEYSPACE: str = "ent_files"

    # ── MinIO — gestion des fichiers ──────────────────────────────────────────
    MINIO_ENDPOINT:   str  = "minio:9000"
    MINIO_ACCESS_KEY: str  = "ent_user"
    MINIO_SECRET_KEY: str  = "ent_password"
    MINIO_BUCKET:     str  = "ent-courses"
    MINIO_SECURE:     bool = False

    # ── Keycloak / JWT ────────────────────────────────────────────────────────
    KEYCLOAK_URL:            str = "http://ent_keycloak:8080"
    KEYCLOAK_REALM:          str = "ent-sale"
    KEYCLOAK_ADMIN_USER:     str = "admin"
    KEYCLOAK_ADMIN_PASSWORD: str = "admin_password"
    KEYCLOAK_CLIENT_ID:      str = "ent-backend"
    JWT_ALGORITHM:           str = "RS256"

    # ── URLs des microservices (proxy HTTP — AUCUNE connexion DB directe) ──────
    # ms-admin délègue 100 % des opérations métier via les REST des services dédiés.
    MS_CALENDAR_URL:  str = "http://ent_ms_calendar:8000"
    MS_NOTES_URL:     str = "http://ent_ms_notes:8000"
    MS_MESSAGING_URL: str = "http://ent_ms_messaging:8000"
    MS_UPLOAD_URL:    str = "http://ent_ms_upload:8000"
    MS_DOWNLOAD_URL:  str = "http://ent_ms_download:8000"

    class Config:
        env_file = ".env"


settings = Settings()
