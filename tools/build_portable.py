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
    # Allègement : on ne garde que QtCore / QtGui / QtWidgets et le plugin Windows
    pyside = APP / "libs" / "PySide6"
    keep_mods = {"QtCore", "QtGui", "QtWidgets"}
    for f in list(pyside.iterdir()):
        name = f.name
        if f.is_dir():
            if name != "plugins":
                shutil.rmtree(f)
        elif name.startswith("Qt6") and "Qt" + name[3:].rsplit(".", 1)[0] not in keep_mods:
            f.unlink()
        elif name.endswith((".pyi", ".exe")) or (name.endswith(".pyd") and name.split(".")[0] not in keep_mods):
            f.unlink()
        elif name.startswith(("opengl32sw", "d3dcompiler", "libEGL", "libGLES")):
            f.unlink()
    plugins = pyside / "plugins"
    for d in list(plugins.iterdir()):
        if d.name not in ("platforms", "styles"):
            shutil.rmtree(d)
    for f in (plugins / "platforms").iterdir():
        if f.name != "qwindows.dll":
            f.unlink()
    # pyspellchecker : uniquement fr / en / de
    res = APP / "libs" / "spellchecker" / "resources"
    for f in res.glob("*.json.gz"):
        if f.name.split(".")[0] not in ("fr", "en", "de"):
            f.unlink()

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

    # Allègement de Python embarqué (modules inutiles ici)
    py = APP / "python"
    for pattern in ("_sqlite3.pyd", "sqlite3.dll", "_msi.pyd", "_wmi.pyd", "_overlapped.pyd",
                    "_multiprocessing.pyd", "python.cat"):
        for f in py.glob(pattern):
            f.unlink()
    pa = APP / "libs" / "_sounddevice_data" / "portaudio-binaries"
    for f in pa.iterdir():
        if f.name != "libportaudio64bit.dll":
            shutil.rmtree(f) if f.is_dir() else f.unlink()

    # 4) Archives : un zip complet + deux zips (runtime / application) si le transfert est limité en taille
    archive = shutil.make_archive(str(OUT / "VocabApp-portable"), "zip", OUT, "VocabApp")
    print("OK :", archive)
    heavy = ("VocabApp/python/", "VocabApp/libs/PySide6/", "VocabApp/libs/shiboken6/")
    with zipfile.ZipFile(OUT / "VocabApp-1-runtime.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z1, \
         zipfile.ZipFile(OUT / "VocabApp-2-application.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z2:
        for f in sorted(APP.rglob("*")):
            if f.is_file():
                arc = f.relative_to(OUT).as_posix()
                (z1 if arc.startswith(heavy) else z2).write(f, arc)
    print("OK : VocabApp-1-runtime.zip + VocabApp-2-application.zip")


if __name__ == "__main__":
    main()
