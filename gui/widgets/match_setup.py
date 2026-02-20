"""
Match Setup Wizard

Multi-step form for configuring a new match:
1. Game Mode selection
2. Match Configuration (rounds, age category)
3. Players/Teams
4. Officials
5. Toss
"""

from typing import Optional, TYPE_CHECKING

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QSpinBox, QComboBox,
    QGroupBox, QRadioButton, QButtonGroup, QStackedWidget,
    QFormLayout, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, Signal

from services.event_bus import EventBus
from models.match import GameMode
from models.player import AgeCategory
from engine.scoring import ScoringEngine

if TYPE_CHECKING:
    from gui.main_window import MainWindow


class MatchSetupWidget(QWidget):
    """
    Match Setup Wizard - guides the Ampfre through match configuration.

    Steps:
    1. Select game mode (1v1, Team vs Team, Tournament)
    2. Configure match settings (rounds, age category)
    3. Enter player/team information
    4. Assign officials
    5. Record toss result
    """

    match_ready = Signal(object)  # Emits ScoringEngine when setup complete

    def __init__(self, event_bus: EventBus, main_window: "MainWindow"):
        super().__init__()
        self.event_bus = event_bus
        self.main_window = main_window

        # Setup state
        self.game_mode: Optional[GameMode] = None
        self.total_rounds = 5
        self.age_category: Optional[AgeCategory] = None

        # Player info
        self.player1_name = ""
        self.player2_name = ""

        # Toss info
        self.toss_winner = ""
        self.toss_choice = ""

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the setup wizard UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Title
        title = QLabel("Match Setup")
        title.setStyleSheet("font-size: 32px; font-weight: bold; color: #FCD116;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Step indicator
        self.step_indicator = QLabel("Step 1 of 5: Select Game Mode")
        self.step_indicator.setStyleSheet("font-size: 14px; color: #A0A0B0;")
        self.step_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.step_indicator)

        # Stacked widget for steps
        self.steps = QStackedWidget()
        layout.addWidget(self.steps)

        # Create step widgets
        self.steps.addWidget(self._create_step1_game_mode())
        self.steps.addWidget(self._create_step2_config())
        self.steps.addWidget(self._create_step3_players())
        self.steps.addWidget(self._create_step4_officials())
        self.steps.addWidget(self._create_step5_toss())

        # Navigation buttons
        nav_layout = QHBoxLayout()

        self.btn_back = QPushButton("◀ Back")
        self.btn_back.clicked.connect(self._go_back)
        self.btn_back.setEnabled(False)
        nav_layout.addWidget(self.btn_back)

        nav_layout.addStretch()

        self.btn_next = QPushButton("Next ▶")
        self.btn_next.clicked.connect(self._go_next)
        nav_layout.addWidget(self.btn_next)

        self.btn_start = QPushButton("Start Match ▶")
        self.btn_start.clicked.connect(self._start_match)
        self.btn_start.setVisible(False)
        self.btn_start.setStyleSheet(
            "background-color: #006B3F; font-size: 16px; padding: 15px 30px;"
        )
        nav_layout.addWidget(self.btn_start)

        layout.addLayout(nav_layout)

    def _create_step1_game_mode(self) -> QWidget:
        """Step 1: Game Mode Selection."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)

        label = QLabel("Select Game Mode")
        label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(label)

        # Mode buttons
        modes_layout = QHBoxLayout()
        modes_layout.setSpacing(20)

        self.mode_group = QButtonGroup(self)

        # 1v1 Mode
        btn_1v1 = self._create_mode_button(
            "1 vs 1",
            "Individual match\n5, 10, or 15 rounds\n60 seconds per round",
            GameMode.ONE_VS_ONE
        )
        btn_1v1.setChecked(True)
        self.game_mode = GameMode.ONE_VS_ONE
        modes_layout.addWidget(btn_1v1)

        # Team Mode
        btn_team = self._create_mode_button(
            "Team vs Team",
            "Shooter Mode\n3 games × 15 rounds\n15 players per team",
            GameMode.TEAM_VS_TEAM
        )
        modes_layout.addWidget(btn_team)

        # Tournament Mode
        btn_tournament = self._create_mode_button(
            "Tournament",
            "Bracket competition\nGroup stage to Finals\nMultiple teams",
            GameMode.TOURNAMENT
        )
        btn_tournament.setEnabled(False)  # Phase 4
        modes_layout.addWidget(btn_tournament)

        layout.addLayout(modes_layout)
        layout.addStretch()

        return widget

    def _create_mode_button(self, title: str, description: str, mode: GameMode) -> QRadioButton:
        """Create a styled radio button for mode selection."""
        btn = QRadioButton()
        btn.setStyleSheet("""
            QRadioButton {
                background-color: #16213E;
                border: 2px solid #333355;
                border-radius: 12px;
                padding: 20px;
                min-width: 200px;
                min-height: 120px;
            }
            QRadioButton:checked {
                border-color: #FCD116;
                background-color: #1A2744;
            }
            QRadioButton:hover {
                border-color: #555577;
            }
            QRadioButton::indicator {
                width: 0;
                height: 0;
            }
        """)

        # Create label layout inside
        container = QWidget()
        container_layout = QVBoxLayout(container)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #FCD116;")
        container_layout.addWidget(title_label)

        desc_label = QLabel(description)
        desc_label.setStyleSheet("font-size: 12px; color: #A0A0B0;")
        container_layout.addWidget(desc_label)

        self.mode_group.addButton(btn)
        btn.toggled.connect(lambda checked, m=mode: self._set_mode(m) if checked else None)

        return btn

    def _set_mode(self, mode: GameMode) -> None:
        """Set the selected game mode."""
        self.game_mode = mode

    def _create_step2_config(self) -> QWidget:
        """Step 2: Match Configuration."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)

        label = QLabel("Match Configuration")
        label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(label)

        form = QFormLayout()
        form.setSpacing(15)

        # Number of rounds
        self.rounds_combo = QComboBox()
        self.rounds_combo.addItems(["5 Rounds", "10 Rounds", "15 Rounds"])
        self.rounds_combo.currentIndexChanged.connect(self._update_rounds)
        form.addRow("Rounds:", self.rounds_combo)

        # Age category
        self.age_combo = QComboBox()
        for cat in AgeCategory:
            self.age_combo.addItem(cat.value, cat)
        self.age_combo.setCurrentIndex(2)  # Default to Young Adults (a)
        form.addRow("Age Category:", self.age_combo)

        layout.addLayout(form)
        layout.addStretch()

        return widget

    def _update_rounds(self, index: int) -> None:
        """Update rounds based on combo selection."""
        rounds_map = {0: 5, 1: 10, 2: 15}
        self.total_rounds = rounds_map.get(index, 5)

    def _create_step3_players(self) -> QWidget:
        """Step 3: Player/Team Entry."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)

        label = QLabel("Enter Player Information")
        label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(label)

        # Two-column layout for players
        players_layout = QHBoxLayout()
        players_layout.setSpacing(30)

        # Player 1
        p1_group = QGroupBox("Player 1 / Home")
        p1_layout = QFormLayout(p1_group)

        self.p1_name = QLineEdit()
        self.p1_name.setPlaceholderText("Enter player name")
        self.p1_name.textChanged.connect(lambda t: setattr(self, 'player1_name', t))
        p1_layout.addRow("Name:", self.p1_name)

        self.p1_jersey = QSpinBox()
        self.p1_jersey.setRange(1, 99)
        self.p1_jersey.setValue(1)
        p1_layout.addRow("Jersey #:", self.p1_jersey)

        players_layout.addWidget(p1_group)

        # VS label
        vs_label = QLabel("VS")
        vs_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #FCD116;")
        vs_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        players_layout.addWidget(vs_label)

        # Player 2
        p2_group = QGroupBox("Player 2 / Away")
        p2_layout = QFormLayout(p2_group)

        self.p2_name = QLineEdit()
        self.p2_name.setPlaceholderText("Enter player name")
        self.p2_name.textChanged.connect(lambda t: setattr(self, 'player2_name', t))
        p2_layout.addRow("Name:", self.p2_name)

        self.p2_jersey = QSpinBox()
        self.p2_jersey.setRange(1, 99)
        self.p2_jersey.setValue(2)
        p2_layout.addRow("Jersey #:", self.p2_jersey)

        players_layout.addWidget(p2_group)

        layout.addLayout(players_layout)
        layout.addStretch()

        return widget

    def _create_step4_officials(self) -> QWidget:
        """Step 4: Officials Assignment."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)

        label = QLabel("Assign Officials")
        label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(label)

        form = QFormLayout()
        form.setSpacing(10)

        self.official_master = QLineEdit()
        self.official_master.setPlaceholderText("Master Ampfre name")
        form.addRow("Master Ampfre:", self.official_master)

        self.official_caller = QLineEdit()
        self.official_caller.setPlaceholderText("Caller Ampfre name")
        form.addRow("Caller Ampfre:", self.official_caller)

        self.official_recorder1 = QLineEdit()
        self.official_recorder1.setPlaceholderText("Recorder 1 name")
        form.addRow("Recorder 1:", self.official_recorder1)

        self.official_recorder2 = QLineEdit()
        self.official_recorder2.setPlaceholderText("Recorder 2 name")
        form.addRow("Recorder 2:", self.official_recorder2)

        self.official_timer = QLineEdit()
        self.official_timer.setPlaceholderText("Timer name")
        form.addRow("Timer:", self.official_timer)

        self.official_counter = QLineEdit()
        self.official_counter.setPlaceholderText("Counter name")
        form.addRow("Counter:", self.official_counter)

        note = QLabel("(Officials are optional for demo mode)")
        note.setStyleSheet("color: #666; font-style: italic;")
        form.addRow("", note)

        layout.addLayout(form)
        layout.addStretch()

        return widget

    def _create_step5_toss(self) -> QWidget:
        """Step 5: Toss Result."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)

        label = QLabel("Record Toss Result")
        label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(label)

        # Toss winner
        winner_group = QGroupBox("Toss Winner")
        winner_layout = QHBoxLayout(winner_group)

        self.toss_winner_group = QButtonGroup(self)

        self.toss_p1 = QRadioButton("Player 1")
        self.toss_p1.setChecked(True)
        self.toss_winner_group.addButton(self.toss_p1)
        winner_layout.addWidget(self.toss_p1)

        self.toss_p2 = QRadioButton("Player 2")
        self.toss_winner_group.addButton(self.toss_p2)
        winner_layout.addWidget(self.toss_p2)

        layout.addWidget(winner_group)

        # Toss choice
        choice_group = QGroupBox("Winner's Choice")
        choice_layout = QHBoxLayout(choice_group)

        self.toss_choice_group = QButtonGroup(self)

        self.choice_opa = QRadioButton("Opa (Different Legs)")
        self.choice_opa.setChecked(True)
        self.choice_opa.setStyleSheet("color: #006B3F; font-weight: bold;")
        self.toss_choice_group.addButton(self.choice_opa)
        choice_layout.addWidget(self.choice_opa)

        self.choice_oshi = QRadioButton("Oshi (Same Legs)")
        self.choice_oshi.setStyleSheet("color: #CE1126; font-weight: bold;")
        self.toss_choice_group.addButton(self.choice_oshi)
        choice_layout.addWidget(self.choice_oshi)

        layout.addWidget(choice_group)

        # Summary
        self.summary_frame = QFrame()
        self.summary_frame.setStyleSheet("""
            QFrame {
                background-color: #16213E;
                border: 1px solid #333355;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        summary_layout = QVBoxLayout(self.summary_frame)

        summary_title = QLabel("Match Summary")
        summary_title.setStyleSheet("font-weight: bold; color: #FCD116;")
        summary_layout.addWidget(summary_title)

        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("color: #A0A0B0;")
        summary_layout.addWidget(self.summary_label)

        layout.addWidget(self.summary_frame)
        layout.addStretch()

        return widget

    def _go_back(self) -> None:
        """Go to previous step."""
        current = self.steps.currentIndex()
        if current > 0:
            self.steps.setCurrentIndex(current - 1)
            self._update_navigation()

    def _go_next(self) -> None:
        """Go to next step."""
        current = self.steps.currentIndex()

        # Validate current step
        if not self._validate_step(current):
            return

        if current < self.steps.count() - 1:
            self.steps.setCurrentIndex(current + 1)
            self._update_navigation()

            # Update summary on last step
            if current + 1 == self.steps.count() - 1:
                self._update_summary()

    def _validate_step(self, step: int) -> bool:
        """Validate the current step before proceeding."""
        if step == 2:  # Players step
            if not self.p1_name.text().strip() or not self.p2_name.text().strip():
                QMessageBox.warning(
                    self,
                    "Missing Information",
                    "Please enter names for both players."
                )
                return False
        return True

    def _update_navigation(self) -> None:
        """Update navigation button states."""
        current = self.steps.currentIndex()
        total = self.steps.count()

        self.btn_back.setEnabled(current > 0)
        self.btn_next.setVisible(current < total - 1)
        self.btn_start.setVisible(current == total - 1)

        # Update step indicator
        step_names = [
            "Select Game Mode",
            "Match Configuration",
            "Enter Players",
            "Assign Officials",
            "Toss & Start",
        ]
        self.step_indicator.setText(f"Step {current + 1} of {total}: {step_names[current]}")

    def _update_summary(self) -> None:
        """Update the match summary display."""
        mode_names = {
            GameMode.ONE_VS_ONE: "1 vs 1",
            GameMode.TEAM_VS_TEAM: "Team vs Team",
            GameMode.TOURNAMENT: "Tournament",
        }

        summary = f"""
Mode: {mode_names.get(self.game_mode, 'Unknown')}
Rounds: {self.total_rounds}
Age Category: {self.age_combo.currentText()}

Player 1: {self.p1_name.text() or 'Not set'}
Player 2: {self.p2_name.text() or 'Not set'}
        """
        self.summary_label.setText(summary.strip())

    def _start_match(self) -> None:
        """Create the scoring engine and start the match."""
        # Get player names
        p1_name = self.p1_name.text().strip() or "Player 1"
        p2_name = self.p2_name.text().strip() or "Player 2"

        # Create scoring engine
        engine = ScoringEngine(self.game_mode, self.total_rounds)
        engine.setup_1v1_match(
            player1_id=1,
            player1_name=p1_name,
            player2_id=2,
            player2_name=p2_name,
        )

        # Record toss
        engine._toss_winner = "player1" if self.toss_p1.isChecked() else "player2"
        engine._toss_choice = "opa" if self.choice_opa.isChecked() else "oshi"

        # Wire to main window
        self.main_window.set_scoring_engine(engine)

        # Start match
        engine.start_match()

        # Emit event and switch to scoring
        self.event_bus.match_created.emit({
            "mode": self.game_mode.value,
            "rounds": self.total_rounds,
            "player1": p1_name,
            "player2": p2_name,
        })

        self.main_window.start_match_scoring()

    def reset(self) -> None:
        """Reset the wizard to initial state."""
        self.steps.setCurrentIndex(0)
        self.p1_name.clear()
        self.p2_name.clear()
        self.rounds_combo.setCurrentIndex(0)
        self._update_navigation()
