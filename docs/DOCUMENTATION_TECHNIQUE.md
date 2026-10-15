# VocabApp : documentation technique

## 1. Vue d'ensemble

VocabApp est une application de bureau (Python 3.11+, PySide6) pour apprendre du vocabulaire FR / EN / DE. Elle ne comporte ni compte, ni cloud, ni base de données : les listes sont des fichiers JSON locaux.

| Besoin | Solution |
|---|---|
| Interface | PySide6 (Qt 6), feuille de style globale |
| Stockage | un fichier JSON par liste |
| Orthographe | `pyspellchecker` (fr, en, de ; hors-ligne) |
| Voix | `sounddevice` (micro) + `SpeechRecognition` (Google, en ligne) |
| Tests | `pytest` (+ Qt en mode `offscreen`) |

## 2. Architecture

Quatre couches. Les couches basses n'importent jamais PySide6, donc elles sont testables sans interface.

```
main.py
  └─ ui/            Écrans PySide6 (présentation, navigation)
       ├─ learning/ Logique d'une session (pure Python)
       ├─ services/ Orthographe, voix (accès à l'extérieur)
       └─ storage   Lecture/écriture des fichiers
            └─ models   Dataclasses VocabList / WordPair
```

```
FlashCard/
├── main.py                      point d'entrée
├── requirements.txt / run.bat   dépendances / lanceur Windows
├── data/lists/                  listes livrées (copiées au 1er lancement)
├── tools/build_portable.py      construction du paquet Windows autonome
├── tests/                       tests unitaires + test d'interface
└── vocabapp/
    ├── models.py                VocabList, WordPair, langues
    ├── storage.py               JSON, CSV, dossier de données
    ├── learning/
    │   ├── checker.py           comparaison tolérante des réponses
    │   ├── qcm.py               génération des choix
    │   └── session.py           session, cartes, score, « refaire les erreurs »
    ├── services/
    │   ├── spell.py             correcteur orthographique
    │   └── speech.py            enregistrement + reconnaissance
    └── ui/
        ├── main_window.py       navigation (QStackedWidget), contrôleur
        ├── home_view.py         accueil
        ├── edit_view.py         création / édition d'une liste
        ├── spell_edit.py        champ avec soulignement orthographique
        ├── setup_view.py        choix liste / sens / mode / options
        ├── session_view.py      session (saisie, QCM, voix)
        ├── result_view.py       résultats
        └── styles.py            feuille de style
```

## 3. Modèle de données (`models.py`)

- `LANGUAGES` : `{"fr": "Français", "en": "Anglais", "de": "Allemand"}`.
- `SPEECH_CODES` : code attendu par Google (`fr-FR`, `en-US`, `de-DE`).
- `WordPair(source, target)`.
- `VocabList(name, source_lang, target_lang, pairs, id)` : `id` est un identifiant aléatoire de 12 caractères hexadécimaux, stable au renommage.
- `VocabList.from_dict()` valide les données : nom non vide, langues connues, paires sans champ vide. Les paires invalides sont ignorées et une liste invalide lève `ValueError`.

### Format JSON

```json
{
  "id": "foot0002",
  "name": "Football et arbitrage FR-DE",
  "source_lang": "fr",
  "target_lang": "de",
  "pairs": [
    {"source": "le but", "target": "das Tor"},
    {"source": "le gardien de but", "target": "der Torwart / der Torhüter"}
  ]
}
```

Fichier UTF-8, `ensure_ascii=False` : les accents, umlauts et ß sont écrits tels quels.

## 4. Stockage (`storage.py`)

### Emplacement
Ordre de résolution : variable `VOCABAPP_DATA`, sinon `%APPDATA%\VocabApp\lists\`, sinon `~/.vocabapp/lists/`. Le dossier est créé s'il n'existe pas.

### Nommage
Un fichier par liste : `<nom-nettoyé>-<id>.json`. Le nom est nettoyé (caractères non alphanumériques remplacés par `_`, 40 caractères max).

### Opérations (`Storage`)

| Méthode | Comportement |
|---|---|
| `install_examples()` | Copie `data/lists/*.json` **uniquement** si le dossier ne contient aucun `.json` ni `.bad`. Les listes supprimées ne reviennent donc pas. |
| `load_all()` | Lit tous les `.json`. Un fichier illisible ou invalide est renommé en `.json.bad` et signalé dans `LoadResult.errors` ; le chargement continue. Tri alphabétique. |
| `save(vlist)` | Écriture atomique (fichier `.tmp` puis `replace`). Si le nom a changé, l'ancien fichier de même `id` est supprimé. |
| `delete(vlist)` | Supprime les fichiers dont le nom se termine par `-<id>`. |
| `export_list(vlist, path)` | JSON, ou CSV (séparateur `;`, encodage `utf-8-sig` pour Excel, 1re ligne = codes de langue). |
| `import_list(path)` | JSON (nouvel `id` pour éviter les collisions) ou CSV (séparateur détecté, en-tête de langues optionnel, sinon fr→en). Lève `ValueError` si le fichier est invalide. |

Cas particuliers : en PyInstaller (`sys.frozen`), les exemples sont lus depuis `sys._MEIPASS`.

## 5. Logique d'apprentissage (`learning/`)

### 5.1 `checker.py` : comparaison tolérante

`normalize(text, accept_accent_errors)` applique, dans l'ordre :
1. normalisation Unicode NFC et `casefold()` ;
2. apostrophes typographiques (`’`, `` ` ``) ramenées à `'` ;
3. espaces multiples réduits et espaces de bord supprimés ;
4. si l'option accents est active : `ß` → `ss`, puis décomposition NFD et suppression des signes combinants (é→e, ü→u, ç→c…).

`alternatives(expected)` découpe sur `/` et `;` (espaces autour ignorés) et renvoie la chaîne complète plus chaque variante.
`is_correct(answer, expected, accept_accent_errors)` est vraie si la réponse normalisée est vide-non et égale à une variante normalisée.

Limites : la virgule n'est pas un séparateur ; les parenthèses facultatives (`(to) eat`) ne sont pas gérées ; ä↔ae n'est pas traité (seulement ä→a).

### 5.2 `qcm.py`

`make_choices(correct, pool, n_wrong=3)` : retire de `pool` les réponses identiques (après normalisation) à la bonne, tire au hasard jusqu'à 3 distracteurs, ajoute la bonne et mélange. Si la liste est trop petite, il y a moins de 4 choix (minimum 2 mots pour le QCM ; l'option est désactivée en dessous).

### 5.3 `session.py`

- `Mode` : `TYPING`, `QCM`, `VOICE`.
- `SessionOptions` : `mode`, `reverse` (cible→source), `shuffle`, `count` (`None` = tous), `accept_accent_errors`.
- `Card(question, answer)`, `Result(card, given, correct)`.
- `Session.from_list(vlist, options)` : construit les cartes (selon le sens), mélange, tronque à `count`, déduit `question_lang` / `answer_lang`. Lève `ValueError` si la liste est vide.
- `check(answer)` : en mode `VOICE`, la tolérance aux accents est toujours active (un accent ne s'entend pas).
- `submit(answer)` : évalue, enregistre un `Result`, avance l'index. Renvoie le booléen.
- `score`, `wrong`, `finished`, `total`.
- `retry_wrong()` : nouvelle `Session` sur les cartes ratées (mêmes options, remélangées si `shuffle`). Le `pool` de distracteurs reste celui de toute la liste, pour que le QCM garde 4 choix.

## 6. Services (`services/`)

### 6.1 `spell.py`
`SpellService` charge un `SpellChecker` par langue, **à la première utilisation** (le chargement du dictionnaire prend un moment). Si `pyspellchecker` est absent ou échoue, le service désactive silencieusement la vérification.

- Mot = suite de lettres Unicode, traits d'union internes inclus (`WORD_RE`). Les chiffres et la ponctuation sont ignorés ; les mots d'une seule lettre aussi.
- `is_misspelled` : un mot avec trait d'union est valide si chaque partie est connue ; les mots « ignorés » (set en mémoire) sont acceptés.
- `suggestions(word, lang, limit=5)` : candidats triés par fréquence d'usage, majuscule initiale conservée.
- `find_errors(text, lang)` : liste `(début, fin, mot)`.

Limites : les noms propres et le jargon peuvent être signalés ; la liste « ignorés » n'est pas conservée entre deux lancements.

### 6.2 `speech.py`
Flux de `listen_and_recognize(lang)` :
1. `sounddevice` ouvre un flux brut 16 kHz mono int16 par blocs de 0,1 s.
2. Les 3 premiers blocs servent à calibrer le bruit ambiant (seuil = max(2,5 × niveau, 400)).
3. Détection d'activité par énergie RMS : arrêt après 0,9 s de silence suivant la parole, au plus 6 s ; abandon après 5 s sans parole.
4. Les octets deviennent un `sr.AudioData`, envoyé à `recognize_google(..., language=<code>)`.

Toute erreur est convertie en `SpeechError` avec un message en français : aucun micro, module absent, rien entendu, parole non comprise, réseau injoignable. La voix **nécessite Internet** (service Google).

## 7. Interface (`ui/`)

### 7.1 Navigation (`main_window.py`)
`MainWindow` est le contrôleur : il possède `Storage`, la liste des `VocabList` en mémoire et un `QStackedWidget`.

```
Accueil ──Nouvelle/Modifier──▶ Édition ──Retour──▶ Accueil
   │
   └─Apprendre─▶ Choix (liste, sens, mode, options) ─Commencer─▶ Session ─▶ Résultats
                                                               ▲                │
                                                               └─Refaire erreurs┘
```

Les écrans fixes (accueil, édition, choix) sont créés une fois. Session et résultats sont créés à la demande et détruits au changement d'écran (`_show_dynamic`). Les vues communiquent par signaux Qt ; seul `MainWindow` appelle le stockage.

### 7.2 Accueil et édition
- `HomeView` : une carte par liste (nom, langues, nombre de mots) ; « Apprendre » est désactivé pour une liste vide.
- `EditView` : la sauvegarde est automatique (signal `changed`) dès que la liste a un nom, à chaque ajout, modification, suppression, renommage ou changement de langue. Une paire s'ajoute avec Entrée ; double-clic ou « Modifier la sélection » la recharge dans les champs (bouton « Enregistrer »).

### 7.3 Correction orthographique (`spell_edit.py`)
`SpellLineEdit` est un `QPlainTextEdit` d'une ligne (retours à la ligne bloqués, collage aplati). Un `QSyntaxHighlighter` applique un soulignement rouge (`SpellCheckUnderline`) aux mots suspects. Le menu clic droit ajoute les suggestions au-dessus du menu standard, plus « Ignorer ce mot ». La saisie n'est jamais bloquée. L'étiquette sous les champs liste les mots suspects.

### 7.4 Session (`session_view.py`)
Un seul écran, trois panneaux selon le mode, avec deux états : *réponse* puis *retour* (correct/faux + bouton Suivant).

| Mode | Validation | Raccourcis |
|---|---|---|
| Saisie | Entrée | Entrée : valider, puis passer à la suite |
| QCM | clic ou touche | `1`–`4`, Entrée pour la suite |
| Voix | bouton « Parler » | Espace : parler, Entrée : suite, bouton « Passer » |

`_validate()` appelle `Session.submit`, colore les boutons du QCM (vert la bonne réponse, rouge le choix fautif), affiche la bonne réponse en cas d'erreur et avance la barre de progression. L'écoute vocale tourne dans un `QThread` (`_SpeechWorker`) pour ne pas figer l'interface ; ses erreurs réactivent le bouton pour réessayer.

### 7.5 Résultats (`result_view.py`)
Score, pourcentage, détail mot à mot (réponse donnée en rouge et bonne réponse). Boutons : « Refaire les erreurs (N) » (désactivé s'il n'y en a pas), « Recommencer » (mêmes options), « Accueil ».

### 7.6 Style
`styles.py` : une feuille de style Qt unique, pilotée par `objectName` (`primary`, `danger`, `card`, `question`…) et par la propriété dynamique `state` des boutons de QCM.

## 8. Gestion des erreurs

| Situation | Comportement |
|---|---|
| JSON corrompu ou invalide | fichier renommé en `.json.bad`, avertissement, l'appli démarre |
| Liste vide | « Apprendre » désactivé ; `Session` lève `ValueError` |
| Moins de 2 mots | mode QCM désactivé |
| Échec d'écriture | boîte d'erreur (`OSError`) |
| Import invalide | message, aucune liste créée |
| Pas de micro / pas de réseau / voix incomprise | message dans l'écran, on peut réessayer ou passer |
| `pyspellchecker` absent | pas de soulignement, le reste fonctionne |

## 9. Tests

```
python -m pytest
```

- `tests/test_core.py` : comparaison tolérante, QCM, session et « refaire les erreurs », liste vide, stockage (aller-retour, renommage, fichier corrompu), import/export JSON et CSV, validité des listes livrées.
- `tests/test_ui_smoke.py` : parcours complet de l'interface en mode `offscreen` (création de liste, QCM au clavier, saisie).

Non couvert : la voix (micro et réseau réels) et le rendu sous Windows.

## 10. Packaging

### 10.1 Exécution depuis les sources
`run.bat` crée `.venv`, installe `requirements.txt` puis lance `main.py`.

### 10.2 Paquet portable Windows (`tools/build_portable.py`)
Sans Python ni pip sur le poste cible. Le script :
1. télécharge Python 3.12.8 « embeddable » (amd64) et écrit `python312._pth` avec `..` et `..\libs` (en mode embarqué, le dossier du script n'est pas dans `sys.path`) ;
2. télécharge les wheels Windows avec `pip download --platform win_amd64` et les décompresse dans `libs/` ;
3. allège : ne garde que QtCore / QtGui / QtWidgets et le plugin `qwindows`, supprime les modèles hors-ligne de SpeechRecognition (en gardant `flac-win32.exe`, nécessaire à l'envoi audio), ne garde que les dictionnaires fr/en/de, les DLL PortAudio 64 bits, et retire les modules Python inutiles ;
4. copie l'application et crée `Lancer_VocabApp.bat` (`pythonw`, sans console) et `Lancer_avec_console.bat` (diagnostic) ;
5. produit `VocabApp-portable.zip` (~32 Mo), ainsi que `VocabApp-1-runtime.zip` + `VocabApp-2-application.zip` à extraire dans le même dossier.

### 10.3 `.exe` PyInstaller (optionnel)
```
pip install pyinstaller
pyinstaller --noconsole --name VocabApp --add-data "data;data" main.py
```

## 11. Étendre l'application

- **Nouvelle langue** : ajouter dans `LANGUAGES` et `SPEECH_CODES` (`models.py`) ; vérifier que `pyspellchecker` la supporte (`spell.py`) et mettre à jour la liste des dictionnaires dans `build_portable.py`.
- **Nouveau mode d'apprentissage** : ajouter une valeur à `Mode`, un panneau dans `session_view.py`, et la sélection dans `setup_view.py`. La logique de session ne change pas.
- **Nouveau séparateur de variantes** : modifier `_SEPARATORS` dans `checker.py`.

## 12. Limites connues

- Pas de répétition espacée ni d'historique de progression (voulu).
- Voix : dépend d'Internet et du service Google ; une détection d'activité par énergie peut mal réagir dans un environnement très bruyant.
- Pas de gestion de l'édition simultanée de la même liste par deux instances.
- Application non testée sous Windows par son auteur automatique : les captures et les tests ont été faits sous Linux.
