"""
Live Scoring Panel - ONE-CLICK BOUT RECORDING

The primary screen during a match. Designed for MAXIMUM speed — bouts happen
in split seconds during heated exchanges and must be recorded instantly.

ONE-CLICK SYSTEM:
The toss determines which player has OPA vs OSHI. During the match:
- Click OPA button → records bout win for the OPA player
- Click OSHI button → records bout win for the OSHI player
NO winner selection needed. NO "Record Bout" button needed. ONE CLICK = ONE BOUT.

Keyboard shortcuts:
- O: Record OPA bout (instant)
- S: Record OSHI bout (instant)
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
    QFrame, QSplitter, QDialog, QComboBox, QLineEdit, QFormLayout
)
from PySide6.QtCore import Qt, Slot, Signal, QSize
from PySide6.QtGui import QKeySequence, QShortcut

from gui.icons import icon_foul, icon_undo, icon_substitution, icon_size_normal

from models.match import GameMode

from services.event_bus import EventBus
from engine.scoring import ScoringEngine, ScoreState, MatchState
from engine.timer import RoundTimer
from models.bout import BoutResult

if TYPE_CHECKING:
    from gui.main_window import MainWindow


class ScoringPanel(QWidget):
    """
    ONE-CLICK bout recording panel.

    The toss determines which player has OPA vs OSHI, so clicking
    a button immediately records a bout win for that player.

    - Click OPA → records win for the OPA player
    - Click OSHI → records win for the OSHI player
    - Press O or S for keyboard shortcuts

    Signals:
        bout_submitted: Emitted when a bout is recorded (includes result and winner)
    """

    bout_submitted = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Player assignments from toss
        self._opa_player_id: Optional[int] = None
        self._oshi_player_id: Optional[int] = None
        self._opa_player_name: str = "OPA Player"
        self._oshi_player_name: str = "OSHI Player"

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the one-click bout recording UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Title with instructions (section title style)
        title = QLabel("ONE-CLICK BOUT RECORDING")
        title.setObjectName("section_title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        hint = QLabel("Click the winning call or press O / S")
        hint.setObjectName("hint_label")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        # Large OPA/OSHI buttons - clicking records immediately
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)

        # OPA Button - shows player name who has OPA (styled via QSS #opa_button)
        self.btn_opa = QPushButton()
        self.btn_opa.setObjectName("opa_button")
        self.btn_opa.setMinimumHeight(120)
        self.btn_opa.clicked.connect(self._record_opa)
        buttons_layout.addWidget(self.btn_opa)

        # OSHI Button - shows player name who has OSHI (styled via QSS #oshi_button)
        self.btn_oshi = QPushButton()
        self.btn_oshi.setObjectName("oshi_button")
        self.btn_oshi.setMinimumHeight(120)
        self.btn_oshi.clicked.connect(self._record_oshi)
        buttons_layout.addWidget(self.btn_oshi)

        layout.addLayout(buttons_layout)

        # Update button labels
        self._update_button_labels()

        # Secondary actions row (Qt icons for visibility and consistency)
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)
        icon_sz = icon_size_normal()

        self.btn_foul = QPushButton("Foul (F)")
        self.btn_foul.setIcon(icon_foul())
        self.btn_foul.setIconSize(QSize(icon_sz, icon_sz))
        self.btn_foul.clicked.connect(self._open_foul_dialog)
        actions_layout.addWidget(self.btn_foul)

        self.btn_undo = QPushButton("Undo (Ctrl+Z)")
        self.btn_undo.setIcon(icon_undo())
        self.btn_undo.setIconSize(QSize(icon_sz, icon_sz))
        self.btn_undo.clicked.connect(self._undo_bout)
        actions_layout.addWidget(self.btn_undo)

        layout.addLayout(actions_layout)

    def _update_button_labels(self) -> None:
        """Update the button labels with player names."""
        self.btn_opa.setText(f"OPA\n(O)\n\n{self._opa_player_name}")
        self.btn_oshi.setText(f"OSHI\n(S)\n\n{self._oshi_player_name}")

    def set_toss_result(self, opa_player_id: int, opa_player_name: str,
                        oshi_player_id: int, oshi_player_name: str) -> None:
        """
        Set which player has OPA vs OSHI based on toss result.

        Args:
            opa_player_id: Player ID who has OPA
            opa_player_name: Name of OPA player
            oshi_player_id: Player ID who has OSHI
            oshi_player_name: Name of OSHI player
        """
        self._opa_player_id = opa_player_id
        self._oshi_player_id = oshi_player_id
        self._opa_player_name = opa_player_name
        self._oshi_player_name = oshi_player_name
        self._update_button_labels()

    def _record_opa(self) -> None:
        """Record OPA bout - winner is the OPA player."""
        if self._opa_player_id is not None:
            self.bout_submitted.emit({
                "result": BoutResult.OPA,
                "winner_id": self._opa_player_id,
                "loser_id": self._oshi_player_id,
            })

    def _record_oshi(self) -> None:
        """Record OSHI bout - winner is the OSHI player."""
        if self._oshi_player_id is not None:
            self.bout_submitted.emit({
                "result": BoutResult.OSHI,
                "winner_id": self._oshi_player_id,
                "loser_id": self._opa_player_id,
            })

    def record_opa(self) -> None:
        """Public method for keyboard shortcut - record OPA."""
        self._record_opa()

    def record_oshi(self) -> None:
        """Public method for keyboard shortcut - record OSHI."""
        self._record_oshi()

    def _open_foul_dialog(self) -> None:
        """Open the foul recording dialog."""
        QMessageBox.information(self, "Foul", "Foul recording dialog - coming soon")

    def _undo_bout(self) -> None:
        """Request undo of last bout - handled by parent ScoringScreen."""
        pass

    # Legacy methods for compatibility (no longer used)
    def set_player_names(self, p1_name: str, p2_name: str) -> None:
        """Legacy - use set_toss_result instead."""
        pass

    def select_opa(self) -> None:
        """Legacy keyboard handler - now directly records."""
        self._record_opa()

    def select_oshi(self) -> None:
        """Legacy keyboard handler - now directly records."""
        self._record_oshi()

    def select_winner_1(self) -> None:
        """Legacy - no longer needed with one-click recording."""
        pass

    def select_winner_2(self) -> None:
        """Legacy - no longer needed with one-click recording."""
        pass


class SubstitutionDialog(QDialog):
    """
    Dialog for making player substitutions in Team mode.

    Allows selecting a player to sub out (not the active player)
    and entering the substitute player's information.
    """

    def __init__(self, team_name: str, queue_state: list[dict],
                 remaining_subs: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Substitution - {team_name}")
        self.setMinimumWidth(400)

        self.queue_state = queue_state
        self.remaining_subs = remaining_subs

        self._build_ui(team_name)

    def _build_ui(self, team_name: str) -> None:
        """Build the substitution dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        header = QLabel(f"Make Substitution for {team_name}")
        header.setObjectName("section_title")
        layout.addWidget(header)

        # Remaining subs info
        subs_info = QLabel(f"Substitutions remaining: {self.remaining_subs}")
        subs_info.setObjectName("hint_label")
        layout.addWidget(subs_info)

        if self.remaining_subs <= 0:
            no_subs = QLabel("No substitutions remaining for this team.")
            no_subs.setStyleSheet("color: #CE1126; font-weight: bold;")
            layout.addWidget(no_subs)

            close_btn = QPushButton("Close")
            close_btn.clicked.connect(self.reject)
            layout.addWidget(close_btn)
            return

        # Form
        form = QFormLayout()
        form.setSpacing(10)

        # Player to sub out (dropdown of non-active players)
        self.out_combo = QComboBox()
        for player in self.queue_state:
            if not player["is_active"]:  # Can't sub out active player
                self.out_combo.addItem(
                    f"Box {player['box_number']}: {player['player_name']}",
                    player["player_id"]
                )
        form.addRow("Player OUT:", self.out_combo)

        # Substitute player info
        self.sub_name = QLineEdit()
        self.sub_name.setPlaceholderText("Enter substitute player name")
        form.addRow("Substitute Name:", self.sub_name)

        self.sub_jersey = QLineEdit()
        self.sub_jersey.setPlaceholderText("Jersey number")
        self.sub_jersey.setMaximumWidth(80)
        form.addRow("Jersey #:", self.sub_jersey)

        layout.addLayout(form)

        # Note
        note = QLabel("Note: Cannot substitute the active player (Box 1)")
        note.setStyleSheet("font-size: 9pt; color: #666; font-style: italic;")
        layout.addWidget(note)

        # Buttons
        buttons = QHBoxLayout()
        buttons.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)

        self.confirm_btn = QPushButton("Confirm Substitution")
        self.confirm_btn.setObjectName("primary_button")
        self.confirm_btn.clicked.connect(self._validate_and_accept)
        buttons.addWidget(self.confirm_btn)

        layout.addLayout(buttons)

    def _validate_and_accept(self) -> None:
        """Validate inputs and accept dialog."""
        if not self.sub_name.text().strip():
            QMessageBox.warning(self, "Missing Info", "Please enter the substitute player's name.")
            return

        self.accept()

    def get_substitution_data(self) -> dict:
        """Get the substitution data."""
        return {
            "out_player_id": self.out_combo.currentData(),
            "in_player_name": self.sub_name.text().strip(),
            "in_player_jersey": self.sub_jersey.text().strip(),
        }


class EliminationDialog(QDialog):
    """
    Dialog for selecting which opponent player to eliminate.

    In Team mode, when a team wins a round, they must select one
    opponent player to eliminate from the game.
    """

    def __init__(self, winning_team: str, losing_team_name: str,
                 losing_queue_state: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Player to Eliminate")
        self.setMinimumWidth(400)

        self.winning_team = winning_team
        self.losing_team_name = losing_team_name
        self.losing_queue_state = losing_queue_state

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the elimination dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        header = QLabel(f"Round Won!")
        header.setStyleSheet("font-size: 14pt; font-weight: bold; color: #006B3F;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        instruction = QLabel(f"Select a player from {self.losing_team_name} to eliminate:")
        instruction.setStyleSheet("font-size: 11pt; color: #E8B923;")
        instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(instruction)

        # Player selection list
        self.player_combo = QComboBox()
        self.player_combo.setStyleSheet("font-size: 11pt; padding: 8px;")
        for player in self.losing_queue_state:
            self.player_combo.addItem(
                f"Box {player['box_number']}: {player['player_name']}",
                player["player_id"]
            )
        layout.addWidget(self.player_combo)

        # Info about remaining players
        remaining = len(self.losing_queue_state)
        info = QLabel(f"{self.losing_team_name} has {remaining} players remaining")
        info.setStyleSheet("font-size: 9pt; color: #A0A0B0;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)

        # Confirm button
        self.confirm_btn = QPushButton("Eliminate Selected Player")
        self.confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #CE1126;
                font-size: 11pt;
                font-weight: bold;
                padding: 12px 24px;
            }
            QPushButton:hover {
                background-color: #EE3146;
            }
        """)
        self.confirm_btn.clicked.connect(self.accept)
        layout.addWidget(self.confirm_btn)

    def get_eliminated_player_id(self) -> int:
        """Get the selected player ID to eliminate."""
        return self.player_combo.currentData()

    def get_eliminated_player_name(self) -> str:
        """Get the selected player name."""
        return self.player_combo.currentText().split(": ", 1)[1] if ": " in self.player_combo.currentText() else ""


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

        # Team mode: track elapsed time instead of countdown
        self._is_team_mode: bool = False
        self._round_start_time: Optional[float] = None
        self._elapsed_timer_id: Optional[int] = None

        self._build_ui()
        self._setup_shortcuts()
        self._connect_signals()

    def _build_ui(self) -> None:
        """Build the scoring screen UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # Top bar: Round info and timer
        top_bar = QHBoxLayout()

        self.round_label = QLabel("ROUND 0 / 0")
        self.round_label.setObjectName("round_label")
        top_bar.addWidget(self.round_label)

        top_bar.addStretch()

        self.timer_label = QLabel("01:00")
        self.timer_label.setObjectName("timer_display")
        self.timer_label.setStyleSheet(
            "font-size: 32pt; font-weight: bold; font-family: 'JetBrains Mono', monospace; color: #00CC00;"
        )
        top_bar.addWidget(self.timer_label)

        layout.addLayout(top_bar)

        # Main content: Scores and bout panel
        content = QHBoxLayout()
        content.setSpacing(24)

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
        self.btn_start_round.setObjectName("primary_button")
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
        self.btn_end_match.setObjectName("danger_button")
        self.btn_end_match.clicked.connect(self._end_match)
        controls.addWidget(self.btn_end_match)

        layout.addLayout(controls)

        # Team mode controls: visible only when match is Team vs Team (see set_scoring_engine)
        self.team_controls = QFrame()
        self.team_controls.setObjectName("team_controls_frame")
        self.team_controls.setToolTip("Substitutions (Team vs Team only). Max 5 per team.")
        team_layout = QHBoxLayout(self.team_controls)
        team_layout.setSpacing(20)
        icon_sz = icon_size_normal()

        # Home team substitution
        home_sub_layout = QVBoxLayout()
        self.home_sub_label = QLabel("Home Team: 5 subs remaining")
        self.home_sub_label.setStyleSheet("font-size: 9pt; color: #2196F3;")
        home_sub_layout.addWidget(self.home_sub_label)

        self.btn_home_sub = QPushButton("Home Substitution")
        self.btn_home_sub.setIcon(icon_substitution())
        self.btn_home_sub.setIconSize(QSize(icon_sz, icon_sz))
        self.btn_home_sub.setStyleSheet("font-size: 9pt; padding: 8px 16px;")
        self.btn_home_sub.clicked.connect(lambda: self._open_substitution_dialog("home"))
        home_sub_layout.addWidget(self.btn_home_sub)

        team_layout.addLayout(home_sub_layout)

        team_layout.addStretch()

        # Game/Round info for team mode
        game_info_layout = QVBoxLayout()
        self.game_label = QLabel("GAME 1 / 3")
        self.game_label.setStyleSheet("font-size: 11pt; font-weight: bold; color: #E8B923;")
        self.game_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        game_info_layout.addWidget(self.game_label)

        self.elimination_label = QLabel("Eliminations: Home 0 - Away 0")
        self.elimination_label.setStyleSheet("font-size: 9pt; color: #A0A0B0;")
        self.elimination_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        game_info_layout.addWidget(self.elimination_label)

        team_layout.addLayout(game_info_layout)

        team_layout.addStretch()

        # Away team substitution
        away_sub_layout = QVBoxLayout()
        self.away_sub_label = QLabel("Away Team: 5 subs remaining")
        self.away_sub_label.setStyleSheet("font-size: 9pt; color: #FF5722;")
        away_sub_layout.addWidget(self.away_sub_label)

        self.btn_away_sub = QPushButton("Away Substitution")
        self.btn_away_sub.setIcon(icon_substitution())
        self.btn_away_sub.setIconSize(QSize(icon_sz, icon_sz))
        self.btn_away_sub.setStyleSheet("font-size: 9pt; padding: 8px 16px;")
        self.btn_away_sub.clicked.connect(lambda: self._open_substitution_dialog("away"))
        away_sub_layout.addWidget(self.btn_away_sub)

        team_layout.addLayout(away_sub_layout)

        layout.addWidget(self.team_controls)
        self.team_controls.setVisible(False)  # Hidden by default, shown for Team mode

    def _create_player_frame(self, player_id: str) -> QFrame:
        """Create a player score display frame (styled via QSS #player_card)."""
        frame = QFrame()
        frame.setObjectName("player_card")

        layout = QVBoxLayout(frame)
        layout.setSpacing(8)

        name_label = QLabel("Player")
        name_label.setObjectName("player_name")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)

        score_label = QLabel("0")
        score_label.setObjectName("player_score")
        score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(score_label)

        ap_label = QLabel("AP")
        ap_label.setObjectName("player_ap_label")
        ap_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ap_label)

        stats_label = QLabel("Opa: 0 | Oshi: 0")
        stats_label.setObjectName("player_stats")
        stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(stats_label)

        return frame

    def _setup_shortcuts(self) -> None:
        """
        Set up keyboard shortcuts for INSTANT bout recording.

        ONE-CLICK shortcuts:
        - O: Record OPA bout (winner = OPA player)
        - S: Record OSHI bout (winner = OSHI player)

        Other shortcuts:
        - Ctrl+Z: Undo last bout
        - Space: Pause/Resume
        - F: Open foul dialog
        - Ctrl+E: End round
        """
        # O - Record OPA (instant, one key)
        QShortcut(QKeySequence("O"), self).activated.connect(
            self.scoring_panel.record_opa
        )

        # S - Record OSHI (instant, one key)
        QShortcut(QKeySequence("S"), self).activated.connect(
            self.scoring_panel.record_oshi
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

        # Determine game mode
        self._is_team_mode = engine.is_team_mode()

        if self._is_team_mode:
            # Team mode: NO countdown timer - track elapsed time instead
            self.round_timer = None
            self.timer_label.setText("00:00")  # Start at 0, count UP
            self.timer_label.setStyleSheet(
                "font-size: 32pt; font-weight: bold; font-family: 'JetBrains Mono', monospace; color: #00CC00;"
            )
        else:
            # 1v1 mode: Use countdown timer (60 seconds)
            self.round_timer = RoundTimer()
            self.round_timer.tick.connect(self._on_timer_tick)
            self.round_timer.round_expired.connect(self._on_timer_expired)
            self.timer_label.setText("01:00")

        # Connect engine signals
        engine.score_updated.connect(self._on_score_updated)
        engine.bout_recorded.connect(self._on_bout_logged)
        engine.round_started.connect(self._on_round_started)
        engine.round_ended.connect(self._on_round_ended)
        engine.match_completed.connect(self._on_match_completed)

        # Update UI with initial state
        self._update_display(engine.get_score_state())

        # Set player names on display
        self.p1_name_label.setText(engine._p1_name)
        self.p2_name_label.setText(engine._p2_name)

        # Set toss result on scoring panel for one-click recording
        # The engine now has opa_player_id and oshi_player_id properties
        self.scoring_panel.set_toss_result(
            opa_player_id=engine.opa_player_id,
            opa_player_name=engine.opa_player_name,
            oshi_player_id=engine.oshi_player_id,
            oshi_player_name=engine.oshi_player_name,
        )

        # Show/hide team controls based on game mode
        if self._is_team_mode:
            self.team_controls.setVisible(True)
            self._update_team_display()

            # Connect team mode signals
            engine.substitution_made.connect(self._on_substitution_made)
            engine.player_eliminated.connect(self._on_player_eliminated)
            engine.game_ended.connect(self._on_game_ended)
        else:
            self.team_controls.setVisible(False)

    def _open_substitution_dialog(self, team: str) -> None:
        """Open the substitution dialog for a team."""
        if not self.scoring_engine or not self.scoring_engine.is_team_mode():
            return

        # Get team info
        if team == "home":
            team_name = self.scoring_engine._p1_name
        else:
            team_name = self.scoring_engine._p2_name

        queue_state = self.scoring_engine.get_queue_state(team)
        sub_info = self.scoring_engine.get_substitution_info(team)

        dialog = SubstitutionDialog(
            team_name=team_name,
            queue_state=queue_state,
            remaining_subs=sub_info["remaining"],
            parent=self,
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_substitution_data()

            # Generate a unique ID for the substitute
            # In real usage, this would come from a player database
            import time
            in_player_id = int(time.time() * 1000) % 100000

            success = self.scoring_engine.substitute_player(
                team=team,
                out_player_id=data["out_player_id"],
                in_player_id=in_player_id,
                in_player_name=data["in_player_name"],
            )

            if success:
                QMessageBox.information(
                    self,
                    "Substitution Complete",
                    f"Substitution made for {team_name}.\n\n"
                    f"IN: {data['in_player_name']}"
                )
                self._update_team_display()
            else:
                QMessageBox.warning(
                    self,
                    "Substitution Failed",
                    "Could not complete substitution. The selected player may be in the active position."
                )

    def _update_team_display(self) -> None:
        """Update team-specific display elements."""
        if not self.scoring_engine or not self.scoring_engine.is_team_mode():
            return

        # Update substitution counts
        home_info = self.scoring_engine.get_substitution_info("home")
        away_info = self.scoring_engine.get_substitution_info("away")

        self.home_sub_label.setText(
            f"{self.scoring_engine._p1_name}: {home_info['remaining']} subs remaining"
        )
        self.away_sub_label.setText(
            f"{self.scoring_engine._p2_name}: {away_info['remaining']} subs remaining"
        )

        # Update game info
        state = self.scoring_engine.get_score_state()
        self.game_label.setText(f"GAME {state.current_game} / {state.total_games}")
        self.elimination_label.setText(
            f"Eliminations: {self.scoring_engine._p1_name} {state.home_eliminations} - "
            f"{self.scoring_engine._p2_name} {state.away_eliminations}"
        )

        # Disable substitution buttons if no subs remaining
        self.btn_home_sub.setEnabled(home_info['remaining'] > 0)
        self.btn_away_sub.setEnabled(away_info['remaining'] > 0)

    @Slot(dict)
    def _on_substitution_made(self, data: dict) -> None:
        """Handle substitution signal from engine."""
        self._update_team_display()

    @Slot(int, int)
    def _on_player_eliminated(self, player_id: int, team_id: int) -> None:
        """Handle player elimination signal."""
        self._update_team_display()

    @Slot(int, str)
    def _on_game_ended(self, game_num: int, winner: str) -> None:
        """Handle end of a game in team mode."""
        if self.scoring_engine:
            winner_name = (self.scoring_engine._p1_name if winner == "home"
                          else self.scoring_engine._p2_name)
        else:
            winner_name = winner

        QMessageBox.information(
            self,
            f"Game {game_num} Complete",
            f"Game {game_num} winner: {winner_name}"
        )
        self._update_team_display()

    @Slot(dict)
    def _on_bout_submitted(self, data: dict) -> None:
        """
        Handle bout submission from the scoring panel.

        With ONE-CLICK recording, data contains:
        - result: BoutResult (OPA or OSHI)
        - winner_id: Player ID who won
        - loser_id: Player ID who lost
        """
        if not self.scoring_engine:
            QMessageBox.warning(
                self,
                "No Active Match",
                "No scoring engine is active. Please set up a match first."
            )
            return

        if not self.scoring_engine.can_record_bout:
            # Provide helpful feedback about why bout can't be recorded
            state = self.scoring_engine.state
            if state == MatchState.MATCH_ACTIVE or state == MatchState.ROUND_COMPLETE:
                QMessageBox.warning(
                    self,
                    "Round Not Started",
                    "Please click 'Start Round' before recording bouts."
                )
            elif state == MatchState.PAUSED:
                QMessageBox.warning(
                    self,
                    "Match Paused",
                    "The match is paused. Click 'Resume' to continue recording bouts."
                )
            elif state == MatchState.COMPLETED:
                QMessageBox.warning(
                    self,
                    "Match Completed",
                    "The match has already completed. No more bouts can be recorded."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Cannot Record Bout",
                    f"Cannot record bout in current state: {state.value}"
                )
            return

        result = data["result"]
        winner_id = data["winner_id"]
        loser_id = data["loser_id"]

        if self._is_team_mode:
            # Team mode: use record_team_bout so queues advance and AP/undo work correctly
            winning_team = "home" if winner_id == self.scoring_engine._p1_id else "away"
            time_ms = self.round_timer.remaining_ms if self.round_timer else 0
            self.scoring_engine.record_team_bout(result, winning_team, time_ms)
        else:
            # 1v1 mode: pass time remaining
            time_value = self.round_timer.remaining_ms if self.round_timer else 0
            self.scoring_engine.record_bout(result, winner_id, loser_id, time_value)
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

        if self._is_team_mode:
            # Team mode: Start elapsed time tracking (counts UP)
            import time
            self._round_start_time = time.time()
            self._start_elapsed_timer()
        elif self.round_timer:
            # 1v1 mode: Start countdown timer
            self.round_timer.start()

        # Update button states
        self.btn_start_round.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_end_round.setEnabled(True)

        # Clear bout log for new round
        self.bout_log.clear()

    def _start_elapsed_timer(self) -> None:
        """Start the elapsed time timer for team mode (ticks every second)."""
        if self._elapsed_timer_id is not None:
            self.killTimer(self._elapsed_timer_id)
        self._elapsed_timer_id = self.startTimer(1000)  # 1 second intervals

    def _stop_elapsed_timer(self) -> None:
        """Stop the elapsed time timer."""
        if self._elapsed_timer_id is not None:
            self.killTimer(self._elapsed_timer_id)
            self._elapsed_timer_id = None

    def timerEvent(self, event) -> None:
        """Handle elapsed timer ticks for team mode."""
        if self._is_team_mode and self._round_start_time is not None:
            import time
            elapsed = time.time() - self._round_start_time
            minutes = int(elapsed) // 60
            seconds = int(elapsed) % 60
            self.timer_label.setText(f"{minutes:02d}:{seconds:02d}")

    def _toggle_pause(self) -> None:
        """Toggle pause state."""
        if not self.scoring_engine:
            return

        if self.scoring_engine.state == MatchState.PAUSED:
            self.scoring_engine.resume()
            if self._is_team_mode:
                # Resume elapsed timer - adjust start time for pause duration
                import time
                if hasattr(self, '_pause_time') and self._pause_time:
                    pause_duration = time.time() - self._pause_time
                    self._round_start_time += pause_duration
                self._start_elapsed_timer()
            elif self.round_timer:
                self.round_timer.resume()
            self.btn_pause.setText("Pause")
        elif self.scoring_engine.state == MatchState.ROUND_ACTIVE:
            self.scoring_engine.pause()
            if self._is_team_mode:
                # Pause elapsed timer
                import time
                self._pause_time = time.time()
                self._stop_elapsed_timer()
            elif self.round_timer:
                self.round_timer.pause()
            self.btn_pause.setText("Resume")

    def _end_round(self) -> None:
        """End the current round."""
        if not self.scoring_engine:
            return

        if self.scoring_engine.state == MatchState.ROUND_ACTIVE:
            if self._is_team_mode:
                # Stop elapsed timer for team mode
                self._stop_elapsed_timer()
            elif self.round_timer:
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
            if self._is_team_mode:
                self._stop_elapsed_timer()
            elif self.round_timer:
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
                "font-size: 32pt; font-weight: bold; font-family: 'JetBrains Mono', monospace; color: #FF4444;"
            )
        elif remaining_ms < 30000:
            self.timer_label.setStyleSheet(
                "font-size: 32pt; font-weight: bold; font-family: 'JetBrains Mono', monospace; color: #FFB74D;"
            )
        else:
            self.timer_label.setStyleSheet(
                "font-size: 32pt; font-weight: bold; font-family: 'JetBrains Mono', monospace; color: #00CC00;"
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

        # Update team display if in team mode
        if self.scoring_engine and self.scoring_engine.is_team_mode():
            self._update_team_display()

    @Slot(dict)
    def _on_bout_logged(self, bout_data: dict) -> None:
        """Add bout to the log."""
        result = bout_data["result"].upper()
        winner_id = bout_data["winner_id"]

        # Get actual player/team name from scoring engine
        if self.scoring_engine:
            if self._is_team_mode and bout_data.get("winning_team"):
                winner_name = (self.scoring_engine._p1_name if bout_data["winning_team"] == "home"
                               else self.scoring_engine._p2_name)
            elif winner_id == self.scoring_engine._p1_id:
                winner_name = self.scoring_engine._p1_name
            else:
                winner_name = self.scoring_engine._p2_name
        else:
            winner_name = "P1" if winner_id == 1 else "P2"

        time_ms = bout_data.get("time_remaining_ms", 0)
        if self._is_team_mode:
            # Team mode: show elapsed time with @ prefix
            minutes = time_ms // 60000
            seconds = (time_ms % 60000) // 1000
            time_str = f"@{minutes}:{seconds:02d}" if time_ms else ""
        else:
            # 1v1 mode: show time remaining
            time_str = f"{time_ms // 1000}s left" if time_ms else ""

        item = QListWidgetItem(f"#{bout_data['bout']} {result} → {winner_name} ({time_str})")

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

        # Reset timer display based on mode
        if self._is_team_mode:
            # Team mode: reset to 00:00 for next round (elapsed timer)
            self._round_start_time = None
            self.timer_label.setText("00:00")
        else:
            # 1v1 mode: reset to 01:00 countdown
            self.timer_label.setText("01:00")
        self.timer_label.setStyleSheet(
            "font-size: 32pt; font-weight: bold; font-family: 'JetBrains Mono', monospace; color: #00CC00;"
        )

        # Show round result with actual player/team name
        if winner == "player1":
            winner_text = self.scoring_engine._p1_name if self.scoring_engine else "Player 1"
            winning_team = "home"
            losing_team = "away"
        elif winner == "player2":
            winner_text = self.scoring_engine._p2_name if self.scoring_engine else "Player 2"
            winning_team = "away"
            losing_team = "home"
        else:
            winner_text = "Tie"
            winning_team = None
            losing_team = None

        # Team mode: Show elimination dialog
        if self.scoring_engine and self.scoring_engine.is_team_mode() and winning_team:
            losing_team_name = (self.scoring_engine._p2_name if losing_team == "away"
                               else self.scoring_engine._p1_name)
            losing_queue = self.scoring_engine.get_queue_state(losing_team)

            if losing_queue:  # Only show if there are players to eliminate
                dialog = EliminationDialog(
                    winning_team=winning_team,
                    losing_team_name=losing_team_name,
                    losing_queue_state=losing_queue,
                    parent=self,
                )

                if dialog.exec() == QDialog.DialogCode.Accepted:
                    eliminated_id = dialog.get_eliminated_player_id()
                    eliminated_name = dialog.get_eliminated_player_name()

                    # Eliminate the player and get bonus AP
                    bonus_ap = self.scoring_engine.eliminate_player(eliminated_id, losing_team)

                    QMessageBox.information(
                        self,
                        f"Round {round_num} Complete",
                        f"Round winner: {winner_text}\n\n"
                        f"Eliminated: {eliminated_name}\n"
                        f"Bonus AP: +{bonus_ap}"
                    )
                else:
                    # Dialog was closed without selection - still need to show result
                    QMessageBox.information(
                        self,
                        f"Round {round_num} Complete",
                        f"Round winner: {winner_text}\n\n"
                        "(No elimination selected)"
                    )
            else:
                # No players left to eliminate
                QMessageBox.information(
                    self,
                    f"Round {round_num} Complete",
                    f"Round winner: {winner_text}"
                )
        else:
            # 1v1 mode or tie - simple message
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

        # Get actual player/team names
        p1_name = self.scoring_engine._p1_name if self.scoring_engine else "Player 1"
        p2_name = self.scoring_engine._p2_name if self.scoring_engine else "Player 2"

        if winner == "player1":
            winner_text = p1_name
        elif winner == "player2":
            winner_text = p2_name
        else:
            winner_text = "Tie"

        QMessageBox.information(
            self,
            "Match Complete",
            f"Winner: {winner_text}\n\nFinal Score:\n{p1_name}: {p1_ap} AP\n{p2_name}: {p2_ap} AP"
        )

        # Disable all controls
        self.btn_start_round.setEnabled(False)
        self.btn_pause.setEnabled(False)
        self.btn_end_round.setEnabled(False)
