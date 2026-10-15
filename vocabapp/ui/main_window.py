"""Fenêtre principale : navigation entre les écrans."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QStackedWidget

from ..learning.session import Session
from ..models import VocabList
from ..services.spell import SpellService
from ..storage import Storage
from .edit_view import EditView
from .home_view import HomeView
from .result_view import ResultView
from .session_view import SessionView
from .setup_view import SetupView


class MainWindow(QMainWindow):
    def __init__(self, storage: Storage | None = None):
        super().__init__()
        self.setWindowTitle("VocabApp")
        self.resize(900, 680)
        self.storage = storage or Storage()
        self.storage.install_examples()
        self.lists: list[VocabList] = []
        self.session: Session | None = None
        self.dynamic = None   # écran de session / résultats courant

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        spell = SpellService()
        self.home = HomeView()
        self.edit = EditView(spell)
        self.setup = SetupView()
        for w in (self.home, self.edit, self.setup):
            self.stack.addWidget(w)

        h = self.home
        h.newRequested.connect(self.new_list)
        h.importRequested.connect(self.import_list)
        h.editRequested.connect(self.open_edit)
        h.deleteRequested.connect(self.delete_list)
        h.learnRequested.connect(self.open_setup)
        self.edit.backRequested.connect(self.go_home)
        self.edit.changed.connect(self.save_list)
        self.edit.exportRequested.connect(self.export_list)
        self.setup.backRequested.connect(self.go_home)
        self.setup.startRequested.connect(self.start_session)

        self.reload()

    # -- navigation ----------------------------------------------------------------
    def reload(self) -> None:
        res = self.storage.load_all()
        self.lists = res.lists
        self.home.set_lists(self.lists)
        if res.errors:
            QMessageBox.warning(self, "Fichiers ignorés",
                                "Certaines listes sont illisibles et ont été mises de côté :\n\n"
                                + "\n".join(res.errors))

    def go_home(self) -> None:
        self._drop_dynamic()
        self.reload()
        self.stack.setCurrentWidget(self.home)

    def _drop_dynamic(self) -> None:
        if self.dynamic is not None:
            self.stack.removeWidget(self.dynamic)
            self.dynamic.deleteLater()
            self.dynamic = None

    def _show_dynamic(self, widget) -> None:
        self._drop_dynamic()
        self.dynamic = widget
        self.stack.addWidget(widget)
        self.stack.setCurrentWidget(widget)

    # -- listes --------------------------------------------------------------------
    def new_list(self) -> None:
        self.edit.load(VocabList(name=""))
        self.stack.setCurrentWidget(self.edit)

    def open_edit(self, vlist: VocabList) -> None:
        self.edit.load(vlist)
        self.stack.setCurrentWidget(self.edit)

    def save_list(self, vlist: VocabList) -> None:
        try:
            self.storage.save(vlist)
        except OSError as exc:
            QMessageBox.critical(self, "Sauvegarde impossible", str(exc))

    def delete_list(self, vlist: VocabList) -> None:
        r = QMessageBox.question(self, "Supprimer", f"Supprimer la liste « {vlist.name} » ?")
        if r == QMessageBox.StandardButton.Yes:
            self.storage.delete(vlist)
            self.reload()

    def import_list(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Importer une liste", "", "Listes (*.json *.csv)")
        if not path:
            return
        try:
            vlist = self.storage.import_list(Path(path))
            if not vlist.pairs:
                raise ValueError("Le fichier ne contient aucun mot valide.")
            self.storage.save(vlist)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Import impossible", str(exc))
            return
        self.reload()

    def export_list(self, vlist: VocabList) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Exporter la liste", f"{vlist.name}.json",
                                              "JSON (*.json);;CSV (*.csv)")
        if path:
            try:
                self.storage.export_list(vlist, Path(path))
            except OSError as exc:
                QMessageBox.warning(self, "Export impossible", str(exc))

    # -- apprentissage ---------------------------------------------------------------
    def open_setup(self, vlist: VocabList | None = None) -> None:
        self.setup.load(self.lists, vlist)
        self.stack.setCurrentWidget(self.setup)

    def start_session(self, vlist: VocabList, options) -> None:
        try:
            self.session = Session.from_list(vlist, options)
        except ValueError as exc:
            QMessageBox.warning(self, "Session impossible", str(exc))
            return
        self._run(self.session)
        self._last = (vlist, options)

    def _run(self, session: Session) -> None:
        view = SessionView(session)
        view.finished.connect(self.show_results)
        view.quit.connect(self.go_home)
        self._show_dynamic(view)
        view.setFocus()

    def show_results(self, session: Session) -> None:
        view = ResultView(session)
        view.retryErrors.connect(lambda: self._run(session.retry_wrong()))
        view.restart.connect(lambda: self.start_session(*self._last))
        view.home.connect(self.go_home)
        self._show_dynamic(view)
