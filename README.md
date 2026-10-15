# VocabApp

Application de bureau (Windows) minimaliste pour apprendre du vocabulaire entre le français, l'anglais et l'allemand.

## Installation

Prérequis : **Python 3.11+** (cocher « Add Python to PATH » à l'installation).

```bat
run.bat
```

Au premier lancement, `run.bat` crée un environnement virtuel `.venv`, installe `requirements.txt` puis démarre l'application.
Installation manuelle :

```bat
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Utilisation

- **Accueil** : liste des listes (nom, langues, nombre de mots) ; boutons *Apprendre*, *Modifier*, *Supprimer*, plus *Nouvelle liste* et *Importer* (JSON ou CSV).
- **Modifier une liste** : ajout/modification/suppression de paires (Entrée valide, double-clic pour modifier). La sauvegarde est automatique. Les mots suspects sont soulignés en rouge ; clic droit pour les suggestions ou « Ignorer ce mot » (la saisie n'est jamais bloquée).
- **Apprendre** : choix de la liste, du sens, du mode (Saisie / QCM / Voix) et des options (ordre aléatoire, nombre de mots, tolérance aux accents). À la fin : score et bouton « Refaire les erreurs ».

Raccourcis : `Entrée` valider / passer au suivant, `1`–`4` choisir en QCM, `Espace` parler en mode voix.
Plusieurs traductions acceptées : écrivez `maison / foyer` (séparateurs `/` ou `;`), chacune est acceptée.

### Reconnaissance vocale
Elle utilise **Google Speech Recognition** via `SpeechRecognition` : une **connexion Internet** et un **micro** sont nécessaires (l'interface le rappelle). Le micro est lu avec `sounddevice` (pas besoin de PyAudio). L'absence de micro ou une erreur réseau affiche un message et permet de réessayer ou de passer le mot.

## Données

Les listes sont des fichiers JSON (un par liste) dans `%APPDATA%\VocabApp\lists\` (ailleurs : `~/.vocabapp/lists/`).
Deux listes d'exemple (`data/lists/`, FR→EN et FR→DE) sont copiées au premier lancement. Un fichier corrompu est renommé en `.json.bad` et signalé, sans bloquer l'application.

## Tests

```bat
pip install pytest
python -m pytest
```

## Version portable (sans Python ni pip)

`python tools/build_portable.py` construit `dist/VocabApp-portable.zip` : Python embarqué + toutes les dépendances Windows.
Sur le poste cible : dézipper puis double-clic sur `Lancer_VocabApp.bat` (ou `Lancer_avec_console.bat` pour voir les erreurs).

## Générer un .exe (optionnel)

```bat
pip install pyinstaller
pyinstaller --noconsole --name VocabApp --add-data "data;data" main.py
```

L'exécutable se trouve dans `dist\VocabApp\`.

## Structure

```
main.py                 point d'entrée
vocabapp/models.py      modèles (VocabList, WordPair)
vocabapp/storage.py     JSON, import/export CSV
vocabapp/learning/      vérification des réponses, QCM, logique de session
vocabapp/services/      orthographe (pyspellchecker), voix
vocabapp/ui/            écrans PySide6
```
