from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class EscalationTracker(Base):
    __tablename__ = "escalation_trackers"
    __table_args__ = (
        Index("ix_esc_region_category", "region", "category"),
        Index("ix_esc_level", "escalation_level"),
        Index("ix_esc_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Identity
    name: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50), default="")
    region: Mapped[str] = mapped_column(String(100), default="")
    countries: Mapped[str] = mapped_column(Text, default="[]")
    keywords: Mapped[str] = mapped_column(Text, default="[]")

    # Escalation state: stable -> concerning -> elevated -> critical -> crisis
    escalation_level: Mapped[str] = mapped_column(String(20), default="stable")
    escalation_score: Mapped[float] = mapped_column(Float, default=0.0)
    previous_level: Mapped[str] = mapped_column(String(20), default="stable")
    level_changed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Signal accumulation
    signal_count_1h: Mapped[int] = mapped_column(Integer, default=0)
    signal_count_6h: Mapped[int] = mapped_column(Integer, default=0)
    signal_count_24h: Mapped[int] = mapped_column(Integer, default=0)
    unique_sources_1h: Mapped[int] = mapped_column(Integer, default=0)
    avg_sentiment_1h: Mapped[float] = mapped_column(Float, default=0.0)
    max_priority_1h: Mapped[float] = mapped_column(Float, default=0.0)

    # Contributing intelligence
    contributing_item_ids: Mapped[str] = mapped_column(Text, default="[]")
    contributing_source_types: Mapped[str] = mapped_column(Text, default="[]")

    # Matched precursor patterns
    matched_patterns: Mapped[str] = mapped_column(Text, default="[]")

    # Polymarket links
    linked_market_ids: Mapped[str] = mapped_column(Text, default="[]")
    linked_market_questions: Mapped[str] = mapped_column(Text, default="[]")

    # Lifecycle
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
