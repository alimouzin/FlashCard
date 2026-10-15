"""Création / modification d'une liste, avec correction orthographique non bloquante."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from ..models import LANGUAGES, VocabList, WordPair
from ..services.spell import SpellService
from .spell_edit import SpellLineEdit


class EditView(QWidget):
    backRequested = Signal()
    changed = Signal(object)          # liste à sauvegarder (sauvegarde automatique)
    exportRequested = Signal(object)

    def __init__(self, spell: SpellService):
        super().__init__()
        self.setObjectName("page")
        self.vlist: VocabList | None = None
        self.editing_row = -1
        self._loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(10)

        top = QHBoxLayout()
        back = QPushButton("← Accueil")
        back.clicked.connect(self.backRequested)
        title = QLabel("Modifier la liste")
        title.setObjectName("title")
        top.addWidget(back)
        top.addWidget(title)
        top.addStretch()
        export = QPushButton("Exporter…")
        export.clicked.connect(lambda: self.vlist and self.exportRequested.emit(self.vlist))
        top.addWidget(export)
        root.addLayout(top)

        meta = QHBoxLayout()
        self.name = QLineEdit()
        self.name.setPlaceholderText("Nom de la liste")
        self.src = QComboBox()
        self.tgt = QComboBox()
        for code, label in LANGUAGES.items():
            self.src.addItem(label, code)
            self.tgt.addItem(label, code)
        meta.addWidget(self.name, 1)
        meta.addWidget(QLabel("Langue source"))
        meta.addWidget(self.src)
        meta.addWidget(QLabel("Langue cible"))
        meta.addWidget(self.tgt)
        root.addLayout(meta)

        # Zone de saisie d'une paire
        form = QHBoxLayout()
        self.src_edit = SpellLineEdit(spell, "Mot source")
        self.tgt_edit = SpellLineEdit(spell, "Traduction")
        self.add_btn = QPushButton("Ajouter")
        self.add_btn.setObjectName("primary")
        self.cancel_btn = QPushButton("Annuler")
        self.cancel_btn.hide()
        form.addWidget(self.src_edit, 1)
        form.addWidget(self.tgt_edit, 1)
        form.addWidget(self.add_btn)
        form.addWidget(self.cancel_btn)
        root.addLayout(form)
        self.spell_info = QLabel("")
        self.spell_info.setObjectName("warn")
        root.addWidget(self.spell_info)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Source", "Traduction"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        root.addWidget(self.table, 1)

        bottom = QHBoxLayout()
        self.count = QLabel("")
        self.count.setObjectName("hint")
        self.edit_btn = QPushButton("Modifier la sélection")
        self.del_btn = QPushButton("Supprimer la sélection")
        self.del_btn.setObjectName("danger")
        bottom.addWidget(self.count)
        bottom.addStretch()
        bottom.addWidget(self.edit_btn)
        bottom.addWidget(self.del_btn)
        root.addLayout(bottom)

        # Signaux
        self.name.editingFinished.connect(self._meta_changed)
        self.src.currentIndexChanged.connect(self._meta_changed)
        self.tgt.currentIndexChanged.connect(self._meta_changed)
        self.add_btn.clicked.connect(self._commit_pair)
        self.cancel_btn.clicked.connect(self._cancel_edit)
        self.src_edit.returnPressed.connect(self.tgt_edit.setFocus)
        self.tgt_edit.returnPressed.connect(self._commit_pair)
        self.src_edit.suspectChanged.connect(self._update_suspects)
        self.tgt_edit.suspectChanged.connect(self._update_suspects)
        self.table.itemDoubleClicked.connect(lambda _: self._begin_edit())
        self.edit_btn.clicked.connect(self._begin_edit)
        self.del_btn.clicked.connect(self._delete_selected)

    # -- chargement ------------------------------------------------------------
    def load(self, vlist: VocabList) -> None:
        self._loading = True
        self.vlist = vlist
        self.name.setText(vlist.name)
        self.src.setCurrentIndex(self.src.findData(vlist.source_lang))
        self.tgt.setCurrentIndex(self.tgt.findData(vlist.target_lang))
        self._loading = False
        self._apply_languages()
        self._cancel_edit()
        self._fill_table()
        self.src_edit.setFocus() if vlist.name else self.name.setFocus()

    def _fill_table(self) -> None:
        assert self.vlist
        self.table.setRowCount(len(self.vlist.pairs))
        for i, p in enumerate(self.vlist.pairs):
            self.table.setItem(i, 0, QTableWidgetItem(p.source))
            self.table.setItem(i, 1, QTableWidgetItem(p.target))
        n = len(self.vlist.pairs)
        self.count.setText(f"{n} mot{'s' if n > 1 else ''}")

    def _apply_languages(self) -> None:
        self.src_edit.set_language(self.src.currentData())
        self.tgt_edit.set_language(self.tgt.currentData())

    # -- modifications ---------------------------------------------------------
    def _save(self) -> None:
        # Sauvegarde automatique, dès que la liste a un nom
        if self.vlist and self.vlist.name:
            self.changed.emit(self.vlist)

    def _meta_changed(self) -> None:
        if self._loading or not self.vlist:
            return
        self.vlist.name = self.name.text().strip()
        self.vlist.source_lang = self.src.currentData()
        self.vlist.target_lang = self.tgt.currentData()
        self._apply_languages()
        self._save()

    def _commit_pair(self) -> None:
        if not self.vlist:
            return
        if not self.name.text().strip():
            self.spell_info.setText("Donnez d'abord un nom à la liste.")
            self.name.setFocus()
            return
        self._meta_changed()
        s, t = self.src_edit.text(), self.tgt_edit.text()
        if not s or not t:
            self.spell_info.setText("Renseignez le mot et sa traduction.")
            return
        if self.editing_row >= 0:
            self.vlist.pairs[self.editing_row] = WordPair(s, t)
        else:
            self.vlist.pairs.append(WordPair(s, t))
        self._cancel_edit()
        self._fill_table()
        self.table.scrollToBottom()
        self._save()
        self.src_edit.setFocus()

    def _begin_edit(self) -> None:
        row = self.table.currentRow()
        if row < 0 or not self.vlist:
            return
        self.editing_row = row
        p = self.vlist.pairs[row]
        self.src_edit.setText(p.source)
        self.tgt_edit.setText(p.target)
        self.add_btn.setText("Enregistrer")
        self.cancel_btn.show()
        self.src_edit.setFocus()

    def _cancel_edit(self) -> None:
        self.editing_row = -1
        self.src_edit.setText("")
        self.tgt_edit.setText("")
        self.add_btn.setText("Ajouter")
        self.cancel_btn.hide()
        self.spell_info.setText("")

    def _delete_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0 or not self.vlist:
            return
        del self.vlist.pairs[row]
        self._cancel_edit()
        self._fill_table()
        self._save()

    def _update_suspects(self, _=None) -> None:
        words = [w for e in (self.src_edit, self.tgt_edit) if e.lang
                 for _, _, w in e.spell.find_errors(e.toPlainText(), e.lang)]
        if words:
            self.spell_info.setText(f"Mot(s) suspect(s) : {', '.join(words)} — clic droit pour les suggestions, "
                                    "ou ignorez-les et validez quand même.")
        else:
            self.spell_info.setText("")
