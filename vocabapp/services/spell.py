"""Correction orthographique (pyspellchecker : fr, en, de ; hors-ligne)."""
from __future__ import annotations

import re

try:
    from spellchecker import SpellChecker
except ImportError:  # l'appli reste utilisable sans correcteur
    SpellChecker = None  # type: ignore[assignment]

# Un mot = suite de lettres, éventuellement avec des traits d'union internes.
WORD_RE = re.compile(r"[^\W\d_]+(?:-[^\W\d_]+)*", re.UNICODE)


class SpellService:
    def __init__(self) -> None:
        self._checkers: dict[str, object] = {}
        self._ignored: set[str] = set()

    @property
    def available(self) -> bool:
        return SpellChecker is not None

    def _checker(self, lang: str):
        if SpellChecker is None:
            return None
        if lang not in self._checkers:
            try:
                self._checkers[lang] = SpellChecker(language=lang)  # chargement paresseux
            except Exception:
                self._checkers[lang] = None
        return self._checkers[lang]

    def ignore(self, word: str) -> None:
        self._ignored.add(word.casefold())

    def is_misspelled(self, word: str, lang: str) -> bool:
        checker = self._checker(lang)
        if checker is None or len(word) < 2 or word.casefold() in self._ignored:
            return False
        if not checker.unknown([word]):
            return False
        if "-" in word:  # mot composé : valide si chaque partie est connue
            return bool(checker.unknown([p for p in word.split("-") if p]))
        return True

    def suggestions(self, word: str, lang: str, limit: int = 5) -> list[str]:
        checker = self._checker(lang)
        if checker is None:
            return []
        cands = checker.candidates(word.casefold()) or set()
        cands.discard(word.casefold())
        ranked = sorted(cands, key=lambda c: (-checker.word_usage_frequency(c), c))
        if word[:1].isupper():  # conserve la majuscule saisie (noms allemands, etc.)
            ranked = [c.capitalize() for c in ranked]
        return ranked[:limit]

    def find_errors(self, text: str, lang: str) -> list[tuple[int, int, str]]:
        """Liste des (début, fin, mot) suspects dans le texte."""
        return [(m.start(), m.end(), m.group()) for m in WORD_RE.finditer(text)
                if self.is_misspelled(m.group(), lang)]
