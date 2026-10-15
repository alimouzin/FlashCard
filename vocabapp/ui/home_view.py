"""Écran d'accueil : liste des listes avec Apprendre / Modifier / Supprimer."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
                               QVBoxLayout, QWidget)

from ..models import VocabList


class HomeView(QWidget):
    newRequested = Signal()
    importRequested = Signal()
    learnRequested = Signal(object)
    editRequested = Signal(object)
    deleteRequested = Signal(object)

    def __init__(self):
        super().__init__()
        self.setObjectName("page")
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)

        head = QHBoxLayout()
        titles = QVBoxLayout()
        title = QLabel("VocabApp")
        title.setObjectName("title")
        sub = QLabel("Vos listes de vocabulaire")
        sub.setObjectName("subtitle")
        titles.addWidget(title)
        titles.addWidget(sub)
        head.addLayout(titles)
        head.addStretch()
        imp = QPushButton("Importer…")
        imp.clicked.connect(self.importRequested)
        new = QPushButton("+ Nouvelle liste")
        new.setObjectName("primary")
        new.clicked.connect(self.newRequested)
        head.addWidget(imp)
        head.addWidget(new)
        root.addLayout(head)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.body = QWidget()
        self.body.setObjectName("page")
        self.vbox = QVBoxLayout(self.body)
        self.vbox.setContentsMargins(0, 16, 0, 0)
        self.vbox.setSpacing(10)
        self.scroll.setWidget(self.body)
        root.addWidget(self.scroll)

    def set_lists(self, lists: list[VocabList]) -> None:
        while self.vbox.count():
            item = self.vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not lists:
            empty = QLabel("Aucune liste pour l'instant.\nCliquez sur « Nouvelle liste » pour commencer.")
            empty.setObjectName("subtitle")
            self.vbox.addWidget(empty)
        for vl in lists:
            self.vbox.addWidget(self._card(vl))
        self.vbox.addStretch()

    def _card(self, vl: VocabList) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(18, 14, 18, 14)
        info = QVBoxLayout()
        name = QLabel(vl.name)
        name.setObjectName("cardTitle")
        n = len(vl.pairs)
        meta = QLabel(f"{vl.description}  ·  {n} mot{'s' if n > 1 else ''}")
        meta.setObjectName("subtitle")
        info.addWidget(name)
        info.addWidget(meta)
        lay.addLayout(info, 1)

        learn = QPushButton("Apprendre")
        learn.setObjectName("primary")
        learn.setEnabled(n > 0)
        learn.setToolTip("" if n else "La liste est vide")
        learn.clicked.connect(lambda: self.learnRequested.emit(vl))
        edit = QPushButton("Modifier")
        edit.clicked.connect(lambda: self.editRequested.emit(vl))
        delete = QPushButton("Supprimer")
        delete.setObjectName("danger")
        delete.clicked.connect(lambda: self.deleteRequested.emit(vl))
        for b in (learn, edit, delete):
            lay.addWidget(b)
        return card
