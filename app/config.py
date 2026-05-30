from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Private Credit Risk Watch v2"
    database_url: str = "sqlite+aiosqlite:///./private_credit.db"
    sync_database_url: str = "sqlite:///./private_credit.db"
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = False
    update_interval_seconds: float = 15.0
    history_limit: int = 300
    replay_default_limit: int = 120
    auth_token: str = "dev-token"
    fred_api_key: str = ""
    fred_poll_interval_seconds: float = 300.0
    massive_api_key: str = ""
    massive_poll_interval_seconds: float = 3600.0
    bdc_tickers: list[str] = ["ARCC", "BXSL", "OBDC", "MAIN", "FSK", "GBDC", "TSLX"]
    credit_etf_ticker: str = "HYG"
    software_etf_ticker: str = "IGV"
    sec_user_agent: str = ""
    sec_ciks: list[str] = []
    sec_poll_interval_seconds: float = 900.0
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
