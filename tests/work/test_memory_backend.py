"""What only the in-memory test backend does: its call log, its knobs, and its
naming (TCW-69 Design 5). Behavior every backend shares is in
`test_backend_contract.py`."""

import pytest

from tcw.errors import MovedWithoutNote, Refused
from tcw.work.model import Changes, Slug
from tests.work.memory_backend import MemoryBackend


@pytest.fixture
def backend(tmp_path):
    return MemoryBackend(tmp_path / "work", user="sam")


def make(backend, title, stage="request", **props):
    return backend.create(title, Changes(**props), stage=stage, request=None)


def test_create_numbers_the_folder(backend, tmp_path):
    item = make(backend, "Add a thing!")
    assert item.slug == Slug("tcw", "1-add-a-thing")
    assert (tmp_path / "work" / "1-add-a-thing").is_dir()


def test_lookup_matches_a_whole_name(backend):
    backend.items["TCW-67-x"] = make(backend, "x")
    assert backend.lookup("TCW-67") == "TCW-67-x"
    assert backend.lookup("TCW-6") is None


def test_writes_are_logged_and_reads_are_not(backend):
    item = make(backend, "x")
    backend.set_stage(item.slug.folder, "spec", "why")
    backend.comment(item.slug.folder, "hi")
    writes = list(backend.calls)
    assert [c[0] for c in writes] == ["create", "set_stage", "comment"]
    backend.read(item.slug.folder)
    backend.read_request(item.slug.folder)
    backend.read_comments(item.slug.folder)
    backend.current_user()
    assert backend.calls == writes


def test_comments_carry_the_user(backend):
    item = make(backend, "x")
    backend.comment(item.slug.folder, "hi")
    assert backend.read_comments(item.slug.folder)[0].author == "sam"


def test_the_knobs(backend):
    item = make(backend, "x")
    backend.refuse_moves = True
    with pytest.raises(Refused):
        backend.set_stage(item.slug.folder, "spec", None)
    backend.refuse_moves = False
    backend.lose_notes = True
    with pytest.raises(MovedWithoutNote):
        backend.set_stage(item.slug.folder, "spec", "n")
    assert backend.stage_of(item.slug.folder) == "spec"
    backend.lose_notes = False
    backend.report_stage = "plan"
    assert backend.set_stage(item.slug.folder, "implement", None) == "plan"
