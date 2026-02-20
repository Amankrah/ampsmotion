"""
Main Window - Ampfre Console

The primary control panel for match officiating.
Uses QStackedWidget to navigate between functional screens.
"""

from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QStackedWidget, QToolBar, QStatusBar,
    QWidget, QVBoxLayout, QLabel, QMessageBox
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QAction, QKeySequence

from services.event_bus import EventBus
from engine.scoring import ScoringEngine, ScoreState


class MainWindow(QMainWindow):
    """
    Primary Ampfre Console — the operator's control panel.

    Provides navigation between:
    - Match Setup
    - Live Scoring
    - Match History
    """

    def __init__(self, event_bus: EventBus):
        super().__init__()
        self.event_bus = event_bus
        self.scoring_engine: Optional[ScoringEngine] = None

        self.setWindowTitle("AmpsMotion — Ampfre Console")
        self.setMinimumSize(1280, 800)

        # Central stacked widget for screen navigation
        self.stack = QStackedWidget()
        self.stack.setObjectName("main_stack")
        self.stack.setContentsMargins(16, 16, 16, 16)
        self.setCentralWidget(self.stack)

        # Import screens here to avoid circular imports
        from gui.widgets.match_setup import MatchSetupWidget
        from gui.widgets.scoring_panel import ScoringScreen
        from gui.widgets.match_history import MatchHistoryWidget

        # Create screens
        self.match_setup_screen = MatchSetupWidget(event_bus, self)
        self.scoring_screen = ScoringScreen(event_bus, self)
        self.history_screen = MatchHistoryWidget(event_bus)

        # Add screens to stack
        self.stack.addWidget(self.match_setup_screen)   # index 0
        self.stack.addWidget(self.scoring_screen)       # index 1
        self.stack.addWidget(self.history_screen)       # index 2

        # Build UI
        self._build_toolbar()
        self._build_statusbar()
        self._connect_signals()

        # Audience display window (created on demand)
        self.audience_display = None

    def _build_toolbar(self) -> None:
        """Build the navigation toolbar."""
        tb = QToolBar("Navigation")
        tb.setObjectName("nav_toolbar")
        tb.setMovable(False)
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, tb)

        # Navigation actions (checkable for current-screen indication)
        self.action_setup = QAction("Setup Match", self)
        self.action_setup.setCheckable(True)
        self.action_setup.setChecked(True)
        self.action_setup.setShortcut(QKeySequence("Ctrl+1"))
        self.action_setup.triggered.connect(lambda: self.navigate_to("setup"))
        tb.addAction(self.action_setup)

        self.action_scoring = QAction("Live Scoring", self)
        self.action_scoring.setCheckable(True)
        self.action_scoring.setShortcut(QKeySequence("Ctrl+2"))
        self.action_scoring.triggered.connect(lambda: self.navigate_to("scoring"))
        tb.addAction(self.action_scoring)

        self.action_history = QAction("Match History", self)
        self.action_history.setCheckable(True)
        self.action_history.setShortcut(QKeySequence("Ctrl+3"))
        self.action_history.triggered.connect(lambda: self.navigate_to("history"))
        tb.addAction(self.action_history)

        self._nav_actions = [self.action_setup, self.action_scoring, self.action_history]

        tb.addSeparator()

        # Audience display
        self.action_audience = QAction("Open Audience Display", self)
        self.action_audience.setShortcut(QKeySequence("F11"))
        self.action_audience.triggered.connect(self._open_audience_display)
        tb.addAction(self.action_audience)

    def _build_statusbar(self) -> None:
        """Build the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready — Set up a match to begin")

        # Permanent widgets
        self.status_match = QLabel("No active match")
        self.status_bar.addPermanentWidget(self.status_match)

    def _connect_signals(self) -> None:
        """Connect event bus signals."""
        self.event_bus.match_started.connect(self._on_match_started)
        self.event_bus.match_completed.connect(self._on_match_completed)
        self.event_bus.score_updated.connect(self._on_score_updated)
        self.event_bus.system_message.connect(self._on_system_message)

    @Slot(str)
    def navigate_to(self, screen: str) -> None:
        """Navigate to a specific screen."""
        screens = {
            "setup": 0,
            "scoring": 1,
            "history": 2,
        }
        if screen in screens:
            self.stack.setCurrentIndex(screens[screen])
            for i, act in enumerate(self._nav_actions):
                act.setChecked(i == screens[screen])
            self.status_bar.showMessage(f"Viewing: {screen.title()}")

    def set_scoring_engine(self, engine: ScoringEngine) -> None:
        """Set the active scoring engine for the current match."""
        self.scoring_engine = engine
        self.scoring_screen.set_scoring_engine(engine)

    def start_match_scoring(self) -> None:
        """Switch to the scoring screen after match setup."""
        self.navigate_to("scoring")
        self.status_bar.showMessage("Match in progress")
        self.status_match.setText("Match active — Click 'Start Round' to begin")

    def _open_audience_display(self) -> None:
        """Open the audience display window."""
        from gui.audience_display import AudienceDisplay

        if self.audience_display is None:
            self.audience_display = AudienceDisplay(self.event_bus, self.scoring_engine)

        # Move to secondary monitor if available
        from PySide6.QtWidgets import QApplication
        screens = QApplication.screens()
        if len(screens) > 1:
            self.audience_display.setScreen(screens[1])

        self.audience_display.showFullScreen()
        self.status_bar.showMessage("Audience display opened")

    @Slot(int)
    def _on_match_started(self, match_id: int) -> None:
        """Handle match started event."""
        self.status_match.setText(f"Match #{match_id} in progress")

    @Slot(dict)
    def _on_match_completed(self, results: dict) -> None:
        """Handle match completed event."""
        winner = results.get("winner", "Unknown")
        self.status_match.setText(f"Match complete — Winner: {winner}")
        self.status_bar.showMessage("Match completed")

    @Slot(object)
    def _on_score_updated(self, state: ScoreState) -> None:
        """Handle score update."""
        if state.is_match_active:
            p1 = state.player1_ap
            p2 = state.player2_ap
            self.status_match.setText(f"Score: {p1} - {p2}")

    @Slot(str, str)
    def _on_system_message(self, level: str, message: str) -> None:
        """Display system message in status bar."""
        self.status_bar.showMessage(f"[{level.upper()}] {message}", 5000)

    def closeEvent(self, event) -> None:
        """Handle window close."""
        if self.scoring_engine and self.scoring_engine.state.value == "round_active":
            reply = QMessageBox.question(
                self,
                "Match in Progress",
                "A match is currently in progress. Are you sure you want to exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return

        # Close audience display if open
        if self.audience_display:
            self.audience_display.close()

        event.accept()
