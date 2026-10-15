import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from vocabapp.storage import Storage
from vocabapp.ui.main_window import MainWindow
from vocabapp.ui.session_view import SessionView
from vocabapp.ui.styles import STYLE

app = QApplication.instance() or QApplication([])
app.setStyleSheet(STYLE)


def test_full_flow(tmp_path):
    win = MainWindow(Storage(tmp_path))
    assert len(win.lists) == 4
    # Création + saisie d'une paire (avec faute : ne doit pas bloquer)
    win.new_list()
    win.edit.name.setText("Test")
    win.edit.tgt.setCurrentIndex(win.edit.tgt.findData("de"))
    win.edit.src_edit.setText("bonjour")
    win.edit.tgt_edit.setText("Hallooo")
    win.edit._commit_pair()
    win.edit.src_edit.setText("merci"); win.edit.tgt_edit.setText("danke")
    win.edit._commit_pair()
    win.reload()
    assert any(v.name == "Test" and len(v.pairs) == 2 for v in win.lists)
    assert "Hallooo" in win.edit.src_edit.spell.find_errors("Hallooo", "de")[0][2]

    # Session QCM
    vl = next(v for v in win.lists if "FR-DE" in v.name)
    win.open_setup(vl)
    win.setup.r_qcm.setChecked(True)
    win.setup._start()
    view = win.dynamic
    assert isinstance(view, SessionView)
    for _ in range(vl.pairs.__len__()):
        QTest.keyClick(view, Qt.Key.Key_1)
        QTest.keyClick(view, Qt.Key.Key_Return)
    assert win.dynamic.__class__.__name__ == "ResultView"

    # Session saisie + refaire les erreurs
    win.open_setup(vl)
    win.setup.shuffle.setChecked(False)
    win.setup._start()
    view = win.dynamic
    view.answer.setText("faux"); view._enter(); view._enter()
    assert view.session.score == 0
