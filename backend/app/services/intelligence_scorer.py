from datetime import datetime


SOURCE_CREDIBILITY = {
    # OSINT sources (raw data, high credibility)
    "sec_edgar": 1.0,
    "fred": 1.0,
    "acled": 1.0,
    "gov_rss": 0.95,
    "nasa_firms": 0.95,
    "adsb": 0.9,
    "finnhub": 0.9,
    "whale_crypto": 0.85,
    "ship_tracker": 0.8,
    # News/media
    "gdelt": 0.7,
    "newsdata": 0.7,
    # Social (less reliable)
    "telegram": 0.5,
    "reddit": 0.4,
}

# Sources that provide raw data (not news articles) get a priority bonus
OSINT_EXCLUSIVE_SOURCES = {
    "sec_edgar", "fred", "whale_crypto", "adsb",
    "nasa_firms", "ship_tracker", "gov_rss",
}


class IntelligenceScorer:
    """Scores intelligence items by priority (0-100)."""

    def score_item(self, item: dict, has_market_match: bool = False) -> dict:
        """Compute priority_score, confidence, urgency, market_impact.

        Priority formula (0-100):
          raw_relevance * 30     (0-30)
          + abs(sentiment) * 20  (0-20)
          + recency_bonus * 20   (0-20, decays over 24h)
          + source_cred * 15     (0-15)
          + market_match * 15    (0-15)
        """
        raw_rel = min(1.0, max(0.0, item.get("raw_relevance", 0.5)))
        sentiment = max(-1.0, min(1.0, item.get("sentiment_score", 0.0)))
        source = item.get("source", "unknown")
        published_at = item.get("published_at")

        # Raw relevance component (0-30)
        score_relevance = raw_rel * 30

        # Sentiment strength component (0-20)
        score_sentiment = abs(sentiment) * 20

        # Recency bonus (0-20, decays linearly over 24h)
        recency_bonus = 0.0
        if published_at and isinstance(published_at, datetime):
            age_hours = (datetime.utcnow() - published_at).total_seconds() / 3600
            recency_bonus = max(0.0, 1.0 - age_hours / 24.0) * 20

        # Source credibility (0-15)
        cred = SOURCE_CREDIBILITY.get(source, 0.5)
        score_source = cred * 15

        # Market match bonus (0-15)
        score_market = 15.0 if has_market_match else 0.0

        priority = score_relevance + score_sentiment + recency_bonus + score_source + score_market

        # OSINT exclusivity bonus: raw data sources get +10
        if source in OSINT_EXCLUSIVE_SOURCES:
            priority += 10

        priority = min(100.0, max(0.0, priority))

        # Confidence based on source + relevance
        confidence = min(1.0, (raw_rel + cred) / 2.0)

        # Urgency thresholds
        if priority >= 80:
            urgency = "critical"
        elif priority >= 60:
            urgency = "high"
        elif priority >= 40:
            urgency = "medium"
        else:
            urgency = "low"

        # Market impact direction
        if sentiment > 0.3:
            market_impact = "bullish"
        elif sentiment < -0.3:
            market_impact = "bearish"
        elif abs(sentiment) > 0.1:
            market_impact = "volatile"
        else:
            market_impact = "neutral"

        return {
            "priority_score": round(priority, 1),
            "confidence": round(confidence, 2),
            "urgency": urgency,
            "market_impact": market_impact,
        }
