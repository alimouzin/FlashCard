"""Choix de la liste, du sens, du mode et des options de session."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QFrame, QHBoxLayout, QLabel,
                               QPushButton, QRadioButton, QSpinBox, QVBoxLayout, QWidget)

from ..learning.session import Mode, SessionOptions
from ..models import VocabList, language_name


class SetupView(QWidget):
    backRequested = Signal()
    startRequested = Signal(object, object)   # VocabList, SessionOptions

    def __init__(self):
        super().__init__()
        self.setObjectName("page")
        self.lists: list[VocabList] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(14)
        top = QHBoxLayout()
        back = QPushButton("← Accueil")
        back.clicked.connect(self.backRequested)
        title = QLabel("Apprendre")
        title.setObjectName("title")
        top.addWidget(back)
        top.addWidget(title)
        top.addStretch()
        root.addLayout(top)

        card = QFrame()
        card.setObjectName("card")
        form = QFormLayout(card)
        form.setContentsMargins(24, 20, 24, 20)
        form.setVerticalSpacing(14)

        self.list_combo = QComboBox()
        self.dir_combo = QComboBox()
        form.addRow("Liste", self.list_combo)
        form.addRow("Sens", self.dir_combo)

        self.r_typing = QRadioButton("Saisie — taper la traduction")
        self.r_qcm = QRadioButton("QCM — 4 choix")
        self.r_voice = QRadioButton("Voix — prononcer la traduction")
        self.r_typing.setChecked(True)
        modes = QVBoxLayout()
        for r in (self.r_typing, self.r_qcm, self.r_voice):
            modes.addWidget(r)
        self.voice_note = QLabel("⚠ Reconnaissance vocale en ligne (Google) : connexion Internet et micro requis.")
        self.voice_note.setObjectName("warn")
        modes.addWidget(self.voice_note)
        form.addRow("Mode", modes)

        self.shuffle = QCheckBox("Ordre aléatoire")
        self.shuffle.setChecked(True)
        self.accents = QCheckBox("Accepter les fautes d'accents / umlauts (é/e, ü/u, ß/ss…)")
        self.all_words = QCheckBox("Tous les mots")
        self.all_words.setChecked(True)
        self.count = QSpinBox()
        self.count.setMinimum(1)
        self.count.setEnabled(False)
        cnt = QHBoxLayout()
        cnt.addWidget(self.all_words)
        cnt.addWidget(self.count)
        cnt.addStretch()
        form.addRow("Options", self.shuffle)
        form.addRow("", self.accents)
        form.addRow("Nombre de mots", cnt)
        root.addWidget(card)

        self.start = QPushButton("Commencer")
        self.start.setObjectName("primary")
        self.start.setMinimumHeight(44)
        root.addWidget(self.start)
        root.addStretch()

        self.list_combo.currentIndexChanged.connect(self._list_changed)
        self.all_words.toggled.connect(lambda on: self.count.setEnabled(not on))
        for r in (self.r_typing, self.r_qcm, self.r_voice):
            r.toggled.connect(self._mode_changed)
        self.start.clicked.connect(self._start)

    def load(self, lists: list[VocabList], selected: VocabList | None) -> None:
        self.lists = [v for v in lists if v.pairs]
        self.list_combo.blockSignals(True)
        self.list_combo.clear()
        for v in self.lists:
            self.list_combo.addItem(f"{v.name}  ({len(v.pairs)} mots)", v.id)
        idx = next((i for i, v in enumerate(self.lists) if selected and v.id == selected.id), 0)
        self.list_combo.setCurrentIndex(idx)
        self.list_combo.blockSignals(False)
        self.start.setEnabled(bool(self.lists))
        self._list_changed()
        self._mode_changed()

    def _current(self) -> VocabList | None:
        i = self.list_combo.currentIndex()
        return self.lists[i] if 0 <= i < len(self.lists) else None

    def _list_changed(self) -> None:
        vl = self._current()
        self.dir_combo.clear()
        if not vl:
            return
        s, t = language_name(vl.source_lang), language_name(vl.target_lang)
        self.dir_combo.addItem(f"{s} → {t}", False)
        self.dir_combo.addItem(f"{t} → {s}", True)
        self.count.setMaximum(len(vl.pairs))
        self.count.setValue(min(10, len(vl.pairs)))
        self.r_qcm.setEnabled(len(vl.pairs) >= 2)
        if not self.r_qcm.isEnabled() and self.r_qcm.isChecked():
            self.r_typing.setChecked(True)

    def _mode_changed(self, *_) -> None:
        self.voice_note.setVisible(self.r_voice.isChecked())
        self.accents.setEnabled(not self.r_qcm.isChecked())

    def _start(self) -> None:
        vl = self._current()
        if not vl:
            return
        mode = Mode.QCM if self.r_qcm.isChecked() else Mode.VOICE if self.r_voice.isChecked() else Mode.TYPING
        opts = SessionOptions(
            mode=mode,
            reverse=bool(self.dir_combo.currentData()),
            shuffle=self.shuffle.isChecked(),
            count=None if self.all_words.isChecked() else self.count.value(),
            accept_accent_errors=self.accents.isChecked(),
        )
        self.startRequested.emit(vl, opts)
