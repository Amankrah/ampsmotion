"""
Tournament Bracket Visualization Widget

Visual bracket display showing group stage tables and knockout bracket tree.
"""

from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QScrollArea, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QFont

from gui.styles.theme import (
    SURFACE_CARD, SURFACE_ELEVATED, SURFACE_MAIN,
    BORDER_DEFAULT, BORDER_ACCENT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    PRIMARY_GOLD, PRIMARY_GREEN, PRIMARY_RED,
    TEAM_HOME, TEAM_AWAY,
    SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_SM, RADIUS_MD,
    FONT_SIZE_SM, FONT_SIZE_BASE, FONT_SIZE_LG, FONT_SIZE_XL,
)


class MatchCard(QFrame):
    """A single match card in the bracket."""

    clicked = Signal(str)  # match_id

    def __init__(
        self,
        match_id: str,
        team1_name: str = "TBD",
        team2_name: str = "TBD",
        team1_score: Optional[int] = None,
        team2_score: Optional[int] = None,
        is_complete: bool = False,
        winner_team: int = 0,  # 1 or 2
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.match_id = match_id

        self.setFixedSize(180, 70)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {SURFACE_CARD};
                border: 1px solid {BORDER_DEFAULT};
                border-radius: {RADIUS_SM}px;
            }}
            QFrame:hover {{
                background-color: {SURFACE_ELEVATED};
                border-color: {BORDER_ACCENT};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)
        layout.setSpacing(2)

        # Team 1 row
        team1_row = QHBoxLayout()
        team1_label = QLabel(team1_name[:15] + "..." if len(team1_name) > 15 else team1_name)
        team1_label.setStyleSheet(f"""
            color: {PRIMARY_GOLD if winner_team == 1 else TEXT_PRIMARY};
            font-size: {FONT_SIZE_BASE}pt;
            font-weight: {'bold' if winner_team == 1 else 'normal'};
        """)
        team1_score_label = QLabel(str(team1_score) if team1_score is not None else "-")
        team1_score_label.setStyleSheet(f"""
            color: {PRIMARY_GOLD if winner_team == 1 else TEXT_SECONDARY};
            font-size: {FONT_SIZE_BASE}pt;
            font-weight: bold;
        """)
        team1_row.addWidget(team1_label, 1)
        team1_row.addWidget(team1_score_label)

        # Team 2 row
        team2_row = QHBoxLayout()
        team2_label = QLabel(team2_name[:15] + "..." if len(team2_name) > 15 else team2_name)
        team2_label.setStyleSheet(f"""
            color: {PRIMARY_GOLD if winner_team == 2 else TEXT_PRIMARY};
            font-size: {FONT_SIZE_BASE}pt;
            font-weight: {'bold' if winner_team == 2 else 'normal'};
        """)
        team2_score_label = QLabel(str(team2_score) if team2_score is not None else "-")
        team2_score_label.setStyleSheet(f"""
            color: {PRIMARY_GOLD if winner_team == 2 else TEXT_SECONDARY};
            font-size: {FONT_SIZE_BASE}pt;
            font-weight: bold;
        """)
        team2_row.addWidget(team2_label, 1)
        team2_row.addWidget(team2_score_label)

        layout.addLayout(team1_row)
        layout.addWidget(self._create_separator())
        layout.addLayout(team2_row)

    def _create_separator(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background-color: {BORDER_DEFAULT};")
        line.setFixedHeight(1)
        return line

    def mousePressEvent(self, event):
        self.clicked.emit(self.match_id)
        super().mousePressEvent(event)


class GroupTable(QWidget):
    """Group standings table."""

    def __init__(self, group_name: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.group_name = group_name

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_SM)

        # Group header
        header = QLabel(f"Group {group_name}")
        header.setStyleSheet(f"""
            color: {PRIMARY_GOLD};
            font-size: {FONT_SIZE_LG}pt;
            font-weight: bold;
            padding: {SPACING_SM}px;
        """)
        layout.addWidget(header)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Team", "P", "W", "L", "AP+", "AP-", "Pts"
        ])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        for i in range(1, 7):
            self.table.horizontalHeader().setSectionResizeMode(
                i, QHeaderView.ResizeMode.Fixed
            )
            self.table.setColumnWidth(i, 45)

        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {SURFACE_CARD};
                border: 1px solid {BORDER_DEFAULT};
                border-radius: {RADIUS_SM}px;
                gridline-color: {BORDER_DEFAULT};
            }}
            QTableWidget::item {{
                color: {TEXT_PRIMARY};
                padding: {SPACING_SM}px;
            }}
            QTableWidget::item:selected {{
                background-color: {SURFACE_ELEVATED};
            }}
            QHeaderView::section {{
                background-color: {SURFACE_ELEVATED};
                color: {TEXT_SECONDARY};
                padding: {SPACING_SM}px;
                border: none;
                font-weight: bold;
            }}
        """)

        layout.addWidget(self.table)

    def update_standings(self, standings: list[dict]) -> None:
        """Update the table with standings data."""
        self.table.setRowCount(len(standings))

        for row, standing in enumerate(standings):
            self.table.setItem(row, 0, QTableWidgetItem(standing.get("team_name", "")))
            self.table.setItem(row, 1, QTableWidgetItem(str(standing.get("played", 0))))
            self.table.setItem(row, 2, QTableWidgetItem(str(standing.get("wins", 0))))
            self.table.setItem(row, 3, QTableWidgetItem(str(standing.get("losses", 0))))
            self.table.setItem(row, 4, QTableWidgetItem(str(standing.get("ap_scored", 0))))
            self.table.setItem(row, 5, QTableWidgetItem(str(standing.get("ap_conceded", 0))))
            self.table.setItem(row, 6, QTableWidgetItem(str(standing.get("points", 0))))

            # Highlight top 2 (qualifiers)
            if row < 2:
                for col in range(7):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(QColor(PRIMARY_GREEN).darker(200))


class KnockoutBracketWidget(QWidget):
    """Visual bracket tree for knockout stages."""

    match_selected = Signal(str)  # match_id

    STAGE_NAMES = {
        "round_of_16": "Round of 16",
        "quarter_final": "Quarter-Finals",
        "semi_final": "Semi-Finals",
        "final": "Final",
    }

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.matches: dict[str, list[dict]] = {}

        self.setMinimumSize(900, 600)

    def update_bracket(self, knockout_data: dict) -> None:
        """Update bracket with knockout stage data."""
        self.matches = knockout_data
        self.update()

    def paintEvent(self, event):
        """Draw the bracket with connecting lines."""
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw connecting lines between stages
        pen = QPen(QColor(BORDER_DEFAULT))
        pen.setWidth(2)
        painter.setPen(pen)

        # Calculate positions
        stages = ["round_of_16", "quarter_final", "semi_final", "final"]
        stage_counts = [8, 4, 2, 1]

        width = self.width()
        height = self.height()

        x_positions = []
        for i, stage in enumerate(stages):
            x = int(50 + (width - 280) * i / (len(stages) - 1) if len(stages) > 1 else width // 2)
            x_positions.append(x)

        # Draw horizontal lines connecting matches
        for stage_idx in range(len(stages) - 1):
            stage = stages[stage_idx]
            count = stage_counts[stage_idx]

            for match_idx in range(count):
                # Calculate y positions
                y_spacing = height / (count + 1)
                y1 = int(y_spacing * (match_idx + 1))

                # Next stage match
                next_count = stage_counts[stage_idx + 1]
                next_y_spacing = height / (next_count + 1)
                next_match_idx = match_idx // 2
                y2 = int(next_y_spacing * (next_match_idx + 1))

                x1 = x_positions[stage_idx] + 180
                x2 = x_positions[stage_idx + 1]

                # Draw horizontal line from match
                mid_x = (x1 + x2) // 2
                painter.drawLine(x1, y1, mid_x, y1)

                # Draw vertical connector
                if match_idx % 2 == 0:
                    # Top match of pair
                    painter.drawLine(mid_x, y1, mid_x, y2)
                else:
                    # Bottom match of pair - connect up
                    prev_y = int(y_spacing * match_idx)
                    painter.drawLine(mid_x, prev_y, mid_x, y1)

                # Draw line to next match
                painter.drawLine(mid_x, y2, x2, y2)

        painter.end()

        # Draw match cards using layout
        self._draw_match_cards()

    def _draw_match_cards(self) -> None:
        """Position and draw match cards."""
        # Clear existing cards
        for child in self.findChildren(MatchCard):
            child.deleteLater()

        stages = ["round_of_16", "quarter_final", "semi_final", "final"]
        stage_counts = [8, 4, 2, 1]

        width = self.width()
        height = self.height()

        for stage_idx, stage in enumerate(stages):
            count = stage_counts[stage_idx]
            matches = self.matches.get(stage, [])

            x = int(50 + (width - 280) * stage_idx / (len(stages) - 1) if len(stages) > 1 else width // 2)
            y_spacing = height / (count + 1)

            for match_idx in range(count):
                y = int(y_spacing * (match_idx + 1)) - 35  # Center vertically

                if match_idx < len(matches):
                    match = matches[match_idx]
                    team1 = match.get("team1", {})
                    team2 = match.get("team2", {})

                    winner = 0
                    if match.get("is_complete"):
                        winner = 1 if team1.get("is_winner") else (2 if team2.get("is_winner") else 0)

                    card = MatchCard(
                        match_id=match.get("match_id", ""),
                        team1_name=team1.get("name") or "TBD",
                        team2_name=team2.get("name") or "TBD",
                        team1_score=match.get("home_score") if match.get("is_complete") else None,
                        team2_score=match.get("away_score") if match.get("is_complete") else None,
                        is_complete=match.get("is_complete", False),
                        winner_team=winner,
                        parent=self
                    )
                else:
                    card = MatchCard(
                        match_id=f"{stage}_{match_idx}",
                        parent=self
                    )

                card.clicked.connect(self.match_selected.emit)
                card.move(x, y)
                card.show()


class TournamentBracketWidget(QWidget):
    """
    Main tournament bracket widget with tabs for groups and knockout.

    Usage:
        widget = TournamentBracketWidget()
        widget.update_bracket(bracket_data)
    """

    match_selected = Signal(str)  # match_id

    def __init__(self, event_bus=None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.event_bus = event_bus

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        layout.setSpacing(SPACING_MD)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("Tournament Bracket")
        title.setStyleSheet(f"""
            color: {TEXT_PRIMARY};
            font-size: {FONT_SIZE_XL}pt;
            font-weight: bold;
        """)
        header_layout.addWidget(title)

        self.stage_label = QLabel("Group Stage")
        self.stage_label.setStyleSheet(f"""
            color: {PRIMARY_GOLD};
            font-size: {FONT_SIZE_LG}pt;
            padding: {SPACING_SM}px {SPACING_MD}px;
            background-color: {SURFACE_CARD};
            border-radius: {RADIUS_SM}px;
        """)
        header_layout.addStretch()
        header_layout.addWidget(self.stage_label)

        layout.addLayout(header_layout)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {BORDER_DEFAULT};
                border-radius: {RADIUS_MD}px;
                background-color: {SURFACE_MAIN};
            }}
            QTabBar::tab {{
                background-color: {SURFACE_CARD};
                color: {TEXT_SECONDARY};
                padding: {SPACING_SM}px {SPACING_LG}px;
                margin-right: 2px;
                border-top-left-radius: {RADIUS_SM}px;
                border-top-right-radius: {RADIUS_SM}px;
            }}
            QTabBar::tab:selected {{
                background-color: {SURFACE_ELEVATED};
                color: {TEXT_PRIMARY};
            }}
            QTabBar::tab:hover {{
                background-color: {SURFACE_ELEVATED};
            }}
        """)

        # Group stage tab
        self.groups_widget = QWidget()
        groups_layout = QGridLayout(self.groups_widget)
        groups_layout.setSpacing(SPACING_LG)

        self.group_tables: dict[str, GroupTable] = {}
        for i, group in enumerate(["A", "B", "C", "D"]):
            table = GroupTable(group)
            self.group_tables[group] = table
            groups_layout.addWidget(table, i // 2, i % 2)

        groups_scroll = QScrollArea()
        groups_scroll.setWidget(self.groups_widget)
        groups_scroll.setWidgetResizable(True)
        groups_scroll.setStyleSheet("border: none;")

        self.tabs.addTab(groups_scroll, "Group Stage")

        # Knockout bracket tab
        self.knockout_widget = KnockoutBracketWidget()
        self.knockout_widget.match_selected.connect(self.match_selected.emit)

        knockout_scroll = QScrollArea()
        knockout_scroll.setWidget(self.knockout_widget)
        knockout_scroll.setWidgetResizable(True)
        knockout_scroll.setStyleSheet("border: none;")

        self.tabs.addTab(knockout_scroll, "Knockout Bracket")

        layout.addWidget(self.tabs)

        # Placeholder message when no tournament
        self.placeholder = QLabel(
            "No tournament active.\n\n"
            "Create a new tournament from Match Setup to begin."
        )
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setStyleSheet(f"""
            color: {TEXT_MUTED};
            font-size: {FONT_SIZE_LG}pt;
            padding: {SPACING_XL}px;
        """)
        layout.addWidget(self.placeholder)

        # Initially hide tabs, show placeholder
        self.tabs.hide()
        self.placeholder.show()

    def update_bracket(self, bracket_data: dict) -> None:
        """
        Update the bracket display with new data.

        Args:
            bracket_data: Dict from TournamentBracket.get_bracket_display()
        """
        if not bracket_data:
            self.tabs.hide()
            self.placeholder.show()
            return

        self.tabs.show()
        self.placeholder.hide()

        # Update stage label
        current_stage = bracket_data.get("current_stage", "group_stage")
        stage_names = {
            "group_stage": "Group Stage",
            "round_of_16": "Round of 16",
            "quarter_final": "Quarter-Finals",
            "semi_final": "Semi-Finals",
            "final": "Final",
            "completed": "Tournament Complete",
        }
        self.stage_label.setText(stage_names.get(current_stage, current_stage))

        # Update group tables
        groups = bracket_data.get("groups", {})
        for group_name, group_data in groups.items():
            if group_name in self.group_tables:
                standings = group_data.get("standings", [])
                self.group_tables[group_name].update_standings(standings)

        # Update knockout bracket
        knockout = bracket_data.get("knockout", {})
        self.knockout_widget.update_bracket(knockout)

        # Switch to appropriate tab
        if current_stage == "group_stage":
            self.tabs.setCurrentIndex(0)
        else:
            self.tabs.setCurrentIndex(1)

    def set_tournament(self, tournament_bracket) -> None:
        """
        Connect to a TournamentBracket instance.

        Args:
            tournament_bracket: TournamentBracket instance
        """
        if tournament_bracket:
            tournament_bracket.bracket_updated.connect(
                lambda: self.update_bracket(tournament_bracket.get_bracket_display())
            )
            # Initial update
            self.update_bracket(tournament_bracket.get_bracket_display())
