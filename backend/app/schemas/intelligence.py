from datetime import datetime

from pydantic import BaseModel


class IntelligenceItemResponse(BaseModel):
    id: int
    source: str
    title: str
    summary: str
    url: str
    image_url: str = ""
    category: str
    region: str
    country: str
    tags: list[str] = []
    sentiment_score: float
    priority_score: float
    confidence: float
    urgency: str
    market_impact: str
    linked_markets: list[dict] = []
    published_at: datetime | None = None
    collected_at: datetime


class IntelligenceBriefResponse(BaseModel):
    id: int
    title: str
    summary: str
    trading_implication: str = ""
    priority_score: float
    confidence: float
    urgency: str
    source_count: int
    linked_markets: list[dict] = []
    category: str
    region: str
    is_actionable: bool
    is_dismissed: bool = False
    created_at: datetime
    expires_at: datetime | None = None


class OSINTConfig(BaseModel):
    """OSINT scanner configuration. 0 = disabled for numeric params."""

    enabled: bool = False
    collection_interval_seconds: int = 600
    max_items_per_cycle: int = 100
    stale_after_hours: int = 48

    # Source toggles — News/Data
    gdelt_enabled: bool = True
    newsdata_enabled: bool = True
    acled_enabled: bool = True
    finnhub_enabled: bool = True
    reddit_enabled: bool = True

    # FININT (Financial Intelligence)
    sec_edgar_enabled: bool = True
    whale_crypto_enabled: bool = False
    fred_enabled: bool = False

    # GEOINT (Geospatial Intelligence)
    adsb_enabled: bool = True
    nasa_firms_enabled: bool = True
    ship_tracker_enabled: bool = True
    usgs_earthquake_enabled: bool = True
    noaa_weather_enabled: bool = True

    # Behavioral OSINT
    pentagon_pizza_enabled: bool = True

    # Conflict OSINT
    liveuamap_enabled: bool = True
    nuclear_monitor_enabled: bool = True

    # Social OSINT
    telegram_enabled: bool = True
    gov_rss_enabled: bool = True

    # API keys (runtime-configurable via UI)
    newsdata_api_key: str = ""
    finnhub_api_key: str = ""
    acled_api_key: str = ""
    acled_email: str = ""
    etherscan_api_key: str = ""
    fred_api_key: str = ""

    # Filtering
    min_priority_score: float = 0.0
    categories: list[str] = []
    regions: list[str] = []


class IntelligenceStats(BaseModel):
    total_items: int
    items_last_24h: int
    briefs_count: int
    actionable_briefs: int
    sources_active: list[str]
    last_collection_at: datetime | None = None
    linked_markets_count: int


# --- Alert / Early Warning schemas ---


class AlertConfigSchema(BaseModel):
    """Global alert delivery configuration."""
    alerts_enabled: bool = False
    discord_webhook_url: str = ""
    discord_enabled: bool = False
    webhook_url: str = ""
    webhook_enabled: bool = False
    webhook_secret: str = ""
    global_cooldown_minutes: int = 15
    max_alerts_per_hour: int = 10
    quiet_hours_start: int = -1   # -1 = disabled, 0-23 = UTC hour
    quiet_hours_end: int = -1


class AlertRuleSchema(BaseModel):
    id: int | None = None
    name: str
    description: str = ""
    is_enabled: bool = True
    min_escalation_level: str = "elevated"
    min_priority_score: float = 70.0
    min_signal_count: int = 3
    min_unique_sources: int = 2
    signal_window_minutes: int = 120
    categories: list[str] = []
    regions: list[str] = []
    required_patterns: list[str] = []
    delivery_channels: list[str] = ["discord"]
    cooldown_minutes: int = 30
    max_alerts_per_hour: int = 5


class EscalationTrackerResponse(BaseModel):
    id: int
    name: str
    category: str
    region: str
    countries: list[str] = []
    escalation_level: str
    escalation_score: float
    previous_level: str
    level_changed_at: datetime | None = None
    signal_count_1h: int
    signal_count_6h: int
    signal_count_24h: int
    unique_sources_1h: int
    avg_sentiment_1h: float
    matched_patterns: list[str] = []
    contributing_source_types: list[str] = []
    linked_markets: list[dict] = []
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AlertHistoryResponse(BaseModel):
    id: int
    title: str
    message: str
    severity: str
    escalation_level: str = ""
    region: str = ""
    category: str = ""
    trigger_signal_count: int
    trigger_source_types: list[str] = []
    matched_patterns: list[str] = []
    channels_sent: list[str] = []
    delivery_status: str
    linked_markets: list[dict] = []
    created_at: datetime
