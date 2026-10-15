"""Génération des choix d'un QCM."""
from __future__ import annotations

import random

from .checker import normalize


def make_choices(correct: str, pool: list[str], n_wrong: int = 3,
                 rng: random.Random | None = None) -> list[str]:
    """Retourne `correct` + jusqu'à `n_wrong` distracteurs distincts, mélangés.

    `pool` contient les réponses des autres mots de la liste. S'il y a moins de
    distracteurs disponibles, le QCM comporte simplement moins de choix.
    """
    rng = rng or random
    seen = {normalize(correct)}
    candidates: list[str] = []
    for p in pool:
        key = normalize(p)
        if key not in seen:
            seen.add(key)
            candidates.append(p)
    wrong = rng.sample(candidates, min(n_wrong, len(candidates)))
    choices = wrong + [correct]
    rng.shuffle(choices)
    return choices
