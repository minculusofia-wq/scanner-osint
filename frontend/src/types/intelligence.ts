export interface IntelligenceItem {
  id: number;
  source: string;
  title: string;
  summary: string;
  url: string;
  image_url: string;
  category: string;
  region: string;
  country: string;
  tags: string[];
  sentiment_score: number;
  priority_score: number;
  confidence: number;
  urgency: "critical" | "high" | "medium" | "low";
  market_impact: "bullish" | "bearish" | "neutral" | "volatile";
  linked_markets: LinkedMarket[];
  published_at: string | null;
  collected_at: string;
}

export interface IntelligenceBrief {
  id: number;
  title: string;
  summary: string;
  trading_implication: string;
  priority_score: number;
  confidence: number;
  urgency: "critical" | "high" | "medium" | "low";
  source_count: number;
  linked_markets: LinkedMarket[];
  category: string;
  region: string;
  is_actionable: boolean;
  is_dismissed: boolean;
  created_at: string;
  expires_at: string | null;
}

export interface LinkedMarket {
  condition_id: string;
  question: string;
}

export interface OSINTConfig {
  enabled: boolean;
  collection_interval_seconds: number;
  max_items_per_cycle: number;
  stale_after_hours: number;
  // News/Data sources
  gdelt_enabled: boolean;
  newsdata_enabled: boolean;
  acled_enabled: boolean;
  finnhub_enabled: boolean;
  reddit_enabled: boolean;
  // FININT
  sec_edgar_enabled: boolean;
  whale_crypto_enabled: boolean;
  fred_enabled: boolean;
  // GEOINT
  adsb_enabled: boolean;
  nasa_firms_enabled: boolean;
  ship_tracker_enabled: boolean;
  // Social OSINT
  telegram_enabled: boolean;
  gov_rss_enabled: boolean;
  // API keys
  newsdata_api_key: string;
  finnhub_api_key: string;
  acled_api_key: string;
  acled_email: string;
  etherscan_api_key: string;
  fred_api_key: string;
  // Filtering
  min_priority_score: number;
  categories: string[];
  regions: string[];
}

export interface IntelligenceStats {
  total_items: number;
  items_last_24h: number;
  briefs_count: number;
  actionable_briefs: number;
  sources_active: string[];
  last_collection_at: string | null;
  linked_markets_count: number;
}
