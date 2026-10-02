"""The in-memory backend the model's tests run against (TCW-69 Design 5; AC 21).

The later tests rely on these behaviors, so they are pinned here.
"""

import pytest

from tcw.errors import NotFound, UsageError
from tcw.work.backend import Query, WorkBackend, default_includes
from tcw.work.model import Changes, Slug
from tests.work.memory_backend import MemoryBackend


@pytest.fixture
def backend(tmp_path):
    return MemoryBackend(tmp_path / "work", user="sam")


def make(backend, title, stage="request", **props):
    return backend.create(title, Changes(**props), stage=stage, request=None)


def test_it_satisfies_the_protocol(backend):
    # A protocol check proves only that the names exist.
    assert isinstance(backend, WorkBackend)


def test_create_makes_the_folder(backend, tmp_path):
    item = make(backend, "Add a thing!", add_tags=("bug",))
    assert item.slug == Slug("tcw", "1-add-a-thing")
    assert (tmp_path / "work" / "1-add-a-thing").is_dir()
    assert item.priority == "medium"
    assert item.tags == ("bug",)
    assert backend.read("1-add-a-thing") == item


def test_an_unknown_folder_is_not_found(backend):
    with pytest.raises(NotFound):
        backend.read("nope")
    with pytest.raises(NotFound):
        backend.update("nope", Changes(title="x"))


def test_the_default_list_shows_unfinished_and_stageless_items(backend):
    open_ = make(backend, "open")
    done = make(backend, "done", stage="completed")
    lost = make(backend, "lost")
    backend.set_reported_stage(lost.slug.folder, None)
    shown = [i.slug.folder for i in backend.list(Query())]
    assert shown == [open_.slug.folder, lost.slug.folder]
    assert done.slug.folder in [i.slug.folder for i in backend.list(Query(all=True))]
    assert default_includes(None) and not default_includes("discarded")


def test_list_filters(backend):
    epic = make(backend, "epic")
    child = make(backend, "child", parent=epic.slug, add_tags=("docs",))
    make(backend, "other", add_tags=("bug",))
    assert [i.slug for i in backend.list(Query(parent=epic.slug))] == [child.slug]
    tagged = backend.list(Query(tags=frozenset({"docs", "bug"})))
    assert len(tagged) == 2
    assert [i.slug for i in backend.list(Query(stages=frozenset({"request"}),
                                               tags=frozenset({"docs"})))] == [child.slug]


def test_stages_with_all_is_a_usage_error(backend):
    with pytest.raises(UsageError):
        backend.list(Query(stages=frozenset({"spec"}), all=True))


def test_lookup_matches_a_whole_name(backend):
    backend.items["TCW-67-x"] = make(backend, "x")
    assert backend.lookup("TCW-67") == "TCW-67-x"
    assert backend.lookup("TCW-6") is None


def test_set_stage_records_its_note_as_a_comment(backend):
    item = make(backend, "x")
    assert backend.set_stage(item.slug.folder, "spec", "why") == "spec"
    assert backend.read(item.slug.folder).stage == "spec"
    assert backend.read_comments(item.slug.folder)[0].text == "why"
    assert backend.calls[-1] == ("set_stage", item.slug.folder, "spec", "why")


def test_rename_keeps_the_prefix(backend, tmp_path):
    item = make(backend, "old words")
    renamed = backend.rename(item.slug.folder, "new-words")
    assert renamed.slug.folder == "1-new-words"
    assert (tmp_path / "work" / "1-new-words").is_dir()
    with pytest.raises(NotFound):
        backend.read("1-old-words")


def test_the_three_reads(backend, tmp_path):
    with_request = backend.create("a", Changes(), stage="request", request="Do X.")
    without = make(backend, "b")
    assert backend.read_request(with_request.slug.folder) == "Do X."
    assert backend.read_request(without.slug.folder) is None

    folder = without.slug.folder
    for text in ("first", "second", "third"):
        backend.comment(folder, text)
    writes = list(backend.calls)
    assert [c.text for c in backend.read_comments(folder)] == [
        "third", "second", "first"]
    assert [c.text for c in backend.read_comments(folder, limit=1)] == ["third"]
    assert backend.read_comments(folder)[0].author == "sam"

    assert backend.current_user() == "sam"
    assert MemoryBackend(tmp_path / "other").current_user() is None
    assert backend.calls == writes
