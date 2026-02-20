"""
Tournament model for bracket management and persistence.

Stores tournament state including group stages, standings, and knockout brackets.
"""

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.team import Team
    from models.match import Match


# Association table for tournament teams
tournament_teams = Table(
    "tournament_teams",
    Base.metadata,
    Column("tournament_id", Integer, ForeignKey("tournaments.id"), primary_key=True),
    Column("team_id", Integer, ForeignKey("teams.id"), primary_key=True),
    Column("seed", Integer, nullable=True),
    Column("group_name", String(10), nullable=True),
)


class Tournament(Base):
    """
    A tournament competition with bracket progression.

    Stages: Group Stage -> Round of 16 -> Quarter-finals -> Semi-finals -> Final

    Tournament state (group standings, bracket positions, head-to-head records)
    is persisted in JSON fields for full recovery on reload.
    """
    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Tournament configuration
    num_groups: Mapped[int] = mapped_column(Integer, default=4)
    teams_per_group: Mapped[int] = mapped_column(Integer, default=4)
    team_count: Mapped[int] = mapped_column(Integer, default=16)

    # Current stage
    current_stage: Mapped[str] = mapped_column(String(50), default="group_stage")

    # Status
    is_active: Mapped[bool] = mapped_column(default=True)
    is_complete: Mapped[bool] = mapped_column(default=False)

    # Winner
    winner_team_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("teams.id"),
        nullable=True
    )
    runner_up_team_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("teams.id"),
        nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # State persistence (JSON)
    # Stores group assignments: {"A": [team_ids], "B": [team_ids], ...}
    groups_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Stores group standings: {"A": [{team_id, wins, losses, ap_scored, ...}], ...}
    group_standings_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Stores head-to-head records: {"team1_id-team2_id": {team1: {...}, team2: {...}}}
    head_to_head_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Stores knockout bracket state: {stage: [{match_id, slot1, slot2, winner, ...}]}
    knockout_bracket_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Stores group matches: [{match_id, team1_id, team2_id, winner_id, ...}]
    group_matches_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    teams: Mapped[list["Team"]] = relationship(
        secondary=tournament_teams,
        backref="tournaments"
    )
    matches: Mapped[list["Match"]] = relationship(
        back_populates="tournament",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Tournament(id={self.id}, name='{self.name}', stage={self.current_stage})>"

    # JSON property helpers
    @property
    def groups(self) -> dict[str, list[int]]:
        """Get group assignments."""
        if self.groups_json:
            return json.loads(self.groups_json)
        return {}

    @groups.setter
    def groups(self, value: dict[str, list[int]]) -> None:
        """Set group assignments."""
        self.groups_json = json.dumps(value)

    @property
    def group_standings(self) -> dict[str, list[dict]]:
        """Get group standings."""
        if self.group_standings_json:
            return json.loads(self.group_standings_json)
        return {}

    @group_standings.setter
    def group_standings(self, value: dict[str, list[dict]]) -> None:
        """Set group standings."""
        self.group_standings_json = json.dumps(value)

    @property
    def head_to_head(self) -> dict[str, dict]:
        """Get head-to-head records."""
        if self.head_to_head_json:
            return json.loads(self.head_to_head_json)
        return {}

    @head_to_head.setter
    def head_to_head(self, value: dict[str, dict]) -> None:
        """Set head-to-head records."""
        self.head_to_head_json = json.dumps(value)

    @property
    def knockout_bracket(self) -> dict[str, list[dict]]:
        """Get knockout bracket state."""
        if self.knockout_bracket_json:
            return json.loads(self.knockout_bracket_json)
        return {}

    @knockout_bracket.setter
    def knockout_bracket(self, value: dict[str, list[dict]]) -> None:
        """Set knockout bracket state."""
        self.knockout_bracket_json = json.dumps(value)

    @property
    def group_matches(self) -> list[dict]:
        """Get group match results."""
        if self.group_matches_json:
            return json.loads(self.group_matches_json)
        return []

    @group_matches.setter
    def group_matches(self, value: list[dict]) -> None:
        """Set group match results."""
        self.group_matches_json = json.dumps(value)

    def to_bracket_state(self) -> dict:
        """
        Export full tournament state for TournamentBracket engine.

        Returns dict that can be used to reconstruct a TournamentBracket.
        """
        return {
            "tournament_id": self.id,
            "name": self.name,
            "current_stage": self.current_stage,
            "num_groups": self.num_groups,
            "teams_per_group": self.teams_per_group,
            "groups": self.groups,
            "group_standings": self.group_standings,
            "head_to_head": self.head_to_head,
            "knockout_bracket": self.knockout_bracket,
            "group_matches": self.group_matches,
            "is_complete": self.is_complete,
            "winner_team_id": self.winner_team_id,
        }

    def update_from_bracket(self, bracket_engine) -> None:
        """
        Update tournament model from TournamentBracket engine state.

        Args:
            bracket_engine: TournamentBracket instance with current state
        """
        self.current_stage = bracket_engine.current_stage.value

        # Serialize groups
        self.groups = bracket_engine.groups

        # Serialize group standings
        standings_data = {}
        for group, standings in bracket_engine.group_standings.items():
            standings_data[group] = [
                {
                    "team_id": s.team_id,
                    "team_name": s.team_name,
                    "group": s.group,
                    "played": s.played,
                    "wins": s.wins,
                    "losses": s.losses,
                    "ap_scored": s.ap_scored,
                    "ap_conceded": s.ap_conceded,
                }
                for s in standings
            ]
        self.group_standings = standings_data

        # Serialize head-to-head
        h2h_data = {}
        for key, records in bracket_engine._head_to_head.items():
            key_str = f"{key[0]}-{key[1]}"
            h2h_data[key_str] = {
                str(team_id): {
                    "team_id": record.team_id,
                    "opponent_id": record.opponent_id,
                    "wins": record.wins,
                    "losses": record.losses,
                    "ap_scored": record.ap_scored,
                    "ap_conceded": record.ap_conceded,
                }
                for team_id, record in records.items()
            }
        self.head_to_head = h2h_data

        # Serialize knockout bracket
        knockout_data = {}
        for match in bracket_engine.knockout_matches:
            stage_key = match.stage.value
            if stage_key not in knockout_data:
                knockout_data[stage_key] = []

            knockout_data[stage_key].append({
                "match_id": match.match_id,
                "position": match.position,
                "slot1": {
                    "slot_id": match.slot1.slot_id,
                    "team_id": match.slot1.team_id,
                    "team_name": match.slot1.team_name,
                    "seed": match.slot1.seed,
                    "is_winner": match.slot1.is_winner,
                },
                "slot2": {
                    "slot_id": match.slot2.slot_id,
                    "team_id": match.slot2.team_id,
                    "team_name": match.slot2.team_name,
                    "seed": match.slot2.seed,
                    "is_winner": match.slot2.is_winner,
                },
                "winner_slot_id": match.winner_slot_id,
                "is_complete": match.is_complete,
                "winner_team_id": match.winner_team_id,
                "home_score": match.home_score,
                "away_score": match.away_score,
            })
        self.knockout_bracket = knockout_data

        # Serialize group matches
        group_matches_data = []
        for match in bracket_engine.group_matches:
            group_matches_data.append({
                "match_id": match.match_id,
                "position": match.position,
                "team1_id": match.slot1.team_id,
                "team1_name": match.slot1.team_name,
                "team2_id": match.slot2.team_id,
                "team2_name": match.slot2.team_name,
                "is_complete": match.is_complete,
                "winner_team_id": match.winner_team_id,
                "home_score": match.home_score,
                "away_score": match.away_score,
            })
        self.group_matches = group_matches_data

        # Check completion
        if bracket_engine.current_stage.value == "completed":
            self.is_complete = True
            self.completed_at = datetime.now(timezone.utc)
            # Find winner from final match
            final_matches = [m for m in bracket_engine.knockout_matches
                           if m.stage.value == "final"]
            if final_matches and final_matches[0].winner_team_id:
                self.winner_team_id = final_matches[0].winner_team_id
                # Runner-up is the other team in the final
                final = final_matches[0]
                if final.slot1.team_id == self.winner_team_id:
                    self.runner_up_team_id = final.slot2.team_id
                else:
                    self.runner_up_team_id = final.slot1.team_id


class TournamentTeamStats(Base):
    """
    Detailed statistics for a team in a tournament.

    Tracks per-tournament performance separate from overall team stats.
    """
    __tablename__ = "tournament_team_stats"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tournament_id: Mapped[int] = mapped_column(
        ForeignKey("tournaments.id"),
        nullable=False
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id"),
        nullable=False
    )

    # Group stage stats
    group_name: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    group_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    group_matches_played: Mapped[int] = mapped_column(Integer, default=0)
    group_wins: Mapped[int] = mapped_column(Integer, default=0)
    group_losses: Mapped[int] = mapped_column(Integer, default=0)
    group_ap_scored: Mapped[int] = mapped_column(Integer, default=0)
    group_ap_conceded: Mapped[int] = mapped_column(Integer, default=0)
    qualified_from_group: Mapped[bool] = mapped_column(default=False)

    # Knockout stats
    knockout_stage_reached: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    knockout_matches_played: Mapped[int] = mapped_column(Integer, default=0)
    knockout_wins: Mapped[int] = mapped_column(Integer, default=0)
    knockout_losses: Mapped[int] = mapped_column(Integer, default=0)
    knockout_ap_scored: Mapped[int] = mapped_column(Integer, default=0)
    knockout_ap_conceded: Mapped[int] = mapped_column(Integer, default=0)

    # Overall tournament stats
    total_ap_scored: Mapped[int] = mapped_column(Integer, default=0)
    total_ap_conceded: Mapped[int] = mapped_column(Integer, default=0)
    total_eliminations: Mapped[int] = mapped_column(Integer, default=0)
    final_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<TournamentTeamStats(tournament={self.tournament_id}, team={self.team_id})>"
