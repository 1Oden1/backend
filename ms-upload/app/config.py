from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # MinIO
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "ent_user"
    MINIO_SECRET_KEY: str = "ent_password"
    MINIO_BUCKET: str = "ent-courses"
    MINIO_SECURE: bool = False

    # Cassandra
    CASSANDRA_HOSTS: list = ["cassandra"]
    CASSANDRA_KEYSPACE: str = "ent_files"

    # Keycloak / JWT
    KEYCLOAK_URL: str = "http://keycloak:8080"
    KEYCLOAK_REALM: str = "ent-sale"
    JWT_ALGORITHM: str = "RS256"

    # Limites upload
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: list = [
        "pdf", "docx", "pptx", "xlsx",
        "jpg", "jpeg", "png",
        "mp4", "zip", "txt", "md"
    ]

    class Config:
        env_file = ".env"

settings = Settings()
