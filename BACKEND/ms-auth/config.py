from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # JWT
    JWT_SECRET: str = "change_me_super_secret_key_est_sale_2024"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Keycloak
    KEYCLOAK_URL: str = "http://keycloak:8080"
    KEYCLOAK_REALM: str = "ent-sale"
    KEYCLOAK_CLIENT_ID: str = "ent-client"
    KEYCLOAK_CLIENT_SECRET: str = "your_client_secret_here"

    # App
    APP_ENV: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()