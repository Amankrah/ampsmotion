"""
Unit tests for the RulesEngine.
"""

import pytest

from engine.rules import RulesEngine, PenaltyResult
from models.foul import FoulType, PenaltyAction


class TestRulesEngineFouls:
    """Tests for foul processing."""

    def setup_method(self):
        """Set up a fresh RulesEngine for each test."""
        self.rules = RulesEngine()

    def test_first_delay_of_game_is_warning(self):
        """First delay of game should result in a warning."""
        result = self.rules.process_foul(player_id=1, foul_type=FoulType.DELAY_OF_GAME)

        assert result.action == PenaltyAction.WARNING
        assert result.ap_deduction == 0
        assert not result.is_disqualification

    def test_second_delay_of_game_deducts_ap(self):
        """Second delay of game should deduct 1 AP."""
        self.rules.process_foul(player_id=1, foul_type=FoulType.DELAY_OF_GAME)
        result = self.rules.process_foul(player_id=1, foul_type=FoulType.DELAY_OF_GAME)

        assert result.action == PenaltyAction.AP_DEDUCTION
        assert result.ap_deduction == 1

    def test_first_excessive_contact_is_warning(self):
        """First excessive contact should result in a warning."""
        result = self.rules.process_foul(player_id=1, foul_type=FoulType.EXCESSIVE_CONTACT)

        assert result.action == PenaltyAction.WARNING
        assert result.ap_deduction == 0

    def test_second_excessive_contact_deducts_3ap(self):
        """Second excessive contact should deduct 3 AP."""
        self.rules.process_foul(player_id=1, foul_type=FoulType.EXCESSIVE_CONTACT)
        result = self.rules.process_foul(player_id=1, foul_type=FoulType.EXCESSIVE_CONTACT)

        assert result.action == PenaltyAction.AP_DEDUCTION
        assert result.ap_deduction == 3

    def test_illegal_foot_thrust_is_bout_loss(self):
        """Illegal foot thrust should result in bout loss."""
        result = self.rules.process_foul(player_id=1, foul_type=FoulType.ILLEGAL_FOOT_THRUST)

        assert result.action == PenaltyAction.BOUT_LOSS
        assert result.bout_loss

    def test_encroachment_is_bout_loss(self):
        """Encroachment should result in bout loss."""
        result = self.rules.process_foul(player_id=1, foul_type=FoulType.ENCROACHMENT)

        assert result.action == PenaltyAction.BOUT_LOSS
        assert result.bout_loss

    def test_illegal_substitution_is_round_loss(self):
        """Illegal substitution should result in round loss."""
        result = self.rules.process_foul(player_id=1, foul_type=FoulType.ILLEGAL_SUBSTITUTION)

        assert result.action == PenaltyAction.ROUND_LOSS
        assert result.round_loss

    def test_improper_positioning_is_round_loss(self):
        """Improper positioning should result in round loss."""
        result = self.rules.process_foul(player_id=1, foul_type=FoulType.IMPROPER_POSITIONING)

        assert result.action == PenaltyAction.ROUND_LOSS
        assert result.round_loss

    def test_reentry_escalation(self):
        """Re-entry after elimination should escalate penalties."""
        # First offense: round loss
        result1 = self.rules.process_foul(player_id=1, foul_type=FoulType.REENTRY_AFTER_ELIMINATION)
        assert result1.action == PenaltyAction.ROUND_LOSS

        # Second offense: -3 AP
        result2 = self.rules.process_foul(player_id=1, foul_type=FoulType.REENTRY_AFTER_ELIMINATION)
        assert result2.action == PenaltyAction.AP_DEDUCTION
        assert result2.ap_deduction == 3

        # Third offense: disqualification
        result3 = self.rules.process_foul(player_id=1, foul_type=FoulType.REENTRY_AFTER_ELIMINATION)
        assert result3.action == PenaltyAction.DISQUALIFICATION
        assert result3.is_disqualification

    def test_unsportsmanlike_conduct_escalation(self):
        """Unsportsmanlike conduct should escalate."""
        # First: warning
        result1 = self.rules.process_foul(player_id=1, foul_type=FoulType.UNSPORTSMANLIKE_CONDUCT)
        assert result1.action == PenaltyAction.WARNING

        # Second: -3 AP
        result2 = self.rules.process_foul(player_id=1, foul_type=FoulType.UNSPORTSMANLIKE_CONDUCT)
        assert result2.action == PenaltyAction.AP_DEDUCTION
        assert result2.ap_deduction == 3

        # Third: disqualification
        result3 = self.rules.process_foul(player_id=1, foul_type=FoulType.UNSPORTSMANLIKE_CONDUCT)
        assert result3.action == PenaltyAction.DISQUALIFICATION

    def test_intentional_foul_immediate_disqualification(self):
        """Intentional foul should result in immediate disqualification."""
        result = self.rules.process_foul(player_id=1, foul_type=FoulType.INTENTIONAL_FOUL)

        assert result.action == PenaltyAction.DISQUALIFICATION
        assert result.is_disqualification

    def test_equipment_tampering_immediate_disqualification(self):
        """Equipment tampering should result in immediate disqualification."""
        result = self.rules.process_foul(player_id=1, foul_type=FoulType.EQUIPMENT_TAMPERING)

        assert result.action == PenaltyAction.DISQUALIFICATION
        assert result.is_disqualification

    def test_different_players_tracked_separately(self):
        """Fouls should be tracked separately for each player."""
        self.rules.process_foul(player_id=1, foul_type=FoulType.DELAY_OF_GAME)
        result = self.rules.process_foul(player_id=2, foul_type=FoulType.DELAY_OF_GAME)

        # Player 2's first offense should be a warning, not -1 AP
        assert result.action == PenaltyAction.WARNING

    def test_get_foul_count(self):
        """get_foul_count should return correct count."""
        self.rules.process_foul(player_id=1, foul_type=FoulType.DELAY_OF_GAME)
        self.rules.process_foul(player_id=1, foul_type=FoulType.DELAY_OF_GAME)
        self.rules.process_foul(player_id=1, foul_type=FoulType.EXCESSIVE_CONTACT)

        assert self.rules.get_foul_count(1, FoulType.DELAY_OF_GAME) == 2
        assert self.rules.get_foul_count(1, FoulType.EXCESSIVE_CONTACT) == 1
        assert self.rules.get_foul_count(1, FoulType.ENCROACHMENT) == 0

    def test_get_total_fouls(self):
        """get_total_fouls should return total count across all foul types."""
        self.rules.process_foul(player_id=1, foul_type=FoulType.DELAY_OF_GAME)
        self.rules.process_foul(player_id=1, foul_type=FoulType.DELAY_OF_GAME)
        self.rules.process_foul(player_id=1, foul_type=FoulType.EXCESSIVE_CONTACT)

        assert self.rules.get_total_fouls(1) == 3

    def test_reset_clears_foul_counts(self):
        """reset should clear all foul counts."""
        self.rules.process_foul(player_id=1, foul_type=FoulType.DELAY_OF_GAME)
        self.rules.reset()

        assert self.rules.get_foul_count(1, FoulType.DELAY_OF_GAME) == 0


class TestRulesEngineValidation:
    """Tests for validation methods."""

    def test_validate_round_count_1v1_valid(self):
        """Valid 1v1 round counts should pass."""
        assert RulesEngine.validate_round_count(5, is_team_mode=False)
        assert RulesEngine.validate_round_count(10, is_team_mode=False)
        assert RulesEngine.validate_round_count(15, is_team_mode=False)

    def test_validate_round_count_1v1_invalid(self):
        """Invalid 1v1 round counts should fail."""
        assert not RulesEngine.validate_round_count(3, is_team_mode=False)
        assert not RulesEngine.validate_round_count(7, is_team_mode=False)
        assert not RulesEngine.validate_round_count(20, is_team_mode=False)

    def test_validate_round_count_team_mode(self):
        """Team mode should require exactly 15 rounds."""
        assert RulesEngine.validate_round_count(15, is_team_mode=True)
        assert not RulesEngine.validate_round_count(5, is_team_mode=True)
        assert not RulesEngine.validate_round_count(10, is_team_mode=True)

    def test_validate_team_size_valid(self):
        """Valid team sizes should pass."""
        valid, msg = RulesEngine.validate_team_size(1)
        assert valid

        valid, msg = RulesEngine.validate_team_size(15)
        assert valid

    def test_validate_team_size_too_small(self):
        """Team size of 0 should fail."""
        valid, msg = RulesEngine.validate_team_size(0)
        assert not valid
        assert "at least 1" in msg

    def test_validate_team_size_too_large(self):
        """Team size > 15 should fail."""
        valid, msg = RulesEngine.validate_team_size(16)
        assert not valid
        assert "cannot exceed" in msg

    def test_can_substitute(self):
        """can_substitute should check against max substitutions."""
        rules = RulesEngine()

        assert rules.can_substitute(0)
        assert rules.can_substitute(4)
        assert not rules.can_substitute(5)
        assert not rules.can_substitute(6)


class TestRulesEngineWinnerDetermination:
    """Tests for winner determination methods."""

    def test_determine_round_winner_player1(self):
        """Player 1 should win with higher AP."""
        winner = RulesEngine.determine_round_winner(p1_ap=5, p2_ap=3)
        assert winner == "player1"

    def test_determine_round_winner_player2(self):
        """Player 2 should win with higher AP."""
        winner = RulesEngine.determine_round_winner(p1_ap=3, p2_ap=5)
        assert winner == "player2"

    def test_determine_round_winner_tie(self):
        """Equal AP should result in tie."""
        winner = RulesEngine.determine_round_winner(p1_ap=5, p2_ap=5)
        assert winner is None

    def test_determine_match_winner_by_ap(self):
        """Match winner should be determined by total AP."""
        winner = RulesEngine.determine_match_winner(
            p1_total_ap=50, p2_total_ap=40
        )
        assert winner == "player1"

    def test_determine_match_winner_tie_uses_rounds(self):
        """Tied AP should use rounds won as tiebreaker."""
        winner = RulesEngine.determine_match_winner(
            p1_total_ap=50, p2_total_ap=50,
            p1_rounds_won=3, p2_rounds_won=2
        )
        assert winner == "player1"

    def test_determine_match_winner_complete_tie(self):
        """Equal AP and rounds should result in tie."""
        winner = RulesEngine.determine_match_winner(
            p1_total_ap=50, p2_total_ap=50,
            p1_rounds_won=2, p2_rounds_won=2
        )
        assert winner is None


class TestRulesEngineTeamMode:
    """Tests for team mode specific methods."""

    def test_calculate_elimination_bonus_standard(self):
        """Standard elimination should give +3 AP."""
        # 14 remaining (started with 15, one eliminated)
        bonus = RulesEngine.calculate_elimination_bonus(remaining_players=14)
        assert bonus == 3

        # 4 remaining
        bonus = RulesEngine.calculate_elimination_bonus(remaining_players=4)
        assert bonus == 3

    def test_calculate_elimination_bonus_endgame(self):
        """Endgame eliminations should give increased bonuses."""
        # First of last 3 (3 remaining after)
        bonus = RulesEngine.calculate_elimination_bonus(remaining_players=3)
        assert bonus == 5

        # Second of last 3 (2 remaining after)
        bonus = RulesEngine.calculate_elimination_bonus(remaining_players=2)
        assert bonus == 10

        # Last player (1 remaining after)
        bonus = RulesEngine.calculate_elimination_bonus(remaining_players=1)
        assert bonus == 15

        # Team fully eliminated (0 remaining)
        bonus = RulesEngine.calculate_elimination_bonus(remaining_players=0)
        assert bonus == 15

    def test_is_team_eliminated(self):
        """is_team_eliminated should return True when roster is empty."""
        assert RulesEngine.is_team_eliminated(0)
        assert not RulesEngine.is_team_eliminated(1)
        assert not RulesEngine.is_team_eliminated(15)
