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
    QFormLayout, QMessageBox, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, Signal

from services.event_bus import EventBus
from models.match import GameMode
from models.player import AgeCategory
from models.base import get_session
from engine.scoring import ScoringEngine
from engine.tournament_bracket import TournamentBracket

if TYPE_CHECKING:
    from gui.main_window import MainWindow

# Default player names for Team vs Team testing (15 per roster)
_DEFAULT_ROSTER_NAMES = [
    "Kofi", "Ama", "Yaw", "Abena", "Kwame", "Akua", "Kweku",
    "Adwoa", "Kojo", "Afia", "Yaa", "Kwesi", "Akosua", "Esi", "Kofi J.",
]


class TeamRosterWidget(QWidget):
    """
    Widget for entering a team's roster of 15 players.
    Shows team name input and a scrollable list of player name/jersey entries.
    """

    def __init__(self, team_label: str = "Team", color: str = "#2196F3", parent=None):
        super().__init__(parent)
        self.team_label = team_label
        self.color = color
        self.player_entries: list[tuple[QLineEdit, QSpinBox]] = []

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the roster entry UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Team name header
        header = QLabel(self.team_label)
        header.setStyleSheet(f"font-size: 14pt; font-weight: bold; color: {self.color};")
        layout.addWidget(header)

        # Team name input
        team_form = QFormLayout()
        self.team_name_input = QLineEdit()
        self.team_name_input.setPlaceholderText(f"Enter {self.team_label.lower()} name")
        team_form.addRow("Team Name:", self.team_name_input)
        layout.addLayout(team_form)

        # Scrollable player list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #333355;
                border-radius: 8px;
                background-color: #1C1C28;
            }
        """)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(5)

        # Default names for testing Team vs Team (15 per team; prefix by side)
        prefix = "H" if "Home" in self.team_label else "A"
        default_names = [
            f"{prefix}-{_DEFAULT_ROSTER_NAMES[i]}" if i < len(_DEFAULT_ROSTER_NAMES) else f"{prefix}-Player {i + 1}"
            for i in range(15)
        ]

        # Create 15 player entry rows
        for i in range(15):
            box_num = i + 1
            row = QHBoxLayout()

            # Box number label
            box_label = QLabel(f"Box {box_num:2d}:")
            box_label.setFixedWidth(60)
            box_label.setStyleSheet("color: #A0A0B0;")
            row.addWidget(box_label)

            # Player name (pre-filled with default for testing)
            name_input = QLineEdit()
            name_input.setPlaceholderText(f"Player {box_num} name")
            name_input.setText(default_names[i])
            row.addWidget(name_input)

            # Jersey number
            jersey_spin = QSpinBox()
            jersey_spin.setRange(1, 99)
            jersey_spin.setValue(box_num)
            jersey_spin.setFixedWidth(60)
            row.addWidget(jersey_spin)

            self.player_entries.append((name_input, jersey_spin))
            scroll_layout.addLayout(row)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

    def get_team_name(self) -> str:
        """Get the team name."""
        return self.team_name_input.text().strip()

    def get_roster(self) -> list[tuple[int, str]]:
        """
        Get the roster as a list of (player_id, player_name) tuples.
        Uses jersey number as player_id.
        """
        roster = []
        for name_input, jersey_spin in self.player_entries:
            name = name_input.text().strip()
            if name:
                roster.append((jersey_spin.value(), name))
        return roster

    def get_filled_count(self) -> int:
        """Get the number of filled player slots."""
        count = 0
        for name_input, _ in self.player_entries:
            if name_input.text().strip():
                count += 1
        return count

    def clear(self) -> None:
        """Clear all entries and reset to default test names."""
        self.team_name_input.clear()
        prefix = "H" if "Home" in self.team_label else "A"
        default_names = [
            f"{prefix}-{_DEFAULT_ROSTER_NAMES[i]}" if i < len(_DEFAULT_ROSTER_NAMES) else f"{prefix}-Player {i + 1}"
            for i in range(15)
        ]
        for i, (name_input, jersey_spin) in enumerate(self.player_entries):
            name_input.setText(default_names[i])
            jersey_spin.setValue(i + 1)


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

        # Player info (1v1 mode)
        self.player1_name = ""
        self.player2_name = ""

        # Team info (Team vs Team mode)
        self.home_roster_widget: Optional[TeamRosterWidget] = None
        self.away_roster_widget: Optional[TeamRosterWidget] = None

        # Tournament info
        self.tournament_bracket: Optional[TournamentBracket] = None
        self.tournament_teams: list[dict] = []  # [{"id": 1, "name": "Team A"}, ...]

        # Toss info
        self.toss_winner = ""
        self.toss_choice = ""

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the setup wizard UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(24)
        layout.setContentsMargins(24, 24, 24, 24)

        # Title
        title = QLabel("Match Setup")
        title.setObjectName("page_title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Step indicator
        self.step_indicator = QLabel("Step 1 of 5: Select Game Mode")
        self.step_indicator.setObjectName("hint_label")
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
            "background-color: #006B3F; font-size: 12pt; padding: 15px 30px;"
        )
        nav_layout.addWidget(self.btn_start)

        layout.addLayout(nav_layout)

    def _create_step1_game_mode(self) -> QWidget:
        """Step 1: Game Mode Selection."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)

        label = QLabel("Select Game Mode")
        label.setStyleSheet("font-size: 18pt; font-weight: bold;")
        layout.addWidget(label)

        # Mode buttons using clickable frames
        modes_layout = QHBoxLayout()
        modes_layout.setSpacing(20)

        self.mode_group = QButtonGroup(self)

        # 1v1 Mode
        frame_1v1, btn_1v1 = self._create_mode_card(
            "1 vs 1",
            "Individual match\n5, 10, or 15 rounds\n60 seconds per round",
            GameMode.ONE_VS_ONE
        )
        btn_1v1.setChecked(True)
        self.game_mode = GameMode.ONE_VS_ONE
        modes_layout.addWidget(frame_1v1)

        # Team Mode
        frame_team, btn_team = self._create_mode_card(
            "Team vs Team",
            "Shooter Mode\n3 games x 15 rounds\n15 players per team",
            GameMode.TEAM_VS_TEAM
        )
        modes_layout.addWidget(frame_team)

        # Tournament Mode
        frame_tournament, btn_tournament = self._create_mode_card(
            "Tournament",
            "Bracket competition\nGroup stage to Finals\n16 teams required",
            GameMode.TOURNAMENT,
            enabled=True
        )
        modes_layout.addWidget(frame_tournament)

        layout.addLayout(modes_layout)
        layout.addStretch()

        return widget

    def _create_mode_card(self, title: str, description: str, mode: GameMode,
                          enabled: bool = True) -> tuple[QFrame, QRadioButton]:
        """Create a clickable card for mode selection."""
        frame = QFrame()
        frame.setFixedSize(280, 160)
        frame.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ForbiddenCursor)

        # Style for the frame (theme-aligned)
        base_style = """
            QFrame {
                background-color: #1C1C28;
                border: 2px solid #3A3A4C;
                border-radius: 12px;
            }
            QFrame:hover {
                border-color: #4A4A5E;
            }
        """
        disabled_style = """
            QFrame {
                background-color: #12121A;
                border: 2px solid #2A2A38;
                border-radius: 12px;
            }
        """
        frame.setStyleSheet(base_style if enabled else disabled_style)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # Hidden radio button for selection tracking
        radio = QRadioButton()
        radio.setVisible(False)
        radio.setEnabled(enabled)
        self.mode_group.addButton(radio)
        radio.toggled.connect(lambda checked, m=mode, f=frame: self._on_mode_toggled(checked, m, f))
        layout.addWidget(radio)

        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"font-size: 18pt; font-weight: bold; color: {'#E8B923' if enabled else '#6A6A7A'};"
        )
        layout.addWidget(title_label)

        # Description
        desc_label = QLabel(description)
        desc_label.setStyleSheet(f"font-size: 11pt; color: {'#A0A0B0' if enabled else '#444444'};")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        layout.addStretch()

        # Make frame clickable
        if enabled:
            frame.mousePressEvent = lambda e, r=radio: r.setChecked(True)

        return frame, radio

    def _on_mode_toggled(self, checked: bool, mode: GameMode, frame: QFrame) -> None:
        """Handle mode selection toggle."""
        if checked:
            self.game_mode = mode
            # Update frame style to show selection
            frame.setStyleSheet("""
                QFrame {
                    background-color: #222230;
                    border: 3px solid #E8B923;
                    border-radius: 12px;
                }
            """)
        else:
            # Reset to default style
            frame.setStyleSheet("""
                QFrame {
                    background-color: #1C1C28;
                    border: 2px solid #3A3A4C;
                    border-radius: 12px;
                }
                QFrame:hover {
                    border-color: #555577;
                }
            """)

    def _create_step2_config(self) -> QWidget:
        """Step 2: Match Configuration."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)

        label = QLabel("Match Configuration")
        label.setStyleSheet("font-size: 13pt; font-weight: bold;")
        layout.addWidget(label)

        # Stacked widget for mode-specific configuration
        self.step2_stack = QStackedWidget()

        # Page 0: 1v1 Configuration
        onevsone_widget = QWidget()
        onevsone_layout = QVBoxLayout(onevsone_widget)
        onevsone_form = QFormLayout()
        onevsone_form.setSpacing(15)

        # Number of rounds (1v1 only)
        self.rounds_combo = QComboBox()
        self.rounds_combo.addItems(["5 Rounds", "10 Rounds", "15 Rounds"])
        self.rounds_combo.currentIndexChanged.connect(self._update_rounds)
        onevsone_form.addRow("Rounds:", self.rounds_combo)

        onevsone_layout.addLayout(onevsone_form)
        self.step2_stack.addWidget(onevsone_widget)

        # Page 1: Team vs Team Configuration (fixed format)
        team_widget = QWidget()
        team_layout = QVBoxLayout(team_widget)

        # Fixed format info
        format_frame = QFrame()
        format_frame.setStyleSheet("""
            QFrame {
                background-color: #1C1C28;
                border: 2px solid #E8B923;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        format_inner = QVBoxLayout(format_frame)

        format_title = QLabel("Shooter Mode Format")
        format_title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #E8B923;")
        format_inner.addWidget(format_title)

        format_details = QLabel(
            "• 3 Games per match\n"
            "• 15 Rounds per game\n"
            "• 15 Players per team\n"
            "• Max 5 substitutions per match\n"
            "• Round winner eliminates 1 opponent (+3 AP)\n"
            "• Endgame bonuses: +5/+10/+15 AP"
        )
        format_details.setStyleSheet("font-size: 10pt; color: #A0A0B0;")
        format_inner.addWidget(format_details)

        team_layout.addWidget(format_frame)
        team_layout.addStretch()
        self.step2_stack.addWidget(team_widget)

        # Page 2: Tournament Configuration
        tournament_widget = QWidget()
        tournament_layout = QVBoxLayout(tournament_widget)

        tournament_frame = QFrame()
        tournament_frame.setStyleSheet("""
            QFrame {
                background-color: #1C1C28;
                border: 2px solid #E8B923;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        tournament_inner = QVBoxLayout(tournament_frame)

        tournament_title = QLabel("Tournament Format")
        tournament_title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #E8B923;")
        tournament_inner.addWidget(tournament_title)

        tournament_details = QLabel(
            "• 16 Teams required\n"
            "• 4 Groups of 4 teams each\n"
            "• Round-robin group stage\n"
            "• Top 2 from each group advance\n"
            "• Knockout: R16 → QF → SF → Final\n"
            "• Head-to-head tiebreakers applied"
        )
        tournament_details.setStyleSheet("font-size: 10pt; color: #A0A0B0;")
        tournament_inner.addWidget(tournament_details)

        tournament_layout.addWidget(tournament_frame)
        tournament_layout.addStretch()
        self.step2_stack.addWidget(tournament_widget)

        layout.addWidget(self.step2_stack)

        # Age category (applies to both modes)
        shared_form = QFormLayout()
        shared_form.setSpacing(15)

        self.age_combo = QComboBox()
        for cat in AgeCategory:
            self.age_combo.addItem(cat.value, cat)
        self.age_combo.setCurrentIndex(2)  # Default to Young Adults (a)
        shared_form.addRow("Age Category:", self.age_combo)

        layout.addLayout(shared_form)
        layout.addStretch()

        return widget

    def _update_rounds(self, index: int) -> None:
        """Update rounds based on combo selection (1v1 mode only)."""
        rounds_map = {0: 5, 1: 10, 2: 15}
        self.total_rounds = rounds_map.get(index, 5)

    def _switch_step2_mode(self) -> None:
        """Switch step 2 UI based on game mode."""
        if self.game_mode == GameMode.TOURNAMENT:
            self.step2_stack.setCurrentIndex(2)  # Tournament format info
            self.total_rounds = 15  # Fixed 15 rounds per game in tournament mode
        elif self.game_mode == GameMode.TEAM_VS_TEAM:
            self.step2_stack.setCurrentIndex(1)  # Team format info
            self.total_rounds = 15  # Fixed 15 rounds per game in team mode
        else:
            self.step2_stack.setCurrentIndex(0)  # 1v1 rounds selector
            self._update_rounds(self.rounds_combo.currentIndex())

    def _create_step3_players(self) -> QWidget:
        """Step 3: Player/Team Entry - switches UI based on game mode."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)

        # Stacked widget to switch between 1v1 and team mode
        self.step3_stack = QStackedWidget()
        layout.addWidget(self.step3_stack)

        # Page 0: 1v1 Player Entry
        self.step3_stack.addWidget(self._create_1v1_player_entry())

        # Page 1: Team Roster Entry
        self.step3_stack.addWidget(self._create_team_roster_entry())

        # Page 2: Tournament Teams Entry
        self.step3_stack.addWidget(self._create_tournament_teams_entry())

        return widget

    def _create_1v1_player_entry(self) -> QWidget:
        """Create the 1v1 player entry UI."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)

        label = QLabel("Enter Player Information")
        label.setStyleSheet("font-size: 13pt; font-weight: bold;")
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
        vs_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #E8B923;")
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

    def _create_team_roster_entry(self) -> QWidget:
        """Create the Team vs Team roster entry UI."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)

        # Header
        header_layout = QHBoxLayout()
        label = QLabel("Enter Team Rosters")
        label.setStyleSheet("font-size: 13pt; font-weight: bold;")
        header_layout.addWidget(label)

        header_layout.addStretch()

        # Roster info
        info_label = QLabel("15 players per team required")
        info_label.setStyleSheet("color: #A0A0B0; font-style: italic;")
        header_layout.addWidget(info_label)

        layout.addLayout(header_layout)

        # Two-column layout for team rosters
        teams_layout = QHBoxLayout()
        teams_layout.setSpacing(20)

        # Home team roster
        self.home_roster_widget = TeamRosterWidget("Home Team", "#2196F3")
        teams_layout.addWidget(self.home_roster_widget)

        # VS separator
        vs_frame = QFrame()
        vs_frame.setFixedWidth(50)
        vs_layout = QVBoxLayout(vs_frame)
        vs_layout.addStretch()
        vs_label = QLabel("VS")
        vs_label.setStyleSheet("font-size: 18pt; font-weight: bold; color: #E8B923;")
        vs_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vs_layout.addWidget(vs_label)
        vs_layout.addStretch()
        teams_layout.addWidget(vs_frame)

        # Away team roster
        self.away_roster_widget = TeamRosterWidget("Away Team", "#FF5722")
        teams_layout.addWidget(self.away_roster_widget)

        layout.addLayout(teams_layout)

        return widget

    def _create_tournament_teams_entry(self) -> QWidget:
        """Create the Tournament teams entry UI (16 teams)."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)

        # Header
        header_layout = QHBoxLayout()
        label = QLabel("Enter Tournament Teams")
        label.setStyleSheet("font-size: 13pt; font-weight: bold;")
        header_layout.addWidget(label)

        header_layout.addStretch()

        info_label = QLabel("16 teams required (4 groups × 4 teams)")
        info_label.setStyleSheet("color: #A0A0B0; font-style: italic;")
        header_layout.addWidget(info_label)

        layout.addLayout(header_layout)

        # Scrollable team list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #333355;
                border-radius: 8px;
                background-color: #1C1C28;
            }
        """)

        scroll_content = QWidget()
        scroll_layout = QGridLayout(scroll_content)
        scroll_layout.setSpacing(10)

        # Store team name inputs
        self.tournament_team_inputs: list[QLineEdit] = []

        # Create 16 team entry rows in a 2-column grid
        default_team_names = [
            "Lions FC", "Eagles United", "Thunder SC", "Phoenix FC",
            "Dragons AC", "Wolves FC", "Tigers SC", "Panthers United",
            "Hawks FC", "Falcons SC", "Cobras United", "Vipers FC",
            "Sharks SC", "Dolphins FC", "Stallions United", "Bulls FC"
        ]

        for i in range(16):
            row = i % 8
            col = i // 8

            # Container for each team entry
            team_container = QHBoxLayout()

            # Seed number
            seed_label = QLabel(f"#{i + 1:2d}")
            seed_label.setFixedWidth(30)
            seed_label.setStyleSheet("color: #E8B923; font-weight: bold;")
            team_container.addWidget(seed_label)

            # Team name input
            name_input = QLineEdit()
            name_input.setPlaceholderText(f"Team {i + 1} name")
            name_input.setText(default_team_names[i])
            team_container.addWidget(name_input)

            self.tournament_team_inputs.append(name_input)

            # Add to grid
            container_widget = QWidget()
            container_widget.setLayout(team_container)
            scroll_layout.addWidget(container_widget, row, col)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Group preview
        preview_label = QLabel("Teams will be seeded into 4 groups using serpentine seeding")
        preview_label.setStyleSheet("color: #A0A0B0; font-style: italic;")
        layout.addWidget(preview_label)

        return widget

    def _create_step4_officials(self) -> QWidget:
        """Step 4: Officials Assignment."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)

        label = QLabel("Assign Officials")
        label.setStyleSheet("font-size: 13pt; font-weight: bold;")
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
        """Step 5: Toss Result - Recording the outcome of the physical toss."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)

        # Header
        label = QLabel("Record Toss Result")
        label.setStyleSheet("font-size: 13pt; font-weight: bold;")
        layout.addWidget(label)

        # Instructions - toss must happen physically
        instruction_frame = QFrame()
        instruction_frame.setStyleSheet("""
            QFrame {
                background-color: #1A2744;
                border: 2px solid #E8B923;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        instruction_layout = QVBoxLayout(instruction_frame)

        instruction_icon = QLabel("CONDUCT TOSS NOW")
        instruction_icon.setStyleSheet("font-size: 12pt; font-weight: bold; color: #E8B923;")
        instruction_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instruction_layout.addWidget(instruction_icon)

        instruction_text = QLabel(
            "The Master Ampfre must conduct the coin toss on the court before proceeding.\n"
            "After the toss is complete, record the result below."
        )
        instruction_text.setStyleSheet("font-size: 10pt; color: #A0A0B0;")
        instruction_text.setWordWrap(True)
        instruction_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instruction_layout.addWidget(instruction_text)

        layout.addWidget(instruction_frame)

        # Step 1: Record who won the toss
        winner_group = QGroupBox("Step 1: Who Won the Toss?")
        winner_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        winner_layout = QHBoxLayout(winner_group)

        self.toss_winner_group = QButtonGroup(self)

        self.toss_p1 = QRadioButton("Player 1")
        self.toss_p1.setChecked(False)  # No default - Ampfre must explicitly select
        self.toss_winner_group.addButton(self.toss_p1)
        winner_layout.addWidget(self.toss_p1)

        self.toss_p2 = QRadioButton("Player 2")
        self.toss_winner_group.addButton(self.toss_p2)
        winner_layout.addWidget(self.toss_p2)

        layout.addWidget(winner_group)

        # Step 2: Record winner's choice
        choice_group = QGroupBox("Step 2: Winner's Choice (Opa or Oshi)")
        choice_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        choice_layout = QVBoxLayout(choice_group)

        choice_info = QLabel("The toss winner chooses their preferred stance for the first round:")
        choice_info.setStyleSheet("font-size: 9pt; color: #A0A0B0;")
        choice_layout.addWidget(choice_info)

        choice_buttons = QHBoxLayout()

        self.toss_choice_group = QButtonGroup(self)

        self.choice_opa = QRadioButton("OPA (Different Legs)")
        self.choice_opa.setChecked(False)  # No default - Ampfre must explicitly select
        self.choice_opa.setStyleSheet("color: #006B3F; font-weight: bold; font-size: 11pt;")
        self.toss_choice_group.addButton(self.choice_opa)
        choice_buttons.addWidget(self.choice_opa)

        self.choice_oshi = QRadioButton("OSHI (Same Legs)")
        self.choice_oshi.setStyleSheet("color: #CE1126; font-weight: bold; font-size: 11pt;")
        self.toss_choice_group.addButton(self.choice_oshi)
        choice_buttons.addWidget(self.choice_oshi)

        choice_layout.addLayout(choice_buttons)
        layout.addWidget(choice_group)

        # Match Summary
        self.summary_frame = QFrame()
        self.summary_frame.setStyleSheet("""
            QFrame {
                background-color: #1C1C28;
                border: 1px solid #333355;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        summary_layout = QVBoxLayout(self.summary_frame)

        summary_title = QLabel("Match Summary")
        summary_title.setStyleSheet("font-weight: bold; color: #E8B923;")
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
            # Before moving to step 2, switch the config UI based on game mode
            if current == 0:  # About to enter step 2 (match configuration)
                self._switch_step2_mode()

            # Before moving to step 3, switch the UI based on game mode
            if current == 1:  # About to enter step 3 (players/teams)
                self._switch_step3_mode()

            self.steps.setCurrentIndex(current + 1)
            self._update_navigation()

            # Update summary and toss labels on last step
            if current + 1 == self.steps.count() - 1:
                self._update_summary()
                self._update_toss_labels()
                # Update button text for tournament mode
                if self.game_mode == GameMode.TOURNAMENT:
                    self.btn_start.setText("Create Tournament ▶")
                else:
                    self.btn_start.setText("Start Match ▶")

    def _switch_step3_mode(self) -> None:
        """Switch step 3 UI between 1v1, team, and tournament mode."""
        if self.game_mode == GameMode.TOURNAMENT:
            self.step3_stack.setCurrentIndex(2)  # Tournament teams entry
        elif self.game_mode == GameMode.TEAM_VS_TEAM:
            self.step3_stack.setCurrentIndex(1)  # Team roster entry
        else:
            self.step3_stack.setCurrentIndex(0)  # 1v1 player entry

    def _validate_step(self, step: int) -> bool:
        """Validate the current step before proceeding."""
        if step == 2:  # Players/Teams step
            if self.game_mode == GameMode.TOURNAMENT:
                # Validate tournament teams
                filled_teams = [
                    inp.text().strip()
                    for inp in self.tournament_team_inputs
                    if inp.text().strip()
                ]
                if len(filled_teams) < 16:
                    QMessageBox.warning(
                        self,
                        "Incomplete Teams",
                        f"Tournament requires 16 teams.\n\n"
                        f"Currently entered: {len(filled_teams)}/16 teams"
                    )
                    return False
                # Check for duplicate names
                if len(filled_teams) != len(set(filled_teams)):
                    QMessageBox.warning(
                        self,
                        "Duplicate Names",
                        "Each team must have a unique name."
                    )
                    return False
            elif self.game_mode == GameMode.TEAM_VS_TEAM:
                # Validate team rosters
                if not self.home_roster_widget or not self.away_roster_widget:
                    return False

                home_name = self.home_roster_widget.get_team_name()
                away_name = self.away_roster_widget.get_team_name()

                if not home_name or not away_name:
                    QMessageBox.warning(
                        self,
                        "Missing Information",
                        "Please enter names for both teams."
                    )
                    return False

                home_count = self.home_roster_widget.get_filled_count()
                away_count = self.away_roster_widget.get_filled_count()

                if home_count < 15 or away_count < 15:
                    QMessageBox.warning(
                        self,
                        "Incomplete Rosters",
                        f"Each team requires 15 players.\n\n"
                        f"Home team: {home_count}/15 players\n"
                        f"Away team: {away_count}/15 players"
                    )
                    return False
            else:
                # Validate 1v1 players
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

        if self.game_mode == GameMode.TOURNAMENT:
            team_count = sum(1 for inp in self.tournament_team_inputs if inp.text().strip())
            team_names = [inp.text().strip() for inp in self.tournament_team_inputs[:4] if inp.text().strip()]
            preview = ", ".join(team_names) + "..." if len(team_names) >= 4 else ", ".join(team_names)

            summary = f"""
Mode: {mode_names.get(self.game_mode, 'Unknown')}
Format: 4 Groups → Knockout (R16 → QF → SF → Final)
Age Category: {self.age_combo.currentText()}

Teams: {team_count}/16 registered
Preview: {preview}

Note: Toss is conducted before each individual match.
            """
        elif self.game_mode == GameMode.TEAM_VS_TEAM:
            home_name = self.home_roster_widget.get_team_name() if self.home_roster_widget else "Not set"
            away_name = self.away_roster_widget.get_team_name() if self.away_roster_widget else "Not set"
            home_count = self.home_roster_widget.get_filled_count() if self.home_roster_widget else 0
            away_count = self.away_roster_widget.get_filled_count() if self.away_roster_widget else 0

            summary = f"""
Mode: {mode_names.get(self.game_mode, 'Unknown')}
Format: 3 Games × 15 Rounds (Shooter Mode)
Age Category: {self.age_combo.currentText()}

Home Team: {home_name} ({home_count} players)
Away Team: {away_name} ({away_count} players)
            """
        else:
            summary = f"""
Mode: {mode_names.get(self.game_mode, 'Unknown')}
Rounds: {self.total_rounds}
Age Category: {self.age_combo.currentText()}

Player 1: {self.p1_name.text() or 'Not set'}
Player 2: {self.p2_name.text() or 'Not set'}
            """
        self.summary_label.setText(summary.strip())

    def _update_toss_labels(self) -> None:
        """Update toss step labels based on game mode."""
        if self.game_mode == GameMode.TOURNAMENT:
            # Tournament mode - toss is per match, not at setup
            self.toss_p1.setText("N/A (Per-Match)")
            self.toss_p2.setText("N/A (Per-Match)")
            self.toss_p1.setEnabled(False)
            self.toss_p2.setEnabled(False)
            self.choice_opa.setEnabled(False)
            self.choice_oshi.setEnabled(False)
        elif self.game_mode == GameMode.TEAM_VS_TEAM:
            home_name = self.home_roster_widget.get_team_name() if self.home_roster_widget else "Home Team"
            away_name = self.away_roster_widget.get_team_name() if self.away_roster_widget else "Away Team"
            self.toss_p1.setText(home_name or "Home Team")
            self.toss_p2.setText(away_name or "Away Team")
            self.toss_p1.setEnabled(True)
            self.toss_p2.setEnabled(True)
            self.choice_opa.setEnabled(True)
            self.choice_oshi.setEnabled(True)
        else:
            p1_name = self.p1_name.text().strip() or "Player 1"
            p2_name = self.p2_name.text().strip() or "Player 2"
            self.toss_p1.setText(p1_name)
            self.toss_p2.setText(p2_name)
            self.toss_p1.setEnabled(True)
            self.toss_p2.setEnabled(True)
            self.choice_opa.setEnabled(True)
            self.choice_oshi.setEnabled(True)

    def _start_match(self) -> None:
        """Create the scoring engine and start the match."""
        # Tournament mode has different flow
        if self.game_mode == GameMode.TOURNAMENT:
            self._start_tournament()
            return

        # Validate toss has been recorded (not needed for tournament)
        toss_winner_selected = self.toss_p1.isChecked() or self.toss_p2.isChecked()
        toss_choice_selected = self.choice_opa.isChecked() or self.choice_oshi.isChecked()

        if not toss_winner_selected:
            QMessageBox.warning(
                self,
                "Toss Not Recorded",
                "Please conduct the toss and record who won.\n\n"
                "Select the toss winner before starting the match."
            )
            return

        if not toss_choice_selected:
            QMessageBox.warning(
                self,
                "Choice Not Recorded",
                "Please record the toss winner's choice (Opa or Oshi).\n\n"
                "The winner must choose their preferred stance."
            )
            return

        # Create scoring engine
        engine = ScoringEngine(self.game_mode, self.total_rounds)

        if self.game_mode == GameMode.TEAM_VS_TEAM:
            # Team vs Team mode
            home_name = self.home_roster_widget.get_team_name()
            away_name = self.away_roster_widget.get_team_name()
            home_roster = self.home_roster_widget.get_roster()
            away_roster = self.away_roster_widget.get_roster()

            engine.setup_team_match(
                home_team_id=1,
                home_team_name=home_name,
                home_roster=home_roster,
                away_team_id=2,
                away_team_name=away_name,
                away_roster=away_roster,
            )

            # Record toss
            engine._toss_winner = "home" if self.toss_p1.isChecked() else "away"
            engine._toss_choice = "opa" if self.choice_opa.isChecked() else "oshi"

            # Emit event
            self.event_bus.match_created.emit({
                "mode": self.game_mode.value,
                "rounds": self.total_rounds,
                "home_team": home_name,
                "away_team": away_name,
                "home_roster_size": len(home_roster),
                "away_roster_size": len(away_roster),
            })
        else:
            # 1v1 mode
            p1_name = self.p1_name.text().strip() or "Player 1"
            p2_name = self.p2_name.text().strip() or "Player 2"

            engine.setup_1v1_match(
                player1_id=1,
                player1_name=p1_name,
                player2_id=2,
                player2_name=p2_name,
            )

            # Record toss
            engine._toss_winner = "player1" if self.toss_p1.isChecked() else "player2"
            engine._toss_choice = "opa" if self.choice_opa.isChecked() else "oshi"

            # Emit event
            self.event_bus.match_created.emit({
                "mode": self.game_mode.value,
                "rounds": self.total_rounds,
                "player1": p1_name,
                "player2": p2_name,
            })

        # Wire to main window
        self.main_window.set_scoring_engine(engine)

        # Start match
        engine.start_match()

        self.main_window.start_match_scoring()

    def _start_tournament(self) -> None:
        """Create and start a tournament."""
        # Collect team data
        teams = []
        for i, inp in enumerate(self.tournament_team_inputs):
            name = inp.text().strip()
            if name:
                teams.append({"id": i + 1, "name": name})

        if len(teams) != 16:
            QMessageBox.warning(
                self,
                "Incomplete Teams",
                f"Tournament requires exactly 16 teams.\n"
                f"Currently entered: {len(teams)}/16"
            )
            return

        # Create tournament bracket
        self.tournament_bracket = TournamentBracket()
        self.tournament_bracket.initialize_tournament(
            teams=teams,
            num_groups=4,
            teams_per_group=4
        )

        # Save to database
        try:
            with get_session() as session:
                from models.tournament import Tournament as TournamentModel

                # Create tournament record
                tournament = TournamentModel(
                    name=f"Tournament {len(teams)} Teams",
                    num_groups=4,
                    teams_per_group=4,
                    team_count=16,
                )
                session.add(tournament)
                session.flush()

                # Update bracket with tournament ID
                self.tournament_bracket.tournament_id = tournament.id

                # Save bracket state
                tournament.update_from_bracket(self.tournament_bracket)
                session.commit()

        except Exception as e:
            QMessageBox.warning(
                self,
                "Database Error",
                f"Failed to save tournament: {e}\n\n"
                "Tournament will continue without persistence."
            )

        # Emit event
        self.event_bus.match_created.emit({
            "mode": GameMode.TOURNAMENT.value,
            "tournament_id": self.tournament_bracket.tournament_id,
            "team_count": len(teams),
            "groups": 4,
        })

        # Navigate to tournament bracket view
        self.main_window.set_tournament_bracket(self.tournament_bracket)
        self.main_window.show_tournament_view()

    def reset(self) -> None:
        """Reset the wizard to initial state."""
        self.steps.setCurrentIndex(0)

        # Reset 1v1 fields
        self.p1_name.clear()
        self.p2_name.clear()
        self.rounds_combo.setCurrentIndex(0)

        # Reset team roster widgets
        if self.home_roster_widget:
            self.home_roster_widget.clear()
        if self.away_roster_widget:
            self.away_roster_widget.clear()

        # Reset tournament team inputs with default names
        if hasattr(self, 'tournament_team_inputs'):
            default_team_names = [
                "Lions FC", "Eagles United", "Thunder SC", "Phoenix FC",
                "Dragons AC", "Wolves FC", "Tigers SC", "Panthers United",
                "Hawks FC", "Falcons SC", "Cobras United", "Vipers FC",
                "Sharks SC", "Dolphins FC", "Stallions United", "Bulls FC"
            ]
            for i, inp in enumerate(self.tournament_team_inputs):
                inp.setText(default_team_names[i])

        # Reset tournament state
        self.tournament_bracket = None
        self.tournament_teams = []

        # Reset step stacks to default (1v1 mode)
        self.step2_stack.setCurrentIndex(0)
        self.step3_stack.setCurrentIndex(0)

        self._update_navigation()
