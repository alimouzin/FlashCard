@echo off
REM Lance VocabApp (crée l'environnement virtuel et installe les dépendances au premier lancement)
cd /d "%~dp0"
if not exist .venv (
    py -3 -m venv .venv || (echo Python 3.11+ est requis. & pause & exit /b 1)
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)
python main.py
if errorlevel 1 pause
