"""
Tournament Bracket Engine

Manages tournament progression through stages:
Group Stage -> Round of 16 -> Quarter-finals -> Semi-finals -> Final

Based on AmpeSports rules: Tournament mode follows Team vs Team rules
with bracket structure.
"""

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from PySide6.QtCore import QObject, Signal


class TournamentStage(enum.Enum):
    """Tournament progression stages."""
    GROUP_STAGE = "group_stage"
    ROUND_OF_16 = "round_of_16"
    QUARTER_FINAL = "quarter_final"
    SEMI_FINAL = "semi_final"
    FINAL = "final"
    COMPLETED = "completed"


@dataclass
class BracketSlot:
    """A slot in the tournament bracket."""
    slot_id: str
    stage: TournamentStage
    position: int  # Position within the stage (0-indexed)
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    seed: Optional[int] = None
    is_winner: bool = False
    match_id: Optional[int] = None


@dataclass
class BracketMatch:
    """A match in the bracket."""
    match_id: str
    stage: TournamentStage
    position: int
    slot1: BracketSlot
    slot2: BracketSlot
    winner_slot_id: Optional[str] = None  # Slot ID this winner advances to
    is_complete: bool = False
    winner_team_id: Optional[int] = None
    home_score: int = 0
    away_score: int = 0
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class GroupStanding:
    """Team standing within a group."""
    team_id: int
    team_name: str
    group: str
    played: int = 0
    wins: int = 0
    losses: int = 0
    ap_scored: int = 0
    ap_conceded: int = 0

    @property
    def ap_differential(self) -> int:
        return self.ap_scored - self.ap_conceded

    @property
    def points(self) -> int:
        """3 points per win."""
        return self.wins * 3


class TournamentBracket(QObject):
    """
    Manages tournament bracket generation and progression.

    Stages: Group Stage -> Round of 16 -> Quarter-finals -> Semi-finals -> Final

    Usage:
        bracket = TournamentBracket()
        bracket.initialize_tournament(teams, num_groups=4)
        bracket.record_group_result(match_id, winner_id, home_score, away_score)
        bracket.advance_to_knockout()
        bracket.record_knockout_result(match_id, winner_id)
    """

    # Signals
    stage_changed = Signal(str)  # stage name
    match_completed = Signal(dict)  # match details
    tournament_completed = Signal(dict)  # final results
    bracket_updated = Signal()  # bracket structure changed

    # Stage order for progression
    STAGES = [
        TournamentStage.GROUP_STAGE,
        TournamentStage.ROUND_OF_16,
        TournamentStage.QUARTER_FINAL,
        TournamentStage.SEMI_FINAL,
        TournamentStage.FINAL,
        TournamentStage.COMPLETED,
    ]

    def __init__(self, tournament_id: Optional[int] = None):
        super().__init__()
        self.tournament_id = tournament_id
        self.current_stage = TournamentStage.GROUP_STAGE

        # Group stage data
        self.groups: dict[str, list[int]] = {}  # group_name -> [team_ids]
        self.group_standings: dict[str, list[GroupStanding]] = {}
        self.group_matches: list[BracketMatch] = []

        # Knockout bracket data
        self.bracket_slots: dict[str, BracketSlot] = {}
        self.knockout_matches: list[BracketMatch] = []

        # All teams
        self._teams: dict[int, str] = {}  # team_id -> team_name

    def initialize_tournament(
        self,
        teams: list[dict],  # [{"id": 1, "name": "Team A"}, ...]
        num_groups: int = 4,
        teams_per_group: int = 4
    ) -> None:
        """
        Initialize a tournament with teams seeded into groups.

        Args:
            teams: List of team dictionaries with 'id' and 'name' keys
            num_groups: Number of groups for group stage
            teams_per_group: Teams per group
        """
        if len(teams) != num_groups * teams_per_group:
            raise ValueError(
                f"Expected {num_groups * teams_per_group} teams, got {len(teams)}"
            )

        # Store team info
        self._teams = {t["id"]: t["name"] for t in teams}

        # Seed teams into groups using serpentine seeding
        self._seed_groups(teams, num_groups, teams_per_group)

        # Generate group stage matches
        self._generate_group_matches()

        # Initialize knockout bracket structure (empty slots)
        self._initialize_knockout_bracket()

        self.current_stage = TournamentStage.GROUP_STAGE
        self.bracket_updated.emit()

    def _seed_groups(
        self,
        teams: list[dict],
        num_groups: int,
        teams_per_group: int
    ) -> None:
        """
        Seed teams into groups using serpentine seeding.

        Serpentine: Top seeds spread across groups, then reverse direction
        for next row, creating balanced groups.

        Example with 16 teams, 4 groups:
        Group A: 1, 8, 9, 16
        Group B: 2, 7, 10, 15
        Group C: 3, 6, 11, 14
        Group D: 4, 5, 12, 13
        """
        group_names = [chr(ord('A') + i) for i in range(num_groups)]
        self.groups = {name: [] for name in group_names}
        self.group_standings = {name: [] for name in group_names}

        # Assume teams are already sorted by seed/ranking
        team_index = 0
        for row in range(teams_per_group):
            if row % 2 == 0:
                # Left to right
                group_order = group_names
            else:
                # Right to left (serpentine)
                group_order = list(reversed(group_names))

            for group_name in group_order:
                if team_index < len(teams):
                    team = teams[team_index]
                    self.groups[group_name].append(team["id"])
                    self.group_standings[group_name].append(
                        GroupStanding(
                            team_id=team["id"],
                            team_name=team["name"],
                            group=group_name
                        )
                    )
                    team_index += 1

    def _generate_group_matches(self) -> None:
        """Generate round-robin matches for each group."""
        self.group_matches = []
        match_counter = 0

        for group_name, team_ids in self.groups.items():
            # Round-robin: each team plays every other team once
            for i, team1_id in enumerate(team_ids):
                for team2_id in team_ids[i + 1:]:
                    match_counter += 1
                    match_id = f"G{group_name}_{match_counter}"

                    slot1 = BracketSlot(
                        slot_id=f"{match_id}_1",
                        stage=TournamentStage.GROUP_STAGE,
                        position=match_counter,
                        team_id=team1_id,
                        team_name=self._teams.get(team1_id, ""),
                    )
                    slot2 = BracketSlot(
                        slot_id=f"{match_id}_2",
                        stage=TournamentStage.GROUP_STAGE,
                        position=match_counter,
                        team_id=team2_id,
                        team_name=self._teams.get(team2_id, ""),
                    )

                    self.group_matches.append(BracketMatch(
                        match_id=match_id,
                        stage=TournamentStage.GROUP_STAGE,
                        position=match_counter,
                        slot1=slot1,
                        slot2=slot2,
                    ))

    def _initialize_knockout_bracket(self) -> None:
        """Initialize empty knockout bracket structure."""
        self.knockout_matches = []

        # Round of 16: 8 matches
        for i in range(8):
            match_id = f"R16_{i + 1}"
            winner_match = f"QF_{i // 2 + 1}"

            slot1 = BracketSlot(
                slot_id=f"{match_id}_1",
                stage=TournamentStage.ROUND_OF_16,
                position=i * 2,
            )
            slot2 = BracketSlot(
                slot_id=f"{match_id}_2",
                stage=TournamentStage.ROUND_OF_16,
                position=i * 2 + 1,
            )

            self.bracket_slots[slot1.slot_id] = slot1
            self.bracket_slots[slot2.slot_id] = slot2

            self.knockout_matches.append(BracketMatch(
                match_id=match_id,
                stage=TournamentStage.ROUND_OF_16,
                position=i,
                slot1=slot1,
                slot2=slot2,
                winner_slot_id=f"{winner_match}_{(i % 2) + 1}",
            ))

        # Quarter-finals: 4 matches
        for i in range(4):
            match_id = f"QF_{i + 1}"
            winner_match = f"SF_{i // 2 + 1}"

            slot1 = BracketSlot(
                slot_id=f"{match_id}_1",
                stage=TournamentStage.QUARTER_FINAL,
                position=i * 2,
            )
            slot2 = BracketSlot(
                slot_id=f"{match_id}_2",
                stage=TournamentStage.QUARTER_FINAL,
                position=i * 2 + 1,
            )

            self.bracket_slots[slot1.slot_id] = slot1
            self.bracket_slots[slot2.slot_id] = slot2

            self.knockout_matches.append(BracketMatch(
                match_id=match_id,
                stage=TournamentStage.QUARTER_FINAL,
                position=i,
                slot1=slot1,
                slot2=slot2,
                winner_slot_id=f"{winner_match}_{(i % 2) + 1}",
            ))

        # Semi-finals: 2 matches
        for i in range(2):
            match_id = f"SF_{i + 1}"

            slot1 = BracketSlot(
                slot_id=f"{match_id}_1",
                stage=TournamentStage.SEMI_FINAL,
                position=i * 2,
            )
            slot2 = BracketSlot(
                slot_id=f"{match_id}_2",
                stage=TournamentStage.SEMI_FINAL,
                position=i * 2 + 1,
            )

            self.bracket_slots[slot1.slot_id] = slot1
            self.bracket_slots[slot2.slot_id] = slot2

            self.knockout_matches.append(BracketMatch(
                match_id=match_id,
                stage=TournamentStage.SEMI_FINAL,
                position=i,
                slot1=slot1,
                slot2=slot2,
                winner_slot_id=f"FINAL_1_{(i % 2) + 1}",
            ))

        # Final: 1 match
        slot1 = BracketSlot(
            slot_id="FINAL_1_1",
            stage=TournamentStage.FINAL,
            position=0,
        )
        slot2 = BracketSlot(
            slot_id="FINAL_1_2",
            stage=TournamentStage.FINAL,
            position=1,
        )

        self.bracket_slots[slot1.slot_id] = slot1
        self.bracket_slots[slot2.slot_id] = slot2

        self.knockout_matches.append(BracketMatch(
            match_id="FINAL_1",
            stage=TournamentStage.FINAL,
            position=0,
            slot1=slot1,
            slot2=slot2,
            winner_slot_id=None,  # Tournament winner
        ))

    def record_group_result(
        self,
        match_id: str,
        winner_team_id: int,
        home_score: int,
        away_score: int
    ) -> None:
        """
        Record a group stage match result.

        Args:
            match_id: The match identifier (e.g., "GA_1")
            winner_team_id: ID of the winning team
            home_score: Total AP scored by home team
            away_score: Total AP scored by away team
        """
        # Find the match
        match = next((m for m in self.group_matches if m.match_id == match_id), None)
        if not match:
            raise ValueError(f"Match not found: {match_id}")

        # Update match
        match.is_complete = True
        match.winner_team_id = winner_team_id
        match.home_score = home_score
        match.away_score = away_score
        match.completed_at = datetime.now(timezone.utc)

        # Mark winner slot
        if match.slot1.team_id == winner_team_id:
            match.slot1.is_winner = True
        else:
            match.slot2.is_winner = True

        # Update standings
        team1_id = match.slot1.team_id
        team2_id = match.slot2.team_id

        for group_standings in self.group_standings.values():
            for standing in group_standings:
                if standing.team_id == team1_id:
                    standing.played += 1
                    standing.ap_scored += home_score
                    standing.ap_conceded += away_score
                    if winner_team_id == team1_id:
                        standing.wins += 1
                    else:
                        standing.losses += 1

                elif standing.team_id == team2_id:
                    standing.played += 1
                    standing.ap_scored += away_score
                    standing.ap_conceded += home_score
                    if winner_team_id == team2_id:
                        standing.wins += 1
                    else:
                        standing.losses += 1

        self.match_completed.emit({
            "match_id": match_id,
            "stage": "group_stage",
            "winner_team_id": winner_team_id,
            "home_score": home_score,
            "away_score": away_score,
        })
        self.bracket_updated.emit()

    def get_group_standings(self, group: str) -> list[GroupStanding]:
        """
        Get sorted standings for a group.

        Sorted by: points (desc), AP differential (desc), AP scored (desc)
        """
        standings = self.group_standings.get(group, [])
        return sorted(
            standings,
            key=lambda s: (s.points, s.ap_differential, s.ap_scored),
            reverse=True
        )

    def is_group_stage_complete(self) -> bool:
        """Check if all group stage matches are complete."""
        return all(m.is_complete for m in self.group_matches)

    def advance_to_knockout(self) -> None:
        """
        Advance top teams from group stage to knockout bracket.

        Standard format: Top 2 from each group advance to Round of 16.
        """
        if not self.is_group_stage_complete():
            raise RuntimeError("Group stage is not complete")

        # Get top 2 from each group
        qualifiers: list[tuple[int, str, int]] = []  # (team_id, team_name, seed)

        group_names = sorted(self.groups.keys())
        for i, group in enumerate(group_names):
            standings = self.get_group_standings(group)
            if len(standings) >= 2:
                # Group winner
                qualifiers.append((
                    standings[0].team_id,
                    standings[0].team_name,
                    i * 2 + 1  # Seed 1, 3, 5, 7
                ))
                # Group runner-up
                qualifiers.append((
                    standings[1].team_id,
                    standings[1].team_name,
                    i * 2 + 2  # Seed 2, 4, 6, 8
                ))

        # Place teams into Round of 16 bracket
        # Standard bracket: 1v16, 8v9, 5v12, 4v13, 3v14, 6v11, 7v10, 2v15
        # For 16 teams from 4 groups: cross-group matchups
        # A1 vs B2, C1 vs D2, A2 vs B1, C2 vs D1, etc.
        bracket_order = [
            (0, 3),   # A1 vs B2
            (4, 7),   # C1 vs D2
            (2, 1),   # A2 vs B1
            (6, 5),   # C2 vs D1
            (1, 2),   # B1 vs A2
            (5, 6),   # D1 vs C2
            (3, 0),   # B2 vs A1
            (7, 4),   # D2 vs C1
        ]

        r16_matches = [m for m in self.knockout_matches
                       if m.stage == TournamentStage.ROUND_OF_16]

        for i, (idx1, idx2) in enumerate(bracket_order):
            if idx1 < len(qualifiers) and idx2 < len(qualifiers):
                team1 = qualifiers[idx1]
                team2 = qualifiers[idx2]

                r16_matches[i].slot1.team_id = team1[0]
                r16_matches[i].slot1.team_name = team1[1]
                r16_matches[i].slot1.seed = team1[2]

                r16_matches[i].slot2.team_id = team2[0]
                r16_matches[i].slot2.team_name = team2[1]
                r16_matches[i].slot2.seed = team2[2]

        self.current_stage = TournamentStage.ROUND_OF_16
        self.stage_changed.emit(self.current_stage.value)
        self.bracket_updated.emit()

    def record_knockout_result(
        self,
        match_id: str,
        winner_team_id: int,
        home_score: int = 0,
        away_score: int = 0
    ) -> None:
        """
        Record a knockout stage match result.

        The winner automatically advances to the next round.
        """
        match = next(
            (m for m in self.knockout_matches if m.match_id == match_id),
            None
        )
        if not match:
            raise ValueError(f"Match not found: {match_id}")

        # Update match
        match.is_complete = True
        match.winner_team_id = winner_team_id
        match.home_score = home_score
        match.away_score = away_score
        match.completed_at = datetime.now(timezone.utc)

        # Determine winner slot
        if match.slot1.team_id == winner_team_id:
            winner_slot = match.slot1
            match.slot1.is_winner = True
        else:
            winner_slot = match.slot2
            match.slot2.is_winner = True

        # Advance winner to next round
        if match.winner_slot_id and match.winner_slot_id in self.bracket_slots:
            next_slot = self.bracket_slots[match.winner_slot_id]
            next_slot.team_id = winner_team_id
            next_slot.team_name = winner_slot.team_name
            next_slot.seed = winner_slot.seed

        self.match_completed.emit({
            "match_id": match_id,
            "stage": match.stage.value,
            "winner_team_id": winner_team_id,
            "home_score": home_score,
            "away_score": away_score,
        })

        # Check if stage is complete and advance
        self._check_stage_advancement(match.stage)

        self.bracket_updated.emit()

    def _check_stage_advancement(self, completed_stage: TournamentStage) -> None:
        """Check if all matches in a stage are complete and advance."""
        stage_matches = [m for m in self.knockout_matches if m.stage == completed_stage]

        if all(m.is_complete for m in stage_matches):
            # Find next stage
            current_index = self.STAGES.index(completed_stage)
            if current_index + 1 < len(self.STAGES):
                next_stage = self.STAGES[current_index + 1]
                self.current_stage = next_stage
                self.stage_changed.emit(next_stage.value)

                # Check if tournament is complete
                if next_stage == TournamentStage.COMPLETED:
                    final_match = next(
                        (m for m in self.knockout_matches
                         if m.stage == TournamentStage.FINAL),
                        None
                    )
                    if final_match and final_match.winner_team_id:
                        self.tournament_completed.emit({
                            "winner_team_id": final_match.winner_team_id,
                            "winner_team_name": self._teams.get(
                                final_match.winner_team_id, ""
                            ),
                        })

    def get_current_stage(self) -> TournamentStage:
        """Get the current tournament stage."""
        return self.current_stage

    def get_bracket_display(self) -> dict:
        """
        Get bracket data for visualization.

        Returns nested dict suitable for bracket visualization widget.
        """
        return {
            "tournament_id": self.tournament_id,
            "current_stage": self.current_stage.value,
            "groups": {
                group: {
                    "standings": [
                        {
                            "team_id": s.team_id,
                            "team_name": s.team_name,
                            "played": s.played,
                            "wins": s.wins,
                            "losses": s.losses,
                            "points": s.points,
                            "ap_scored": s.ap_scored,
                            "ap_conceded": s.ap_conceded,
                            "ap_differential": s.ap_differential,
                        }
                        for s in self.get_group_standings(group)
                    ],
                    "matches": [
                        self._match_to_dict(m)
                        for m in self.group_matches
                        if m.match_id.startswith(f"G{group}")
                    ],
                }
                for group in sorted(self.groups.keys())
            },
            "knockout": {
                stage.value: [
                    self._match_to_dict(m)
                    for m in self.knockout_matches
                    if m.stage == stage
                ]
                for stage in [
                    TournamentStage.ROUND_OF_16,
                    TournamentStage.QUARTER_FINAL,
                    TournamentStage.SEMI_FINAL,
                    TournamentStage.FINAL,
                ]
            },
        }

    def _match_to_dict(self, match: BracketMatch) -> dict:
        """Convert a BracketMatch to dictionary."""
        return {
            "match_id": match.match_id,
            "stage": match.stage.value,
            "position": match.position,
            "team1": {
                "id": match.slot1.team_id,
                "name": match.slot1.team_name,
                "seed": match.slot1.seed,
                "is_winner": match.slot1.is_winner,
            },
            "team2": {
                "id": match.slot2.team_id,
                "name": match.slot2.team_name,
                "seed": match.slot2.seed,
                "is_winner": match.slot2.is_winner,
            },
            "is_complete": match.is_complete,
            "home_score": match.home_score,
            "away_score": match.away_score,
        }

    def get_upcoming_matches(self) -> list[BracketMatch]:
        """Get incomplete matches for the current stage."""
        if self.current_stage == TournamentStage.GROUP_STAGE:
            return [m for m in self.group_matches if not m.is_complete]
        else:
            return [
                m for m in self.knockout_matches
                if m.stage == self.current_stage and not m.is_complete
            ]

    def get_match_by_id(self, match_id: str) -> Optional[BracketMatch]:
        """Get a specific match by ID."""
        # Check group matches
        for match in self.group_matches:
            if match.match_id == match_id:
                return match

        # Check knockout matches
        for match in self.knockout_matches:
            if match.match_id == match_id:
                return match

        return None
