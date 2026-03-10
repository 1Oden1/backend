from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # MinIO
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ENDPOINT_PUBLIC: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "ent_user"
    MINIO_SECRET_KEY: str = "ent_password"
    MINIO_BUCKET: str = "ent-courses"
    MINIO_SECURE: bool = False

    # Cassandra — string simple, on split dans database.py
    CASSANDRA_HOST: str = "ent_cassandra"
    CASSANDRA_KEYSPACE: str = "ent_files"

    # Keycloak / JWT
    KEYCLOAK_URL: str = "http://ent_keycloak:8080"
    KEYCLOAK_REALM: str = "ent-sale"
    JWT_ALGORITHM: str = "RS256"

    class Config:
        env_file = ".env"

settings = Settings()
