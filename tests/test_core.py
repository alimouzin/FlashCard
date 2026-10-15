import json
import random

import pytest

from vocabapp.learning.checker import is_correct
from vocabapp.learning.qcm import make_choices
from vocabapp.learning.session import Mode, Session, SessionOptions
from vocabapp.models import VocabList, WordPair
from vocabapp.storage import Storage


def sample():
    return VocabList("T", "fr", "de", [WordPair(f"m{i}", f"w{i}") for i in range(6)])


def test_checker_tolerance():
    assert is_correct("  Das   HAUS ", "das Haus")
    assert not is_correct("Haus", "das Haus")
    assert is_correct("glucklich", "glücklich", True)
    assert not is_correct("glucklich", "glücklich", False)
    assert is_correct("strasse", "Straße", True)
    assert is_correct("foyer", "maison / foyer")
    assert not is_correct("", "x")


def test_qcm_choices():
    ch = make_choices("a", ["a", "b", "c", "d", "e"], rng=random.Random(1))
    assert len(ch) == 4 and "a" in ch and len(set(ch)) == 4
    assert len(make_choices("a", ["a", "b"])) == 2


def test_session_and_retry():
    s = Session.from_list(sample(), SessionOptions(shuffle=False, count=3))
    assert s.total == 3
    s.submit("w0"); s.submit("zz"); s.submit("w2")
    assert s.finished and s.score == 2
    r = s.retry_wrong()
    assert r.total == 1 and r.current.answer == "w1"
    rev = Session.from_list(sample(), SessionOptions(reverse=True, shuffle=False))
    assert rev.current.question == "w0" and rev.question_lang == "de"


def test_empty_list():
    with pytest.raises(ValueError):
        Session.from_list(VocabList("x"), SessionOptions())


def test_storage_roundtrip_and_corruption(tmp_path):
    st = Storage(tmp_path)
    v = sample(); v.name = "Ça été"
    st.save(v)
    v.name = "Renommée"
    st.save(v)
    assert len(list(tmp_path.glob("*.json"))) == 1
    (tmp_path / "broken-abc.json").write_text("{pas du json", encoding="utf-8")
    res = st.load_all()
    assert [x.name for x in res.lists] == ["Renommée"] and len(res.errors) == 1
    assert (tmp_path / "broken-abc.json.bad").exists()
    st.delete(v)
    assert not st.load_all().lists


def test_import_export(tmp_path):
    st = Storage(tmp_path / "d")
    v = sample()
    for ext in ("json", "csv"):
        f = tmp_path / f"o.{ext}"
        st.export_list(v, f)
        back = st.import_list(f)
        assert back.source_lang == "fr" and back.target_lang == "de" and len(back.pairs) == 6
    (tmp_path / "bad.json").write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError):
        st.import_list(tmp_path / "bad.json")


def test_examples_load():
    from vocabapp.storage import examples_dir
    for f in examples_dir().glob("*.json"):
        assert len(VocabList.from_dict(json.loads(f.read_text(encoding="utf-8"))).pairs) >= 10
