"""
Foul and violation models for AmpeSports rule enforcement.
"""

import enum
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.match import Match, Round
    from models.player import Player


class FoulType(enum.Enum):
    """Types of fouls and violations as defined in AmpeSports rules."""
    DELAY_OF_GAME = "delay_of_game"
    EXCESSIVE_CONTACT = "excessive_contact"
    ILLEGAL_FOOT_THRUST = "illegal_foot_thrust"
    ENCROACHMENT = "encroachment"
    ILLEGAL_SUBSTITUTION = "illegal_substitution"
    IMPROPER_POSITIONING = "improper_positioning"
    REENTRY_AFTER_ELIMINATION = "reentry_after_elimination"
    UNSPORTSMANLIKE_CONDUCT = "unsportsmanlike_conduct"
    INTENTIONAL_FOUL = "intentional_foul"
    EQUIPMENT_TAMPERING = "equipment_tampering"


class PenaltyAction(enum.Enum):
    """Possible penalties for fouls."""
    WARNING = "warning"
    AP_DEDUCTION = "ap_deduction"
    BOUT_LOSS = "bout_loss"
    ROUND_LOSS = "round_loss"
    DISQUALIFICATION = "disqualification"


# Default penalty progression for each foul type
FOUL_PENALTIES = {
    FoulType.DELAY_OF_GAME: {
        1: (PenaltyAction.WARNING, 0),
        2: (PenaltyAction.AP_DEDUCTION, 1),
    },
    FoulType.EXCESSIVE_CONTACT: {
        1: (PenaltyAction.WARNING, 0),
        2: (PenaltyAction.AP_DEDUCTION, 3),
    },
    FoulType.ILLEGAL_FOOT_THRUST: {
        1: (PenaltyAction.BOUT_LOSS, 0),
    },
    FoulType.ENCROACHMENT: {
        1: (PenaltyAction.BOUT_LOSS, 0),
    },
    FoulType.ILLEGAL_SUBSTITUTION: {
        1: (PenaltyAction.ROUND_LOSS, 0),
    },
    FoulType.IMPROPER_POSITIONING: {
        1: (PenaltyAction.ROUND_LOSS, 0),
    },
    FoulType.REENTRY_AFTER_ELIMINATION: {
        1: (PenaltyAction.ROUND_LOSS, 0),
        2: (PenaltyAction.AP_DEDUCTION, 3),
        3: (PenaltyAction.DISQUALIFICATION, 0),
    },
    FoulType.UNSPORTSMANLIKE_CONDUCT: {
        1: (PenaltyAction.WARNING, 0),
        2: (PenaltyAction.AP_DEDUCTION, 3),
        3: (PenaltyAction.DISQUALIFICATION, 0),
    },
    FoulType.INTENTIONAL_FOUL: {
        1: (PenaltyAction.DISQUALIFICATION, 0),
    },
    FoulType.EQUIPMENT_TAMPERING: {
        1: (PenaltyAction.DISQUALIFICATION, 0),
    },
}


class FoulRecord(Base):
    """
    A record of a foul or violation committed during a match.
    """
    __tablename__ = "foul_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False)
    round_id: Mapped[Optional[int]] = mapped_column(ForeignKey("rounds.id"), nullable=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)

    # Foul details
    foul_type: Mapped[FoulType] = mapped_column(SAEnum(FoulType), nullable=False)
    penalty: Mapped[PenaltyAction] = mapped_column(SAEnum(PenaltyAction), nullable=False)
    ap_deducted: Mapped[int] = mapped_column(Integer, default=0)

    # This is the nth occurrence of this foul type for this player in this match
    occurrence_number: Mapped[int] = mapped_column(Integer, default=1)

    # Optional notes from the official
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timing
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    match: Mapped["Match"] = relationship(back_populates="fouls")

    def __repr__(self) -> str:
        return f"<FoulRecord(id={self.id}, type={self.foul_type.value}, penalty={self.penalty.value})>"

    @classmethod
    def get_penalty(cls, foul_type: FoulType, occurrence: int = 1) -> tuple[PenaltyAction, int]:
        """
        Get the appropriate penalty for a foul based on occurrence count.

        Returns:
            Tuple of (PenaltyAction, AP to deduct)
        """
        foul_config = FOUL_PENALTIES.get(foul_type, {})

        # Find the highest defined occurrence that applies
        applicable_occurrence = 1
        for occ in sorted(foul_config.keys()):
            if occ <= occurrence:
                applicable_occurrence = occ

        return foul_config.get(applicable_occurrence, (PenaltyAction.WARNING, 0))
