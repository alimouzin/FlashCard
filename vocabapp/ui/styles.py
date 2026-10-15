"""Feuille de style globale (thème clair, minimaliste)."""

STYLE = """
* { font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif; font-size: 14px; color: #1f2937; }
QMainWindow, QWidget#page { background: #f5f7fb; }
QLabel#title { font-size: 26px; font-weight: 700; }
QLabel#subtitle { color: #6b7280; }
QLabel#question { font-size: 36px; font-weight: 700; }
QLabel#hint { color: #6b7280; font-size: 12px; }
QLabel#ok { color: #15803d; font-size: 18px; font-weight: 600; }
QLabel#ko { color: #b91c1c; font-size: 18px; font-weight: 600; }
QLabel#warn { color: #b45309; font-size: 12px; }
QFrame#card { background: white; border: 1px solid #e5e7eb; border-radius: 12px; }
QLabel#cardTitle { font-size: 17px; font-weight: 600; }
QPushButton { background: white; border: 1px solid #d1d5db; border-radius: 8px; padding: 8px 16px; }
QPushButton:hover { background: #eef2ff; border-color: #6366f1; }
QPushButton:disabled { color: #9ca3af; background: #f3f4f6; }
QPushButton#primary { background: #4f46e5; color: white; border: none; font-weight: 600; }
QPushButton#primary:hover { background: #4338ca; }
QPushButton#primary:disabled { background: #c7d2fe; color: white; }
QPushButton#danger { color: #b91c1c; }
QPushButton#danger:hover { background: #fee2e2; border-color: #ef4444; }
QPushButton#choice { text-align: left; padding: 14px 18px; font-size: 16px; }
QPushButton#choice[state="right"] { background: #dcfce7; border-color: #16a34a; }
QPushButton#choice[state="wrong"] { background: #fee2e2; border-color: #dc2626; }
QLineEdit, QPlainTextEdit, QComboBox, QSpinBox { background: white; border: 1px solid #d1d5db; border-radius: 8px; padding: 6px 10px; }
QLineEdit:focus, QPlainTextEdit:focus { border-color: #4f46e5; }
QLineEdit#answer { font-size: 22px; padding: 10px 14px; }
QTableWidget { background: white; border: 1px solid #e5e7eb; border-radius: 8px; gridline-color: #f3f4f6; }
QHeaderView::section { background: #f9fafb; border: none; border-bottom: 1px solid #e5e7eb; padding: 6px; font-weight: 600; }
QProgressBar { border: none; background: #e5e7eb; border-radius: 4px; height: 8px; text-align: center; }
QProgressBar::chunk { background: #4f46e5; border-radius: 4px; }
"""
