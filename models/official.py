"""
Official (Ampfre) model for match officiating.
"""

import enum
from typing import Optional

from sqlalchemy import String, ForeignKey, Enum as SAEnum, Table, Column, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class OfficialRole(enum.Enum):
    """Officiating roles as defined in AmpeSports rules."""
    MASTER_AMPFRE = "master_ampfre"  # Oversees all, master recorder, announces scores
    CALLER_AMPFRE = "caller_ampfre"  # Calls "Opa" or "Oshi" for each bout
    RECORDER_AMPFRE = "recorder_ampfre"  # Independent score recorder (2 per match)
    TIMER = "timer"  # Calls START/STOP, manages round timing
    COUNTER = "counter"  # Counts total bouts per round
    VIDEO_ASSISTANT = "video_assistant"  # Manages camera/replay technology


# Association table for match-official relationship
match_officials = Table(
    "match_officials",
    Base.metadata,
    Column("match_id", Integer, ForeignKey("matches.id"), primary_key=True),
    Column("official_id", Integer, ForeignKey("officials.id"), primary_key=True),
    Column("role", String(50)),  # Role in this specific match
)


class Official(Base):
    """
    An official (Ampfre) who can officiate matches.
    """
    __tablename__ = "officials"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Primary role (can officiate other roles as needed)
    primary_role: Mapped[OfficialRole] = mapped_column(
        SAEnum(OfficialRole),
        default=OfficialRole.RECORDER_AMPFRE
    )

    # Certification level (for future use)
    certification_level: Mapped[int] = mapped_column(default=1)

    # Contact info (optional)
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(default=True)

    def __repr__(self) -> str:
        return f"<Official(id={self.id}, name='{self.name}', role={self.primary_role.value})>"

    @property
    def role_display(self) -> str:
        """Human-readable role name."""
        role_names = {
            OfficialRole.MASTER_AMPFRE: "Master Ampfre",
            OfficialRole.CALLER_AMPFRE: "Caller Ampfre",
            OfficialRole.RECORDER_AMPFRE: "Recorder Ampfre",
            OfficialRole.TIMER: "Timer",
            OfficialRole.COUNTER: "Counter",
            OfficialRole.VIDEO_ASSISTANT: "Video Assistant Ampfre",
        }
        return role_names.get(self.primary_role, self.primary_role.value)
