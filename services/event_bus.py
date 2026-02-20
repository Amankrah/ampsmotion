"""
Event Bus - Central signal hub for inter-module communication.

All modules connect to this single object rather than directly to each other,
enabling loose coupling between the scoring engine, GUI, and camera systems.
"""

from PySide6.QtCore import QObject, Signal


class EventBus(QObject):
    """
    Central signal hub for AmpsMotion.

    The EventBus acts as a mediator between all application components:
    - ScoringEngine emits scoring events
    - GUI components listen and update displays
    - Camera system emits frames for replay
    - Match Manager coordinates lifecycle

    Usage:
        # In ScoringEngine
        self.event_bus.bout_recorded.emit(bout_data)

        # In AudienceDisplay
        self.event_bus.score_updated.connect(self._on_score_updated)
    """

    # ============ Match Lifecycle ============
    match_created = Signal(dict)        # Match details dict
    match_started = Signal(int)         # match_id
    match_paused = Signal(int)          # match_id
    match_resumed = Signal(int)         # match_id
    match_completed = Signal(dict)      # Final results dict

    # ============ Game Lifecycle (Team Mode) ============
    game_started = Signal(int, int)     # match_id, game_number
    game_completed = Signal(int, int, str)  # match_id, game_number, winner ("home"/"away")

    # ============ Round Lifecycle ============
    round_started = Signal(int)         # round_number
    round_ended = Signal(int, str)      # round_number, winner side
    round_paused = Signal()
    round_resumed = Signal()

    # ============ Scoring Events ============
    bout_recorded = Signal(dict)        # Bout details: {round, bout, result, winner_id, loser_id}
    score_updated = Signal(object)      # ScoreUpdate dataclass
    bout_undone = Signal(dict)          # Bout that was undone

    # ============ Team Mode Events ============
    player_eliminated = Signal(int, int)    # player_id, team_id
    substitution_made = Signal(dict)        # {player_out_id, player_in_id, team_id}
    player_queue_updated = Signal(dict)     # {home_queue: [...], away_queue: [...]}

    # ============ Foul Events ============
    foul_recorded = Signal(dict)        # Foul details
    foul_penalty_applied = Signal(dict) # {player_id, penalty_type, ap_deducted}
    player_disqualified = Signal(int)   # player_id

    # ============ Timer Events ============
    timer_tick = Signal(float)          # seconds remaining
    timer_expired = Signal()            # Round time is up
    timer_paused = Signal()
    timer_resumed = Signal()
    pause_violation = Signal(int)       # player_id who paused > 10s

    # ============ Camera Events ============
    camera_frame = Signal(object)       # numpy array (BGR frame)
    camera_error = Signal(str)          # Error message
    replay_requested = Signal(int)      # seconds to go back
    clip_exported = Signal(str)         # filepath of exported clip

    # ============ UI Navigation ============
    navigate_to = Signal(str)           # screen name

    # ============ System Events ============
    database_error = Signal(str)        # Database error message
    system_message = Signal(str, str)   # (level, message) - e.g., ("info", "Match saved")

    def __init__(self):
        super().__init__()

    def emit_score_update(self, score_update) -> None:
        """Convenience method to emit a score update."""
        self.score_updated.emit(score_update)

    def emit_bout(self, round_num: int, bout_num: int, result: str,
                  winner_id: int, loser_id: int) -> None:
        """Convenience method to emit a bout recording."""
        self.bout_recorded.emit({
            "round": round_num,
            "bout": bout_num,
            "result": result,
            "winner_id": winner_id,
            "loser_id": loser_id,
        })

    def emit_foul(self, match_id: int, player_id: int, foul_type: str,
                  penalty: str, ap_deducted: int) -> None:
        """Convenience method to emit a foul recording."""
        self.foul_recorded.emit({
            "match_id": match_id,
            "player_id": player_id,
            "foul_type": foul_type,
            "penalty": penalty,
            "ap_deducted": ap_deducted,
        })

    def emit_message(self, level: str, message: str) -> None:
        """Emit a system message (info, warning, error)."""
        self.system_message.emit(level, message)
