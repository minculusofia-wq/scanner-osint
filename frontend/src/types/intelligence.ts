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
  ai_title: string;
  ai_situation: string;
  ai_analysis: string;
  ai_trading_signal: string;
  ai_confidence: number;
  ai_risk_factors: string;
  created_at: string;
  expires_at: string | null;
  graph_data: string; // JSON string of {nodes, edges}
}

export interface LinkedMarket {
  condition_id: string;
  question: string;
  slug?: string;
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
  usgs_earthquake_enabled: boolean;
  noaa_weather_enabled: boolean;
  // Behavioral OSINT
  pentagon_pizza_enabled: boolean;
  // Conflict OSINT
  liveuamap_enabled: boolean;
  nuclear_monitor_enabled: boolean;
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

// --- Early Warning / Alerts ---

export type EscalationLevel =
  | "stable"
  | "concerning"
  | "elevated"
  | "critical"
  | "crisis";

export interface EscalationTracker {
  id: number;
  name: string;
  category: string;
  region: string;
  countries: string[];
  escalation_level: EscalationLevel;
  escalation_score: number;
  previous_level: string;
  level_changed_at: string | null;
  signal_count_1h: number;
  signal_count_6h: number;
  signal_count_24h: number;
  unique_sources_1h: number;
  avg_sentiment_1h: number;
  matched_patterns: string[];
  contributing_source_types: string[];
  key_headlines: { title: string; source: string }[];
  linked_markets: LinkedMarket[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AlertRule {
  id: number | null;
  name: string;
  description: string;
  is_enabled: boolean;
  min_escalation_level: string;
  min_priority_score: number;
  min_signal_count: number;
  min_unique_sources: number;
  signal_window_minutes: number;
  categories: string[];
  regions: string[];
  required_patterns: string[];
  delivery_channels: string[];
  cooldown_minutes: number;
  max_alerts_per_hour: number;
}

export interface AlertHistoryEntry {
  id: number;
  title: string;
  message: string;
  severity: string;
  escalation_level: string;
  region: string;
  category: string;
  trigger_signal_count: number;
  trigger_source_types: string[];
  matched_patterns: string[];
  channels_sent: string[];
  delivery_status: string;
  linked_markets: LinkedMarket[];
  created_at: string;
}

export interface AlertConfig {
  alerts_enabled: boolean;
  discord_webhook_url: string;
  discord_enabled: boolean;
  webhook_url: string;
  webhook_enabled: boolean;
  webhook_secret: string;
  global_cooldown_minutes: number;
  max_alerts_per_hour: number;
  quiet_hours_start: number;
  quiet_hours_end: number;
}

export interface PrecursorPattern {
  id: string;
  name: string;
  category: string;
  severity: string;
  description: string;
  required_sources: string[];
  min_source_match: number;
  keywords: string[];
  min_keyword_match: number;
}
