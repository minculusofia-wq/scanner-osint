from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./intelligence.db"

    # API keys (all optional — sources without keys are skipped)
    NEWSDATA_API_KEY: str = ""
    FINNHUB_API_KEY: str = ""
    ACLED_API_KEY: str = ""
    ACLED_EMAIL: str = ""
    ETHERSCAN_API_KEY: str = ""
    FRED_API_KEY: str = ""

    # Alerts
    DISCORD_WEBHOOK_URL: str = ""

    # Collection
    COLLECTION_INTERVAL: int = 600  # seconds (10 min default)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
