from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Ollama
    OLLAMA_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "llama3"

    # Keycloak / JWT
    KEYCLOAK_URL: str = "http://keycloak:8080"
    KEYCLOAK_REALM: str = "ent-sale"
    JWT_ALGORITHM: str = "RS256"

    # Limites
    MAX_HISTORY_MESSAGES: int = 20   # garder les N derniers messages du contexte
    MAX_PROMPT_CHARS: int = 4000     # caractères max par message utilisateur

    class Config:
        env_file = ".env"

settings = Settings()
