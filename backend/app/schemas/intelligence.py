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
