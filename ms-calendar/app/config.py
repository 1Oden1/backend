from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # MySQL
    MYSQL_HOST:     str = "ent_mysql"
    MYSQL_PORT:     int = 3306
    MYSQL_USER:     str = "ent_user"
    MYSQL_PASSWORD: str = "ent_password"
    MYSQL_DATABASE: str = "ent_calendar"

    # Keycloak / JWT
    KEYCLOAK_URL:       str = "http://ent_keycloak:8080"
    KEYCLOAK_REALM:     str = "ent-sale"
    KEYCLOAK_CLIENT_ID: str = "ent-backend"
    JWT_ALGORITHM:      str = "RS256"

    # RabbitMQ — publie les événements filière/séance vers ms-messaging
    RABBITMQ_URL: str = "amqp://ent_user:ent_password@ent_rabbitmq:5672/"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )

    class Config:
        env_file = ".env"


settings = Settings()
