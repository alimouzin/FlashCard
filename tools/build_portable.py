"""Construit un dossier/zip portable pour Windows : Python embarqué + dépendances incluses.

Aucune installation (ni pip) n'est nécessaire sur le poste cible.
Utilisation (sur une machine avec Python et un accès Internet) :
    python tools/build_portable.py [dossier_de_sortie]
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

PY_VERSION = "3.12.8"
PY_TAG = "312"
ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist"
APP = OUT / "VocabApp"

LAUNCHER = '@echo off\r\ncd /d "%~dp0"\r\nstart "" python\\pythonw.exe main.py\r\n'
LAUNCHER_DEBUG = ('@echo off\r\ncd /d "%~dp0"\r\npython\\python.exe main.py\r\n'
                  'echo.\r\npause\r\n')


def main() -> None:
    if APP.exists():
        shutil.rmtree(APP)
    (APP / "libs").mkdir(parents=True)
    tmp = Path(tempfile.mkdtemp())

    # 1) Python embarqué
    url = f"https://www.python.org/ftp/python/{PY_VERSION}/python-{PY_VERSION}-embed-amd64.zip"
    zpath = tmp / "py.zip"
    urllib.request.urlretrieve(url, zpath)
    with zipfile.ZipFile(zpath) as z:
        z.extractall(APP / "python")
    # Chemins de recherche : l'appli (..) et les bibliothèques (..\libs)
    pth = APP / "python" / f"python{PY_TAG}._pth"
    pth.write_text(f"python{PY_TAG}.zip\n.\n..\n..\\libs\n", encoding="utf-8")

    # 2) Dépendances Windows (wheels) décompressées dans libs/
    wheels = tmp / "wheels"
    subprocess.check_call([
        sys.executable, "-m", "pip", "download", "-q", "--dest", str(wheels), "--only-binary=:all:",
        "--platform", "win_amd64", "--python-version", "3.12", "--implementation", "cp",
        "PySide6-Essentials", "pyspellchecker", "SpeechRecognition", "sounddevice",
    ])
    for whl in wheels.glob("*.whl"):
        with zipfile.ZipFile(whl) as z:
            z.extractall(APP / "libs")
    # Allègement : traductions et outils Qt inutiles
    pyside = APP / "libs" / "PySide6"
    shutil.rmtree(pyside / "translations", ignore_errors=True)
    shutil.rmtree(pyside / "qml", ignore_errors=True)
    for exe in pyside.glob("*.exe"):
        exe.unlink()

    # SpeechRecognition : on n'utilise que Google (en ligne) ; on garde flac-win32.exe (requis)
    sr = APP / "libs" / "speech_recognition"
    shutil.rmtree(sr / "pocketsphinx-data", ignore_errors=True)
    for f in list(sr.glob("flac-linux-*")) + list(sr.glob("flac-mac*")):
        f.unlink()

    # 3) Application
    shutil.copy(ROOT / "main.py", APP / "main.py")
    shutil.copytree(ROOT / "vocabapp", APP / "vocabapp", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "data", APP / "data")
    shutil.copy(ROOT / "README.md", APP / "LISEZMOI.md")
    (APP / "Lancer_VocabApp.bat").write_bytes(LAUNCHER.encode())
    (APP / "Lancer_avec_console.bat").write_bytes(LAUNCHER_DEBUG.encode())

    # 4) Zip
    archive = shutil.make_archive(str(OUT / "VocabApp-portable"), "zip", OUT, "VocabApp")
    print("OK :", archive)


if __name__ == "__main__":
    main()
