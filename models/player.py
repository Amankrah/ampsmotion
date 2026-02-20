"""
Player model for AmpeSports participants.
"""

import enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Integer, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.team import Team


class AgeCategory(enum.Enum):
    """Age categories as defined in AmpeSports rules."""
    JUVENILE_A = "Juvenile (a) 6-12"
    JUVENILE_B = "Juvenile (b) 13-17"
    YOUNG_ADULT_A = "Young Adults (a) 18-29"
    YOUNG_ADULT_B = "Young Adults (b) 30-39"
    MIDDLE_AGED_A = "Middle-aged Adults (a) 40-49"
    MIDDLE_AGED_B = "Middle-aged Adults (b) 50-59"
    OLD_ADULT = "Old Adults 60+"

    @classmethod
    def from_age(cls, age: int) -> "AgeCategory":
        """Determine age category from a player's age."""
        if 6 <= age <= 12:
            return cls.JUVENILE_A
        elif 13 <= age <= 17:
            return cls.JUVENILE_B
        elif 18 <= age <= 29:
            return cls.YOUNG_ADULT_A
        elif 30 <= age <= 39:
            return cls.YOUNG_ADULT_B
        elif 40 <= age <= 49:
            return cls.MIDDLE_AGED_A
        elif 50 <= age <= 59:
            return cls.MIDDLE_AGED_B
        else:
            return cls.OLD_ADULT


class Player(Base):
    """
    A player participating in AmpeSports matches.

    Players can be individuals (1v1 mode) or members of a team.
    """
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    jersey_number: Mapped[int] = mapped_column(Integer, nullable=True)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    age_category: Mapped[AgeCategory] = mapped_column(SAEnum(AgeCategory), nullable=False)

    # Team association (optional for 1v1 players)
    team_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teams.id"), nullable=True)
    team: Mapped[Optional["Team"]] = relationship(back_populates="players")

    # Player status
    is_active: Mapped[bool] = mapped_column(default=True)
    is_eliminated: Mapped[bool] = mapped_column(default=False)  # For team mode

    def __repr__(self) -> str:
        return f"<Player(id={self.id}, name='{self.name}', jersey={self.jersey_number})>"

    @classmethod
    def create(cls, name: str, age: int, jersey_number: int = None, team_id: int = None) -> "Player":
        """Factory method to create a player with auto-calculated age category."""
        return cls(
            name=name,
            age=age,
            jersey_number=jersey_number,
            age_category=AgeCategory.from_age(age),
            team_id=team_id,
        )
