"""
Substitution Panel Widget

Manages player substitutions in Team Mode.
Displays current roster, tracks substitution count (max 5),
and provides UI for swapping players in/out.
"""

from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem,
    QGroupBox, QComboBox, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, Signal, Slot

from engine.player_queue import PlayerQueue


class SubstitutionPanel(QWidget):
    """
    Substitution management panel for Team Mode.

    Shows:
    - Current active roster with box positions
    - Bench players available for substitution
    - Substitution counter (X / 5 used)
    - Eliminated players

    Signals:
        substitution_requested: Emitted when user requests a substitution
    """

    substitution_requested = Signal(dict)  # {out_id, in_id, in_name}

    def __init__(self, team_name: str = "Team", parent=None):
        super().__init__(parent)
        self.team_name = team_name
        self._queue: Optional[PlayerQueue] = None

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the substitution panel UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header with team name and sub counter
        header = QHBoxLayout()

        self.team_label = QLabel(self.team_name)
        self.team_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #FCD116;")
        header.addWidget(self.team_label)

        header.addStretch()

        self.sub_counter = QLabel("Substitutions: 0 / 5")
        self.sub_counter.setStyleSheet("font-size: 10pt; color: #A0A0B0;")
        header.addWidget(self.sub_counter)

        layout.addLayout(header)

        # Active roster list
        active_group = QGroupBox("Active Roster")
        active_layout = QVBoxLayout(active_group)

        self.active_list = QListWidget()
        self.active_list.setStyleSheet("""
            QListWidget {
                background-color: #16213E;
                border: 1px solid #333355;
                border-radius: 8px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #222244;
            }
            QListWidget::item:selected {
                background-color: #1A2744;
            }
        """)
        self.active_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.active_list.itemSelectionChanged.connect(self._on_active_selection_changed)
        active_layout.addWidget(self.active_list)

        layout.addWidget(active_group)

        # Substitution controls
        sub_frame = QFrame()
        sub_frame.setStyleSheet("""
            QFrame {
                background-color: #16213E;
                border: 1px solid #333355;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        sub_layout = QVBoxLayout(sub_frame)

        sub_title = QLabel("Make Substitution")
        sub_title.setStyleSheet("font-weight: bold;")
        sub_layout.addWidget(sub_title)

        form_layout = QGridLayout()

        form_layout.addWidget(QLabel("Player Out:"), 0, 0)
        self.out_combo = QComboBox()
        self.out_combo.setMinimumWidth(180)
        form_layout.addWidget(self.out_combo, 0, 1)

        form_layout.addWidget(QLabel("Player In:"), 1, 0)
        self.in_combo = QComboBox()
        self.in_combo.setMinimumWidth(180)
        form_layout.addWidget(self.in_combo, 1, 1)

        sub_layout.addLayout(form_layout)

        self.btn_substitute = QPushButton("Confirm Substitution")
        self.btn_substitute.setStyleSheet("""
            QPushButton {
                background-color: #006B3F;
                padding: 10px 20px;
            }
        """)
        self.btn_substitute.clicked.connect(self._request_substitution)
        sub_layout.addWidget(self.btn_substitute)

        layout.addWidget(sub_frame)

        # Eliminated players
        elim_group = QGroupBox("Eliminated")
        elim_layout = QVBoxLayout(elim_group)

        self.eliminated_list = QListWidget()
        self.eliminated_list.setStyleSheet("""
            QListWidget {
                background-color: #1A0A0A;
                border: 1px solid #553333;
                border-radius: 8px;
            }
            QListWidget::item {
                padding: 6px;
                color: #AA6666;
            }
        """)
        self.eliminated_list.setMaximumHeight(100)
        elim_layout.addWidget(self.eliminated_list)

        layout.addWidget(elim_group)

        layout.addStretch()

    def set_queue(self, queue: PlayerQueue) -> None:
        """
        Set the PlayerQueue to display.

        Args:
            queue: The PlayerQueue for this team
        """
        self._queue = queue
        self.team_name = queue.team_name
        self.team_label.setText(queue.team_name)
        self._refresh_display()

    def _refresh_display(self) -> None:
        """Refresh all displays from the queue state."""
        if not self._queue:
            return

        # Update substitution counter
        used = self._queue.substitution_count
        remaining = self._queue.remaining_substitutions()
        self.sub_counter.setText(f"Substitutions: {used} / 5")

        if remaining == 0:
            self.sub_counter.setStyleSheet("font-size: 10pt; color: #FF4444;")
            self.btn_substitute.setEnabled(False)
        else:
            self.sub_counter.setStyleSheet("font-size: 10pt; color: #A0A0B0;")
            self.btn_substitute.setEnabled(True)

        # Update active roster list
        self.active_list.clear()
        for player in self._queue.get_queue_state():
            text = f"Box {player['box_number']:2d}: {player['player_name']}"
            if player['is_active']:
                text = f"[RED ZONE] {player['player_name']}"

            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, player['player_id'])

            if player['is_active']:
                item.setForeground(Qt.GlobalColor.green)

            self.active_list.addItem(item)

        # Update eliminated list
        self.eliminated_list.clear()
        for player in self._queue.get_eliminated_players():
            item = QListWidgetItem(f"✗ {player['player_name']}")
            item.setData(Qt.ItemDataRole.UserRole, player['player_id'])
            self.eliminated_list.addItem(item)

        # Update combo boxes
        self._update_combos()

    def _update_combos(self) -> None:
        """Update the substitution combo boxes."""
        if not self._queue:
            return

        self.out_combo.clear()
        self.in_combo.clear()

        # Players who can be substituted out (not active, not eliminated)
        active_players = self._queue.get_queue_state()
        for player in active_players:
            if not player['is_active']:  # Can't sub out the active player
                self.out_combo.addItem(
                    player['player_name'],
                    player['player_id']
                )

        # TODO: In a real implementation, bench players would come from
        # a separate roster. For now, show placeholder
        self.in_combo.addItem("(Select bench player)", -1)

    def _on_active_selection_changed(self) -> None:
        """Handle active list selection change."""
        selected = self.active_list.selectedItems()
        if selected:
            player_id = selected[0].data(Qt.ItemDataRole.UserRole)
            # Find this player in out combo
            index = self.out_combo.findData(player_id)
            if index >= 0:
                self.out_combo.setCurrentIndex(index)

    def _request_substitution(self) -> None:
        """Request a substitution."""
        if not self._queue:
            return

        if not self._queue.can_substitute():
            QMessageBox.warning(
                self,
                "Cannot Substitute",
                "Maximum substitutions (5) have been used."
            )
            return

        out_id = self.out_combo.currentData()
        in_id = self.in_combo.currentData()
        in_name = self.in_combo.currentText()

        if out_id is None or in_id is None or in_id == -1:
            QMessageBox.warning(
                self,
                "Invalid Selection",
                "Please select both a player to remove and a player to add."
            )
            return

        self.substitution_requested.emit({
            "out_player_id": out_id,
            "in_player_id": in_id,
            "in_player_name": in_name,
        })

    @Slot(dict)
    def on_substitution_made(self, data: dict) -> None:
        """Handle successful substitution (from engine)."""
        self._refresh_display()

    @Slot(int)
    def on_player_eliminated(self, player_id: int) -> None:
        """Handle player elimination."""
        self._refresh_display()

    def set_bench_players(self, bench: list[tuple[int, str]]) -> None:
        """
        Set the list of available bench players.

        Args:
            bench: List of (player_id, player_name) tuples
        """
        self.in_combo.clear()
        for player_id, player_name in bench:
            self.in_combo.addItem(player_name, player_id)

        if not bench:
            self.in_combo.addItem("(No bench players)", -1)


class TeamSubstitutionWidget(QWidget):
    """
    Combined substitution panel for both teams.
    Used in the main scoring interface during team mode.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setSpacing(20)

        # Home team panel
        self.home_panel = SubstitutionPanel("Home Team")
        layout.addWidget(self.home_panel)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setStyleSheet("background-color: #333355;")
        layout.addWidget(separator)

        # Away team panel
        self.away_panel = SubstitutionPanel("Away Team")
        layout.addWidget(self.away_panel)

    def set_queues(self, home_queue: PlayerQueue, away_queue: PlayerQueue) -> None:
        """Set the player queues for both teams."""
        self.home_panel.set_queue(home_queue)
        self.away_panel.set_queue(away_queue)

    def refresh(self) -> None:
        """Refresh both panels."""
        self.home_panel._refresh_display()
        self.away_panel._refresh_display()
