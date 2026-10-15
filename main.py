"""Point d'entrée de VocabApp."""
import sys

from PySide6.QtWidgets import QApplication

from vocabapp.ui.main_window import MainWindow
from vocabapp.ui.styles import STYLE


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("VocabApp")
    app.setStyleSheet(STYLE)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
