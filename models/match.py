"""
Match, Game, and Round models for AmpeSports competitions.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.player import Player
    from models.team import Team
    from models.bout import Bout
    from models.foul import FoulRecord
    from models.official import Official


class GameMode(enum.Enum):
    """The three game modes defined in AmpeSports rules."""
    ONE_VS_ONE = "1v1"
    TEAM_VS_TEAM = "team_vs_team"
    TOURNAMENT = "tournament"


class MatchStatus(enum.Enum):
    """Match lifecycle states."""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    PROTESTED = "protested"


class Match(Base):
    """
    A match between two players or two teams.

    - 1v1 Mode: 5, 10, or 15 rounds of 60-second continuous play
    - Team Mode: 3 games, each with 15 rounds (Shooter Mode)
    - Tournament: Team Mode with bracket progression
    """
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    game_mode: Mapped[GameMode] = mapped_column(SAEnum(GameMode), nullable=False)
    status: Mapped[MatchStatus] = mapped_column(
        SAEnum(MatchStatus),
        default=MatchStatus.SCHEDULED
    )

    # Match configuration
    total_rounds: Mapped[int] = mapped_column(Integer, nullable=False)  # 5, 10, or 15

    # 1v1 mode participants
    player1_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("players.id"),
        nullable=True
    )
    player2_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("players.id"),
        nullable=True
    )

    # Team mode participants
    home_team_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("teams.id"),
        nullable=True
    )
    away_team_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("teams.id"),
        nullable=True
    )

    # Tournament reference
    tournament_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("tournaments.id"),
        nullable=True
    )
    tournament_stage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Toss details
    toss_winner: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # "home"/"away" or "player1"/"player2"
    toss_choice: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # "opa" or "oshi"

    # Timing
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Final scores
    player1_total_ap: Mapped[int] = mapped_column(Integer, default=0)
    player2_total_ap: Mapped[int] = mapped_column(Integer, default=0)
    home_total_ap: Mapped[int] = mapped_column(Integer, default=0)
    away_total_ap: Mapped[int] = mapped_column(Integer, default=0)

    # Winner reference
    winner_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # player_id or team_id

    # Team mode specific
    home_substitutions_used: Mapped[int] = mapped_column(Integer, default=0)
    away_substitutions_used: Mapped[int] = mapped_column(Integer, default=0)
    max_substitutions: Mapped[int] = mapped_column(Integer, default=5)

    # Relationships
    games: Mapped[list["Game"]] = relationship(back_populates="match", cascade="all, delete-orphan")
    fouls: Mapped[list["FoulRecord"]] = relationship(back_populates="match", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Match(id={self.id}, mode={self.game_mode.value}, status={self.status.value})>"

    @property
    def current_round(self) -> int:
        """Get the current round number."""
        if not self.games:
            return 0
        active_game = self.active_game
        if active_game:
            return len([r for r in active_game.rounds if r.is_complete]) + 1
        return self.total_rounds

    @property
    def active_game(self) -> Optional["Game"]:
        """Get the currently active game (for Team mode)."""
        for game in self.games:
            if not game.is_complete:
                return game
        return None

    @property
    def is_1v1(self) -> bool:
        """Check if this is a 1v1 match."""
        return self.game_mode == GameMode.ONE_VS_ONE


class Game(Base):
    """
    A game within a Team vs Team match.

    Each match has 3 games, each game has 15 rounds.
    """
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False)
    game_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, or 3

    # Scores
    home_ap: Mapped[int] = mapped_column(Integer, default=0)
    away_ap: Mapped[int] = mapped_column(Integer, default=0)

    # Eliminations
    home_eliminations: Mapped[int] = mapped_column(Integer, default=0)
    away_eliminations: Mapped[int] = mapped_column(Integer, default=0)

    # Status
    is_complete: Mapped[bool] = mapped_column(default=False)
    winner: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # "home" or "away"

    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    match: Mapped["Match"] = relationship(back_populates="games")
    rounds: Mapped[list["Round"]] = relationship(back_populates="game", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Game(id={self.id}, match={self.match_id}, game_number={self.game_number})>"


class Round(Base):
    """
    A round within a match or game.

    - 1v1 Mode: Each round is 60 seconds of continuous bouts
    - Team Mode: Each round is one cycle through the player queue
    """
    __tablename__ = "rounds"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # For 1v1 mode, track which player is Opa/Oshi this round
    opa_player_id: Mapped[Optional[int]] = mapped_column(ForeignKey("players.id"), nullable=True)
    oshi_player_id: Mapped[Optional[int]] = mapped_column(ForeignKey("players.id"), nullable=True)

    # Scores for this round
    player1_ap: Mapped[int] = mapped_column(Integer, default=0)
    player2_ap: Mapped[int] = mapped_column(Integer, default=0)
    player1_opa_wins: Mapped[int] = mapped_column(Integer, default=0)
    player1_oshi_wins: Mapped[int] = mapped_column(Integer, default=0)
    player2_opa_wins: Mapped[int] = mapped_column(Integer, default=0)
    player2_oshi_wins: Mapped[int] = mapped_column(Integer, default=0)

    # Total bouts in this round
    bout_count: Mapped[int] = mapped_column(Integer, default=0)

    # Round timing (1v1 mode)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=60)
    actual_duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Status
    is_complete: Mapped[bool] = mapped_column(default=False)
    winner_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # player_id
    winner_side: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # "player1"/"player2" or "home"/"away"

    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Team mode: player eliminated this round
    eliminated_player_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("players.id"),
        nullable=True
    )

    # Relationships
    game: Mapped["Game"] = relationship(back_populates="rounds")
    bouts: Mapped[list["Bout"]] = relationship(back_populates="round", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Round(id={self.id}, game={self.game_id}, round_number={self.round_number})>"
