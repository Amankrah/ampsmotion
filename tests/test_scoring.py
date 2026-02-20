"""
Unit tests for the ScoringEngine.

Tests cover 1v1 mode scoring, foul penalties, and team mode eliminations.
"""

import pytest
from unittest.mock import MagicMock

from engine.scoring import ScoringEngine, MatchState, ScoreState
from models.match import GameMode
from models.bout import BoutResult


class TestScoringEngine1v1:
    """Tests for 1v1 mode scoring."""

    def setup_method(self):
        """Set up a fresh ScoringEngine for each test."""
        self.engine = ScoringEngine(GameMode.ONE_VS_ONE, total_rounds=5)
        self.engine.setup_1v1_match(
            player1_id=1, player1_name="Player One",
            player2_id=2, player2_name="Player Two"
        )

    def test_initial_state_is_setup(self):
        """Engine should be in SETUP state after setup_1v1_match."""
        assert self.engine.state == MatchState.SETUP

    def test_start_match_transitions_to_match_active(self):
        """Starting a match should transition to MATCH_ACTIVE."""
        self.engine.start_match()
        assert self.engine.state == MatchState.MATCH_ACTIVE

    def test_start_round_increments_round_number(self):
        """Starting a round should increment the round counter."""
        self.engine.start_match()
        self.engine.start_round()
        assert self.engine._current_round == 1
        assert self.engine.state == MatchState.ROUND_ACTIVE

    def test_opa_win_awards_1ap_to_player1(self):
        """An Opa win should award 1 AP to the winner."""
        self.engine.start_match()
        self.engine.start_round()

        self.engine.record_bout(BoutResult.OPA, winner_id=1, loser_id=2)

        assert self.engine._p1_ap == 1
        assert self.engine._p1_opa_count == 1
        assert self.engine._p2_ap == 0

    def test_opa_win_awards_1ap_to_player2(self):
        """An Opa win should award 1 AP to the winner (player 2)."""
        self.engine.start_match()
        self.engine.start_round()

        self.engine.record_bout(BoutResult.OPA, winner_id=2, loser_id=1)

        assert self.engine._p2_ap == 1
        assert self.engine._p2_opa_count == 1
        assert self.engine._p1_ap == 0

    def test_oshi_win_awards_1ap(self):
        """An Oshi win should award 1 AP and track Oshi count."""
        self.engine.start_match()
        self.engine.start_round()

        self.engine.record_bout(BoutResult.OSHI, winner_id=1, loser_id=2)

        assert self.engine._p1_ap == 1
        assert self.engine._p1_oshi_count == 1
        assert self.engine._p1_opa_count == 0

    def test_multiple_bouts_accumulate_ap(self):
        """Multiple bouts should accumulate AP correctly."""
        self.engine.start_match()
        self.engine.start_round()

        # Player 1 wins 3 Opa bouts
        for _ in range(3):
            self.engine.record_bout(BoutResult.OPA, winner_id=1, loser_id=2)

        # Player 2 wins 2 Oshi bouts
        for _ in range(2):
            self.engine.record_bout(BoutResult.OSHI, winner_id=2, loser_id=1)

        assert self.engine._p1_ap == 3
        assert self.engine._p2_ap == 2
        assert self.engine._bout_count == 5

    def test_bout_count_increments(self):
        """Bout count should increment with each bout."""
        self.engine.start_match()
        self.engine.start_round()

        self.engine.record_bout(BoutResult.OPA, winner_id=1, loser_id=2)
        assert self.engine._bout_count == 1

        self.engine.record_bout(BoutResult.OSHI, winner_id=2, loser_id=1)
        assert self.engine._bout_count == 2

    def test_cannot_record_bout_before_round_starts(self):
        """Recording a bout before starting a round should raise an error."""
        self.engine.start_match()

        with pytest.raises(RuntimeError, match="Cannot record bout"):
            self.engine.record_bout(BoutResult.OPA, winner_id=1, loser_id=2)

    def test_foul_deduction(self):
        """Foul penalty should deduct AP from the offending player."""
        self.engine.start_match()
        self.engine.start_round()

        # Give player 1 some AP first
        for _ in range(5):
            self.engine.record_bout(BoutResult.OPA, winner_id=1, loser_id=2)

        assert self.engine._p1_ap == 5

        # Apply a 3 AP penalty
        self.engine.apply_foul_penalty(1, "excessive_contact", 3)

        assert self.engine._p1_ap == 2

    def test_foul_cannot_go_negative(self):
        """AP cannot go below zero after a foul penalty."""
        self.engine.start_match()
        self.engine.start_round()

        # Player 1 has only 1 AP
        self.engine.record_bout(BoutResult.OPA, winner_id=1, loser_id=2)
        assert self.engine._p1_ap == 1

        # Apply a 3 AP penalty - should not go negative
        self.engine.apply_foul_penalty(1, "excessive_contact", 3)

        assert self.engine._p1_ap == 0

    def test_undo_last_bout(self):
        """Undoing a bout should reverse the scoring."""
        self.engine.start_match()
        self.engine.start_round()

        self.engine.record_bout(BoutResult.OPA, winner_id=1, loser_id=2)
        assert self.engine._p1_ap == 1

        undone = self.engine.undo_last_bout()

        assert undone is not None
        assert undone.winner_id == 1
        assert self.engine._p1_ap == 0
        assert self.engine._p1_opa_count == 0
        assert self.engine._bout_count == 0

    def test_undo_multiple_bouts(self):
        """Multiple undo operations should work correctly."""
        self.engine.start_match()
        self.engine.start_round()

        self.engine.record_bout(BoutResult.OPA, winner_id=1, loser_id=2)
        self.engine.record_bout(BoutResult.OSHI, winner_id=2, loser_id=1)
        self.engine.record_bout(BoutResult.OPA, winner_id=1, loser_id=2)

        assert self.engine._p1_ap == 2
        assert self.engine._p2_ap == 1

        self.engine.undo_last_bout()
        assert self.engine._p1_ap == 1

        self.engine.undo_last_bout()
        assert self.engine._p2_ap == 0

        self.engine.undo_last_bout()
        assert self.engine._p1_ap == 0

    def test_undo_returns_none_when_no_bouts(self):
        """Undo should return None when there are no bouts to undo."""
        self.engine.start_match()
        self.engine.start_round()

        result = self.engine.undo_last_bout()
        assert result is None

    def test_end_round_determines_winner(self):
        """Ending a round should determine the winner correctly."""
        self.engine.start_match()
        self.engine.start_round()

        # Player 1 wins more bouts
        self.engine.record_bout(BoutResult.OPA, winner_id=1, loser_id=2)
        self.engine.record_bout(BoutResult.OPA, winner_id=1, loser_id=2)
        self.engine.record_bout(BoutResult.OSHI, winner_id=2, loser_id=1)

        winner = self.engine.end_round()

        assert winner == "player1"
        assert self.engine.state == MatchState.ROUND_COMPLETE

    def test_end_round_tie(self):
        """A tied round should return 'tie'."""
        self.engine.start_match()
        self.engine.start_round()

        self.engine.record_bout(BoutResult.OPA, winner_id=1, loser_id=2)
        self.engine.record_bout(BoutResult.OPA, winner_id=2, loser_id=1)

        winner = self.engine.end_round()

        assert winner == "tie"

    def test_match_completes_after_all_rounds(self):
        """Match should complete after all rounds are played."""
        self.engine.start_match()

        for round_num in range(5):
            self.engine.start_round()
            self.engine.record_bout(BoutResult.OPA, winner_id=1, loser_id=2)
            self.engine.end_round()

        assert self.engine.state == MatchState.COMPLETED
        assert self.engine.is_match_complete

    def test_pause_and_resume(self):
        """Pausing and resuming should work correctly."""
        self.engine.start_match()
        self.engine.start_round()

        self.engine.pause()
        assert self.engine.state == MatchState.PAUSED

        self.engine.resume()
        assert self.engine.state == MatchState.ROUND_ACTIVE

    def test_score_state_snapshot(self):
        """get_score_state should return accurate snapshot."""
        self.engine.start_match()
        self.engine.start_round()

        self.engine.record_bout(BoutResult.OPA, winner_id=1, loser_id=2)
        self.engine.record_bout(BoutResult.OSHI, winner_id=1, loser_id=2)

        state = self.engine.get_score_state()

        assert state.player1_ap == 2
        assert state.player1_opa_wins == 1
        assert state.player1_oshi_wins == 1
        assert state.current_round == 1
        assert state.bout_count == 2
        assert state.is_round_active


class TestScoringEngineTeamMode:
    """Tests for Team vs Team mode scoring."""

    def setup_method(self):
        """Set up a fresh ScoringEngine for team mode tests."""
        self.engine = ScoringEngine(GameMode.TEAM_VS_TEAM, total_rounds=15)
        # Create rosters with player IDs 1-15 (home) and 16-30 (away)
        self.engine._home_roster = list(range(1, 16))
        self.engine._away_roster = list(range(16, 31))
        self.engine._p1_id = "home"
        self.engine._p2_id = "away"
        self.engine.state = MatchState.ROUND_ACTIVE

    def test_elimination_awards_3ap_when_more_than_3_remain(self):
        """Standard elimination should award +3 AP."""
        initial_home_ap = self.engine._p1_ap

        # Eliminate an away player (14 remaining after)
        self.engine.eliminate_player(16, "away")

        # Home team should get +3 AP
        assert self.engine._p1_ap == initial_home_ap + 3
        assert 16 in self.engine._away_eliminated
        assert len(self.engine._away_roster) == 14

    def test_endgame_elimination_bonuses(self):
        """Endgame eliminations should award increased bonuses."""
        # Reduce away roster to exactly 3 players
        self.engine._away_roster = [16, 17, 18]
        self.engine._p1_ap = 0

        # First of last 3 eliminated → +5 AP
        bonus1 = self.engine.eliminate_player(16, "away")
        assert bonus1 == 5
        assert self.engine._p1_ap == 5

        # Second of last 3 eliminated → +10 AP
        bonus2 = self.engine.eliminate_player(17, "away")
        assert bonus2 == 10
        assert self.engine._p1_ap == 15

        # Last player eliminated → +15 AP
        bonus3 = self.engine.eliminate_player(18, "away")
        assert bonus3 == 15
        assert self.engine._p1_ap == 30

    def test_elimination_removes_player_from_roster(self):
        """Eliminated players should be removed from active roster."""
        assert 16 in self.engine._away_roster

        self.engine.eliminate_player(16, "away")

        assert 16 not in self.engine._away_roster
        assert 16 in self.engine._away_eliminated


class TestScoringEngineSignals:
    """Tests for signal emissions."""

    def setup_method(self):
        """Set up engine with signal mocks."""
        self.engine = ScoringEngine(GameMode.ONE_VS_ONE, total_rounds=5)
        self.engine.setup_1v1_match(1, "P1", 2, "P2")

        # Create mock slots
        self.score_updated_mock = MagicMock()
        self.bout_recorded_mock = MagicMock()
        self.round_started_mock = MagicMock()
        self.round_ended_mock = MagicMock()

        # Connect signals
        self.engine.score_updated.connect(self.score_updated_mock)
        self.engine.bout_recorded.connect(self.bout_recorded_mock)
        self.engine.round_started.connect(self.round_started_mock)
        self.engine.round_ended.connect(self.round_ended_mock)

    def test_score_updated_emitted_on_bout(self):
        """score_updated signal should be emitted when a bout is recorded."""
        self.engine.start_match()
        self.engine.start_round()

        self.engine.record_bout(BoutResult.OPA, winner_id=1, loser_id=2)

        assert self.score_updated_mock.called
        # Get the emitted ScoreState
        call_args = self.score_updated_mock.call_args[0]
        assert isinstance(call_args[0], ScoreState)

    def test_bout_recorded_emitted(self):
        """bout_recorded signal should be emitted with bout details."""
        self.engine.start_match()
        self.engine.start_round()

        self.engine.record_bout(BoutResult.OPA, winner_id=1, loser_id=2)

        self.bout_recorded_mock.assert_called_once()
        bout_data = self.bout_recorded_mock.call_args[0][0]
        assert bout_data["result"] == "opa"
        assert bout_data["winner_id"] == 1

    def test_round_started_emitted(self):
        """round_started signal should be emitted with round number."""
        self.engine.start_match()
        self.engine.start_round()

        self.round_started_mock.assert_called_once_with(1)

    def test_round_ended_emitted(self):
        """round_ended signal should be emitted with winner."""
        self.engine.start_match()
        self.engine.start_round()
        self.engine.record_bout(BoutResult.OPA, winner_id=1, loser_id=2)
        self.engine.end_round()

        self.round_ended_mock.assert_called_once_with(1, "player1")
