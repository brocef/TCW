"""`tcw work rename` and `tcw work move` in Jira (TCW-114 Design 5.8, 7.3;
AC 12, AC 13's Jira half, AC 18; plan Steps 17 and 18)."""

from __future__ import annotations

import shutil

import pytest

from tests.statefiles import ITEM_STATE, write_state
from tests.work.jira.fake import FIELDS

ITEM = FIELDS["TCW Item"]


def wid(id_path: str) -> str:
    return f"tcw.work/{id_path}"


class Nest:
    """`TCW-1-epic` holding `TCW-2-p` holding `TCW-3-q`, and `TCW-4-r`, whose
    spec links P's full identifier."""

    def __init__(self, project):
        self.project = project
        self.fake = project.fake
        self.work = project.work
        self.keys = []
        self.paths = []
        under = ""
        for words in ("epic", "p", "q"):
            ticket = self.fake.ticket(words, project="TCW", status="Triage")
            ticket.custom[FIELDS["TCW Project"]] = "tcw"
            path = f"{under}/{ticket.key}-{words}" if under else f"{ticket.key}-{words}"
            ticket.custom[ITEM] = wid(path)
            write_state(self.work / path / ITEM_STATE,
                        f"ticket: {self.fake.site}/browse/{ticket.key}\n")
            self.keys.append(ticket.key)
            self.paths.append(path)
            under = path
        key, self.r = project.item("R", "r")
        self.spec = self.work / self.r / "spec" / "spec.md"
        self.spec.parent.mkdir(parents=True)
        self.spec.write_text(f"See [p](tcw://{wid(self.paths[1])}).\n")

    @property
    def epic(self) -> str:
        return self.paths[0]

    def new(self, i: int, words: str = "new") -> str:
        return self.paths[i].replace(self.epic, f"{self.keys[0]}-{words}", 1)

    def value(self, i: int) -> str:
        return self.fake.tickets[self.keys[i]].custom[ITEM]

    def edits(self) -> list[str]:
        return [p.split("?")[0].rsplit("/", 1)[1] for m, p, _ in self.fake.log
                if m == "PUT" and "/issue/" in p]


@pytest.fixture
def nest(jira_project):
    return Nest(jira_project)


def run(tcw, nest, *argv):
    return tcw(list(argv), nest.project.root)


def test_ac12_a_clean_rename(tcw, nest, monkeypatch):
    import tcw.object_folders as folders
    real = folders.os.rename
    seen = {}

    def rename(a, b):
        seen["spec rewritten"] = wid(nest.new(1)) in nest.spec.read_text()
        return real(a, b)
    monkeypatch.setattr(folders.os, "rename", rename)
    start = len(nest.fake.log)
    result = run(tcw, nest, "rename", nest.epic, "new")
    assert result.code == 0, result.err
    assert result.out.splitlines() == [f"{wid(nest.paths[i])} -> {wid(nest.new(i))}"
                                       for i in range(3)]
    after = [(m, p) for m, p, _ in nest.fake.log[start:]
             if p.endswith("/search/jql") or "/issue/TCW-" in p]
    searches = [i for i, (m, p) in enumerate(after) if p.endswith("/search/jql")]
    assert len(searches) == 1
    rest = [(m, p.split("?")[0].rsplit("/", 1)[1]) for m, p in after[searches[0] + 1:]]
    assert rest[:6] == [("GET", "TCW-1"), ("PUT", "TCW-1"), ("GET", "TCW-2"),
                        ("PUT", "TCW-2"), ("GET", "TCW-3"), ("PUT", "TCW-3")]
    assert [nest.value(i) for i in range(3)] == [wid(nest.new(i)) for i in range(3)]
    assert seen == {"spec rewritten": True}
    assert (nest.work / nest.new(2)).is_dir()


def test_ac12_failed_edits_are_finished_by_running_again(tcw, nest):
    """An edit Jira refuses (400) is exit 1; one it could not do (500) is
    exit 5, Jira could not be reached (the backend's table, Design 10)."""
    nest.fake.fail_edit(2, status=400)
    first = run(tcw, nest, "rename", nest.epic, "new")
    assert first.code == 1, first.err
    assert first.out == ""
    assert f"set {nest.keys[0]}'s TCW Item to {wid(nest.new(0))}" in first.err
    assert f"still to be set: {nest.keys[1]}, {nest.keys[2]}" in first.err
    assert "the folder is still at" in first.err
    assert "run the same command again" in first.err
    assert nest.edits().count(nest.keys[0]) == 1
    assert wid(nest.paths[1]) in nest.spec.read_text()
    assert (nest.work / nest.epic).is_dir()

    nest.fake.fail_edit(2)
    second = run(tcw, nest, "rename", nest.epic, "new")
    assert second.code == 5, second.err
    assert f"{nest.keys[0]}'s TCW Item already names {wid(nest.new(0))}" in second.err
    assert f"set {nest.keys[1]}'s TCW Item to {wid(nest.new(1))}" in second.err
    assert f"still to be set: {nest.keys[2]}" in second.err

    before = len(nest.edits())
    third = run(tcw, nest, "rename", nest.epic, "new")
    assert third.code == 0, third.err
    assert nest.edits()[before:] == [nest.keys[2]]
    assert wid(nest.new(1)) in nest.spec.read_text()
    assert (nest.work / nest.new(0)).is_dir()
    # No ticket was ever set back to an old value.
    assert not [b for m, p, b in nest.fake.log if m == "PUT" and b
                and b.get("fields", {}).get(ITEM) in [wid(p_) for p_ in nest.paths]]


def test_ac12_a_failed_folder_move_keeps_every_ticket_set(tcw, nest, monkeypatch):
    import tcw.object_folders as folders
    real = folders.os.rename

    def rename(a, b):
        raise PermissionError(13, "Permission denied")
    monkeypatch.setattr(folders.os, "rename", rename)
    result = run(tcw, nest, "rename", nest.epic, "new")
    assert result.code == 1, result.err
    assert [nest.value(i) for i in range(3)] == [wid(nest.new(i)) for i in range(3)]
    assert wid(nest.new(1)) in nest.spec.read_text()
    for key in nest.keys:
        assert f"set {key}'s TCW Item" in result.err
    assert "spec/spec.md" in result.err
    monkeypatch.setattr(folders.os, "rename", real)
    before = len(nest.edits())
    again = run(tcw, nest, "rename", nest.epic, "new")
    assert again.code == 0, again.err
    assert nest.edits()[before:] == []


def test_ac12_a_3x_value_stops_before_any_edit(tcw, nest):
    nest.fake.tickets[nest.keys[2]].custom[ITEM] = f"tcw/{nest.keys[2]}-q"
    before = nest.spec.read_text()
    result = run(tcw, nest, "rename", nest.epic, "new")
    assert result.code == 3, result.err
    assert nest.edits() == []
    assert nest.keys[2] in result.err and "tcw migrate" in result.err
    assert nest.spec.read_text() == before


def test_ac12_another_value_stops_before_any_edit(tcw, nest):
    nest.fake.tickets[nest.keys[1]].custom[ITEM] = wid("TCW-2-elsewhere")
    result = run(tcw, nest, "rename", nest.epic, "new")
    assert result.code == 3, result.err
    assert nest.edits() == []
    assert nest.keys[1] in result.err and "tcw validate --remote" in result.err
    assert (nest.work / nest.epic).is_dir()


def test_ac12_a_missing_ticket_stops_before_any_edit(tcw, nest):
    nest.fake.hide(nest.keys[1])
    result = run(tcw, nest, "rename", nest.epic, "new")
    assert result.code == 4, result.err
    assert f"Jira has no ticket {nest.keys[1]}" in result.err
    assert nest.edits() == []


def _after_search(nest, key, change):
    searched = []

    def callback(method, path):
        if path.endswith("/search/jql"):
            searched.append(path)
        elif searched and method == "GET" and path.split("?")[0].endswith(f"/issue/{key}"):
            change()
            nest.fake.before_request(None)
    nest.fake.before_request(callback)


def test_ac12_two_runs_at_once_meet_at_the_first_ticket(tcw, nest):
    other = wid(f"{nest.keys[0]}-other")
    _after_search(nest, nest.keys[0],
                  lambda: nest.fake.tickets[nest.keys[0]].custom.__setitem__(ITEM, other))
    before = nest.spec.read_text()
    result = run(tcw, nest, "rename", nest.epic, "new")
    assert result.code == 3, result.err
    assert nest.edits() == []
    assert nest.spec.read_text() == before and (nest.work / nest.epic).is_dir()
    assert nest.keys[0] in result.err and other in result.err
    assert "another command may be moving this item" in result.err
    assert "tcw validate --remote" in result.err
    assert "run the same command again" not in result.err


def test_ac12_a_clash_after_this_run_set_a_ticket(tcw, nest):
    other = wid(f"{nest.keys[0]}-other/{nest.keys[1]}-p")
    _after_search(nest, nest.keys[1],
                  lambda: nest.fake.tickets[nest.keys[1]].custom.__setitem__(ITEM, other))
    result = run(tcw, nest, "rename", nest.epic, "new")
    assert result.code == 3, result.err
    assert f"set {nest.keys[0]}'s TCW Item to {wid(nest.new(0))}" in result.err
    assert "pull its commit" in result.err
    assert "tcw validate --remote" in result.err
    assert ("in Jira set each ticket it reports to the identifier its folder now has"
            in result.err)
    assert "run the same command again" not in result.err


def test_ac12_the_second_way_out_finishes_at_the_other_place(tcw, nest):
    # The state the clash leaves once the other command has finished.
    other = f"{nest.keys[0]}-other"
    (nest.work / nest.epic).rename(nest.work / other)
    for i in (1, 2):
        nest.fake.tickets[nest.keys[i]].custom[ITEM] = wid(nest.new(i, "other"))
    nest.fake.tickets[nest.keys[0]].custom[ITEM] = wid(nest.new(0))
    nest.spec.write_text(f"See [p](tcw://{wid(nest.new(1, 'other'))}).\n")
    result = run(tcw, nest, "rename", other, "new")
    assert result.code == 0, result.err
    assert nest.edits() == [nest.keys[1], nest.keys[2]]
    assert [nest.value(i) for i in range(3)] == [wid(nest.new(i)) for i in range(3)]
    assert wid(nest.new(1)) in nest.spec.read_text()
    assert (nest.work / nest.new(0)).is_dir()


def test_ac12_the_folder_already_gone(tcw, nest, monkeypatch):
    import tcw.move as move
    real = move.rewrite_references

    def gone(root, pairs):
        shutil.move(str(nest.work / nest.epic), str(nest.work.parent / "elsewhere"))
        return real(root, pairs)
    monkeypatch.setattr(move, "rewrite_references", gone)
    result = run(tcw, nest, "rename", nest.epic, "new")
    assert result.code == 4, result.err
    assert "is no longer at" in result.err and "still at" not in result.err
    assert "tcw validate --remote" in result.err


def test_a_ticket_gone_between_the_search_and_its_edit(tcw, nest):
    _after_search(nest, nest.keys[1], lambda: nest.fake.hide(nest.keys[1]))
    result = run(tcw, nest, "rename", nest.epic, "new")
    assert result.code == 4, result.err
    assert f"Jira has no ticket {nest.keys[1]}" in result.err


def test_a_dropped_connection_after_the_first_edit(tcw, nest):
    nest.fake.drop_after_next_write(then_unreachable=True)
    result = run(tcw, nest, "rename", nest.epic, "new")
    assert result.code == 5, result.err
    assert f"set {nest.keys[0]}'s TCW Item" in result.err or \
        nest.value(0) == wid(nest.new(0))
    nest.fake.down = None
    before = len(nest.edits())
    again = run(tcw, nest, "rename", nest.epic, "new")
    assert again.code == 0, again.err
    assert nest.edits()[before:] == [nest.keys[1], nest.keys[2]]


def test_the_search_is_paged(tcw, jira_project):
    fake = jira_project.fake
    fake.page_size = 2
    keys, under = [], ""
    for words in ("e", "a", "b", "c", "d"):
        ticket = fake.ticket(words, project="TCW", status="Triage")
        ticket.custom[FIELDS["TCW Project"]] = "tcw"
        path = f"{keys[0]}-e/{ticket.key}-{words}" if keys else f"{ticket.key}-{words}"
        ticket.custom[ITEM] = wid(path)
        write_state(jira_project.work / path / ITEM_STATE,
                    f"ticket: {fake.site}/browse/{ticket.key}\n")
        keys.append(ticket.key)
    result = tcw(["rename", f"{keys[0]}-e", "f"], jira_project.root)
    assert result.code == 0, result.err
    edited = [p.rsplit("/", 1)[1] for m, p, _ in fake.log if m == "PUT"]
    assert sorted(edited) == sorted(keys)
    assert len([p for m, p, _ in fake.log if p.endswith("/search/jql")]) >= 3


def test_ac18_a_nested_identifier_too_long_makes_no_request(tcw, jira_project):
    fake = jira_project.fake
    epic = fake.ticket("e", project="TCW", status="Triage")
    epic.custom[ITEM] = wid(f"{epic.key}-e")
    write_state(jira_project.work / f"{epic.key}-e" / ITEM_STATE,
                f"ticket: {fake.site}/browse/{epic.key}\n")
    part = fake.ticket("p", project="TCW", status="Triage")
    used = len(wid(f"{epic.key}-e/{part.key}-"))
    words = "-".join(["abcdefghi"] * 30)[:250 - used].rstrip("-")
    path = f"{epic.key}-e/{part.key}-{words}"
    words_len = len(wid(path))
    write_state(jira_project.work / path / ITEM_STATE,
                f"ticket: {fake.site}/browse/{part.key}\n")
    extra = "e-" + "x" * (255 - words_len)            # one past the limit
    result = tcw(["rename", f"{epic.key}-e", extra], jira_project.root)
    assert result.code == 2, result.err
    assert "a full identifier is at most 255" in result.err
    assert not [m for m, p, _ in fake.log if m == "PUT"]


@pytest.mark.parametrize("words,said", [
    ("TCW-9-new", "a rename keeps the key TCW-1"),
    ("Not Words", "did you mean not-words?"),
])
def test_rename_rules_in_jira(tcw, nest, words, said):
    result = run(tcw, nest, "rename", nest.epic, words)
    assert result.code == 2
    assert said in result.err
    assert nest.edits() == []


def test_every_stop_of_a_jira_rename_is_finished_by_running_again(tcw, fake, tmp_path,
                                                                   monkeypatch):
    from tests.move_stops import Fixture, every_stop
    from tests.work.jira.conftest import ME, JiraProject, jira_config
    from tests.work.jira.fake import FakeJira
    from tests.work.projects import make_project
    made = []

    def make():
        folder = tmp_path / f"run-{len(made)}"
        made.append(folder)
        new_fake = FakeJira().install(monkeypatch)
        new_fake.account("dev@example.test", ME, "Dev Eloper")
        root = make_project(folder, "tcw", config=jira_config())
        made_nest = Nest(JiraProject(root, "tcw", new_fake))
        fixture = Fixture(folder, new_fake)
        fixture.nest = made_nest
        return fixture

    def command(fixture):
        return tcw(["rename", fixture.nest.epic, "new"], fixture.nest.project.root)
    total = every_stop(pytest.MonkeyPatch.context, make, command)
    # Three tickets, R's spec, and the folder.
    assert total == 5


def test_ac13_jira_moves_set_the_tcw_item(tcw, jira_project):
    _, epic = jira_project.item("Epic", "e")
    a_key, a = jira_project.item("A", "a")
    b_key, b = jira_project.item("B", "b")
    result = tcw(["move", a, "--into", epic], jira_project.root)
    assert result.code == 0, result.err
    assert jira_project.fake.tickets[a_key].custom[ITEM] == wid(f"{epic}/{a}")
    result = tcw(["move", b, "--into", "2026/q4"], jira_project.root)
    assert result.code == 0, result.err
    assert (jira_project.work / "2026/q4" / b / ITEM_STATE).is_file()
    assert jira_project.fake.tickets[b_key].custom[ITEM] == wid(f"2026/q4/{b}")


@pytest.mark.parametrize("form", ["{key}", "tcw.work/{key}"])
def test_into_a_key_is_the_folder_of_the_item_carrying_it(tcw, jira_project, form):
    """TCW-110 Design 3.1: `--into TCW-1` names the item carrying the key,
    as the item argument does, never a new folder named `TCW-1`."""
    epic_key, epic = jira_project.item("Epic", "e")
    a_key, a = jira_project.item("A", "a")
    into = form.format(key=epic_key, folder=epic)
    result = tcw(["move", a_key, "--into", into], jira_project.root)
    assert result.code == 0, result.err
    assert not (jira_project.work / epic_key).exists()
    assert (jira_project.work / epic / a / ITEM_STATE).is_file()
    assert jira_project.fake.tickets[a_key].custom[ITEM] == wid(f"{epic}/{a}")


def test_into_a_key_no_item_carries_is_not_found(tcw, jira_project):
    a_key, a = jira_project.item("A", "a")
    result = tcw(["move", a_key, "--into", "TCW-99"], jira_project.root)
    assert result.code == 4, result.err
    assert "carries the key TCW-99" in result.err
    assert not (jira_project.work / "TCW-99").exists()
    assert (jira_project.work / a / ITEM_STATE).is_file()
