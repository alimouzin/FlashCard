"""Écran de résultats."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout,
                               QWidget)

from ..learning.session import Session


class ResultView(QWidget):
    retryErrors = Signal()
    restart = Signal()
    home = Signal()

    def __init__(self, session: Session):
        super().__init__()
        self.setObjectName("page")
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(12)

        total, score = len(session.results), session.score
        pct = round(100 * score / total) if total else 0
        title = QLabel("Session terminée")
        title.setObjectName("title")
        big = QLabel(f"{score} / {total}  ({pct} %)")
        big.setObjectName("question")
        root.addWidget(title)
        root.addWidget(big)

        body = QWidget()
        body.setObjectName("page")
        v = QVBoxLayout(body)
        v.setSpacing(6)
        for r in session.results:
            row = QFrame()
            row.setObjectName("card")
            h = QHBoxLayout(row)
            h.setContentsMargins(14, 8, 14, 8)
            mark = QLabel("✔" if r.correct else "✘")
            mark.setObjectName("ok" if r.correct else "ko")
            h.addWidget(mark)
            h.addWidget(QLabel(r.card.question), 1)
            if r.correct:
                h.addWidget(QLabel(r.card.answer))
            else:
                given = QLabel(r.given or "(sans réponse)")
                given.setObjectName("ko")
                h.addWidget(given)
                h.addWidget(QLabel(f"→ {r.card.answer}"))
            v.addWidget(row)
        v.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        btns = QHBoxLayout()
        retry = QPushButton(f"Refaire les erreurs ({len(session.wrong)})")
        retry.setObjectName("primary")
        retry.setEnabled(bool(session.wrong))
        retry.clicked.connect(self.retryErrors)
        again = QPushButton("Recommencer")
        again.clicked.connect(self.restart)
        home = QPushButton("Accueil")
        home.clicked.connect(self.home)
        btns.addWidget(retry)
        btns.addWidget(again)
        btns.addStretch()
        btns.addWidget(home)
        root.addLayout(btns)
