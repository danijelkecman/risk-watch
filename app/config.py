from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Private Credit Risk Watch v2"
    database_url: str = "sqlite+aiosqlite:///./private_credit.db"
    sync_database_url: str = "sqlite:///./private_credit.db"
    redis_url: str = "redis://localhost:6379/0"
    update_interval_seconds: float = 1.5
    history_limit: int = 300
    replay_default_limit: int = 120
    mock_mode: bool = True
    auth_token: str = "dev-token"
    alert_console_enabled: bool = True
    alert_slack_webhook: str = ""
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_to_number: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    alert_email_to: str = ""

    model_config = SettingsConfigDict(env_prefix="PCRW_", extra="ignore")


settings = Settings()
