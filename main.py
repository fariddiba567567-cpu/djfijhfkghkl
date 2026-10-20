from __future__ import annotations

import sys

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from core import theme
from core.config import APP_NAME
from core.ui import MainWindow


def _dark_palette() -> QPalette:
    palette = QPalette()
    roles = {
        QPalette.ColorRole.Window: theme.BG,
        QPalette.ColorRole.WindowText: theme.TEXT,
        QPalette.ColorRole.Base: theme.FIELD,
        QPalette.ColorRole.AlternateBase: theme.PANEL,
        QPalette.ColorRole.Text: theme.TEXT,
        QPalette.ColorRole.Button: theme.PANEL,
        QPalette.ColorRole.ButtonText: theme.TEXT,
        QPalette.ColorRole.ToolTipBase: theme.PANEL,
        QPalette.ColorRole.ToolTipText: theme.TEXT,
        QPalette.ColorRole.Highlight: theme.ACCENT,
        QPalette.ColorRole.HighlightedText: "#FFFFFF",
        QPalette.ColorRole.PlaceholderText: theme.MUTED,
    }
    for role, color in roles.items():
        palette.setColor(role, QColor(color))
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#5A5A5E")
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#5A5A5E")
    )
    return palette


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setPalette(_dark_palette())
    app.setStyleSheet(theme.QSS)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
