from datetime import datetime
from sqlalchemy import DateTime, Float, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(240), index=True)
    team: Mapped[str] = mapped_column(String(240), default="Unassigned")
    description: Mapped[str] = mapped_column(Text, default="")
    problem: Mapped[str] = mapped_column(Text, default="")
    solution: Mapped[str] = mapped_column(Text, default="")
    impact: Mapped[str] = mapped_column(Text, default="")
    tech_stack: Mapped[str] = mapped_column(String(500), default="")
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    feedback: Mapped[str] = mapped_column(Text, default="")
    evaluation_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
