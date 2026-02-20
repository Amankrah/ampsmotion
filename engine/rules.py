"""
Rules Engine - Enforces AmpeSports rules and penalties.

Handles foul processing, penalty calculation, and rule validation.
"""

from typing import Optional
from dataclasses import dataclass

from models.foul import FoulType, PenaltyAction, FOUL_PENALTIES


@dataclass
class PenaltyResult:
    """Result of applying a penalty."""
    action: PenaltyAction
    ap_deduction: int
    is_disqualification: bool = False
    round_loss: bool = False
    bout_loss: bool = False
    message: str = ""


class RulesEngine:
    """
    Enforces AmpeSports rules and calculates penalties.

    The RulesEngine tracks foul occurrences per player per match
    and determines the appropriate penalty based on the rules.
    """

    # Maximum substitutions allowed per team per match
    MAX_SUBSTITUTIONS = 5

    # Team roster size
    TEAM_SIZE = 15

    # Valid round counts for 1v1 mode
    VALID_1V1_ROUNDS = {5, 10, 15}

    # Rest interval between rounds (milliseconds)
    REST_INTERVAL_MS = 120_000  # 2 minutes

    def __init__(self):
        # Track foul occurrences: {player_id: {foul_type: count}}
        self._foul_counts: dict[int, dict[FoulType, int]] = {}

    def reset(self) -> None:
        """Reset foul tracking for a new match."""
        self._foul_counts.clear()

    def process_foul(self, player_id: int, foul_type: FoulType) -> PenaltyResult:
        """
        Process a foul and determine the penalty.

        Args:
            player_id: The player who committed the foul
            foul_type: The type of foul committed

        Returns:
            PenaltyResult with the appropriate penalty action
        """
        # Increment foul count
        if player_id not in self._foul_counts:
            self._foul_counts[player_id] = {}

        player_fouls = self._foul_counts[player_id]
        occurrence = player_fouls.get(foul_type, 0) + 1
        player_fouls[foul_type] = occurrence

        # Get the appropriate penalty
        action, ap_deduction = self._get_penalty(foul_type, occurrence)

        # Create result
        result = PenaltyResult(
            action=action,
            ap_deduction=ap_deduction,
            is_disqualification=(action == PenaltyAction.DISQUALIFICATION),
            round_loss=(action == PenaltyAction.ROUND_LOSS),
            bout_loss=(action == PenaltyAction.BOUT_LOSS),
            message=self._get_penalty_message(foul_type, action, occurrence),
        )

        return result

    def _get_penalty(self, foul_type: FoulType, occurrence: int) -> tuple[PenaltyAction, int]:
        """Get the penalty for a foul based on occurrence count."""
        foul_config = FOUL_PENALTIES.get(foul_type, {})

        # Find the highest defined occurrence that applies
        applicable_occurrence = 1
        for occ in sorted(foul_config.keys()):
            if occ <= occurrence:
                applicable_occurrence = occ

        return foul_config.get(applicable_occurrence, (PenaltyAction.WARNING, 0))

    def _get_penalty_message(self, foul_type: FoulType, action: PenaltyAction,
                              occurrence: int) -> str:
        """Generate a human-readable penalty message."""
        foul_name = foul_type.value.replace("_", " ").title()

        messages = {
            PenaltyAction.WARNING: f"{foul_name} - Warning issued (occurrence #{occurrence})",
            PenaltyAction.AP_DEDUCTION: f"{foul_name} - AP deducted",
            PenaltyAction.BOUT_LOSS: f"{foul_name} - Bout awarded to opponent",
            PenaltyAction.ROUND_LOSS: f"{foul_name} - Round awarded to opponent",
            PenaltyAction.DISQUALIFICATION: f"{foul_name} - Player disqualified",
        }

        return messages.get(action, f"{foul_name} - Penalty applied")

    def get_foul_count(self, player_id: int, foul_type: FoulType) -> int:
        """Get the number of times a player has committed a specific foul."""
        return self._foul_counts.get(player_id, {}).get(foul_type, 0)

    def get_total_fouls(self, player_id: int) -> int:
        """Get the total number of fouls committed by a player."""
        return sum(self._foul_counts.get(player_id, {}).values())

    # ============ Validation Methods ============

    @staticmethod
    def validate_round_count(rounds: int, is_team_mode: bool = False) -> bool:
        """Validate that the round count is valid."""
        if is_team_mode:
            return rounds == 15  # Team mode always uses 15 rounds per game
        return rounds in RulesEngine.VALID_1V1_ROUNDS

    @staticmethod
    def validate_team_size(player_count: int) -> tuple[bool, str]:
        """Validate team size."""
        if player_count < 1:
            return False, "Team must have at least 1 player"
        if player_count > RulesEngine.TEAM_SIZE:
            return False, f"Team cannot exceed {RulesEngine.TEAM_SIZE} players"
        return True, ""

    def can_substitute(self, team_subs_used: int) -> bool:
        """Check if a team can make another substitution."""
        return team_subs_used < self.MAX_SUBSTITUTIONS

    @staticmethod
    def determine_round_winner(p1_ap: int, p2_ap: int) -> Optional[str]:
        """
        Determine the round winner based on AP scored.

        Returns:
            "player1", "player2", or None (tie)
        """
        if p1_ap > p2_ap:
            return "player1"
        elif p2_ap > p1_ap:
            return "player2"
        return None

    @staticmethod
    def determine_match_winner(p1_total_ap: int, p2_total_ap: int,
                                p1_rounds_won: int = 0, p2_rounds_won: int = 0) -> Optional[str]:
        """
        Determine the match winner.

        Primary tiebreaker: Total AP
        Secondary tiebreaker: Rounds won (if implemented)

        Returns:
            "player1", "player2", or None (tie)
        """
        if p1_total_ap > p2_total_ap:
            return "player1"
        elif p2_total_ap > p1_total_ap:
            return "player2"
        elif p1_rounds_won > p2_rounds_won:
            return "player1"
        elif p2_rounds_won > p1_rounds_won:
            return "player2"
        return None

    # ============ Team Mode Specific ============

    @staticmethod
    def calculate_elimination_bonus(remaining_players: int) -> int:
        """
        Calculate the AP bonus for eliminating a player in team mode.

        Args:
            remaining_players: Number of players remaining on the losing team
                              AFTER the elimination

        Returns:
            The AP bonus to award
        """
        if remaining_players > 3:
            return 3  # Standard bonus

        # Endgame bonuses when 3 or fewer players remain
        bonuses = {
            3: 5,   # First of last 3 eliminated
            2: 10,  # Second of last 3 eliminated
            1: 15,  # Last player eliminated (team eliminated)
            0: 15,  # Same as above
        }
        return bonuses.get(remaining_players, 3)

    @staticmethod
    def is_team_eliminated(roster_size: int) -> bool:
        """Check if a team has been eliminated (no players left)."""
        return roster_size <= 0
