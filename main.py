"""
AmpsMotion - Desktop Scoring System for AmpeSports

Entry point for the application.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from config import init_config, APP_NAME, APP_VERSION


def main() -> int:
    """Main entry point for AmpsMotion."""
    # Initialize configuration and directories
    init_config()

    # High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("AmpeSports")

    # Load stylesheet if it exists
    stylesheet_path = Path(__file__).parent / "gui" / "styles" / "ampsmotion.qss"
    if stylesheet_path.exists():
        with open(stylesheet_path, "r") as f:
            app.setStyleSheet(f.read())

    # Initialize database
    from models.base import init_db
    init_db()

    # Create and show main window
    from app import AmpsMotionApp
    amps_app = AmpsMotionApp()
    amps_app.show()

    # Run event loop
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
