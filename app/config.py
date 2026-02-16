from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "prod"
    app_debug: bool = False
    app_log_level: str = "INFO"

    api_sign_ttl_seconds: int = 300
    api_hmac_algo: str = "sha256"
    api_clients: str = ""
    admin_token: str = ""
    admin_username: str = ""
    admin_password_hash: str = ""
    admin_session_secret: str = ""
    admin_turnstile_site_key: str = ""
    admin_turnstile_secret_key: str = ""

    db_dsn: str = "postgresql+psycopg://pbs:change_me@db:5432/pbs"
    redis_url: str = "redis://redis:6379/0"


settings = Settings()
