"""What every work backend does, run against each one (TCW-70 AC 1).

TCW-71 adds the Jira backend as a third parameter. A case that depends on how
a backend names folders takes the name from what `create` returned.
"""

from datetime import date, datetime, timezone

import pytest
import yaml

from tcw.errors import NotFound, UsageError
from tcw.work.backend import Query, WorkBackend
from tcw.work.config import parse_work_config
from tcw.work.fs_backend import FsWorkBackend
from tcw.work.model import Changes, Slug
from tests.work.memory_backend import MemoryBackend

TAGS = ["bug", "docs", "ui", "api"]


class _Clock:
    def __init__(self):
        self.at = datetime(2026, 10, 2, 12, 0, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.at


def _memory(tmp_path, user):
    backend = MemoryBackend(tmp_path / "work", user=user)
    return backend, backend.set_reported_stage


def _filesystem(tmp_path, user):
    config, problems = parse_work_config({"tags": TAGS})
    assert problems == []
    backend = FsWorkBackend("tcw", tmp_path / "work", config, user,
                            report=lambda line: None,
                            today=lambda: date(2026, 10, 2), now=_Clock())

    def put_stage(folder, stage):
        path = tmp_path / "work" / folder / "item.yaml"
        data = yaml.safe_load(path.read_text())
        data["stage"] = "verify" if stage is None else stage
        path.write_text(yaml.safe_dump(data, sort_keys=False))

    return backend, put_stage


@pytest.fixture(params=[_memory, _filesystem], ids=["memory", "filesystem"])
def make(request, tmp_path):
    return lambda user=None: request.param(tmp_path, user)


@pytest.fixture
def backend(make):
    return make()[0]


def new(backend, title, stage="request", **props):
    return backend.create(title, Changes(**props), stage=stage, request=None)


def test_it_satisfies_the_protocol(backend):
    assert isinstance(backend, WorkBackend)


def test_create_and_read(backend):
    item = new(backend, "Add a thing!", add_tags=("bug",))
    assert item.slug.project == "tcw"
    assert item.slug.folder.endswith("add-a-thing")
    assert (item.title, item.stage, item.priority, item.tags) == (
        "Add a thing!", "request", "medium", ("bug",))
    assert backend.read(item.slug.folder) == item


def test_every_item_read_has_no_untracked_and_a_priority(backend):
    item = new(backend, "x")
    assert item.untracked == () and item.priority is not None


def test_an_unknown_folder_is_not_found(backend):
    with pytest.raises(NotFound):
        backend.read("2026-01-01-nope")
    with pytest.raises(NotFound):
        backend.update("2026-01-01-nope", Changes(title="x"))


def test_update(backend):
    item = new(backend, "x")
    updated = backend.update(item.slug.folder, Changes(priority="high",
                                                       add_tags=("docs",)))
    assert (updated.priority, updated.tags) == ("high", ("docs",))
    assert backend.read(item.slug.folder) == updated


def test_the_default_list_shows_unfinished_and_stageless_items(make):
    backend, put_stage = make()
    open_ = new(backend, "open")
    done = new(backend, "done", stage="completed")
    lost = new(backend, "lost")
    put_stage(lost.slug.folder, None)
    shown = {i.slug.folder for i in backend.list(Query())}
    assert shown == {open_.slug.folder, lost.slug.folder}
    assert backend.read(lost.slug.folder).stage is None
    every = {i.slug.folder for i in backend.list(Query(all=True))}
    assert done.slug.folder in every


def test_list_filters(backend):
    epic = new(backend, "epic")
    child = new(backend, "child", parent=epic.slug, add_tags=("docs",))
    new(backend, "other", add_tags=("bug",))
    assert [i.slug for i in backend.list(Query(parent=epic.slug))] == [child.slug]
    assert len(backend.list(Query(tags=frozenset({"docs", "bug"})))) == 2
    assert [i.slug for i in backend.list(
        Query(stages=frozenset({"request"}), tags=frozenset({"docs"})))] == [child.slug]


def test_the_tag_filter_matches_any_given_tag(backend):
    a = new(backend, "a", add_tags=("ui",))
    b = new(backend, "b", add_tags=("api", "ui"))
    c = new(backend, "c", add_tags=("api",))
    new(backend, "d")
    done = new(backend, "e", stage="completed", add_tags=("ui",))
    folders = lambda q: {i.slug.folder for i in backend.list(q)}
    assert folders(Query(tags=frozenset({"ui"}))) == {a.slug.folder, b.slug.folder}
    assert folders(Query(tags=frozenset({"ui", "api"}))) == {
        a.slug.folder, b.slug.folder, c.slug.folder}
    assert folders(Query(tags=frozenset({"ui"}), all=True)) == {
        a.slug.folder, b.slug.folder, done.slug.folder}


def test_stages_with_all_is_a_usage_error(backend):
    with pytest.raises(UsageError):
        backend.list(Query(stages=frozenset({"spec"}), all=True))


def test_lookup_of_an_unknown_name_is_none(backend):
    assert backend.lookup("NOPE-1") is None


def test_set_stage_records_its_note_as_a_comment(backend):
    item = new(backend, "x")
    assert backend.set_stage(item.slug.folder, "spec", "why") == "spec"
    assert backend.read(item.slug.folder).stage == "spec"
    assert backend.read_comments(item.slug.folder)[0].text == "why"


def test_set_stage_without_a_note_writes_no_comment(backend):
    item = new(backend, "x")
    backend.set_stage(item.slug.folder, "spec", None)
    assert backend.read_comments(item.slug.folder) == []


def test_rename_keeps_the_prefix(backend):
    item = new(backend, "old words")
    prefix = item.slug.folder[: -len("old-words")]
    renamed = backend.rename(item.slug.folder, "new-words")
    assert renamed.slug.folder == f"{prefix}new-words"
    with pytest.raises(NotFound):
        backend.read(item.slug.folder)


def test_the_request(backend):
    with_request = backend.create("a", Changes(), stage="request", request="Do X.\n")
    without = new(backend, "b")
    empty = backend.create("c", Changes(), stage="request", request="")
    assert backend.read_request(with_request.slug.folder) == "Do X.\n"
    assert backend.read_request(without.slug.folder) is None
    assert backend.read_request(empty.slug.folder) is None


def test_comments_newest_first(backend):
    folder = new(backend, "b").slug.folder
    for text in ("first", "second", "third"):
        backend.comment(folder, text)
    assert [c.text for c in backend.read_comments(folder)] == [
        "third", "second", "first"]
    assert [c.text for c in backend.read_comments(folder, limit=1)] == ["third"]


@pytest.mark.parametrize("user", ["sam", None])
def test_current_user(make, user):
    assert make(user)[0].current_user() == user
