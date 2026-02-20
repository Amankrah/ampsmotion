"""
Team model for AmpeSports team competitions.
"""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.player import Player


class Team(Base):
    """
    A team competing in Team vs Team or Tournament mode.

    Teams have 15 players, with a maximum of 5 substitutions per match.
    """
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    abbreviation: Mapped[str] = mapped_column(String(5), nullable=False)

    # Team captain reference
    captain_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("players.id", use_alter=True),
        nullable=True
    )

    # Team colors for display
    primary_color: Mapped[str] = mapped_column(String(7), default="#2196F3")  # Hex color
    secondary_color: Mapped[str] = mapped_column(String(7), default="#FFFFFF")

    # Relationships
    players: Mapped[list["Player"]] = relationship(
        back_populates="team",
        foreign_keys="Player.team_id"
    )

    # Match statistics (for tournament tracking)
    total_wins: Mapped[int] = mapped_column(Integer, default=0)
    total_losses: Mapped[int] = mapped_column(Integer, default=0)
    total_ap_scored: Mapped[int] = mapped_column(Integer, default=0)
    total_ap_conceded: Mapped[int] = mapped_column(Integer, default=0)

    def __repr__(self) -> str:
        return f"<Team(id={self.id}, name='{self.name}', abbr='{self.abbreviation}')>"

    @property
    def player_count(self) -> int:
        """Number of players on the team."""
        return len(self.players)

    @property
    def active_players(self) -> list["Player"]:
        """Players who are not eliminated."""
        return [p for p in self.players if not p.is_eliminated and p.is_active]

    @property
    def is_full(self) -> bool:
        """Check if team has the maximum 15 players."""
        return self.player_count >= 15

    @property
    def ap_differential(self) -> int:
        """AP scored minus AP conceded."""
        return self.total_ap_scored - self.total_ap_conceded
