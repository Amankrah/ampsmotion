"""
Bout model for individual foot-thrust exchanges.
"""

import enum
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Integer, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.match import Round
    from models.player import Player


class BoutResult(enum.Enum):
    """
    The outcome of a bout as called by the Caller Ampfre.

    - OPA (Opare): Players thrust different feet - one wins
    - OSHI (Oshiwa): Players thrust the same foot - one wins
    """
    OPA = "opa"
    OSHI = "oshi"


class Bout(Base):
    """
    A single foot-thrust exchange between two players.

    Each bout results in 1 AP being awarded to the winner.
    """
    __tablename__ = "bouts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    round_id: Mapped[int] = mapped_column(ForeignKey("rounds.id"), nullable=False)

    # Bout sequence within the round
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    # The Caller's call
    caller_result: Mapped[BoutResult] = mapped_column(SAEnum(BoutResult), nullable=False)

    # Bout participants and outcome
    winner_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    loser_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)

    # When this bout occurred (for replay sync)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Time remaining in the round when this bout was recorded (for 1v1)
    time_remaining_ms: Mapped[int] = mapped_column(Integer, nullable=True)

    # Relationships
    round: Mapped["Round"] = relationship(back_populates="bouts")

    def __repr__(self) -> str:
        return f"<Bout(id={self.id}, round={self.round_id}, seq={self.sequence}, result={self.caller_result.value})>"

    @property
    def is_opa(self) -> bool:
        """Check if this bout was an Opa call."""
        return self.caller_result == BoutResult.OPA

    @property
    def is_oshi(self) -> bool:
        """Check if this bout was an Oshi call."""
        return self.caller_result == BoutResult.OSHI
