from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    WORKSPACE_DIR: str = "/app/workspace"
    LLM_BASE_URL: str = "http://host.docker.internal:8080"
    LLM_API_KEY: str = "test"
    LLM_MODEL: str = "claude-opus-4-6-thinking"

    DISCORD_TOKEN: str = ""
    DISCORD_PROXY: str = ""
    OUTBOUND_PROXY: str = ""
    DDGS_API_URL: str = "http://localhost:8000"
    ALLOWED_CHANNEL_ID: int | None = None
    ALLOWED_USER_ID: int | None = None

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
