"""Écran de session : un même écran, trois modes (saisie, QCM, voix)."""
from __future__ import annotations

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QLineEdit, QProgressBar, QPushButton,
                               QStackedWidget, QVBoxLayout, QWidget)

from ..learning.qcm import make_choices
from ..learning.session import Mode, Session
from ..models import language_name
from ..services import speech


class _SpeechWorker(QThread):
    recognized = Signal(str)
    failed = Signal(str)

    def __init__(self, lang: str):
        super().__init__()
        self.lang = lang

    def run(self) -> None:
        try:
            self.recognized.emit(speech.listen_and_recognize(self.lang))
        except speech.SpeechError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # ne jamais planter l'appli à cause du micro
            self.failed.emit(f"Erreur inattendue : {exc}")


class SessionView(QWidget):
    finished = Signal(object)    # Session terminée
    quit = Signal()

    def __init__(self, session: Session):
        super().__init__()
        self.setObjectName("page")
        self.session = session
        self.feedback_mode = False
        self.choice_buttons: list[QPushButton] = []
        self.worker: _SpeechWorker | None = None
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(12)

        top = QHBoxLayout()
        self.counter = QLabel("")
        self.counter.setObjectName("subtitle")
        stop = QPushButton("Arrêter")
        stop.clicked.connect(self._stop)
        top.addWidget(self.counter)
        top.addStretch()
        top.addWidget(stop)
        root.addLayout(top)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setMaximum(session.total)
        root.addWidget(self.progress)

        root.addStretch(1)
        self.lang_label = QLabel("")
        self.lang_label.setObjectName("hint")
        self.lang_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.question = QLabel("")
        self.question.setObjectName("question")
        self.question.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.question.setWordWrap(True)
        root.addWidget(self.lang_label)
        root.addWidget(self.question)

        self.panel = QStackedWidget()
        self.panel.addWidget(self._typing_panel())
        self.panel.addWidget(self._qcm_panel())
        self.panel.addWidget(self._voice_panel())
        root.addWidget(self.panel)

        self.feedback = QLabel("")
        self.feedback.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.feedback.setWordWrap(True)
        root.addWidget(self.feedback)
        self.next_btn = QPushButton("Suivant  (Entrée)")
        self.next_btn.setObjectName("primary")
        self.next_btn.clicked.connect(self._next)
        root.addWidget(self.next_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        root.addStretch(2)

        self.panel.setCurrentIndex({Mode.TYPING: 0, Mode.QCM: 1, Mode.VOICE: 2}[session.options.mode])
        self._show_card()

    # -- construction des panneaux ----------------------------------------------
    def _typing_panel(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        self.answer = QLineEdit()
        self.answer.setObjectName("answer")
        self.answer.setPlaceholderText("Votre traduction… (Entrée pour valider)")
        self.answer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.answer.returnPressed.connect(self._enter)
        v.addWidget(self.answer)
        return w

    def _qcm_panel(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        for i in range(4):
            b = QPushButton()
            b.setObjectName("choice")
            b.setProperty("state", "")
            b.clicked.connect(lambda _=False, i=i: self._pick(i))
            self.choice_buttons.append(b)
            v.addWidget(b)
        return w

    def _voice_panel(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        note = QLabel("Reconnaissance vocale en ligne (Google) — Internet et micro requis.")
        note.setObjectName("hint")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mic_btn = QPushButton("🎤  Parler  (Espace)")
        self.mic_btn.setObjectName("primary")
        self.mic_btn.setMinimumHeight(48)
        self.mic_btn.clicked.connect(self._listen)
        self.skip_btn = QPushButton("Passer")
        self.skip_btn.clicked.connect(lambda: self._validate(""))
        self.heard = QLabel("")
        self.heard.setObjectName("hint")
        self.heard.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.heard.setWordWrap(True)
        v.addWidget(note)
        v.addWidget(self.mic_btn)
        v.addWidget(self.heard)
        v.addWidget(self.skip_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        return w

    # -- affichage d'une carte ---------------------------------------------------
    def _show_card(self) -> None:
        s = self.session
        card = s.current
        assert card is not None
        self.feedback_mode = False
        self.counter.setText(f"Mot {s.index + 1} / {s.total}")
        self.progress.setValue(s.index)
        self.lang_label.setText(f"{language_name(s.question_lang)} → {language_name(s.answer_lang)}")
        self.question.setText(card.question)
        self.feedback.setText("")
        self.next_btn.hide()

        mode = s.options.mode
        if mode == Mode.TYPING:
            self.answer.setReadOnly(False)
            self.answer.clear()
            self.answer.setFocus()
        elif mode == Mode.QCM:
            choices = make_choices(card.answer, s.pool)
            for i, b in enumerate(self.choice_buttons):
                b.setProperty("state", "")
                self._repolish(b)
                if i < len(choices):
                    b.setText(f"{i + 1}   {choices[i]}")
                    b.setEnabled(True)
                    b.show()
                    b.setProperty("value", choices[i])
                else:
                    b.hide()
            self.setFocus()
        else:
            self.heard.setText("")
            self.mic_btn.setEnabled(True)
            self.skip_btn.setEnabled(True)
            self.setFocus()

    @staticmethod
    def _repolish(b: QPushButton) -> None:
        b.style().unpolish(b)
        b.style().polish(b)

    # -- actions -----------------------------------------------------------------
    def _validate(self, given: str, chosen: int | None = None) -> None:
        if self.feedback_mode:
            return
        self.feedback_mode = True
        ok = self.session.submit(given)
        correct = self.session.results[-1].card.answer
        if self.session.options.mode == Mode.QCM:
            for i, b in enumerate(self.choice_buttons):
                b.setEnabled(False)
                if b.property("value") == correct:
                    b.setProperty("state", "right")
                elif i == chosen:
                    b.setProperty("state", "wrong")
                self._repolish(b)
        elif self.session.options.mode == Mode.TYPING:
            self.answer.setReadOnly(True)
        else:
            self.mic_btn.setEnabled(False)
            self.skip_btn.setEnabled(False)
        if ok:
            self.feedback.setObjectName("ok")
            self.feedback.setText("✔ Correct !")
        else:
            self.feedback.setObjectName("ko")
            self.feedback.setText(f"✘ Réponse attendue : {correct}")
        self.feedback.style().unpolish(self.feedback)
        self.feedback.style().polish(self.feedback)
        self.progress.setValue(self.session.index)
        self.next_btn.setText("Voir les résultats  (Entrée)" if self.session.finished else "Suivant  (Entrée)")
        self.next_btn.show()
        self.next_btn.setFocus()

    def _enter(self) -> None:
        if self.feedback_mode:
            self._next()
        else:
            self._validate(self.answer.text())

    def _pick(self, i: int) -> None:
        if self.feedback_mode or i >= len(self.choice_buttons) or self.choice_buttons[i].isHidden():
            return
        self._validate(self.choice_buttons[i].property("value"), chosen=i)

    def _next(self) -> None:
        if not self.feedback_mode:
            return
        if self.session.finished:
            self.finished.emit(self.session)
        else:
            self._show_card()

    def _stop(self) -> None:
        self._cancel_worker()
        self.quit.emit()

    # -- voix --------------------------------------------------------------------
    def _listen(self) -> None:
        if self.feedback_mode or (self.worker and self.worker.isRunning()):
            return
        self.mic_btn.setEnabled(False)
        self.heard.setText("🎙 Écoute en cours… parlez maintenant.")
        self.worker = _SpeechWorker(self.session.answer_lang)
        self.worker.recognized.connect(self._on_recognized)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()

    def _on_recognized(self, text: str) -> None:
        self.heard.setText(f"Entendu : « {text} »")
        self._validate(text)

    def _on_failed(self, message: str) -> None:
        self.heard.setText(f"⚠ {message}")
        self.mic_btn.setEnabled(True)   # on peut réessayer ou passer

    def _cancel_worker(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.wait(8000)

    # -- clavier -----------------------------------------------------------------
    def keyPressEvent(self, event) -> None:
        key = event.key()
        mode = self.session.options.mode
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.feedback_mode:
                self._next()
                return
        elif mode == Mode.QCM and Qt.Key.Key_1 <= key <= Qt.Key.Key_4:
            self._pick(key - Qt.Key.Key_1)
            return
        elif mode == Mode.VOICE and key == Qt.Key.Key_Space and not self.feedback_mode:
            self._listen()
            return
        super().keyPressEvent(event)
