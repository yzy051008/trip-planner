"""数据库表模型。"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class TripRecord(Base):
    """历史旅行计划记录。"""

    __tablename__ = "trip_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    city: Mapped[str] = mapped_column(String(64), index=True)
    start_date: Mapped[str] = mapped_column(String(16))
    end_date: Mapped[str] = mapped_column(String(16))
    travel_days: Mapped[int] = mapped_column(Integer)
    transportation: Mapped[str] = mapped_column(String(32), default="")
    accommodation: Mapped[str] = mapped_column(String(32), default="")
    preferences: Mapped[str] = mapped_column(Text, default="[]")
    free_text_input: Mapped[str] = mapped_column(Text, default="")
    plan_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )
