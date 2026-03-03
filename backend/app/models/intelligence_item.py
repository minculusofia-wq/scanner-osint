from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class IntelligenceItem(Base):
    __tablename__ = "intelligence_items"
    __table_args__ = (
        Index("ix_intel_created", "created_at"),
        Index("ix_intel_source_hash", "source", "content_hash"),
        Index("ix_intel_priority", "priority_score"),
        Index("ix_intel_category", "category"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Source identification
    source: Mapped[str] = mapped_column(String(50))
    source_id: Mapped[str] = mapped_column(String(512), default="")
    content_hash: Mapped[str] = mapped_column(String(64))

    # Content
    title: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(Text, default="")
    image_url: Mapped[str] = mapped_column(Text, default="")

    # Classification
    category: Mapped[str] = mapped_column(String(50), default="general")
    region: Mapped[str] = mapped_column(String(100), default="")
    country: Mapped[str] = mapped_column(String(100), default="")
    tags: Mapped[str] = mapped_column(Text, default="[]")

    # Raw scoring
    raw_relevance: Mapped[float] = mapped_column(Float, default=0.0)
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0)
    goldstein_scale: Mapped[float] = mapped_column(Float, default=0.0)

    # Processed scoring
    priority_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    urgency: Mapped[str] = mapped_column(String(20), default="low")
    market_impact: Mapped[str] = mapped_column(String(20), default="neutral")

    # Market linking
    linked_market_ids: Mapped[str] = mapped_column(Text, default="[]")
    linked_market_questions: Mapped[str] = mapped_column(Text, default="[]")

    # Metadata
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False)
