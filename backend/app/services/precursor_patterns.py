"""Precursor pattern definitions for early warning detection.

Each pattern encodes expert knowledge about what combination of signals
from different OSINT sources indicates a specific type of major event.
"""

from dataclasses import dataclass, field


@dataclass
class PrecursorPattern:
    name: str
    description: str
    severity: str  # concerning, elevated, critical, crisis
    regions: list[str] = field(default_factory=list)  # empty = all regions

    required_sources: list[str] = field(default_factory=list)
    min_source_match: int = 2

    required_keywords: list[str] = field(default_factory=list)
    min_keyword_match: int = 2

    window_hours: float = 6.0
    max_avg_sentiment: float | None = None
    min_signal_count: int = 3


@dataclass
class PatternMatch:
    pattern: PrecursorPattern
    matched_sources: list[str]
    matched_keywords: list[str]
    confidence: float


# ─── MILITARY / WAR ───

MILITARY_ESCALATION_IMMINENT = PrecursorPattern(
    name="military_escalation_imminent",
    description="Imminent military action: GEOINT + conflict + diplomatic signals converging",
    severity="critical",
    regions=["middle_east", "europe", "asia"],
    required_sources=["adsb", "acled", "liveuamap", "gdelt", "gov_rss"],
    min_source_match=3,
    required_keywords=[
        "military", "strike", "missile", "deployment", "airspace",
        "carrier", "troops", "mobilization", "escalation", "retaliation",
        "bombing", "offensive", "invasion", "operation", "intervention",
        "joint operation", "boots on the ground",
    ],
    min_keyword_match=3,
    window_hours=6,
    max_avg_sentiment=-0.3,
    min_signal_count=5,
)

AIRSPACE_CLOSURE = PrecursorPattern(
    name="airspace_closure_military",
    description="Airspace closure pattern: ADS-B surge + conflict RSS + government statements",
    severity="critical",
    regions=["middle_east", "europe"],
    required_sources=["adsb", "liveuamap", "gov_rss"],
    min_source_match=2,
    required_keywords=[
        "airspace", "closed", "notam", "military aircraft", "no-fly",
        "restricted", "flight", "divert", "grounded",
    ],
    min_keyword_match=2,
    window_hours=3,
    min_signal_count=3,
)

NAVAL_ESCALATION = PrecursorPattern(
    name="naval_escalation",
    description="Naval force projection: carrier groups + maritime incidents + rhetoric",
    severity="elevated",
    regions=["middle_east", "asia"],
    required_sources=["ship_tracker", "adsb", "gov_rss"],
    min_source_match=2,
    required_keywords=[
        "carrier", "destroyer", "naval", "fleet", "blockade",
        "strait", "warship", "submarine", "escort", "armada",
    ],
    min_keyword_match=2,
    window_hours=12,
    min_signal_count=3,
)

IRAN_MILITARY_ESCALATION = PrecursorPattern(
    name="iran_military_escalation",
    description="Iran-specific: ADS-B Persian Gulf + conflict events + gov statements + news",
    severity="critical",
    regions=["middle_east"],
    required_sources=["adsb", "liveuamap", "gov_rss", "gdelt"],
    min_source_match=3,
    required_keywords=[
        "iran", "irgc", "tehran", "persian gulf", "hormuz",
        "israel", "strike", "missile", "retaliation", "military",
        "hezbollah", "proxy", "ballistic",
    ],
    min_keyword_match=3,
    window_hours=4,
    max_avg_sentiment=-0.4,
    min_signal_count=5,
)

# ─── NUCLEAR ───

NUCLEAR_ESCALATION = PrecursorPattern(
    name="nuclear_escalation",
    description="Nuclear threat: nuclear monitor + diplomatic + military signals",
    severity="crisis",
    regions=["middle_east", "asia", "europe"],
    required_sources=["nuclear_monitor", "gov_rss", "gdelt"],
    min_source_match=2,
    required_keywords=[
        "nuclear", "enrichment", "warhead", "icbm", "deterrent",
        "weapons-grade", "plutonium", "uranium", "nuclear test",
        "radiation", "atomic",
    ],
    min_keyword_match=2,
    window_hours=12,
    max_avg_sentiment=-0.5,
    min_signal_count=3,
)

# ─── CONFLICT GENERAL ───

CONFLICT_SURGE = PrecursorPattern(
    name="conflict_surge",
    description="Rapid conflict acceleration: ACLED + LiveUAMap + satellite thermal",
    severity="elevated",
    regions=[],
    required_sources=["acled", "liveuamap", "nasa_firms"],
    min_source_match=2,
    required_keywords=[
        "casualties", "attack", "offensive", "shelling", "bombing",
        "explosion", "airstrike", "killed", "wounded",
    ],
    min_keyword_match=2,
    window_hours=6,
    max_avg_sentiment=-0.4,
    min_signal_count=4,
)

DIPLOMATIC_CRISIS = PrecursorPattern(
    name="diplomatic_crisis",
    description="Diplomatic breakdown: government statements + news surge + negative sentiment",
    severity="concerning",
    regions=[],
    required_sources=["gov_rss", "gdelt", "newsdata"],
    min_source_match=2,
    required_keywords=[
        "sanctions", "expel", "ambassador", "recall", "threat",
        "ultimatum", "condemn", "violation", "withdraw", "sever",
        "diplomatic", "retaliation", "intervention", "sovereignty",
        "international law", "resolution",
    ],
    min_keyword_match=2,
    window_hours=12,
    max_avg_sentiment=-0.2,
    min_signal_count=4,
)

# ─── FINANCIAL ───

FINANCIAL_CRASH_IMMINENT = PrecursorPattern(
    name="financial_crash_imminent",
    description="Financial crash signals: market data + macro + news convergence",
    severity="critical",
    regions=[],
    required_sources=["finnhub", "fred", "gdelt", "newsdata"],
    min_source_match=3,
    required_keywords=[
        "crash", "recession", "default", "bank run", "liquidity",
        "margin call", "circuit breaker", "bear market", "collapse",
        "bailout", "insolvency", "contagion", "sell-off",
    ],
    min_keyword_match=3,
    window_hours=6,
    max_avg_sentiment=-0.4,
    min_signal_count=5,
)

CRYPTO_BLACK_SWAN = PrecursorPattern(
    name="crypto_black_swan",
    description="Crypto black swan: whale movements + exchange data + social + news",
    severity="elevated",
    regions=[],
    required_sources=["whale_crypto", "finnhub", "reddit", "gdelt"],
    min_source_match=2,
    required_keywords=[
        "hack", "exploit", "depeg", "insolvency", "freeze",
        "bank run", "collapse", "exchange", "withdrawal",
        "stablecoin", "liquidation", "rug pull",
    ],
    min_keyword_match=3,
    window_hours=4,
    min_signal_count=4,
)

ENERGY_CRISIS = PrecursorPattern(
    name="energy_crisis",
    description="Energy supply crisis: maritime + market + news + government",
    severity="elevated",
    regions=[],
    required_sources=["ship_tracker", "gdelt", "finnhub", "gov_rss"],
    min_source_match=2,
    required_keywords=[
        "oil", "opec", "pipeline", "embargo", "energy crisis",
        "gas shortage", "blackout", "supply disruption",
        "refinery", "lng", "price surge",
    ],
    min_keyword_match=3,
    window_hours=12,
    min_signal_count=4,
)

# ─── SOCIAL / POLITICAL ───

SOCIAL_UNREST_SURGE = PrecursorPattern(
    name="social_unrest_surge",
    description="Social unrest acceleration: conflict data + live events + news + social",
    severity="elevated",
    regions=[],
    required_sources=["acled", "liveuamap", "gdelt", "reddit"],
    min_source_match=2,
    required_keywords=[
        "protest", "riot", "revolution", "uprising", "coup",
        "martial law", "curfew", "tear gas", "crackdown",
        "demonstration", "unrest", "looting",
    ],
    min_keyword_match=3,
    window_hours=6,
    min_signal_count=4,
)

# ─── NATURAL DISASTERS ───

NATURAL_DISASTER_MAJOR = PrecursorPattern(
    name="natural_disaster_major",
    description="Major natural disaster: seismic + weather + satellite + news convergence",
    severity="critical",
    regions=[],
    required_sources=["usgs_earthquake", "noaa_weather", "nasa_firms", "gdelt"],
    min_source_match=2,
    required_keywords=[
        "earthquake", "tsunami", "hurricane", "typhoon", "eruption",
        "catastrophe", "emergency", "evacuation", "magnitude",
        "flooding", "landslide", "cyclone",
    ],
    min_keyword_match=2,
    window_hours=3,
    min_signal_count=3,
)

# ─── HEALTH ───

PANDEMIC_OUTBREAK = PrecursorPattern(
    name="pandemic_outbreak",
    description="Pandemic/outbreak signals: news + government + health data",
    severity="elevated",
    regions=[],
    required_sources=["gdelt", "gov_rss", "newsdata"],
    min_source_match=2,
    required_keywords=[
        "outbreak", "pandemic", "quarantine", "lockdown",
        "who emergency", "epidemic", "virus", "cases surge",
        "hospital", "containment", "mutation",
    ],
    min_keyword_match=2,
    window_hours=12,
    min_signal_count=4,
)


# ─── US MILITARY OPERATIONS ───

US_MILITARY_INTERVENTION = PrecursorPattern(
    name="us_military_intervention",
    description="US military operation abroad: GEOINT + gov + news + maritime convergence",
    severity="critical",
    regions=["americas", "middle_east", "africa", "asia"],
    required_sources=["adsb", "gov_rss", "gdelt", "ship_tracker", "pentagon_pizza"],
    min_source_match=3,
    required_keywords=[
        "military operation", "intervention", "southcom", "centcom",
        "africom", "deployment", "boots on the ground", "joint operation",
        "cartel", "narco", "special forces", "marines", "troops",
        "amphibious", "invasion", "operation", "task force",
    ],
    min_keyword_match=3,
    window_hours=6,
    max_avg_sentiment=-0.3,
    min_signal_count=4,
)

# ─── PEACE / DIPLOMACY ───

PEACE_AGREEMENT_IMMINENT = PrecursorPattern(
    name="peace_agreement_imminent",
    description="Peace deal or major diplomatic breakthrough signals converging",
    severity="elevated",
    regions=[],
    required_sources=["gov_rss", "gdelt", "newsdata"],
    min_source_match=2,
    required_keywords=[
        "peace", "ceasefire", "agreement", "treaty", "negotiation",
        "diplomacy", "summit", "talks", "reconciliation", "normalization",
        "armistice", "truce", "de-escalation", "peace deal",
        "un resolution", "accord", "framework",
    ],
    min_keyword_match=3,
    window_hours=12,
    min_signal_count=4,
)

CEASEFIRE_IMMINENT = PrecursorPattern(
    name="ceasefire_imminent",
    description="Ceasefire or military stand-down signals from multiple sources",
    severity="elevated",
    regions=[],
    required_sources=["gov_rss", "gdelt", "newsdata", "liveuamap"],
    min_source_match=2,
    required_keywords=[
        "ceasefire", "truce", "humanitarian corridor", "withdrawal",
        "stand-down", "peace talks", "geneva", "vienna", "doha",
        "hostage", "prisoner exchange", "demilitarized",
        "peace process", "humanitarian pause",
    ],
    min_keyword_match=2,
    window_hours=6,
    min_signal_count=3,
)


# ─── REGISTRY ───

ALL_PATTERNS: list[PrecursorPattern] = [
    # Military / War
    MILITARY_ESCALATION_IMMINENT,
    AIRSPACE_CLOSURE,
    NAVAL_ESCALATION,
    IRAN_MILITARY_ESCALATION,
    US_MILITARY_INTERVENTION,
    # Nuclear
    NUCLEAR_ESCALATION,
    # Conflict
    CONFLICT_SURGE,
    DIPLOMATIC_CRISIS,
    # Financial
    FINANCIAL_CRASH_IMMINENT,
    CRYPTO_BLACK_SWAN,
    ENERGY_CRISIS,
    # Social
    SOCIAL_UNREST_SURGE,
    # Natural Disasters
    NATURAL_DISASTER_MAJOR,
    # Health
    PANDEMIC_OUTBREAK,
    # Peace / Diplomacy
    PEACE_AGREEMENT_IMMINENT,
    CEASEFIRE_IMMINENT,
]


class PrecursorPatternMatcher:
    """Matches a set of intelligence items against all precursor patterns."""

    def match_patterns(self, items: list[dict], region: str) -> list[PatternMatch]:
        results = []

        for pattern in ALL_PATTERNS:
            # Skip if pattern doesn't apply to this region
            if pattern.regions and region not in pattern.regions:
                continue

            # Check source diversity
            item_sources = set(item["source"] for item in items)
            source_matches = item_sources & set(pattern.required_sources)
            if len(source_matches) < pattern.min_source_match:
                continue

            # Check keyword presence across all item texts
            all_text = " ".join(
                f"{item.get('title', '')} {item.get('summary', '')}".lower()
                for item in items
            )
            keyword_matches = [kw for kw in pattern.required_keywords if kw in all_text]
            if len(keyword_matches) < pattern.min_keyword_match:
                continue

            # Check sentiment threshold
            if pattern.max_avg_sentiment is not None:
                sentiments = [i.get("sentiment_score", 0) for i in items]
                avg_sent = sum(sentiments) / len(sentiments) if sentiments else 0
                if avg_sent > pattern.max_avg_sentiment:
                    continue

            # Check minimum signal count
            if len(items) < pattern.min_signal_count:
                continue

            # Pattern matches — compute confidence
            source_ratio = len(source_matches) / len(pattern.required_sources)
            keyword_ratio = len(keyword_matches) / len(pattern.required_keywords)
            signal_ratio = min(1.0, len(items) / (pattern.min_signal_count * 2))

            confidence = min(1.0, source_ratio * 0.4 + keyword_ratio * 0.3 + signal_ratio * 0.3)

            results.append(PatternMatch(
                pattern=pattern,
                matched_sources=list(source_matches),
                matched_keywords=keyword_matches,
                confidence=confidence,
            ))

        return results
