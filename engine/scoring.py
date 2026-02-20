"""
Scoring Engine - Core game logic for AmpeSports.

The ScoringEngine runs independently of the GUI and encapsulates all
AmpeSports rules for 1v1 and Team modes.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

from PySide6.QtCore import QObject, Signal

from models.match import GameMode
from models.bout import BoutResult
from engine.player_queue import PlayerQueue


class MatchState(Enum):
    """State machine states for match lifecycle."""
    IDLE = "idle"
    SETUP = "setup"
    MATCH_ACTIVE = "match_active"
    ROUND_ACTIVE = "round_active"
    BOUT_IN_PROGRESS = "bout_in_progress"
    ROUND_COMPLETE = "round_complete"
    PAUSED = "paused"
    COMPLETED = "completed"
    PROTESTED = "protested"


@dataclass
class ScoreState:
    """
    Immutable snapshot of the current score state.
    Emitted after every scoring event for GUI updates.
    """
    player1_ap: int = 0
    player2_ap: int = 0
    player1_opa_wins: int = 0
    player1_oshi_wins: int = 0
    player2_opa_wins: int = 0
    player2_oshi_wins: int = 0
    current_round: int = 0
    total_rounds: int = 0
    bout_count: int = 0
    round_time_remaining_ms: int = 60000
    home_eliminations: int = 0
    away_eliminations: int = 0
    is_round_active: bool = False
    is_match_active: bool = False
    state: MatchState = MatchState.IDLE

    # For Team mode
    current_game: int = 0
    total_games: int = 3

    # Player info
    player1_name: str = ""
    player2_name: str = ""


@dataclass
class BoutRecord:
    """Record of a single bout for undo functionality."""
    round_number: int
    bout_number: int
    result: BoutResult
    winner_id: int
    loser_id: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    time_remaining_ms: int = 0


class ScoringEngine(QObject):
    """
    Core scoring logic for all AmpeSports game modes.
    Emits Qt Signals so GUI layers can react without polling.

    This engine maintains the scoring state and enforces game rules.
    It does NOT handle persistence - that's the MatchManager's job.
    """

    # Signals
    score_updated = Signal(object)          # ScoreState
    round_started = Signal(int)             # round number
    round_ended = Signal(int, str)          # round number, winner side
    bout_recorded = Signal(dict)            # bout details
    bout_undone = Signal(dict)              # bout that was undone
    player_eliminated = Signal(int, int)    # player_id, team_id
    foul_applied = Signal(dict)             # foul details
    match_completed = Signal(dict)          # final results
    state_changed = Signal(str)             # new state name

    # Team mode bonus constants (from AmpeSports rules)
    TEAM_ROUND_WIN_BONUS = 3
    ENDGAME_BONUSES = {1: 5, 2: 10, 3: 15}  # elimination order → bonus AP

    # 1v1 round duration
    ROUND_DURATION_MS = 60_000  # 60 seconds

    def __init__(self, game_mode: GameMode, total_rounds: int = 5):
        """
        Initialize the scoring engine.

        Args:
            game_mode: ONE_VS_ONE, TEAM_VS_TEAM, or TOURNAMENT
            total_rounds: Number of rounds (5, 10, or 15 for 1v1)
        """
        super().__init__()
        self.game_mode = game_mode
        self.total_rounds = total_rounds
        self._state = MatchState.IDLE
        self._reset_state()

    def _reset_state(self) -> None:
        """Reset all scoring state to initial values."""
        # Player identifiers
        self._p1_id: Optional[int] = None
        self._p2_id: Optional[int] = None
        self._p1_name: str = ""
        self._p2_name: str = ""

        # Toss information (set during match setup)
        self._toss_winner: str = "player1"  # "player1", "player2", "home", or "away"
        self._toss_choice: str = "opa"  # "opa" or "oshi"

        # AP scores
        self._p1_ap: int = 0
        self._p2_ap: int = 0

        # Opa/Oshi win counts
        self._p1_opa_count: int = 0
        self._p1_oshi_count: int = 0
        self._p2_opa_count: int = 0
        self._p2_oshi_count: int = 0

        # Round tracking
        self._current_round: int = 0
        self._bout_count: int = 0
        self._round_time_remaining_ms: int = self.ROUND_DURATION_MS

        # Per-round scoring (resets each round)
        self._round_p1_ap: int = 0
        self._round_p2_ap: int = 0

        # Round history for undo
        self._bout_history: list[BoutRecord] = []

        # Team mode state
        self._current_game: int = 0
        self._home_roster: list[int] = []
        self._away_roster: list[int] = []
        self._home_eliminated: list[int] = []
        self._away_eliminated: list[int] = []
        self._home_subs_used: int = 0
        self._away_subs_used: int = 0

        # Round winners
        self._round_winners: list[str] = []  # "player1", "player2", or "tie"

    @property
    def state(self) -> MatchState:
        """Current state of the match."""
        return self._state

    @state.setter
    def state(self, new_state: MatchState) -> None:
        """Set the match state and emit signal."""
        self._state = new_state
        self.state_changed.emit(new_state.value)

    def setup_1v1_match(self, player1_id: int, player1_name: str,
                         player2_id: int, player2_name: str) -> None:
        """
        Set up a 1v1 match with two players.

        Args:
            player1_id: Database ID of player 1
            player1_name: Display name of player 1
            player2_id: Database ID of player 2
            player2_name: Display name of player 2
        """
        self._reset_state()
        self._p1_id = player1_id
        self._p2_id = player2_id
        self._p1_name = player1_name
        self._p2_name = player2_name
        self.state = MatchState.SETUP
        self._emit_score_update()

    def start_match(self) -> None:
        """Start the match (transitions from SETUP to MATCH_ACTIVE)."""
        if self.state != MatchState.SETUP:
            raise RuntimeError(f"Cannot start match from state: {self.state}")

        self.state = MatchState.MATCH_ACTIVE
        self._emit_score_update()

    def start_round(self) -> None:
        """
        Start a new round.

        For 1v1 mode, this starts a 60-second countdown.
        """
        if self.state not in (MatchState.MATCH_ACTIVE, MatchState.ROUND_COMPLETE):
            raise RuntimeError(f"Cannot start round from state: {self.state}")

        self._current_round += 1
        self._bout_count = 0
        self._round_p1_ap = 0
        self._round_p2_ap = 0
        self._round_time_remaining_ms = self.ROUND_DURATION_MS

        self.state = MatchState.ROUND_ACTIVE
        self.round_started.emit(self._current_round)
        self._emit_score_update()

    def record_bout(self, result: BoutResult, winner_id: int, loser_id: int,
                    time_remaining_ms: int = 0) -> None:
        """
        Record a bout result.

        Called by the Ampfre Console when the Caller announces
        Opa or Oshi and the Master Ampfre identifies the winner.

        Args:
            result: OPA or OSHI
            winner_id: Player ID of the bout winner
            loser_id: Player ID of the bout loser
            time_remaining_ms: Time remaining in the round when bout was recorded
        """
        if self.state != MatchState.ROUND_ACTIVE:
            raise RuntimeError(f"Cannot record bout in state: {self.state}")

        self._bout_count += 1
        self._round_time_remaining_ms = time_remaining_ms

        # Create bout record for undo
        bout_record = BoutRecord(
            round_number=self._current_round,
            bout_number=self._bout_count,
            result=result,
            winner_id=winner_id,
            loser_id=loser_id,
            time_remaining_ms=time_remaining_ms,
        )
        self._bout_history.append(bout_record)

        # Award AP and track Opa/Oshi counts
        if result == BoutResult.OPA:
            if winner_id == self._p1_id:
                self._p1_opa_count += 1
                self._p1_ap += 1
                self._round_p1_ap += 1
            else:
                self._p2_opa_count += 1
                self._p2_ap += 1
                self._round_p2_ap += 1
        else:  # OSHI
            if winner_id == self._p1_id:
                self._p1_oshi_count += 1
                self._p1_ap += 1
                self._round_p1_ap += 1
            else:
                self._p2_oshi_count += 1
                self._p2_ap += 1
                self._round_p2_ap += 1

        # Emit bout recorded signal
        self.bout_recorded.emit({
            "round": self._current_round,
            "bout": self._bout_count,
            "result": result.value,
            "winner_id": winner_id,
            "loser_id": loser_id,
            "time_remaining_ms": time_remaining_ms,
        })

        self._emit_score_update()

    def undo_last_bout(self) -> Optional[BoutRecord]:
        """
        Undo the last recorded bout.

        Returns:
            The undone BoutRecord, or None if no bouts to undo
        """
        if not self._bout_history:
            return None

        if self.state != MatchState.ROUND_ACTIVE:
            return None

        bout = self._bout_history.pop()

        # Reverse the scoring
        if bout.result == BoutResult.OPA:
            if bout.winner_id == self._p1_id:
                self._p1_opa_count -= 1
                self._p1_ap -= 1
                self._round_p1_ap -= 1
            else:
                self._p2_opa_count -= 1
                self._p2_ap -= 1
                self._round_p2_ap -= 1
        else:  # OSHI
            if bout.winner_id == self._p1_id:
                self._p1_oshi_count -= 1
                self._p1_ap -= 1
                self._round_p1_ap -= 1
            else:
                self._p2_oshi_count -= 1
                self._p2_ap -= 1
                self._round_p2_ap -= 1

        self._bout_count -= 1

        self.bout_undone.emit({
            "round": bout.round_number,
            "bout": bout.bout_number,
            "result": bout.result.value,
            "winner_id": bout.winner_id,
            "loser_id": bout.loser_id,
        })

        self._emit_score_update()
        return bout

    def end_round(self) -> str:
        """
        End the current round and determine the winner.

        Returns:
            The winner side: "player1", "player2", or "tie"
        """
        if self.state != MatchState.ROUND_ACTIVE:
            raise RuntimeError(f"Cannot end round in state: {self.state}")

        # Determine round winner based on AP scored this round
        if self._round_p1_ap > self._round_p2_ap:
            winner = "player1"
        elif self._round_p2_ap > self._round_p1_ap:
            winner = "player2"
        else:
            winner = "tie"

        self._round_winners.append(winner)
        self.state = MatchState.ROUND_COMPLETE
        self.round_ended.emit(self._current_round, winner)

        # Check if match is complete
        if self._current_round >= self.total_rounds:
            self._complete_match()

        self._emit_score_update()
        return winner

    def apply_foul_penalty(self, player_id: int, foul_type: str,
                           ap_deduction: int = 0) -> None:
        """
        Apply a foul penalty to a player.

        Args:
            player_id: The player receiving the penalty
            foul_type: Type of foul committed
            ap_deduction: AP to deduct (0 for warnings)
        """
        if ap_deduction > 0:
            if player_id == self._p1_id:
                self._p1_ap = max(0, self._p1_ap - ap_deduction)
            elif player_id == self._p2_id:
                self._p2_ap = max(0, self._p2_ap - ap_deduction)

        self.foul_applied.emit({
            "player_id": player_id,
            "foul_type": foul_type,
            "ap_deducted": ap_deduction,
        })

        self._emit_score_update()

    def pause(self) -> None:
        """Pause the match/round."""
        if self.state == MatchState.ROUND_ACTIVE:
            self._previous_state = self.state
            self.state = MatchState.PAUSED
            self._emit_score_update()

    def resume(self) -> None:
        """Resume a paused match/round."""
        if self.state == MatchState.PAUSED:
            self.state = getattr(self, '_previous_state', MatchState.ROUND_ACTIVE)
            self._emit_score_update()

    def update_timer(self, remaining_ms: int) -> None:
        """Update the round time remaining (called by RoundTimer)."""
        self._round_time_remaining_ms = remaining_ms
        # Don't emit full update for every tick - handled separately

    def _complete_match(self) -> None:
        """Complete the match and determine the winner."""
        self.state = MatchState.COMPLETED

        # Determine match winner
        if self._p1_ap > self._p2_ap:
            winner = "player1"
            winner_id = self._p1_id
        elif self._p2_ap > self._p1_ap:
            winner = "player2"
            winner_id = self._p2_id
        else:
            winner = "tie"
            winner_id = None

        self.match_completed.emit({
            "winner": winner,
            "winner_id": winner_id,
            "player1_ap": self._p1_ap,
            "player2_ap": self._p2_ap,
            "rounds_played": self._current_round,
            "round_winners": self._round_winners,
        })

    def _emit_score_update(self) -> None:
        """Emit the current score state."""
        update = ScoreState(
            player1_ap=self._p1_ap,
            player2_ap=self._p2_ap,
            player1_opa_wins=self._p1_opa_count,
            player1_oshi_wins=self._p1_oshi_count,
            player2_opa_wins=self._p2_opa_count,
            player2_oshi_wins=self._p2_oshi_count,
            current_round=self._current_round,
            total_rounds=self.total_rounds,
            bout_count=self._bout_count,
            round_time_remaining_ms=self._round_time_remaining_ms,
            home_eliminations=len(self._home_eliminated),
            away_eliminations=len(self._away_eliminated),
            is_round_active=(self.state == MatchState.ROUND_ACTIVE),
            is_match_active=(self.state in (MatchState.MATCH_ACTIVE, MatchState.ROUND_ACTIVE)),
            state=self.state,
            current_game=self._current_game,
            total_games=3 if self.game_mode != GameMode.ONE_VS_ONE else 1,
            player1_name=self._p1_name,
            player2_name=self._p2_name,
        )
        self.score_updated.emit(update)

    # ============ Team Mode Methods (Phase 2) ============

    # Additional signals for team mode
    queue_advanced = Signal(str)            # team name ("home" or "away")
    substitution_made = Signal(dict)        # substitution details
    game_ended = Signal(int, str)           # game number, winning team

    # Team mode constants
    TOTAL_GAMES = 3
    ROUNDS_PER_GAME = 15

    def setup_team_match(
        self,
        home_team_id: int,
        home_team_name: str,
        home_roster: list[tuple[int, str]],
        away_team_id: int,
        away_team_name: str,
        away_roster: list[tuple[int, str]],
    ) -> None:
        """
        Set up a Team vs Team match with full roster information.

        Args:
            home_team_id: Database ID of home team
            home_team_name: Display name of home team
            home_roster: List of (player_id, player_name) for home team
            away_team_id: Database ID of away team
            away_team_name: Display name of away team
            away_roster: List of (player_id, player_name) for away team
        """
        self._reset_state()

        # Team identifiers
        self._home_team_id = home_team_id
        self._away_team_id = away_team_id
        self._p1_name = home_team_name
        self._p2_name = away_team_name

        # Initialize player queues
        self._home_queue = PlayerQueue(home_team_id, home_team_name)
        self._home_queue.setup_roster(home_roster)
        self._away_queue = PlayerQueue(away_team_id, away_team_name)
        self._away_queue.setup_roster(away_roster)

        # Store roster IDs for compatibility
        self._home_roster = [p[0] for p in home_roster]
        self._away_roster = [p[0] for p in away_roster]

        # Team mode uses games (3 games × 15 rounds)
        self._current_game = 1
        self.total_rounds = self.ROUNDS_PER_GAME

        self.state = MatchState.SETUP
        self._emit_score_update()

    def get_active_players(self) -> tuple[Optional[dict], Optional[dict]]:
        """
        Get the currently active players (in the Red Zone) for each team.

        Returns:
            Tuple of (home_player_info, away_player_info) dicts or None
        """
        if not hasattr(self, '_home_queue') or not hasattr(self, '_away_queue'):
            return None, None

        home_active = self._home_queue.active_player
        away_active = self._away_queue.active_player

        home_info = {
            "player_id": home_active.player_id,
            "player_name": home_active.player_name,
        } if home_active else None

        away_info = {
            "player_id": away_active.player_id,
            "player_name": away_active.player_name,
        } if away_active else None

        return home_info, away_info

    def record_team_bout(
        self,
        result: BoutResult,
        winning_team: str,
        time_remaining_ms: int = 0,
    ) -> None:
        """
        Record a bout result in team mode.
        Awards AP to winning team and advances the player queues.

        Args:
            result: OPA or OSHI
            winning_team: "home" or "away"
            time_remaining_ms: Time remaining in the round
        """
        if self.state != MatchState.ROUND_ACTIVE:
            raise RuntimeError(f"Cannot record bout in state: {self.state}")

        self._bout_count += 1
        self._round_time_remaining_ms = time_remaining_ms

        # Get active players
        home_active = self._home_queue.active_player
        away_active = self._away_queue.active_player

        if not home_active or not away_active:
            raise RuntimeError("No active players in queues")

        # Determine winner/loser
        if winning_team == "home":
            winner_id = home_active.player_id
            loser_id = away_active.player_id
            self._p1_ap += 1
            self._round_p1_ap += 1
            if result == BoutResult.OPA:
                self._p1_opa_count += 1
            else:
                self._p1_oshi_count += 1
        else:
            winner_id = away_active.player_id
            loser_id = home_active.player_id
            self._p2_ap += 1
            self._round_p2_ap += 1
            if result == BoutResult.OPA:
                self._p2_opa_count += 1
            else:
                self._p2_oshi_count += 1

        # Create bout record
        bout_record = BoutRecord(
            round_number=self._current_round,
            bout_number=self._bout_count,
            result=result,
            winner_id=winner_id,
            loser_id=loser_id,
            time_remaining_ms=time_remaining_ms,
        )
        self._bout_history.append(bout_record)

        # Advance both queues
        self._home_queue.advance_queue()
        self._away_queue.advance_queue()

        self.bout_recorded.emit({
            "round": self._current_round,
            "bout": self._bout_count,
            "result": result.value,
            "winner_id": winner_id,
            "loser_id": loser_id,
            "winning_team": winning_team,
            "time_remaining_ms": time_remaining_ms,
        })

        self._emit_score_update()

    def eliminate_player(self, player_id: int, from_team: str) -> int:
        """
        Team mode: Remove a player after a round loss.
        Awards bonus AP based on how many players remain (Shooter Mode rules).

        Args:
            player_id: The player to eliminate
            from_team: "home" or "away"

        Returns:
            The bonus AP awarded
        """
        # Use PlayerQueue if available
        if hasattr(self, '_home_queue') and hasattr(self, '_away_queue'):
            if from_team == "home":
                self._home_queue.eliminate_player(player_id)
                remaining = self._home_queue.active_count
                self._home_eliminated.append(player_id)
            else:
                self._away_queue.eliminate_player(player_id)
                remaining = self._away_queue.active_count
                self._away_eliminated.append(player_id)
        else:
            # Fallback for simple roster lists
            if from_team == "home":
                if player_id in self._home_roster:
                    self._home_roster.remove(player_id)
                    self._home_eliminated.append(player_id)
                remaining = len(self._home_roster)
            else:
                if player_id in self._away_roster:
                    self._away_roster.remove(player_id)
                    self._away_eliminated.append(player_id)
                remaining = len(self._away_roster)

        # Calculate bonus based on Shooter Mode rules
        # Standard elimination: +3 AP
        # Endgame (≤3 remaining):
        #   1st eliminated (3→2): +5 AP
        #   2nd eliminated (2→1): +10 AP
        #   Last eliminated (1→0): +15 AP
        if remaining > 3:
            bonus = self.TEAM_ROUND_WIN_BONUS  # +3 AP
        elif remaining == 2:
            bonus = self.ENDGAME_BONUSES[1]  # +5 AP (1st endgame elim)
        elif remaining == 1:
            bonus = self.ENDGAME_BONUSES[2]  # +10 AP (2nd endgame elim)
        elif remaining == 0:
            bonus = self.ENDGAME_BONUSES[3]  # +15 AP (final elim)
        else:
            bonus = self.TEAM_ROUND_WIN_BONUS

        # Award bonus to the winning team (opposite of eliminated team)
        winning_team = "away" if from_team == "home" else "home"
        if winning_team == "home":
            self._p1_ap += bonus
        else:
            self._p2_ap += bonus

        self.player_eliminated.emit(player_id, 0)
        self._emit_score_update()

        # Check for team elimination (game/match end)
        if remaining == 0:
            self._on_team_eliminated(from_team)

        return bonus

    def _on_team_eliminated(self, eliminated_team: str) -> None:
        """Handle when all players on a team are eliminated."""
        winning_team = "home" if eliminated_team == "away" else "away"

        # End the current game
        self.game_ended.emit(self._current_game, winning_team)

        if self._current_game >= self.TOTAL_GAMES:
            self._complete_match()
        else:
            # Advance to next game
            self._current_game += 1
            self._current_round = 0
            # Reset queues for new game (would need to re-setup rosters)
            self.state = MatchState.MATCH_ACTIVE

    def substitute_player(
        self,
        team: str,
        out_player_id: int,
        in_player_id: int,
        in_player_name: str,
    ) -> bool:
        """
        Make a substitution (Team mode only).

        Args:
            team: "home" or "away"
            out_player_id: Player being removed
            in_player_id: Player coming in
            in_player_name: Name of the incoming player

        Returns:
            True if substitution was successful
        """
        queue = self._home_queue if team == "home" else self._away_queue

        if not queue.can_substitute():
            return False

        success = queue.substitute_player(out_player_id, in_player_id, in_player_name)

        if success:
            if team == "home":
                self._home_subs_used += 1
            else:
                self._away_subs_used += 1

            self.substitution_made.emit({
                "team": team,
                "out_player_id": out_player_id,
                "in_player_id": in_player_id,
                "in_player_name": in_player_name,
                "subs_remaining": queue.remaining_substitutions(),
            })

        return success

    def get_queue_state(self, team: str) -> list[dict]:
        """Get the current queue state for a team."""
        if team == "home" and hasattr(self, '_home_queue'):
            return self._home_queue.get_queue_state()
        elif team == "away" and hasattr(self, '_away_queue'):
            return self._away_queue.get_queue_state()
        return []

    def get_substitution_info(self, team: str) -> dict:
        """Get substitution information for a team."""
        if team == "home":
            if hasattr(self, '_home_queue'):
                return {
                    "used": self._home_queue.substitution_count,
                    "remaining": self._home_queue.remaining_substitutions(),
                    "max": PlayerQueue.MAX_SUBSTITUTIONS,
                }
            return {"used": self._home_subs_used, "remaining": 5 - self._home_subs_used, "max": 5}
        else:
            if hasattr(self, '_away_queue'):
                return {
                    "used": self._away_queue.substitution_count,
                    "remaining": self._away_queue.remaining_substitutions(),
                    "max": PlayerQueue.MAX_SUBSTITUTIONS,
                }
            return {"used": self._away_subs_used, "remaining": 5 - self._away_subs_used, "max": 5}

    def is_team_mode(self) -> bool:
        """Check if this is a team mode match."""
        return self.game_mode == GameMode.TEAM_VS_TEAM

    # ============ Query Methods ============

    def get_score_state(self) -> ScoreState:
        """Get the current score state snapshot."""
        return ScoreState(
            player1_ap=self._p1_ap,
            player2_ap=self._p2_ap,
            player1_opa_wins=self._p1_opa_count,
            player1_oshi_wins=self._p1_oshi_count,
            player2_opa_wins=self._p2_opa_count,
            player2_oshi_wins=self._p2_oshi_count,
            current_round=self._current_round,
            total_rounds=self.total_rounds,
            bout_count=self._bout_count,
            round_time_remaining_ms=self._round_time_remaining_ms,
            home_eliminations=len(self._home_eliminated),
            away_eliminations=len(self._away_eliminated),
            is_round_active=(self.state == MatchState.ROUND_ACTIVE),
            is_match_active=(self.state in (MatchState.MATCH_ACTIVE, MatchState.ROUND_ACTIVE)),
            state=self.state,
            player1_name=self._p1_name,
            player2_name=self._p2_name,
        )

    @property
    def is_match_complete(self) -> bool:
        """Check if the match is complete."""
        return self.state == MatchState.COMPLETED

    @property
    def can_start_round(self) -> bool:
        """Check if a new round can be started."""
        return (
            self.state in (MatchState.MATCH_ACTIVE, MatchState.ROUND_COMPLETE)
            and self._current_round < self.total_rounds
        )

    @property
    def can_record_bout(self) -> bool:
        """Check if a bout can be recorded."""
        return self.state == MatchState.ROUND_ACTIVE

    @property
    def opa_player_id(self) -> Optional[int]:
        """Get the player ID who has OPA (from toss)."""
        if not hasattr(self, '_toss_winner') or not hasattr(self, '_toss_choice'):
            return self._p1_id  # Default to player 1

        # Determine who has OPA based on toss
        toss_winner = self._toss_winner
        toss_choice = self._toss_choice

        # For 1v1: toss_winner is "player1" or "player2"
        # For team: toss_winner is "home" or "away"
        if toss_winner in ("player1", "home"):
            # Player 1 / Home won the toss
            if toss_choice == "opa":
                return self._p1_id  # They chose OPA
            else:
                return self._p2_id  # They chose OSHI, so opponent has OPA
        else:
            # Player 2 / Away won the toss
            if toss_choice == "opa":
                return self._p2_id  # They chose OPA
            else:
                return self._p1_id  # They chose OSHI, so opponent has OPA

    @property
    def oshi_player_id(self) -> Optional[int]:
        """Get the player ID who has OSHI (from toss)."""
        # OSHI player is opposite of OPA player
        opa_id = self.opa_player_id
        if opa_id == self._p1_id:
            return self._p2_id
        else:
            return self._p1_id

    @property
    def opa_player_name(self) -> str:
        """Get the name of the player who has OPA."""
        if self.opa_player_id == self._p1_id:
            return self._p1_name
        return self._p2_name

    @property
    def oshi_player_name(self) -> str:
        """Get the name of the player who has OSHI."""
        if self.oshi_player_id == self._p1_id:
            return self._p1_name
        return self._p2_name
