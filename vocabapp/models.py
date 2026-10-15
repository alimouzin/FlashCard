"""Modèles de données (sans aucune dépendance à l'interface)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

# Code de langue -> nom affiché
LANGUAGES: dict[str, str] = {"fr": "Français", "en": "Anglais", "de": "Allemand"}

# Code de langue -> code attendu par la reconnaissance vocale Google
SPEECH_CODES: dict[str, str] = {"fr": "fr-FR", "en": "en-US", "de": "de-DE"}


def language_name(code: str) -> str:
    return LANGUAGES.get(code, code)


@dataclass
class WordPair:
    """Une paire mot source <-> traduction."""

    source: str
    target: str

    def to_dict(self) -> dict:
        return {"source": self.source, "target": self.target}


@dataclass
class VocabList:
    """Une liste de vocabulaire (un fichier JSON)."""

    name: str
    source_lang: str = "fr"
    target_lang: str = "en"
    pairs: list[WordPair] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "pairs": [p.to_dict() for p in self.pairs],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VocabList":
        """Construit une liste depuis un dict ; lève ValueError si invalide."""
        if not isinstance(data, dict):
            raise ValueError("Format de liste invalide.")
        name = str(data.get("name", "")).strip()
        src = data.get("source_lang", "fr")
        tgt = data.get("target_lang", "en")
        if not name:
            raise ValueError("La liste n'a pas de nom.")
        if src not in LANGUAGES or tgt not in LANGUAGES:
            raise ValueError("Langue non prise en charge.")
        pairs = []
        for item in data.get("pairs", []):
            if not isinstance(item, dict):
                continue
            s = str(item.get("source", "")).strip()
            t = str(item.get("target", "")).strip()
            if s and t:
                pairs.append(WordPair(s, t))
        return cls(
            name=name,
            source_lang=src,
            target_lang=tgt,
            pairs=pairs,
            id=str(data.get("id") or uuid.uuid4().hex[:12]),
        )

    @property
    def description(self) -> str:
        return f"{language_name(self.source_lang)} → {language_name(self.target_lang)}"
