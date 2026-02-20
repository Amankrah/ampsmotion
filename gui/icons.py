"""
App icons using Qt standard pixmaps and theme icons.

Uses QStyle.StandardPixmap for cross-platform consistency; falls back to
QIcon.fromTheme() where available (e.g. Linux) for a more native look.
Icons are more visible and consistent than emoji/unicode symbols.
"""

from PySide6.QtWidgets import QApplication, QStyle
from PySide6.QtGui import QIcon


def _style():
    app = QApplication.instance()
    return app.style() if app else None


def icon_foul() -> QIcon:
    """Warning/foul icon (e.g. for Foul button)."""
    style = _style()
    if style:
        return style.standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning)
    icon = QIcon.fromTheme("dialog-warning")
    return icon if not icon.isNull() else QIcon()


def icon_undo() -> QIcon:
    """Undo icon (e.g. for Undo last bout)."""
    style = _style()
    if style:
        return style.standardIcon(QStyle.StandardPixmap.SP_ArrowBack)
    icon = QIcon.fromTheme("edit-undo")
    return icon if not icon.isNull() else QIcon()


def icon_substitution() -> QIcon:
    """Swap/substitution icon (e.g. for Home/Away Substitution)."""
    # Prefer theme "swap" or "arrow-right-left"; fallback to arrows
    icon = QIcon.fromTheme("arrow-right-left")
    if not icon.isNull():
        return icon
    icon = QIcon.fromTheme("swap")
    if not icon.isNull():
        return icon
    style = _style()
    if style:
        return style.standardIcon(QStyle.StandardPixmap.SP_ArrowRight)
    return QIcon()


def icon_size_normal() -> int:
    """Recommended icon size for toolbar/action buttons (px)."""
    return 20


def icon_size_large() -> int:
    """Larger icon size for prominent buttons (px)."""
    return 24
