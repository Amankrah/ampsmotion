"""
Audience Display

Full-screen second window designed for projectors and broadcast.
Read-only display that shows:
- Current scores
- Round information
- Timer
- Player names

Design goals (Section 8.5):
- High contrast (dark background, bright text)
- Large fonts visible from 30+ metres
- Team colors prominently displayed
"""

from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QFont

from services.event_bus import EventBus
from engine.scoring import ScoringEngine, ScoreState


class AudienceDisplay(QMainWindow):
    """
    Full-screen scoreboard for spectators.

    Connects to EventBus signals for live updates.
    This window is read-only - all interaction happens in the Ampfre Console.
    """

    def __init__(self, event_bus: EventBus, scoring_engine: Optional[ScoringEngine] = None):
        super().__init__()
        self.event_bus = event_bus
        self.scoring_engine = scoring_engine

        self.setWindowTitle("AmpsMotion — Live Scoreboard")
        self.setWindowFlags(Qt.WindowType.Window)

        # Dark background
        self.setStyleSheet("background-color: #0A0A15;")

        self._build_ui()
        self._connect_signals()

        # Initialize with current state if engine provided
        if scoring_engine:
            self._on_score_updated(scoring_engine.get_score_state())

    def _build_ui(self) -> None:
        """Build the audience display UI."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        # Title bar
        self.title_label = QLabel("AmpeSports — 1 vs 1")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("""
            font-size: 32pt;
            font-weight: bold;
            color: #FCD116;
            letter-spacing: 2px;
        """)
        layout.addWidget(self.title_label)

        # Main score display
        score_layout = QHBoxLayout()
        score_layout.setSpacing(50)

        # Player 1
        self.p1_frame = self._create_player_display("home")
        self.p1_name = self.p1_frame.findChild(QLabel, "name")
        self.p1_score = self.p1_frame.findChild(QLabel, "score")
        self.p1_stats = self.p1_frame.findChild(QLabel, "stats")
        score_layout.addWidget(self.p1_frame)

        # VS / Score separator
        vs_frame = QFrame()
        vs_layout = QVBoxLayout(vs_frame)

        self.score_display = QLabel("0 — 0")
        self.score_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.score_display.setStyleSheet("""
            font-size: 80pt;
            font-weight: bold;
            color: #FFFFFF;
            letter-spacing: 10px;
        """)
        # Add glow effect
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(30)
        glow.setColor(QColor("#FCD116"))
        glow.setOffset(0, 0)
        self.score_display.setGraphicsEffect(glow)
        vs_layout.addWidget(self.score_display)

        self.round_info = QLabel("Round 0 / 0")
        self.round_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.round_info.setStyleSheet("font-size: 24pt; color: #A0A0B0;")
        vs_layout.addWidget(self.round_info)

        score_layout.addWidget(vs_frame)

        # Player 2
        self.p2_frame = self._create_player_display("away")
        self.p2_name = self.p2_frame.findChild(QLabel, "name")
        self.p2_score = self.p2_frame.findChild(QLabel, "score")
        self.p2_stats = self.p2_frame.findChild(QLabel, "stats")
        score_layout.addWidget(self.p2_frame)

        layout.addLayout(score_layout)

        # Timer display
        timer_frame = QFrame()
        timer_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 0.5);
                border-radius: 20px;
                padding: 20px;
            }
        """)
        timer_layout = QVBoxLayout(timer_frame)

        self.timer_display = QLabel("01:00")
        self.timer_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_display.setStyleSheet("""
            font-size: 64pt;
            font-weight: bold;
            font-family: 'JetBrains Mono', 'Consolas', monospace;
            color: #00CC00;
        """)
        timer_layout.addWidget(self.timer_display)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 16pt; color: #FFB74D;")
        timer_layout.addWidget(self.status_label)

        layout.addWidget(timer_frame, alignment=Qt.AlignmentFlag.AlignCenter)

        # Bout count
        self.bout_label = QLabel("Bout #0")
        self.bout_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bout_label.setStyleSheet("font-size: 28pt; color: #666;")
        layout.addWidget(self.bout_label)

        layout.addStretch()

        # Footer
        footer = QLabel("AmpsMotion — Official AmpeSports Scoring System")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("font-size: 12pt; color: #333;")
        layout.addWidget(footer)

    def _create_player_display(self, side: str) -> QFrame:
        """Create a player display frame."""
        # Different colors for home/away
        border_color = "#2196F3" if side == "home" else "#FF5722"

        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: #16213E;
                border: 4px solid {border_color};
                border-radius: 20px;
                padding: 30px;
                min-width: 300px;
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setSpacing(15)

        # Player name
        name = QLabel("Player")
        name.setObjectName("name")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setStyleSheet(f"""
            font-size: 24pt;
            font-weight: bold;
            color: {border_color};
        """)
        layout.addWidget(name)

        # Individual score (large)
        score = QLabel("0")
        score.setObjectName("score")
        score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score.setStyleSheet("""
            font-size: 80pt;
            font-weight: bold;
            color: #FFFFFF;
        """)
        layout.addWidget(score)

        # AP label
        ap_label = QLabel("AP")
        ap_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ap_label.setStyleSheet("font-size: 13pt; color: #FCD116;")
        layout.addWidget(ap_label)

        # Stats breakdown
        stats = QLabel("Opa: 0 | Oshi: 0")
        stats.setObjectName("stats")
        stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats.setStyleSheet("font-size: 20pt; color: #888;")
        layout.addWidget(stats)

        return frame

    def _connect_signals(self) -> None:
        """Connect to event bus signals."""
        self.event_bus.score_updated.connect(self._on_score_updated)
        self.event_bus.timer_tick.connect(self._on_timer_tick)
        self.event_bus.round_started.connect(self._on_round_started)
        self.event_bus.round_ended.connect(self._on_round_ended)
        self.event_bus.match_completed.connect(self._on_match_completed)

    @Slot(object)
    def _on_score_updated(self, state: ScoreState) -> None:
        """Handle score update."""
        # Main score display
        self.score_display.setText(f"{state.player1_ap}  —  {state.player2_ap}")

        # Player 1
        self.p1_name.setText(state.player1_name or "Player 1")
        self.p1_score.setText(str(state.player1_ap))
        self.p1_stats.setText(f"Opa: {state.player1_opa_wins} | Oshi: {state.player1_oshi_wins}")

        # Player 2
        self.p2_name.setText(state.player2_name or "Player 2")
        self.p2_score.setText(str(state.player2_ap))
        self.p2_stats.setText(f"Opa: {state.player2_opa_wins} | Oshi: {state.player2_oshi_wins}")

        # Round info
        self.round_info.setText(f"Round {state.current_round} / {state.total_rounds}")

        # Bout count
        self.bout_label.setText(f"Bout #{state.bout_count}")

        # Update title based on mode
        if state.total_games > 1:
            self.title_label.setText(
                f"AmpeSports — Team vs Team (Game {state.current_game}/{state.total_games})"
            )
        else:
            self.title_label.setText("AmpeSports — 1 vs 1")

    @Slot(int)
    def _on_timer_tick(self, remaining_ms: int) -> None:
        """Handle timer tick."""
        minutes = remaining_ms // 60000
        seconds = (remaining_ms % 60000) // 1000

        self.timer_display.setText(f"{minutes:02d}:{seconds:02d}")

        # Color based on time
        if remaining_ms < 10000:
            self.timer_display.setStyleSheet("""
                font-size: 64pt;
                font-weight: bold;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
                color: #FF4444;
            """)
            self.status_label.setText("⚠ FINAL SECONDS")
        elif remaining_ms < 30000:
            self.timer_display.setStyleSheet("""
                font-size: 64pt;
                font-weight: bold;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
                color: #FFB74D;
            """)
            self.status_label.setText("")
        else:
            self.timer_display.setStyleSheet("""
                font-size: 64pt;
                font-weight: bold;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
                color: #00CC00;
            """)
            self.status_label.setText("")

    @Slot(int)
    def _on_round_started(self, round_num: int) -> None:
        """Handle round start."""
        self.status_label.setText("ROUND IN PROGRESS")
        self.status_label.setStyleSheet("font-size: 16pt; color: #00CC00;")

    @Slot(int, str)
    def _on_round_ended(self, round_num: int, winner: str) -> None:
        """Handle round end."""
        winner_text = "Player 1" if winner == "player1" else "Player 2" if winner == "player2" else "TIE"
        self.status_label.setText(f"ROUND {round_num} — {winner_text} WINS")
        self.status_label.setStyleSheet("font-size: 16pt; color: #FCD116;")

        # Reset timer display
        self.timer_display.setText("--:--")
        self.timer_display.setStyleSheet("""
            font-size: 64pt;
            font-weight: bold;
            font-family: 'JetBrains Mono', 'Consolas', monospace;
            color: #888888;
        """)

    @Slot(dict)
    def _on_match_completed(self, results: dict) -> None:
        """Handle match completion."""
        winner = results.get("winner", "unknown")
        winner_text = "PLAYER 1" if winner == "player1" else "PLAYER 2" if winner == "player2" else "TIE"

        self.status_label.setText(f"🏆 MATCH COMPLETE — {winner_text} WINS! 🏆")
        self.status_label.setStyleSheet("font-size: 22pt; color: #FCD116;")

        self.timer_display.setText("FINAL")
        self.timer_display.setStyleSheet("""
            font-size: 48pt;
            font-weight: bold;
            font-family: 'JetBrains Mono', 'Consolas', monospace;
            color: #FCD116;
        """)

    def enter_fullscreen(self) -> None:
        """Enter fullscreen mode."""
        self.showFullScreen()

    def exit_fullscreen(self) -> None:
        """Exit fullscreen mode."""
        self.showNormal()

    def keyPressEvent(self, event) -> None:
        """Handle key press - Escape exits fullscreen."""
        if event.key() == Qt.Key.Key_Escape:
            if self.isFullScreen():
                self.exit_fullscreen()
            else:
                self.close()
        else:
            super().keyPressEvent(event)
