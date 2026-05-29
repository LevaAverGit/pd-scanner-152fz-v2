from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_path: str = "pd_scanner.db"
    cors_origins: list[str] = ["http://localhost:5173"]
    log_level: str = "INFO"
    app_name: str = "PD Scanner"
    # Dev/test override — allows localhost / 127.x targets through URL validation.
    # MUST be False in production. Only enable for controlled local fixture testing.
    allow_local_test_targets: bool = False

    model_config = {"env_prefix": "PD_", "env_file": ".env"}


settings = Settings()
