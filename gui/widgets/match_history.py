"""
Match History Widget

Displays completed matches with the ability to view details and export scoresheets.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt

from services.event_bus import EventBus


class MatchHistoryWidget(QWidget):
    """
    Match history display showing completed matches.

    Features:
    - List of completed matches
    - Match details view
    - PDF scoresheet export
    """

    def __init__(self, event_bus: EventBus):
        super().__init__()
        self.event_bus = event_bus
        self._build_ui()

    def _build_ui(self) -> None:
        """Build the match history UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Title
        title = QLabel("Match History")
        title.setStyleSheet("font-size: 32pt; font-weight: bold; color: #FCD116;")
        layout.addWidget(title)

        # Toolbar
        toolbar = QHBoxLayout()

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self._refresh_history)
        toolbar.addWidget(self.btn_refresh)

        self.btn_export = QPushButton("Export Scoresheet")
        self.btn_export.clicked.connect(self._export_selected)
        self.btn_export.setEnabled(False)
        toolbar.addWidget(self.btn_export)

        toolbar.addStretch()

        layout.addLayout(toolbar)

        # Match table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Date", "Mode", "Player 1", "Player 2", "Score", "Winner"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table)

        # Placeholder message
        self.placeholder = QLabel(
            "No match history yet.\n\n"
            "Complete a match to see it here.\n"
            "Match data is saved automatically."
        )
        self.placeholder.setStyleSheet("font-size: 14pt; color: #666;")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.placeholder)

        # Initially show placeholder
        self.table.hide()
        self.placeholder.show()

    def _refresh_history(self) -> None:
        """Refresh the match history from the database."""
        # TODO: Load from database
        # For now, show placeholder
        self.table.setRowCount(0)
        self.table.hide()
        self.placeholder.show()

    def _on_selection_changed(self) -> None:
        """Handle table selection change."""
        self.btn_export.setEnabled(len(self.table.selectedItems()) > 0)

    def _export_selected(self) -> None:
        """Export the selected match as a PDF scoresheet."""
        rows = set(item.row() for item in self.table.selectedItems())
        if not rows:
            return

        # TODO: Implement PDF export
        QMessageBox.information(
            self,
            "Export Scoresheet",
            "PDF export functionality coming soon.\n\n"
            "This will generate an official AmpeSports scoresheet."
        )

    def add_match_to_history(self, match_data: dict) -> None:
        """Add a completed match to the history table."""
        self.placeholder.hide()
        self.table.show()

        row = self.table.rowCount()
        self.table.insertRow(row)

        # Date
        self.table.setItem(row, 0, QTableWidgetItem(
            match_data.get("date", "Unknown")
        ))

        # Mode
        self.table.setItem(row, 1, QTableWidgetItem(
            match_data.get("mode", "1v1")
        ))

        # Player 1
        self.table.setItem(row, 2, QTableWidgetItem(
            match_data.get("player1", "Player 1")
        ))

        # Player 2
        self.table.setItem(row, 3, QTableWidgetItem(
            match_data.get("player2", "Player 2")
        ))

        # Score
        p1_ap = match_data.get("player1_ap", 0)
        p2_ap = match_data.get("player2_ap", 0)
        self.table.setItem(row, 4, QTableWidgetItem(f"{p1_ap} - {p2_ap}"))

        # Winner
        winner = match_data.get("winner", "Unknown")
        self.table.setItem(row, 5, QTableWidgetItem(winner))
