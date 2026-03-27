from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Keycloak
    KEYCLOAK_URL: str = "http://keycloak:8080"
    KEYCLOAK_REALM: str = "ent-sale"
    KEYCLOAK_CLIENT_ID: str = "ent-client"
    KEYCLOAK_CLIENT_SECRET: str = ""

    # ms-auth
    MS_AUTH_URL: str = "http://ms-auth:8001"

    # MySQL
    MYSQL_HOST: str = "mysql"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "root"
    MYSQL_DB: str = "ent_admin"

    # App
    APP_ENV: str = "development"

    class Config:
        env_file = ".env"

settings = Settings()