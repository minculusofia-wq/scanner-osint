from datetime import datetime

from sqlalchemy import DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class AlertConfigRecord(Base):
    __tablename__ = "alert_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    settings_json: Mapped[str] = mapped_column(Text, default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
