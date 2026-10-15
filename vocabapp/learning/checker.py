"""Vérification tolérante des réponses."""
from __future__ import annotations

import re
import unicodedata

_SEPARATORS = re.compile(r"\s*[/;]\s*")


def _fold_accents(text: str) -> str:
    """Supprime accents et umlauts ; ß -> ss."""
    text = text.replace("ß", "ss").replace("ẞ", "ss")
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def normalize(text: str, accept_accent_errors: bool = False) -> str:
    """Minuscules, apostrophes unifiées, espaces superflus réduits."""
    text = unicodedata.normalize("NFC", text).casefold()
    text = text.replace("’", "'").replace("`", "'")
    text = " ".join(text.split())
    if accept_accent_errors:
        text = _fold_accents(text)
    return text


def alternatives(expected: str) -> list[str]:
    """'maison / foyer' -> ['maison / foyer', 'maison', 'foyer'] (toute variante est acceptée)."""
    parts = [p for p in _SEPARATORS.split(expected) if p.strip()]
    result = [expected]
    result.extend(parts)
    return result


def is_correct(answer: str, expected: str, accept_accent_errors: bool = False) -> bool:
    got = normalize(answer, accept_accent_errors)
    if not got:
        return False
    return any(got == normalize(alt, accept_accent_errors) for alt in alternatives(expected))
