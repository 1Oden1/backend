from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    KEYCLOAK_URL: str = "http://keycloak:8080"
    KEYCLOAK_REALM: str = "ent-sale"
    KEYCLOAK_CLIENT_ID: str = "ent-backend"
    KEYCLOAK_CLIENT_SECRET: str = "change-me-in-production"

    class Config:
        env_file = ".env"

settings = Settings()
