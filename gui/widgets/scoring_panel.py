"""
Live Scoring Panel

The primary screen during a match. Designed for speed — the Master Ampfre
must record bouts as fast as they happen (sub-second reaction).

Keyboard shortcuts (from Section 8.3):
- O: Record Opa
- S: Record Oshi
- 1: Winner = Player 1
- 2: Winner = Player 2
- Enter: Confirm & record bout
- Ctrl+Z: Undo last bout
- Space: Pause/Resume timer
- F: Open Foul dialog
- Ctrl+E: End round
"""

from typing import Optional, TYPE_CHECKING

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QGroupBox, QRadioButton,
    QButtonGroup, QListWidget, QListWidgetItem, QMessageBox,
    QFrame, QSplitter
)
from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtGui import QKeySequence, QShortcut

from services.event_bus import EventBus
from engine.scoring import ScoringEngine, ScoreState, MatchState
from engine.timer import RoundTimer
from models.bout import BoutResult

if TYPE_CHECKING:
    from gui.main_window import MainWindow


class ScoringPanel(QWidget):
    """
    Bout recording panel with large Opa/Oshi buttons.

    Signals:
        bout_submitted: Emitted when a bout is recorded
    """

    bout_submitted = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.selected_result: Optional[BoutResult] = None
        self.selected_winner: Optional[int] = None  # 1 or 2

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the bout recording UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Title
        title = QLabel("Bout Recording")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #FCD116;")
        layout.addWidget(title)

        # Opa/Oshi buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(20)

        self.btn_opa = QPushButton("OPA\n(Different Legs)")
        self.btn_opa.setObjectName("opa_button")
        self.btn_opa.setCheckable(True)
        self.btn_opa.clicked.connect(lambda: self._select_result(BoutResult.OPA))
        buttons_layout.addWidget(self.btn_opa)

        self.btn_oshi = QPushButton("OSHI\n(Same Legs)")
        self.btn_oshi.setObjectName("oshi_button")
        self.btn_oshi.setCheckable(True)
        self.btn_oshi.clicked.connect(lambda: self._select_result(BoutResult.OSHI))
        buttons_layout.addWidget(self.btn_oshi)

        layout.addLayout(buttons_layout)

        # Winner selection
        winner_group = QGroupBox("Winner")
        winner_layout = QHBoxLayout(winner_group)

        self.winner_group = QButtonGroup(self)

        self.btn_p1_wins = QRadioButton("Player 1")
        self.btn_p1_wins.setStyleSheet("font-size: 14px; padding: 10px;")
        self.winner_group.addButton(self.btn_p1_wins, 1)
        winner_layout.addWidget(self.btn_p1_wins)

        self.btn_p2_wins = QRadioButton("Player 2")
        self.btn_p2_wins.setStyleSheet("font-size: 14px; padding: 10px;")
        self.winner_group.addButton(self.btn_p2_wins, 2)
        winner_layout.addWidget(self.btn_p2_wins)

        self.winner_group.buttonClicked.connect(self._on_winner_selected)

        layout.addWidget(winner_group)

        # Action buttons
        actions_layout = QHBoxLayout()

        self.btn_record = QPushButton("✓ Record Bout")
        self.btn_record.setStyleSheet(
            "background-color: #006B3F; font-size: 14px; padding: 12px 24px;"
        )
        self.btn_record.clicked.connect(self._record_bout)
        self.btn_record.setEnabled(False)
        actions_layout.addWidget(self.btn_record)

        self.btn_foul = QPushButton("⚠ Foul")
        self.btn_foul.setStyleSheet("font-size: 14px; padding: 12px 24px;")
        self.btn_foul.clicked.connect(self._open_foul_dialog)
        actions_layout.addWidget(self.btn_foul)

        self.btn_undo = QPushButton("↩ Undo")
        self.btn_undo.setStyleSheet("font-size: 14px; padding: 12px 24px;")
        self.btn_undo.clicked.connect(self._undo_bout)
        actions_layout.addWidget(self.btn_undo)

        layout.addLayout(actions_layout)

    def _select_result(self, result: BoutResult) -> None:
        """Select the bout result (Opa or Oshi)."""
        self.selected_result = result

        # Update button states
        self.btn_opa.setChecked(result == BoutResult.OPA)
        self.btn_oshi.setChecked(result == BoutResult.OSHI)

        self._check_ready()

    def _on_winner_selected(self, button: QRadioButton) -> None:
        """Handle winner selection."""
        self.selected_winner = self.winner_group.id(button)
        self._check_ready()

    def _check_ready(self) -> None:
        """Check if ready to record bout."""
        ready = self.selected_result is not None and self.selected_winner is not None
        self.btn_record.setEnabled(ready)

    def _record_bout(self) -> None:
        """Submit the bout recording."""
        if self.selected_result and self.selected_winner:
            self.bout_submitted.emit({
                "result": self.selected_result,
                "winner": self.selected_winner,
            })
            self._reset_selection()

    def _reset_selection(self) -> None:
        """Reset the bout selection state."""
        self.selected_result = None
        self.selected_winner = None
        self.btn_opa.setChecked(False)
        self.btn_oshi.setChecked(False)
        self.winner_group.setExclusive(False)
        self.btn_p1_wins.setChecked(False)
        self.btn_p2_wins.setChecked(False)
        self.winner_group.setExclusive(True)
        self.btn_record.setEnabled(False)

    def _open_foul_dialog(self) -> None:
        """Open the foul recording dialog."""
        # TODO: Implement foul dialog
        QMessageBox.information(self, "Foul", "Foul recording dialog - coming soon")

    def _undo_bout(self) -> None:
        """Request undo of last bout."""
        # Handled by parent ScoringScreen
        pass

    def set_player_names(self, p1_name: str, p2_name: str) -> None:
        """Set the player names on the winner buttons."""
        self.btn_p1_wins.setText(f"{p1_name} (1)")
        self.btn_p2_wins.setText(f"{p2_name} (2)")

    def select_opa(self) -> None:
        """Programmatically select Opa (for keyboard shortcut)."""
        self._select_result(BoutResult.OPA)

    def select_oshi(self) -> None:
        """Programmatically select Oshi (for keyboard shortcut)."""
        self._select_result(BoutResult.OSHI)

    def select_winner_1(self) -> None:
        """Programmatically select Player 1 as winner."""
        self.btn_p1_wins.setChecked(True)
        self.selected_winner = 1
        self._check_ready()

    def select_winner_2(self) -> None:
        """Programmatically select Player 2 as winner."""
        self.btn_p2_wins.setChecked(True)
        self.selected_winner = 2
        self._check_ready()


class ScoringScreen(QWidget):
    """
    Complete scoring screen with timer, scores, and bout recording.

    This is the main interface during an active match.
    """

    def __init__(self, event_bus: EventBus, main_window: "MainWindow"):
        super().__init__()
        self.event_bus = event_bus
        self.main_window = main_window

        self.scoring_engine: Optional[ScoringEngine] = None
        self.round_timer: Optional[RoundTimer] = None

        self._build_ui()
        self._setup_shortcuts()
        self._connect_signals()

    def _build_ui(self) -> None:
        """Build the scoring screen UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Top bar: Round info and timer
        top_bar = QHBoxLayout()

        self.round_label = QLabel("ROUND 0 / 0")
        self.round_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        top_bar.addWidget(self.round_label)

        top_bar.addStretch()

        self.timer_label = QLabel("01:00")
        self.timer_label.setObjectName("timer_display")
        self.timer_label.setStyleSheet(
            "font-size: 48px; font-weight: bold; font-family: 'JetBrains Mono', monospace; color: #00CC00;"
        )
        top_bar.addWidget(self.timer_label)

        layout.addLayout(top_bar)

        # Main content: Scores and bout panel
        content = QHBoxLayout()

        # Player 1 score
        p1_frame = self._create_player_frame("player1")
        self.p1_name_label = p1_frame.findChild(QLabel, "player_name")
        self.p1_score_label = p1_frame.findChild(QLabel, "player_score")
        self.p1_stats_label = p1_frame.findChild(QLabel, "player_stats")
        content.addWidget(p1_frame)

        # Center: Bout recording
        center_layout = QVBoxLayout()

        self.scoring_panel = ScoringPanel()
        self.scoring_panel.bout_submitted.connect(self._on_bout_submitted)
        self.scoring_panel.btn_undo.clicked.connect(self._undo_last_bout)
        center_layout.addWidget(self.scoring_panel)

        # Bout log
        log_group = QGroupBox("Bout Log")
        log_layout = QVBoxLayout(log_group)
        self.bout_log = QListWidget()
        self.bout_log.setMaximumHeight(150)
        log_layout.addWidget(self.bout_log)
        center_layout.addWidget(log_group)

        content.addLayout(center_layout)

        # Player 2 score
        p2_frame = self._create_player_frame("player2")
        self.p2_name_label = p2_frame.findChild(QLabel, "player_name")
        self.p2_score_label = p2_frame.findChild(QLabel, "player_score")
        self.p2_stats_label = p2_frame.findChild(QLabel, "player_stats")
        content.addWidget(p2_frame)

        layout.addLayout(content)

        # Bottom: Control buttons
        controls = QHBoxLayout()

        self.btn_start_round = QPushButton("Start Round")
        self.btn_start_round.setStyleSheet(
            "background-color: #006B3F; font-size: 14px; padding: 12px 24px;"
        )
        self.btn_start_round.clicked.connect(self._start_round)
        controls.addWidget(self.btn_start_round)

        self.btn_pause = QPushButton("Pause")
        self.btn_pause.clicked.connect(self._toggle_pause)
        self.btn_pause.setEnabled(False)
        controls.addWidget(self.btn_pause)

        self.btn_end_round = QPushButton("End Round")
        self.btn_end_round.clicked.connect(self._end_round)
        self.btn_end_round.setEnabled(False)
        controls.addWidget(self.btn_end_round)

        controls.addStretch()

        self.btn_end_match = QPushButton("End Match")
        self.btn_end_match.setStyleSheet("background-color: #CE1126;")
        self.btn_end_match.clicked.connect(self._end_match)
        controls.addWidget(self.btn_end_match)

        layout.addLayout(controls)

    def _create_player_frame(self, player_id: str) -> QFrame:
        """Create a player score display frame."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #16213E;
                border: 2px solid #333355;
                border-radius: 12px;
                padding: 20px;
                min-width: 250px;
            }
        """)

        layout = QVBoxLayout(frame)

        name_label = QLabel("Player")
        name_label.setObjectName("player_name")
        name_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #FCD116;")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)

        score_label = QLabel("0")
        score_label.setObjectName("player_score")
        score_label.setStyleSheet("font-size: 72px; font-weight: bold;")
        score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(score_label)

        ap_label = QLabel("AP")
        ap_label.setStyleSheet("font-size: 14px; color: #A0A0B0;")
        ap_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ap_label)

        stats_label = QLabel("Opa: 0 | Oshi: 0")
        stats_label.setObjectName("player_stats")
        stats_label.setStyleSheet("font-size: 12px; color: #666;")
        stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(stats_label)

        return frame

    def _setup_shortcuts(self) -> None:
        """Set up keyboard shortcuts for fast bout recording."""
        # O - Opa
        QShortcut(QKeySequence("O"), self).activated.connect(
            self.scoring_panel.select_opa
        )

        # S - Oshi
        QShortcut(QKeySequence("S"), self).activated.connect(
            self.scoring_panel.select_oshi
        )

        # 1 - Player 1 wins
        QShortcut(QKeySequence("1"), self).activated.connect(
            self.scoring_panel.select_winner_1
        )

        # 2 - Player 2 wins
        QShortcut(QKeySequence("2"), self).activated.connect(
            self.scoring_panel.select_winner_2
        )

        # Enter - Record bout
        QShortcut(QKeySequence(Qt.Key.Key_Return), self).activated.connect(
            self.scoring_panel._record_bout
        )

        # Ctrl+Z - Undo
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(
            self._undo_last_bout
        )

        # Space - Pause/Resume
        QShortcut(QKeySequence(Qt.Key.Key_Space), self).activated.connect(
            self._toggle_pause
        )

        # F - Foul
        QShortcut(QKeySequence("F"), self).activated.connect(
            self.scoring_panel._open_foul_dialog
        )

        # Ctrl+E - End round
        QShortcut(QKeySequence("Ctrl+E"), self).activated.connect(
            self._end_round
        )

    def _connect_signals(self) -> None:
        """Connect event bus signals."""
        self.event_bus.timer_tick.connect(self._on_timer_tick)
        self.event_bus.timer_expired.connect(self._on_timer_expired)

    def set_scoring_engine(self, engine: ScoringEngine) -> None:
        """Set the active scoring engine."""
        self.scoring_engine = engine

        # Create and configure timer
        self.round_timer = RoundTimer()
        self.round_timer.tick.connect(self._on_timer_tick)
        self.round_timer.round_expired.connect(self._on_timer_expired)

        # Connect engine signals
        engine.score_updated.connect(self._on_score_updated)
        engine.bout_recorded.connect(self._on_bout_logged)
        engine.round_started.connect(self._on_round_started)
        engine.round_ended.connect(self._on_round_ended)
        engine.match_completed.connect(self._on_match_completed)

        # Update UI with initial state
        self._update_display(engine.get_score_state())

        # Set player names
        self.scoring_panel.set_player_names(engine._p1_name, engine._p2_name)
        self.p1_name_label.setText(engine._p1_name)
        self.p2_name_label.setText(engine._p2_name)

    @Slot(dict)
    def _on_bout_submitted(self, data: dict) -> None:
        """Handle bout submission from the scoring panel."""
        if not self.scoring_engine or not self.scoring_engine.can_record_bout:
            return

        result = data["result"]
        winner = data["winner"]

        # Determine winner/loser IDs
        if winner == 1:
            winner_id = self.scoring_engine._p1_id
            loser_id = self.scoring_engine._p2_id
        else:
            winner_id = self.scoring_engine._p2_id
            loser_id = self.scoring_engine._p1_id

        # Get time remaining
        time_remaining = self.round_timer.remaining_ms if self.round_timer else 0

        # Record the bout
        self.scoring_engine.record_bout(result, winner_id, loser_id, time_remaining)

        # Notify timer of activity
        if self.round_timer:
            self.round_timer.notify_bout_activity()

    def _undo_last_bout(self) -> None:
        """Undo the last recorded bout."""
        if self.scoring_engine:
            undone = self.scoring_engine.undo_last_bout()
            if undone:
                # Remove from log
                if self.bout_log.count() > 0:
                    self.bout_log.takeItem(self.bout_log.count() - 1)

    def _start_round(self) -> None:
        """Start a new round."""
        if not self.scoring_engine or not self.scoring_engine.can_start_round:
            return

        self.scoring_engine.start_round()

        if self.round_timer:
            self.round_timer.start()

        # Update button states
        self.btn_start_round.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_end_round.setEnabled(True)

        # Clear bout log for new round
        self.bout_log.clear()

    def _toggle_pause(self) -> None:
        """Toggle pause state."""
        if not self.scoring_engine:
            return

        if self.scoring_engine.state == MatchState.PAUSED:
            self.scoring_engine.resume()
            if self.round_timer:
                self.round_timer.resume()
            self.btn_pause.setText("Pause")
        elif self.scoring_engine.state == MatchState.ROUND_ACTIVE:
            self.scoring_engine.pause()
            if self.round_timer:
                self.round_timer.pause()
            self.btn_pause.setText("Resume")

    def _end_round(self) -> None:
        """End the current round."""
        if not self.scoring_engine:
            return

        if self.scoring_engine.state == MatchState.ROUND_ACTIVE:
            if self.round_timer:
                self.round_timer.stop()
            self.scoring_engine.end_round()

    def _end_match(self) -> None:
        """End the match early."""
        if not self.scoring_engine:
            return

        reply = QMessageBox.question(
            self,
            "End Match",
            "Are you sure you want to end the match early?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.round_timer:
                self.round_timer.stop()
            if self.scoring_engine.state == MatchState.ROUND_ACTIVE:
                self.scoring_engine.end_round()
            # Force completion
            self.scoring_engine._current_round = self.scoring_engine.total_rounds
            self.scoring_engine._complete_match()

    @Slot(int)
    def _on_timer_tick(self, remaining_ms: int) -> None:
        """Handle timer tick."""
        minutes = remaining_ms // 60000
        seconds = (remaining_ms % 60000) // 1000

        self.timer_label.setText(f"{minutes:02d}:{seconds:02d}")

        # Color changes for warnings
        if remaining_ms < 10000:
            self.timer_label.setStyleSheet(
                "font-size: 48px; font-weight: bold; font-family: 'JetBrains Mono', monospace; color: #FF4444;"
            )
        elif remaining_ms < 30000:
            self.timer_label.setStyleSheet(
                "font-size: 48px; font-weight: bold; font-family: 'JetBrains Mono', monospace; color: #FFB74D;"
            )
        else:
            self.timer_label.setStyleSheet(
                "font-size: 48px; font-weight: bold; font-family: 'JetBrains Mono', monospace; color: #00CC00;"
            )

    @Slot()
    def _on_timer_expired(self) -> None:
        """Handle timer expiration."""
        self._end_round()

    @Slot(object)
    def _on_score_updated(self, state: ScoreState) -> None:
        """Handle score update from engine."""
        self._update_display(state)

    def _update_display(self, state: ScoreState) -> None:
        """Update all display elements."""
        # Round info
        self.round_label.setText(f"ROUND {state.current_round} / {state.total_rounds}")

        # Player 1
        self.p1_score_label.setText(str(state.player1_ap))
        self.p1_stats_label.setText(
            f"Opa: {state.player1_opa_wins} | Oshi: {state.player1_oshi_wins}"
        )

        # Player 2
        self.p2_score_label.setText(str(state.player2_ap))
        self.p2_stats_label.setText(
            f"Opa: {state.player2_opa_wins} | Oshi: {state.player2_oshi_wins}"
        )

        # Update button states based on match state
        self.btn_start_round.setEnabled(
            state.state in (MatchState.MATCH_ACTIVE, MatchState.ROUND_COMPLETE)
            and state.current_round < state.total_rounds
        )

    @Slot(dict)
    def _on_bout_logged(self, bout_data: dict) -> None:
        """Add bout to the log."""
        result = bout_data["result"].upper()
        winner_id = bout_data["winner_id"]

        winner_name = "P1" if winner_id == 1 else "P2"
        time_ms = bout_data.get("time_remaining_ms", 0)
        time_str = f"{time_ms // 1000}s" if time_ms else ""

        item = QListWidgetItem(f"#{bout_data['bout']} {result} → {winner_name} wins ({time_str})")

        if result == "OPA":
            item.setForeground(Qt.GlobalColor.green)
        else:
            item.setForeground(Qt.GlobalColor.red)

        self.bout_log.insertItem(0, item)

    @Slot(int)
    def _on_round_started(self, round_num: int) -> None:
        """Handle round start."""
        self.btn_start_round.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_end_round.setEnabled(True)

    @Slot(int, str)
    def _on_round_ended(self, round_num: int, winner: str) -> None:
        """Handle round end."""
        self.btn_start_round.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setText("Pause")
        self.btn_end_round.setEnabled(False)

        # Reset timer display
        self.timer_label.setText("01:00")
        self.timer_label.setStyleSheet(
            "font-size: 48px; font-weight: bold; font-family: 'JetBrains Mono', monospace; color: #00CC00;"
        )

        # Show round result
        winner_text = "Player 1" if winner == "player1" else "Player 2" if winner == "player2" else "Tie"
        QMessageBox.information(
            self,
            f"Round {round_num} Complete",
            f"Round winner: {winner_text}"
        )

    @Slot(dict)
    def _on_match_completed(self, results: dict) -> None:
        """Handle match completion."""
        winner = results.get("winner", "unknown")
        p1_ap = results.get("player1_ap", 0)
        p2_ap = results.get("player2_ap", 0)

        winner_text = "Player 1" if winner == "player1" else "Player 2" if winner == "player2" else "Tie"

        QMessageBox.information(
            self,
            "Match Complete",
            f"Winner: {winner_text}\n\nFinal Score:\nPlayer 1: {p1_ap} AP\nPlayer 2: {p2_ap} AP"
        )

        # Disable all controls
        self.btn_start_round.setEnabled(False)
        self.btn_pause.setEnabled(False)
        self.btn_end_round.setEnabled(False)
