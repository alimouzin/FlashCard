"""Logique d'une session d'apprentissage (indépendante de l'interface)."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum

from ..models import VocabList
from .checker import is_correct


class Mode(str, Enum):
    TYPING = "typing"
    QCM = "qcm"
    VOICE = "voice"


@dataclass
class Card:
    question: str
    answer: str


@dataclass
class SessionOptions:
    mode: Mode = Mode.TYPING
    reverse: bool = False              # False : source -> cible ; True : cible -> source
    shuffle: bool = True
    count: int | None = None           # None = tous les mots
    accept_accent_errors: bool = False


@dataclass
class Result:
    card: Card
    given: str
    correct: bool


def build_cards(vlist: VocabList, reverse: bool) -> list[Card]:
    if reverse:
        return [Card(p.target, p.source) for p in vlist.pairs]
    return [Card(p.source, p.target) for p in vlist.pairs]


class Session:
    def __init__(self, cards: list[Card], options: SessionOptions,
                 question_lang: str, answer_lang: str, pool: list[str] | None = None):
        if not cards:
            raise ValueError("Aucun mot à apprendre.")
        self.options = options
        self.question_lang = question_lang
        self.answer_lang = answer_lang
        # `pool` : toutes les réponses de la liste (distracteurs QCM), même en refaisant les erreurs
        self.pool = pool if pool is not None else [c.answer for c in cards]
        self.cards = list(cards)
        self.index = 0
        self.results: list[Result] = []

    @classmethod
    def from_list(cls, vlist: VocabList, options: SessionOptions,
                  rng: random.Random | None = None) -> "Session":
        cards = build_cards(vlist, options.reverse)
        if not cards:
            raise ValueError("Cette liste est vide.")
        if options.shuffle:
            (rng or random).shuffle(cards)
        if options.count:
            cards = cards[: options.count]
        qlang, alang = ((vlist.target_lang, vlist.source_lang) if options.reverse
                        else (vlist.source_lang, vlist.target_lang))
        return cls(cards, options, qlang, alang, pool=[c.answer for c in build_cards(vlist, options.reverse)])

    # -- déroulement ------------------------------------------------------------
    @property
    def total(self) -> int:
        return len(self.cards)

    @property
    def finished(self) -> bool:
        return self.index >= self.total

    @property
    def current(self) -> Card | None:
        return None if self.finished else self.cards[self.index]

    def check(self, answer: str) -> bool:
        card = self.current
        assert card is not None
        # Les mots prononcés n'ont pas d'accents "visibles" : tolérance forcée à l'oral.
        tolerant = self.options.accept_accent_errors or self.options.mode == Mode.VOICE
        return is_correct(answer, card.answer, tolerant)

    def submit(self, answer: str) -> bool:
        """Enregistre la réponse de la carte courante et passe à la suivante."""
        card = self.current
        assert card is not None
        ok = self.check(answer)
        self.results.append(Result(card, answer, ok))
        self.index += 1
        return ok

    # -- résultats -------------------------------------------------------------
    @property
    def score(self) -> int:
        return sum(r.correct for r in self.results)

    @property
    def wrong(self) -> list[Result]:
        return [r for r in self.results if not r.correct]

    def retry_wrong(self) -> "Session":
        cards = [r.card for r in self.wrong]
        if self.options.shuffle:
            random.shuffle(cards)
        return Session(cards, self.options, self.question_lang, self.answer_lang, pool=self.pool)
