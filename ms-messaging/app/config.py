from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Cassandra
    CASSANDRA_HOST:     str = "ent_cassandra"
    CASSANDRA_KEYSPACE: str = "ent_messaging"

    # RabbitMQ
    RABBITMQ_URL:      str = "amqp://ent_user:ent_password@ent_rabbitmq:5672/"
    RABBITMQ_EXCHANGE: str = "ent.events"
    RABBITMQ_QUEUE:    str = "ms_messaging_queue"

    # Keycloak / JWT
    KEYCLOAK_URL:            str = "http://ent_keycloak:8080"
    KEYCLOAK_REALM:          str = "ent-sale"
    KEYCLOAK_ADMIN_USER:     str = "admin"
    KEYCLOAK_ADMIN_PASSWORD: str = "admin_password"
    KEYCLOAK_CLIENT_ID:      str = "ent-backend"
    JWT_ALGORITHM:           str = "RS256"

    # MS_NOTES_URL et MS_CALENDAR_URL supprimés :
    # ms-messaging n'appelle plus jamais ces services.
    # Toutes les données passent par le cache Cassandra alimenté via RabbitMQ.

    class Config:
        env_file = ".env"


settings = Settings()
