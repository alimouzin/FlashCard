"""Champ de saisie d'une ligne avec soulignement orthographique et suggestions (clic droit)."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QMenu, QPlainTextEdit

from ..services.spell import WORD_RE, SpellService


class _Highlighter(QSyntaxHighlighter):
    def __init__(self, document, owner: "SpellLineEdit"):
        super().__init__(document)
        self.owner = owner
        self.fmt = QTextCharFormat()
        self.fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
        self.fmt.setUnderlineColor(QColor("#dc2626"))

    def highlightBlock(self, text: str) -> None:
        if self.owner.lang:
            for start, end, _ in self.owner.spell.find_errors(text, self.owner.lang):
                self.setFormat(start, end - start, self.fmt)


class SpellLineEdit(QPlainTextEdit):
    """Une seule ligne. Ne bloque jamais la saisie : les fautes sont seulement soulignées."""

    returnPressed = Signal()
    suspectChanged = Signal(list)   # liste des mots suspects

    def __init__(self, spell: SpellService, placeholder: str = "", parent=None):
        super().__init__(parent)
        self.spell = spell
        self.lang = ""
        self.setPlaceholderText(placeholder)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTabChangesFocus(True)
        self.setFixedHeight(self.fontMetrics().height() + 22)
        self._hl = _Highlighter(self.document(), self)
        self.textChanged.connect(self._emit_suspects)

    def set_language(self, lang: str) -> None:
        self.lang = lang
        self._hl.rehighlight()
        self._emit_suspects()

    def text(self) -> str:
        return self.toPlainText().strip()

    def setText(self, text: str) -> None:
        self.setPlainText(text)

    def _emit_suspects(self) -> None:
        words = [w for _, _, w in self.spell.find_errors(self.toPlainText(), self.lang)] if self.lang else []
        self.suspectChanged.emit(words)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.returnPressed.emit()
            return
        super().keyPressEvent(event)

    def insertFromMimeData(self, source) -> None:
        # Collage : on aplatit les retours à la ligne
        self.insertPlainText(" ".join(source.text().split()))

    def contextMenuEvent(self, event) -> None:
        menu = self.createStandardContextMenu()
        cursor = self.cursorForPosition(event.pos())
        pos = cursor.position()
        for m in WORD_RE.finditer(self.toPlainText()):
            if m.start() <= pos <= m.end() and self.lang and self.spell.is_misspelled(m.group(), self.lang):
                first = menu.actions()[0] if menu.actions() else None
                sugg = self.spell.suggestions(m.group(), self.lang)
                acts = []
                for s in sugg:
                    a = menu.addAction(s)
                    a.triggered.connect(lambda _=False, st=m.start(), en=m.end(), r=s: self._replace(st, en, r))
                    acts.append(a)
                if not sugg:
                    a = menu.addAction("(aucune suggestion)")
                    a.setEnabled(False)
                    acts.append(a)
                ign = menu.addAction("Ignorer ce mot")
                ign.triggered.connect(lambda _=False, w=m.group(): self._ignore(w))
                acts.append(ign)
                sep = menu.addSeparator()
                for a in [*acts, sep]:
                    menu.removeAction(a)
                    menu.insertAction(first, a)
                break
        menu.exec(event.globalPos())

    def _replace(self, start: int, end: int, replacement: str) -> None:
        c = self.textCursor()
        c.setPosition(start)
        c.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        c.insertText(replacement)

    def _ignore(self, word: str) -> None:
        self.spell.ignore(word)
        self._hl.rehighlight()
        self._emit_suspects()
