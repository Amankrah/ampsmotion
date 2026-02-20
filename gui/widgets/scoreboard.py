"""
Scoreboard Widget

Compact score display showing current match state.
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt, Slot

from engine.scoring import ScoreState


class ScoreboardWidget(QWidget):
    """
    Compact scoreboard showing:
    - Player names
    - Current AP scores
    - Round info
    - Opa/Oshi breakdown
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        """Build the scoreboard UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Player 1
        p1_frame = self._create_player_section("player1")
        self.p1_name = p1_frame.findChild(QLabel, "name")
        self.p1_score = p1_frame.findChild(QLabel, "score")
        self.p1_stats = p1_frame.findChild(QLabel, "stats")
        layout.addWidget(p1_frame)

        # VS / Round info
        center = QVBoxLayout()

        self.vs_label = QLabel("VS")
        self.vs_label.setStyleSheet("font-size: 24pt; font-weight: bold; color: #FCD116;")
        self.vs_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center.addWidget(self.vs_label)

        self.round_label = QLabel("Round 0/0")
        self.round_label.setStyleSheet("font-size: 14pt; color: #A0A0B0;")
        self.round_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center.addWidget(self.round_label)

        layout.addLayout(center)

        # Player 2
        p2_frame = self._create_player_section("player2")
        self.p2_name = p2_frame.findChild(QLabel, "name")
        self.p2_score = p2_frame.findChild(QLabel, "score")
        self.p2_stats = p2_frame.findChild(QLabel, "stats")
        layout.addWidget(p2_frame)

    def _create_player_section(self, player_id: str) -> QFrame:
        """Create a player score section."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #16213E;
                border-radius: 8px;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setSpacing(5)

        name = QLabel("Player")
        name.setObjectName("name")
        name.setStyleSheet("font-size: 14pt; font-weight: bold;")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name)

        score = QLabel("0")
        score.setObjectName("score")
        score.setStyleSheet("font-size: 36pt; font-weight: bold; color: #FCD116;")
        score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(score)

        stats = QLabel("O: 0 | S: 0")
        stats.setObjectName("stats")
        stats.setStyleSheet("font-size: 11pt; color: #666;")
        stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(stats)

        return frame

    @Slot(object)
    def update_score(self, state: ScoreState) -> None:
        """Update the scoreboard from a ScoreState."""
        # Player 1
        self.p1_name.setText(state.player1_name or "Player 1")
        self.p1_score.setText(str(state.player1_ap))
        self.p1_stats.setText(f"O: {state.player1_opa_wins} | S: {state.player1_oshi_wins}")

        # Player 2
        self.p2_name.setText(state.player2_name or "Player 2")
        self.p2_score.setText(str(state.player2_ap))
        self.p2_stats.setText(f"O: {state.player2_opa_wins} | S: {state.player2_oshi_wins}")

        # Round
        self.round_label.setText(f"Round {state.current_round}/{state.total_rounds}")

    def set_player_names(self, p1_name: str, p2_name: str) -> None:
        """Set player names."""
        self.p1_name.setText(p1_name)
        self.p2_name.setText(p2_name)
