"""
Tests for Tournament Bracket Engine

Tests tournament bracket generation, group stage seeding,
knockout progression, and bracket visualization data.
"""

import pytest
from engine.tournament_bracket import (
    TournamentBracket,
    TournamentStage,
    BracketSlot,
    BracketMatch,
    GroupStanding,
)


class TestTournamentBracketSetup:
    """Tests for tournament initialization and setup."""

    def test_initialize_16_team_tournament(self):
        """Test initializing a 16-team tournament with 4 groups."""
        teams = [{"id": i, "name": f"Team {i}"} for i in range(1, 17)]

        bracket = TournamentBracket()
        bracket.initialize_tournament(teams, num_groups=4, teams_per_group=4)

        # Should have 4 groups
        assert len(bracket.groups) == 4
        assert set(bracket.groups.keys()) == {"A", "B", "C", "D"}

        # Each group should have 4 teams
        for group_name, team_ids in bracket.groups.items():
            assert len(team_ids) == 4

        # Should start in group stage
        assert bracket.current_stage == TournamentStage.GROUP_STAGE

    def test_serpentine_seeding(self):
        """Test that serpentine seeding distributes top seeds across groups."""
        teams = [{"id": i, "name": f"Team {i}"} for i in range(1, 17)]

        bracket = TournamentBracket()
        bracket.initialize_tournament(teams, num_groups=4, teams_per_group=4)

        # Team 1 should be in Group A
        assert 1 in bracket.groups["A"]
        # Team 2 should be in Group B
        assert 2 in bracket.groups["B"]
        # Team 3 should be in Group C
        assert 3 in bracket.groups["C"]
        # Team 4 should be in Group D
        assert 4 in bracket.groups["D"]

        # Serpentine: Team 5-8 go right-to-left (D, C, B, A)
        assert 5 in bracket.groups["D"]
        assert 6 in bracket.groups["C"]
        assert 7 in bracket.groups["B"]
        assert 8 in bracket.groups["A"]

    def test_group_matches_generated(self):
        """Test that round-robin group matches are generated."""
        teams = [{"id": i, "name": f"Team {i}"} for i in range(1, 17)]

        bracket = TournamentBracket()
        bracket.initialize_tournament(teams, num_groups=4, teams_per_group=4)

        # 4 teams per group = 6 matches per group (round-robin)
        # 4 groups = 24 total group matches
        assert len(bracket.group_matches) == 24

    def test_knockout_bracket_initialized(self):
        """Test that knockout bracket structure is created."""
        teams = [{"id": i, "name": f"Team {i}"} for i in range(1, 17)]

        bracket = TournamentBracket()
        bracket.initialize_tournament(teams, num_groups=4, teams_per_group=4)

        # Count matches by stage
        r16_matches = [m for m in bracket.knockout_matches
                       if m.stage == TournamentStage.ROUND_OF_16]
        qf_matches = [m for m in bracket.knockout_matches
                      if m.stage == TournamentStage.QUARTER_FINAL]
        sf_matches = [m for m in bracket.knockout_matches
                      if m.stage == TournamentStage.SEMI_FINAL]
        final_matches = [m for m in bracket.knockout_matches
                         if m.stage == TournamentStage.FINAL]

        assert len(r16_matches) == 8
        assert len(qf_matches) == 4
        assert len(sf_matches) == 2
        assert len(final_matches) == 1

    def test_invalid_team_count_raises_error(self):
        """Test that mismatched team count raises error."""
        teams = [{"id": i, "name": f"Team {i}"} for i in range(1, 10)]  # 9 teams

        bracket = TournamentBracket()
        with pytest.raises(ValueError):
            bracket.initialize_tournament(teams, num_groups=4, teams_per_group=4)


class TestGroupStage:
    """Tests for group stage functionality."""

    @pytest.fixture
    def bracket_with_groups(self):
        """Create a bracket with initialized groups."""
        teams = [{"id": i, "name": f"Team {i}"} for i in range(1, 17)]
        bracket = TournamentBracket()
        bracket.initialize_tournament(teams, num_groups=4, teams_per_group=4)
        return bracket

    def test_record_group_match_result(self, bracket_with_groups):
        """Test recording a group match result."""
        bracket = bracket_with_groups

        # Get first group A match
        group_a_matches = [m for m in bracket.group_matches
                          if m.match_id.startswith("GA")]
        match = group_a_matches[0]

        team1_id = match.slot1.team_id
        team2_id = match.slot2.team_id

        bracket.record_group_result(
            match_id=match.match_id,
            winner_team_id=team1_id,
            home_score=15,
            away_score=10
        )

        # Match should be marked complete
        assert match.is_complete
        assert match.winner_team_id == team1_id
        assert match.home_score == 15
        assert match.away_score == 10

    def test_group_standings_updated(self, bracket_with_groups):
        """Test that standings are updated after match."""
        bracket = bracket_with_groups

        # Get first group A match
        group_a_matches = [m for m in bracket.group_matches
                          if m.match_id.startswith("GA")]
        match = group_a_matches[0]

        team1_id = match.slot1.team_id
        team2_id = match.slot2.team_id

        bracket.record_group_result(
            match_id=match.match_id,
            winner_team_id=team1_id,
            home_score=15,
            away_score=10
        )

        # Check standings
        standings = bracket.get_group_standings("A")

        # Find team1 in standings
        team1_standing = next(s for s in standings if s.team_id == team1_id)
        assert team1_standing.wins == 1
        assert team1_standing.losses == 0
        assert team1_standing.ap_scored == 15
        assert team1_standing.ap_conceded == 10
        assert team1_standing.points == 3

        # Find team2 in standings
        team2_standing = next(s for s in standings if s.team_id == team2_id)
        assert team2_standing.wins == 0
        assert team2_standing.losses == 1
        assert team2_standing.ap_scored == 10
        assert team2_standing.ap_conceded == 15
        assert team2_standing.points == 0

    def test_group_standings_sorted_correctly(self, bracket_with_groups):
        """Test standings are sorted by points, then AP differential."""
        bracket = bracket_with_groups

        # Simulate full group A
        group_a_teams = bracket.groups["A"]
        group_a_matches = [m for m in bracket.group_matches
                          if m.match_id.startswith("GA")]

        # Record all group A matches
        for match in group_a_matches:
            # First team wins each match for simplicity
            bracket.record_group_result(
                match_id=match.match_id,
                winner_team_id=match.slot1.team_id,
                home_score=10,
                away_score=5
            )

        standings = bracket.get_group_standings("A")

        # Should be sorted by points descending
        for i in range(len(standings) - 1):
            assert standings[i].points >= standings[i + 1].points

    def test_is_group_stage_complete(self, bracket_with_groups):
        """Test detection of group stage completion."""
        bracket = bracket_with_groups

        assert not bracket.is_group_stage_complete()

        # Complete all group matches
        for match in bracket.group_matches:
            bracket.record_group_result(
                match_id=match.match_id,
                winner_team_id=match.slot1.team_id,
                home_score=10,
                away_score=5
            )

        assert bracket.is_group_stage_complete()


class TestKnockoutStage:
    """Tests for knockout stage functionality."""

    @pytest.fixture
    def bracket_after_groups(self):
        """Create a bracket with completed group stage."""
        teams = [{"id": i, "name": f"Team {i}"} for i in range(1, 17)]
        bracket = TournamentBracket()
        bracket.initialize_tournament(teams, num_groups=4, teams_per_group=4)

        # Complete all group matches
        for match in bracket.group_matches:
            bracket.record_group_result(
                match_id=match.match_id,
                winner_team_id=match.slot1.team_id,
                home_score=10,
                away_score=5
            )

        bracket.advance_to_knockout()
        return bracket

    def test_advance_to_knockout(self, bracket_after_groups):
        """Test advancing from groups to knockout."""
        bracket = bracket_after_groups

        assert bracket.current_stage == TournamentStage.ROUND_OF_16

        # Check R16 matches have teams assigned
        r16_matches = [m for m in bracket.knockout_matches
                       if m.stage == TournamentStage.ROUND_OF_16]

        for match in r16_matches:
            assert match.slot1.team_id is not None
            assert match.slot2.team_id is not None

    def test_knockout_match_advances_winner(self, bracket_after_groups):
        """Test that knockout winner advances to next round."""
        bracket = bracket_after_groups

        # Get first R16 match
        r16_match = next(m for m in bracket.knockout_matches
                         if m.stage == TournamentStage.ROUND_OF_16)

        winner_id = r16_match.slot1.team_id

        bracket.record_knockout_result(
            match_id=r16_match.match_id,
            winner_team_id=winner_id,
            home_score=20,
            away_score=15
        )

        # Match should be complete
        assert r16_match.is_complete
        assert r16_match.winner_team_id == winner_id

        # Winner should be in QF
        qf_matches = [m for m in bracket.knockout_matches
                      if m.stage == TournamentStage.QUARTER_FINAL]

        # Find the QF match that should have this winner
        found_winner = False
        for qf_match in qf_matches:
            if qf_match.slot1.team_id == winner_id or qf_match.slot2.team_id == winner_id:
                found_winner = True
                break

        assert found_winner

    def test_stage_advancement(self, bracket_after_groups):
        """Test automatic stage advancement when all matches complete."""
        bracket = bracket_after_groups

        # Complete all R16 matches
        r16_matches = [m for m in bracket.knockout_matches
                       if m.stage == TournamentStage.ROUND_OF_16]

        for match in r16_matches:
            bracket.record_knockout_result(
                match_id=match.match_id,
                winner_team_id=match.slot1.team_id,
                home_score=10,
                away_score=5
            )

        assert bracket.current_stage == TournamentStage.QUARTER_FINAL

    def test_tournament_completion(self, bracket_after_groups):
        """Test tournament completes after final."""
        bracket = bracket_after_groups

        # Complete all knockout matches through to final
        for stage in [TournamentStage.ROUND_OF_16,
                      TournamentStage.QUARTER_FINAL,
                      TournamentStage.SEMI_FINAL,
                      TournamentStage.FINAL]:
            stage_matches = [m for m in bracket.knockout_matches if m.stage == stage]
            for match in stage_matches:
                if not match.is_complete:
                    bracket.record_knockout_result(
                        match_id=match.match_id,
                        winner_team_id=match.slot1.team_id,
                        home_score=10,
                        away_score=5
                    )

        assert bracket.current_stage == TournamentStage.COMPLETED


class TestBracketDisplay:
    """Tests for bracket visualization data."""

    def test_get_bracket_display(self):
        """Test bracket display data structure."""
        teams = [{"id": i, "name": f"Team {i}"} for i in range(1, 17)]
        bracket = TournamentBracket()
        bracket.initialize_tournament(teams, num_groups=4, teams_per_group=4)

        display = bracket.get_bracket_display()

        assert "tournament_id" in display
        assert "current_stage" in display
        assert "groups" in display
        assert "knockout" in display

        # Check groups data
        assert "A" in display["groups"]
        assert "standings" in display["groups"]["A"]
        assert "matches" in display["groups"]["A"]

        # Check knockout data
        assert "round_of_16" in display["knockout"]
        assert "quarter_final" in display["knockout"]
        assert "semi_final" in display["knockout"]
        assert "final" in display["knockout"]

    def test_get_upcoming_matches(self):
        """Test getting upcoming matches."""
        teams = [{"id": i, "name": f"Team {i}"} for i in range(1, 17)]
        bracket = TournamentBracket()
        bracket.initialize_tournament(teams, num_groups=4, teams_per_group=4)

        upcoming = bracket.get_upcoming_matches()

        # All 24 group matches should be upcoming
        assert len(upcoming) == 24

        # Complete one match
        match = bracket.group_matches[0]
        bracket.record_group_result(
            match_id=match.match_id,
            winner_team_id=match.slot1.team_id,
            home_score=10,
            away_score=5
        )

        upcoming = bracket.get_upcoming_matches()
        assert len(upcoming) == 23

    def test_get_match_by_id(self):
        """Test finding match by ID."""
        teams = [{"id": i, "name": f"Team {i}"} for i in range(1, 17)]
        bracket = TournamentBracket()
        bracket.initialize_tournament(teams, num_groups=4, teams_per_group=4)

        # Get a known match
        match = bracket.group_matches[0]
        match_id = match.match_id

        found = bracket.get_match_by_id(match_id)
        assert found is not None
        assert found.match_id == match_id

        # Non-existent match
        assert bracket.get_match_by_id("INVALID") is None


class TestGroupStanding:
    """Tests for GroupStanding dataclass."""

    def test_ap_differential(self):
        """Test AP differential calculation."""
        standing = GroupStanding(
            team_id=1,
            team_name="Test",
            group="A",
            ap_scored=50,
            ap_conceded=30
        )

        assert standing.ap_differential == 20

    def test_points_calculation(self):
        """Test points calculation (3 per win)."""
        standing = GroupStanding(
            team_id=1,
            team_name="Test",
            group="A",
            wins=3,
            losses=1
        )

        assert standing.points == 9  # 3 * 3
