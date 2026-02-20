"""
Tournament model for bracket management.

Note: Full tournament functionality is Phase 4. This is a minimal
placeholder to satisfy the Match model's foreign key reference.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Tournament(Base):
    """
    A tournament competition with bracket progression.

    Stages: Group Stage -> Round of 16 -> Quarter-finals -> Semi-finals -> Final
    """
    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Tournament configuration
    team_count: Mapped[int] = mapped_column(Integer, default=16)
    current_stage: Mapped[str] = mapped_column(String(50), default="group_stage")

    # Status
    is_active: Mapped[bool] = mapped_column(default=True)
    is_complete: Mapped[bool] = mapped_column(default=False)

    # Winner
    winner_team_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<Tournament(id={self.id}, name='{self.name}', stage={self.current_stage})>"
