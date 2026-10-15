"""Stockage des listes : un fichier JSON par liste.

Dossier de données : %APPDATA%/VocabApp/lists (Windows) ou ~/.vocabapp/lists.
Peut être forcé avec la variable d'environnement VOCABAPP_DATA (utile pour les tests).
"""
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .models import LANGUAGES, VocabList, WordPair


def _bundle_dir() -> Path:
    """Racine du projet (ou du bundle PyInstaller)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def examples_dir() -> Path:
    return _bundle_dir() / "data" / "lists"


def lists_dir() -> Path:
    override = os.environ.get("VOCABAPP_DATA")
    if override:
        base = Path(override)
    elif os.environ.get("APPDATA"):
        base = Path(os.environ["APPDATA"]) / "VocabApp"
    else:
        base = Path.home() / ".vocabapp"
    path = base / "lists"
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class LoadResult:
    lists: list[VocabList] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)  # fichiers illisibles


def _slug(name: str) -> str:
    s = re.sub(r"[^\w-]+", "_", name.strip(), flags=re.UNICODE).strip("_")
    return s[:40] or "liste"


class Storage:
    def __init__(self, directory: Path | None = None):
        self.dir = Path(directory) if directory else lists_dir()
        self.dir.mkdir(parents=True, exist_ok=True)

    # -- chemins -----------------------------------------------------------
    def path_for(self, vlist: VocabList) -> Path:
        return self.dir / f"{_slug(vlist.name)}-{vlist.id}.json"

    def _existing_paths(self, list_id: str) -> list[Path]:
        return [p for p in self.dir.glob("*.json") if p.stem.endswith(f"-{list_id}")]

    # -- exemples ----------------------------------------------------------
    def install_examples(self) -> None:
        """Copie les listes d'exemple au tout premier lancement (dossier vide)."""
        if any(self.dir.glob("*.json")) or any(self.dir.glob("*.bad")):
            return
        src = examples_dir()
        if src.is_dir():
            for f in src.glob("*.json"):
                shutil.copy(f, self.dir / f.name)

    # -- lecture / écriture --------------------------------------------------
    def load_all(self) -> LoadResult:
        result = LoadResult()
        for path in sorted(self.dir.glob("*.json")):
            try:
                with open(path, encoding="utf-8") as fh:
                    result.lists.append(VocabList.from_dict(json.load(fh)))
            except (OSError, ValueError) as exc:  # JSONDecodeError hérite de ValueError
                # On met le fichier de côté pour ne pas le perdre ni replanter.
                bad = path.with_suffix(".json.bad")
                try:
                    path.replace(bad)
                except OSError:
                    bad = path
                result.errors.append(f"{path.name} : {exc} (déplacé vers {bad.name})")
        result.lists.sort(key=lambda v: v.name.lower())
        return result

    def save(self, vlist: VocabList) -> Path:
        """Écriture atomique ; supprime l'ancien fichier si le nom a changé."""
        target = self.path_for(vlist)
        tmp = target.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(vlist.to_dict(), fh, ensure_ascii=False, indent=2)
        tmp.replace(target)
        for old in self._existing_paths(vlist.id):
            if old != target:
                old.unlink(missing_ok=True)
        return target

    def delete(self, vlist: VocabList) -> None:
        for p in self._existing_paths(vlist.id):
            p.unlink(missing_ok=True)

    # -- import / export -------------------------------------------------------
    def export_list(self, vlist: VocabList, path: Path) -> None:
        path = Path(path)
        if path.suffix.lower() == ".csv":
            # utf-8-sig : Excel lit correctement les accents
            with open(path, "w", encoding="utf-8-sig", newline="") as fh:
                w = csv.writer(fh, delimiter=";")
                w.writerow([vlist.source_lang, vlist.target_lang])
                for p in vlist.pairs:
                    w.writerow([p.source, p.target])
        else:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(vlist.to_dict(), fh, ensure_ascii=False, indent=2)

    def import_list(self, path: Path) -> VocabList:
        """Importe un JSON ou un CSV ; lève ValueError si le fichier est invalide."""
        path = Path(path)
        try:
            if path.suffix.lower() == ".csv":
                vlist = self._read_csv(path)
            else:
                with open(path, encoding="utf-8") as fh:
                    data = json.load(fh)
                if not isinstance(data, dict):
                    raise ValueError("Format de liste invalide.")
                data.pop("id", None)  # nouvel identifiant pour éviter les collisions
                vlist = VocabList.from_dict(data)
        except OSError as exc:
            raise ValueError(f"Lecture impossible : {exc}") from exc
        return vlist

    @staticmethod
    def _read_csv(path: Path) -> VocabList:
        with open(path, encoding="utf-8-sig", newline="") as fh:
            sample = fh.read(2048)
            fh.seek(0)
            delim = ";" if sample.count(";") >= sample.count(",") else ","
            rows = [r for r in csv.reader(fh, delimiter=delim) if r]
        if not rows:
            raise ValueError("Fichier CSV vide.")
        src, tgt = "fr", "en"
        first = [c.strip().lower() for c in rows[0][:2]]
        if len(first) == 2 and all(c in LANGUAGES for c in first):
            src, tgt = first
            rows = rows[1:]
        pairs = [WordPair(r[0].strip(), r[1].strip()) for r in rows
                 if len(r) >= 2 and r[0].strip() and r[1].strip()]
        return VocabList(name=path.stem, source_lang=src, target_lang=tgt, pairs=pairs)
