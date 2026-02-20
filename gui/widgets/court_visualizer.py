"""
AmpsKourt Court Visualizer

2D visualization of the AmpeSports court showing:
- The 5 lanes with Boxes 1-15
- Red Zone (centre) where active bout takes place
- Player positions in each box
- Eliminated players in Exit Lane

Court dimensions: 20m × 25m
Red Zone: 3m × 3m centre area
"""

from typing import Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt, Signal, Slot, QRect, QPoint
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QFont, QPaintEvent

from engine.player_queue import PlayerQueue, Lane


class BoxWidget(QFrame):
    """
    A single box position on the court.
    Shows player name/number when occupied.
    """

    clicked = Signal(int)  # box_number

    def __init__(self, box_number: int, parent=None):
        super().__init__(parent)
        self.box_number = box_number
        self.player_name: str = ""
        self.player_id: Optional[int] = None
        self.is_active = False
        self.is_highlighted = False

        self.setMinimumSize(60, 50)
        self.setMaximumSize(100, 70)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._update_style()

    def _update_style(self) -> None:
        """Update the box visual style."""
        if self.is_active:
            # Red Zone - active player
            bg_color = "#CE1126"
            border_color = "#FF4444"
            text_color = "#FFFFFF"
        elif self.is_highlighted:
            bg_color = "#006B3F"
            border_color = "#00CC00"
            text_color = "#FFFFFF"
        elif self.player_name:
            # Occupied box
            bg_color = "#16213E"
            border_color = "#333355"
            text_color = "#FFFFFF"
        else:
            # Empty box
            bg_color = "#0A0A15"
            border_color = "#222233"
            text_color = "#444444"

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 8px;
            }}
        """)

        # Set label text
        if not hasattr(self, '_label'):
            self._label = QLabel(self)
            self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if self.player_name:
            display = self.player_name[:8]
            if len(self.player_name) > 8:
                display += "..."
            self._label.setText(f"{self.box_number}\n{display}")
        else:
            self._label.setText(str(self.box_number))

        self._label.setStyleSheet(f"color: {text_color}; font-size: 9pt;")
        self._label.setGeometry(self.rect())

    def resizeEvent(self, event) -> None:
        """Handle resize."""
        super().resizeEvent(event)
        if hasattr(self, '_label'):
            self._label.setGeometry(self.rect())

    def set_player(self, player_id: int, player_name: str, is_active: bool = False) -> None:
        """Set the player in this box."""
        self.player_id = player_id
        self.player_name = player_name
        self.is_active = is_active
        self._update_style()

    def clear_player(self) -> None:
        """Clear the player from this box."""
        self.player_id = None
        self.player_name = ""
        self.is_active = False
        self.is_highlighted = False
        self._update_style()

    def set_highlighted(self, highlighted: bool) -> None:
        """Highlight this box (e.g., for selection)."""
        self.is_highlighted = highlighted
        self._update_style()

    def mousePressEvent(self, event) -> None:
        """Handle click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.box_number)
        super().mousePressEvent(event)


class LaneWidget(QFrame):
    """
    A lane containing 3 boxes.
    Lane 1: Boxes 1-3 (closest to Red Zone)
    Lane 2: Boxes 4-6
    etc.
    """

    def __init__(self, lane_number: int, start_box: int, parent=None):
        super().__init__(parent)
        self.lane_number = lane_number
        self.start_box = start_box

        self.setStyleSheet("""
            QFrame {
                background-color: rgba(22, 33, 62, 0.5);
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)

        # Lane label
        lane_label = QLabel(f"Lane {lane_number}")
        lane_label.setStyleSheet("font-size: 8pt; color: #666;")
        lane_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lane_label)

        # Boxes
        self.boxes: list[BoxWidget] = []
        for i in range(3):
            box_num = start_box + i
            box = BoxWidget(box_num)
            self.boxes.append(box)
            layout.addWidget(box)

    def get_box(self, box_number: int) -> Optional[BoxWidget]:
        """Get a specific box by number."""
        for box in self.boxes:
            if box.box_number == box_number:
                return box
        return None


class CourtVisualizer(QWidget):
    """
    Complete AmpsKourt visualization.

    Shows both teams' positions on the court with:
    - Home team on the left
    - Away team on the right
    - Red Zone in the centre
    - Exit lanes for eliminated players

    Signals:
        player_clicked: Emitted when a player box is clicked
    """

    player_clicked = Signal(str, int, int)  # team, box_number, player_id

    def __init__(self, parent=None):
        super().__init__(parent)

        self._home_queue: Optional[PlayerQueue] = None
        self._away_queue: Optional[PlayerQueue] = None

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the court visualization UI."""
        layout = QHBoxLayout(self)
        layout.setSpacing(10)

        # Home team side
        home_side = QVBoxLayout()

        home_label = QLabel("HOME")
        home_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: #2196F3;")
        home_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        home_side.addWidget(home_label)

        # Home lanes
        home_lanes = QHBoxLayout()
        self.home_lanes: list[LaneWidget] = []

        for i in range(5):
            lane = LaneWidget(i + 1, i * 3 + 1)
            self.home_lanes.append(lane)
            home_lanes.addWidget(lane)

            # Connect box clicks
            for box in lane.boxes:
                box.clicked.connect(lambda bn, t="home": self._on_box_clicked(t, bn))

        home_side.addLayout(home_lanes)

        # Home exit lane
        self.home_exit = QLabel("Eliminated: 0")
        self.home_exit.setStyleSheet("font-size: 9pt; color: #FF4444;")
        self.home_exit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        home_side.addWidget(self.home_exit)

        layout.addLayout(home_side)

        # Red Zone (centre)
        red_zone = QFrame()
        red_zone.setFixedSize(120, 150)
        red_zone.setStyleSheet("""
            QFrame {
                background-color: #CE1126;
                border: 3px solid #FF4444;
                border-radius: 12px;
            }
        """)

        rz_layout = QVBoxLayout(red_zone)

        rz_title = QLabel("RED ZONE")
        rz_title.setStyleSheet("font-size: 10pt; font-weight: bold; color: white;")
        rz_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rz_layout.addWidget(rz_title)

        self.home_active = QLabel("-")
        self.home_active.setStyleSheet("font-size: 10pt; color: #2196F3;")
        self.home_active.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rz_layout.addWidget(self.home_active)

        vs_label = QLabel("VS")
        vs_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: #FCD116;")
        vs_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rz_layout.addWidget(vs_label)

        self.away_active = QLabel("-")
        self.away_active.setStyleSheet("font-size: 10pt; color: #FF5722;")
        self.away_active.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rz_layout.addWidget(self.away_active)

        layout.addWidget(red_zone)

        # Away team side
        away_side = QVBoxLayout()

        away_label = QLabel("AWAY")
        away_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: #FF5722;")
        away_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        away_side.addWidget(away_label)

        # Away lanes
        away_lanes = QHBoxLayout()
        self.away_lanes: list[LaneWidget] = []

        for i in range(5):
            lane = LaneWidget(i + 1, i * 3 + 1)
            self.away_lanes.append(lane)
            away_lanes.addWidget(lane)

            # Connect box clicks
            for box in lane.boxes:
                box.clicked.connect(lambda bn, t="away": self._on_box_clicked(t, bn))

        away_side.addLayout(away_lanes)

        # Away exit lane
        self.away_exit = QLabel("Eliminated: 0")
        self.away_exit.setStyleSheet("font-size: 9pt; color: #FF4444;")
        self.away_exit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        away_side.addWidget(self.away_exit)

        layout.addLayout(away_side)

    def set_queues(self, home_queue: PlayerQueue, away_queue: PlayerQueue) -> None:
        """Set the player queues for both teams."""
        self._home_queue = home_queue
        self._away_queue = away_queue
        self._refresh_display()

    def _refresh_display(self) -> None:
        """Refresh the court display from queue states."""
        self._refresh_team_display("home")
        self._refresh_team_display("away")

    def _refresh_team_display(self, team: str) -> None:
        """Refresh display for one team."""
        queue = self._home_queue if team == "home" else self._away_queue
        lanes = self.home_lanes if team == "home" else self.away_lanes
        exit_label = self.home_exit if team == "home" else self.away_exit
        active_label = self.home_active if team == "home" else self.away_active

        if not queue:
            return

        # Clear all boxes first
        for lane in lanes:
            for box in lane.boxes:
                box.clear_player()

        # Fill in active players
        for player in queue.get_queue_state():
            box_num = player['box_number']

            # Find the correct box
            lane_idx = (box_num - 1) // 3
            if 0 <= lane_idx < len(lanes):
                box = lanes[lane_idx].get_box(box_num)
                if box:
                    box.set_player(
                        player['player_id'],
                        player['player_name'],
                        player['is_active']
                    )

        # Update active player label
        active_player = queue.active_player
        if active_player:
            active_label.setText(active_player.player_name[:10])
        else:
            active_label.setText("-")

        # Update eliminated count
        eliminated = queue.get_eliminated_players()
        exit_label.setText(f"Eliminated: {len(eliminated)}")

    def _on_box_clicked(self, team: str, box_number: int) -> None:
        """Handle box click."""
        queue = self._home_queue if team == "home" else self._away_queue

        if not queue:
            return

        player = queue.get_player_at_box(box_number)
        if player:
            self.player_clicked.emit(team, box_number, player.player_id)

    @Slot()
    def refresh(self) -> None:
        """Public method to refresh the display."""
        self._refresh_display()


class CompactCourtVisualizer(QWidget):
    """
    A more compact version of the court visualizer.
    Shows only the essential information in a smaller space.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)

        # Home queue preview
        self.home_preview = QLabel("Home: -- vs --")
        self.home_preview.setStyleSheet("font-size: 9pt; color: #2196F3;")
        layout.addWidget(self.home_preview)

        layout.addStretch()

        # Red zone indicator
        self.red_zone = QLabel("[RED ZONE]")
        self.red_zone.setStyleSheet("font-size: 9pt; color: #CE1126; font-weight: bold;")
        layout.addWidget(self.red_zone)

        layout.addStretch()

        # Away queue preview
        self.away_preview = QLabel("Away: -- vs --")
        self.away_preview.setStyleSheet("font-size: 9pt; color: #FF5722;")
        layout.addWidget(self.away_preview)

    def update_preview(
        self,
        home_active: Optional[str],
        away_active: Optional[str],
        home_remaining: int,
        away_remaining: int
    ) -> None:
        """Update the compact preview."""
        home_text = home_active if home_active else "--"
        away_text = away_active if away_active else "--"

        self.home_preview.setText(f"Home ({home_remaining}): {home_text}")
        self.away_preview.setText(f"Away ({away_remaining}): {away_text}")
