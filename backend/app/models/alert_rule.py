from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Conditions
    min_escalation_level: Mapped[str] = mapped_column(String(20), default="elevated")
    min_priority_score: Mapped[float] = mapped_column(Float, default=70.0)
    min_signal_count: Mapped[int] = mapped_column(Integer, default=3)
    min_unique_sources: Mapped[int] = mapped_column(Integer, default=2)
    signal_window_minutes: Mapped[int] = mapped_column(Integer, default=120)
    categories: Mapped[str] = mapped_column(Text, default="[]")
    regions: Mapped[str] = mapped_column(Text, default="[]")
    required_patterns: Mapped[str] = mapped_column(Text, default="[]")

    # Delivery
    delivery_channels: Mapped[str] = mapped_column(Text, default='["discord"]')

    # Anti-spam
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=30)
    max_alerts_per_hour: Mapped[int] = mapped_column(Integer, default=5)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
