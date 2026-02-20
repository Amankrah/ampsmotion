"""
AmpsMotion Application Controller

Top-level controller that wires together all application components.
"""

from typing import Optional

from PySide6.QtCore import QObject

from services.event_bus import EventBus
from engine.scoring import ScoringEngine
from engine.timer import RoundTimer
from engine.rules import RulesEngine
from models.match import GameMode
from models.base import init_db
from camera.ring_buffer import ReplayBuffer
from config import CAMERA_SETTINGS


class AmpsMotionApp(QObject):
    """
    Top-level application controller.
    Wires together all application components.
    """

    def __init__(self):
        super().__init__()

        # Initialize database
        init_db()

        # Core services
        self.event_bus = EventBus()
        self.rules_engine = RulesEngine()

        # Replay buffer (camera frames)
        self.replay_buffer = ReplayBuffer(
            max_seconds=CAMERA_SETTINGS.replay_buffer_seconds,
            fps=CAMERA_SETTINGS.target_fps
        )

        # Camera capture thread (lazy init)
        self.capture_thread = None

        # Active scoring engine (created per-match)
        self.scoring_engine: Optional[ScoringEngine] = None
        self.round_timer: Optional[RoundTimer] = None

        # Create main window
        from gui.main_window import MainWindow
        self.main_window = MainWindow(self.event_bus)

        # Audience display (created on demand)
        self.audience_display = None

        # Wire up event bus to scoring engine when matches are created
        self.event_bus.match_created.connect(self._on_match_created)

    def show(self) -> None:
        """Show the main application window."""
        self.main_window.show()

    def _on_match_created(self, match_data: dict) -> None:
        """Handle match creation event."""
        # The scoring engine is created by the MatchSetupWidget
        # This just tracks it for application-level access
        if self.main_window.scoring_engine:
            self.scoring_engine = self.main_window.scoring_engine

    def create_match(self, game_mode: GameMode, total_rounds: int = 5) -> ScoringEngine:
        """
        Create a new match with the specified settings.

        Args:
            game_mode: The game mode (1v1, team, tournament)
            total_rounds: Number of rounds for 1v1 mode

        Returns:
            The created ScoringEngine instance
        """
        self.scoring_engine = ScoringEngine(game_mode, total_rounds)
        self.round_timer = RoundTimer()
        self.rules_engine.reset()

        # Wire up signals to event bus
        self.scoring_engine.score_updated.connect(self.event_bus.score_updated.emit)
        self.scoring_engine.bout_recorded.connect(self.event_bus.bout_recorded.emit)
        self.scoring_engine.round_started.connect(self.event_bus.round_started.emit)
        self.scoring_engine.round_ended.connect(self.event_bus.round_ended.emit)
        self.scoring_engine.match_completed.connect(self.event_bus.match_completed.emit)
        self.scoring_engine.player_eliminated.connect(self.event_bus.player_eliminated.emit)
        self.scoring_engine.foul_applied.connect(self.event_bus.foul_recorded.emit)

        self.round_timer.tick.connect(self.event_bus.timer_tick.emit)
        self.round_timer.round_expired.connect(self.event_bus.timer_expired.emit)
        self.round_timer.pause_violation.connect(self.event_bus.pause_violation.emit)

        return self.scoring_engine

    def open_audience_display(self) -> None:
        """Open the audience display window."""
        from gui.audience_display import AudienceDisplay
        from PySide6.QtWidgets import QApplication

        if self.audience_display is None:
            self.audience_display = AudienceDisplay(
                self.event_bus,
                self.scoring_engine
            )

        # Move to secondary monitor if available
        screens = QApplication.screens()
        if len(screens) > 1:
            self.audience_display.setScreen(screens[1])

        self.audience_display.enter_fullscreen()

    def close_audience_display(self) -> None:
        """Close the audience display window."""
        if self.audience_display:
            self.audience_display.close()
            self.audience_display = None

    def start_camera(self, source: int = 0) -> None:
        """Start camera capture for VAR/replay."""
        # Will be implemented in Phase 5 (Camera)
        from camera.capture import CaptureThread

        if self.capture_thread is None:
            self.capture_thread = CaptureThread(source=source)
            self.capture_thread.frame_ready.connect(self.replay_buffer.push)
            self.capture_thread.frame_ready.connect(
                lambda f: self.event_bus.camera_frame.emit(f)
            )
            self.capture_thread.error.connect(
                lambda e: self.event_bus.camera_error.emit(e)
            )
            self.capture_thread.start()

    def stop_camera(self) -> None:
        """Stop camera capture."""
        if self.capture_thread is not None:
            self.capture_thread.stop()
            self.capture_thread = None

    def export_scoresheet(self, filepath: str, format: str = "pdf") -> bool:
        """
        Export the current match as a scoresheet.

        Args:
            filepath: Output file path
            format: "pdf" or "csv"

        Returns:
            True if export successful
        """
        from services.export import ScoresheetExporter

        if not self.scoring_engine:
            return False

        # Build match data from scoring engine
        state = self.scoring_engine.get_score_state()
        match_data = {
            "mode": "1v1" if self.scoring_engine.game_mode == GameMode.ONE_VS_ONE else "team",
            "total_rounds": self.scoring_engine.total_rounds,
            "player1_name": state.player1_name,
            "player2_name": state.player2_name,
            "player1_ap": state.player1_ap,
            "player2_ap": state.player2_ap,
            "winner": "Player 1" if state.player1_ap > state.player2_ap else "Player 2",
            "rounds": [],  # TODO: Populate from engine history
        }

        exporter = ScoresheetExporter()

        if format == "pdf":
            return exporter.export_1v1(match_data, filepath)
        elif format == "csv":
            return exporter.export_csv(match_data, filepath)

        return False
