from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MS_AUTH_URL: str = "http://ms-auth:8001"

    MYSQL_HOST: str = "mysql"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "root"
    MYSQL_DB: str = "ent_calendar"

    APP_ENV: str = "development"

    class Config:
        env_file = ".env"

settings = Settings()