"""
Round Timer Widget

Visual countdown timer display for the Ampfre Console.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, Slot


class RoundTimerWidget(QWidget):
    """
    Visual timer display widget.

    Shows the countdown timer with color-coded warnings:
    - Green: > 30 seconds
    - Orange: 10-30 seconds
    - Red: < 10 seconds
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        """Build the timer display UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Timer display
        self.time_label = QLabel("01:00")
        self.time_label.setObjectName("timer_display")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet("""
            font-size: 72pt;
            font-weight: bold;
            font-family: 'JetBrains Mono', 'Consolas', monospace;
            color: #00CC00;
        """)
        layout.addWidget(self.time_label)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 14pt; color: #A0A0B0;")
        layout.addWidget(self.status_label)

    @Slot(int)
    def update_time(self, remaining_ms: int) -> None:
        """Update the timer display."""
        minutes = remaining_ms // 60000
        seconds = (remaining_ms % 60000) // 1000
        tenths = (remaining_ms % 1000) // 100

        # Show tenths when under 10 seconds
        if remaining_ms < 10000:
            self.time_label.setText(f"{seconds}.{tenths}")
        else:
            self.time_label.setText(f"{minutes:02d}:{seconds:02d}")

        # Update color based on time remaining
        if remaining_ms < 10000:
            self._set_color("#FF4444")  # Red
            self.status_label.setText("⚠ FINAL SECONDS")
        elif remaining_ms < 30000:
            self._set_color("#FFB74D")  # Orange
            self.status_label.setText("⚡ 30 Second Warning")
        else:
            self._set_color("#00CC00")  # Green
            self.status_label.setText("")

    def _set_color(self, color: str) -> None:
        """Set the timer text color."""
        self.time_label.setStyleSheet(f"""
            font-size: 72pt;
            font-weight: bold;
            font-family: 'JetBrains Mono', 'Consolas', monospace;
            color: {color};
        """)

    def set_paused(self, paused: bool) -> None:
        """Show pause state."""
        if paused:
            self.status_label.setText("⏸ PAUSED")
            self._set_color("#888888")
        else:
            self.status_label.setText("")
            self._set_color("#00CC00")

    def reset(self, duration_ms: int = 60000) -> None:
        """Reset to initial state."""
        self.update_time(duration_ms)
        self.status_label.setText("")
