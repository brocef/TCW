"""The Jira half of `tcw migrate` (TCW-116 Design 1.1, 1.6, 2.1-2.7, 5; plan
Step 9; criteria 12, 14, 43, 44, 57-59, 65, 66, 68).

Every run is against the fake Jira at F-single's site, `https://example.invalid`;
nothing here can reach a real one.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest

from tcw.migrate import execute
from tests.migrate import fixtures
from tests.migrate.fixtures import build_f_single, seed_tickets, snapshot
from tests.objectcli import tcw  # noqa: F401  (a fixture)
from tests.work.jira.fake import FIELDS, FakeJira

ITEM = FIELDS["TCW Item"]
REPO = Path(__file__).resolve().parents[2]
NOTHING_WRITTEN = "nothing was written; 'tcw migrate --no-jira' converts the files without Jira"
NOTHING_MORE = ("nothing more was written; 'tcw migrate --no-jira' finishes the files "
                "without Jira")
NO_JIRA_SUMMARY = ("tickets not converted (--no-jira): the TCW Item of every ticket of "
                   "Jira project APP whose TCW Project is 'app' and that holds a 3.x "
                   "value; run 'tcw migrate' to convert them")
EDITS = [
    "edit APP-1: C17 TCW Item: app/APP-1-a -> app.work/APP-1-a",
    "edit APP-2: C17 TCW Item: app/APP-2-b -> app.work/APP-2-b",
    "edit APP-3: C17 TCW Item: app/APP-3-gone -> app.work/APP-3-gone"]


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setenv(fixtures.EMAIL_VARIABLE, "dev@example.invalid")
    monkeypatch.setenv(fixtures.TOKEN_VARIABLE, "token")
    found = FakeJira(site=fixtures.SITE)
    found.install(monkeypatch)
    seed_tickets(found)
    return found


@pytest.fixture
def app(tmp_path):
    return build_f_single(tmp_path / "app")


def puts(fake) -> list[str]:
    return [p.split("?")[0].rsplit("/", 1)[1] for m, p, _ in fake.log if m == "PUT"]


def lines(done) -> list[str]:
    return done.err.splitlines()


def stop_after_phase_a(monkeypatch, run):
    """Run `run()` with the first step after phase A made to fail."""
    real = execute._perform

    def perform(step, root):
        if step.phase != "A":
            raise OSError(5, "made to fail")
        return real(step, root)
    with monkeypatch.context() as patch:
        patch.setattr(execute, "_perform", perform)
        return run()


# ── criteria 43, 44, 65: which tickets, and the edit ────────────────────────

def test_each_3x_ticket_of_this_project_is_edited_once(tcw, fake, app):
    before = {k: dict(t.custom) for k, t in fake.tickets.items()}
    done = tcw(["migrate"], app)
    assert done.code == 0, done.err
    assert puts(fake) == ["APP-1", "APP-2", "APP-3"]
    assert [b for m, _, b in fake.log if m == "PUT"] == [
        {"fields": {ITEM: "app.work/APP-1-a"}}, {"fields": {ITEM: "app.work/APP-2-b"}},
        {"fields": {ITEM: "app.work/APP-3-gone"}}]
    for key in ("APP-4", "APP-5", "APP-6", "APP-7", "APP-8"):
        assert fake.tickets[key].custom == before[key]
    assert [line for line in lines(done) if line.startswith("edit ")] == EDITS
    a10 = [line for line in lines(done) if line.startswith("  A10")]
    assert a10[0] == ("  A10 APP-5: TCW Item 'other/APP-5-e' is neither a TCW 3.x nor a "
                      "TCW 4 value of this project; it is not edited")
    assert a10[1].startswith("  A10 APP-6: TCW Item app/APP-6-xxx") and "256 characters" in a10[1]
    # The search used the 3.x field names' ids, with no status filter.
    searched = [b["jql"] for m, p, b in fake.log if p.endswith("/search/jql")]
    assert searched == ['project = "APP" AND cf[10002] IS NOT EMPTY ORDER BY created ASC']


def test_a_dry_run_lists_the_edits_and_makes_none(tcw, fake, app):
    before = snapshot(app, times=False)
    done = tcw(["migrate", "--dry-run"], app)
    assert done.code == 0, done.err
    assert [line for line in lines(done) if "edit " in line] == \
        [f"would {line}" for line in EDITS]
    assert puts(fake) == [] and snapshot(app, times=False) == before


def test_b16_when_the_edit_screen_lacks_the_field(tcw, fake, app):
    fake.off_edit_screen.add(("Task", ITEM))
    before = snapshot(app, times=False)
    done = tcw(["migrate"], app)
    assert done.code == 3
    assert any(line.startswith("  B16 APP-1: its edit screen does not offer the TCW Item")
               for line in lines(done))
    assert puts(fake) == [] and snapshot(app, times=False) == before


# ── criterion 58: Jira fails while planning ─────────────────────────────────

@pytest.mark.parametrize("fail, code", [("unreachable", 5), ("unset", 1),
                                        ("unauthorized", 1)])
@pytest.mark.parametrize("dry", [False, True])
def test_a_failure_while_planning_writes_nothing(tcw, fake, app, monkeypatch, fail, code, dry):
    if fail == "unset":
        monkeypatch.delenv(fixtures.EMAIL_VARIABLE)
    else:
        getattr(fake, fail)()
    before = snapshot(app, times=False)
    done = tcw(["migrate", *(["--dry-run"] if dry else [])], app)
    assert done.code == code, done.err
    assert snapshot(app, times=False) == before and puts(fake) == []
    if fail == "unset":
        assert fake.log == []
    assert "would write .tcw/tcw-migration.yaml: C10" in lines(done)
    if dry:
        assert "the tickets to edit could not be listed" in done.err
    else:
        assert lines(done)[-1] == NOTHING_WRITTEN


# ── criterion 57: --no-jira ──────────────────────────────────────────────────

def test_no_jira_makes_the_local_changes_and_no_request(tcw, fake, tmp_path):
    fake.unreachable()
    first = build_f_single(tmp_path / "one")
    done = tcw(["migrate", "--no-jira"], first)
    assert done.code == 0, done.err
    assert fake.log == []
    assert NO_JIRA_SUMMARY in lines(done)
    fake.down = None
    second = build_f_single(tmp_path / "two")
    plain = tcw(["migrate"], second)
    assert plain.code == 0, plain.err
    assert {k[len(str(first)):]: v for k, v in snapshot(first, times=False).items()} == \
        {k[len(str(second)):]: v for k, v in snapshot(second, times=False).items()}
    fake.log.clear()
    for key, ticket in fake.tickets.items():         # back to 3.x, for the later run
        if isinstance(ticket.custom.get(ITEM), str) and ticket.custom[ITEM].startswith(
                "app.work/") and key != "APP-4":
            ticket.custom[ITEM] = "app/" + ticket.custom[ITEM].split("/", 1)[1]
    before = snapshot(first, times=False)
    later = tcw(["migrate"], first)
    assert later.code == 0, later.err
    assert snapshot(first, times=False) == before
    assert puts(fake) == ["APP-1", "APP-2", "APP-3"]
    assert [line for line in lines(later) if line.startswith("edit ")] == EDITS


def test_a_dry_run_with_no_jira_makes_no_request(tcw, fake, app):
    done = tcw(["migrate", "--dry-run", "--no-jira"], app)
    assert done.code == 0, done.err
    assert fake.log == []
    assert NO_JIRA_SUMMARY in lines(done)


def test_the_flag_changes_nothing_for_a_files_project(tcw, fake, tmp_path):
    one = tcw(["migrate", "--dry-run"], build_f_single(tmp_path / "a", backend="files"))
    two = tcw(["migrate", "--dry-run", "--no-jira"],
              build_f_single(tmp_path / "b", backend="files"))
    assert one.code == two.code == 0
    assert one.err == two.err and fake.log == []


# ── criterion 12: Jira fails in phase F ──────────────────────────────────────

def test_a_failure_in_phase_f_leaves_the_tickets_named(tcw, fake, app):
    fake.fail_edit(2, then_unreachable=True)
    done = tcw(["migrate"], app)
    assert done.code == 5, done.err
    assert (app / ".tcw/tcw-config.yaml").is_file()
    assert not (app / "tcw-config.yaml").exists()
    assert not (app / ".tcw/tcw-migration-progress.yaml").exists()
    assert "  edit APP-2: C17 TCW Item: app/APP-2-b -> app.work/APP-2-b" in lines(done)
    assert "  edit APP-3: C17 TCW Item: app/APP-3-gone -> app.work/APP-3-gone" in lines(done)
    assert "run 'tcw migrate' again to finish" in lines(done)
    fake.down = None
    fake.log.clear()
    before = snapshot(app, times=False)
    again = tcw(["migrate"], app)
    assert again.code == 0, again.err
    assert puts(fake) == ["APP-2", "APP-3"]
    assert snapshot(app, times=False) == before


def test_credentials_refused_in_phase_f_is_exit_1(tcw, fake, app):
    def refuse(method, path):
        if method == "PUT":
            fake.unauthorized()
    fake.before_request(refuse)
    done = tcw(["migrate"], app)
    assert done.code == 1, done.err
    assert (app / ".tcw/tcw-config.yaml").is_file()


# ── criterion 14: a run after a finished one ─────────────────────────────────

def test_a_run_after_a_finished_one(tcw, fake, app):
    assert tcw(["migrate"], app).code == 0
    fake.log.clear()
    done = tcw(["migrate"], app)
    assert done.code == 0, done.err
    assert lines(done) == ["nothing to migrate"]
    assert puts(fake) == [] and any(p.endswith("/search/jql") for _, p, _ in fake.log)
    fake.unreachable()
    offline = tcw(["migrate"], app)
    assert offline.code == 5
    assert lines(offline)[-1] == "nothing to migrate in the files; the tickets could not be checked"
    fake.log.clear()
    flagged = tcw(["migrate", "--no-jira"], app)
    assert flagged.code == 0 and fake.log == []
    assert lines(flagged) == ["nothing to migrate in the files; tickets not checked (--no-jira)"]


# ── criterion 66: --no-jira never builds a client ────────────────────────────

def _no_jira_objects(monkeypatch):
    from tcw.work.jira.backend import JiraBackend
    from tcw.work.jira.client import JiraClient

    def refuse(*args, **kwargs):
        raise AssertionError("a Jira client or backend was built")
    monkeypatch.setattr(JiraClient, "__init__", refuse)
    monkeypatch.setattr(JiraBackend, "__init__", refuse)


@pytest.mark.parametrize("dry", [False, True])
def test_no_jira_builds_no_client_or_backend(tcw, fake, app, monkeypatch, dry):
    _no_jira_objects(monkeypatch)
    done = tcw(["migrate", "--no-jira", *(["--dry-run"] if dry else [])], app)
    assert done.code == 0, done.err
    assert fake.log == []


@pytest.mark.parametrize("dry", [False, True])
def test_no_jira_builds_none_when_following_a_progress_record(tcw, fake, app, monkeypatch, dry):
    stopped = stop_after_phase_a(monkeypatch, lambda: tcw(["migrate", "--no-jira"], app))
    assert stopped.code == 1, stopped.err
    assert (app / ".tcw/tcw-migration-progress.yaml").is_file()
    _no_jira_objects(monkeypatch)
    done = tcw(["migrate", "--no-jira", *(["--dry-run"] if dry else [])], app)
    assert done.code == 0, done.err
    assert fake.log == []
    assert (app / ".tcw/tcw-migration-progress.yaml").exists() == dry


def test_only_jira_py_names_the_jira_backend_and_one_function_imports_it():
    package = REPO / "tcw" / "migrate"
    naming, importing = [], []
    for path in sorted(package.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node_ in ast.walk(tree):
            names = []
            if isinstance(node_, ast.ImportFrom):
                names = [node_.module or ""] + [f"{node_.module}.{a.name}" for a in node_.names]
            elif isinstance(node_, ast.Import):
                names = [a.name for a in node_.names]
            if any(n.startswith("tcw.work.jira") for n in names):
                naming.append(path.name)
            if any(n == "tcw.migrate.jira" for n in names):
                importing.append((path.name, node_))
        if path.name == "plan.py":
            functions = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
            inside = {id(n) for n in ast.walk(functions["plan_jira_half"])}
            importing = [(name, n) for name, n in importing
                         if not (name == "plan.py" and id(n) in inside)]
    assert sorted(set(naming)) == ["jira.py"]
    assert importing == []


def test_planning_cannot_write_through_its_client(tcw, fake, app, monkeypatch):
    from tcw.migrate import jira

    def writing(project_id, backend):
        backend.client.edit_issue("APP-1", {ITEM: "x"})
    monkeypatch.setattr(jira, "plan_tickets", writing)
    with pytest.raises(AssertionError, match="edit_issue is not allowed while planning"):
        tcw(["migrate", "--dry-run"], app)
    assert puts(fake) == []
    # And with a progress record present.
    stopped = stop_after_phase_a(monkeypatch, lambda: tcw(["migrate", "--no-jira"], app))
    assert stopped.code == 1, stopped.err
    with pytest.raises(AssertionError, match="edit_issue is not allowed"):
        tcw(["migrate", "--dry-run"], app)
    assert puts(fake) == []


@pytest.mark.parametrize("name", ["create_issue", "edit_issue", "apply_transition",
                                  "add_comment", "add_link", "delete_link", "_request",
                                  "_payload", "_json", "config", "new_writer"])
def test_the_read_only_client_refuses(name):
    from tcw.migrate.jira import _ReadOnlyClient
    with pytest.raises(AssertionError, match=f"{name} is not allowed while planning"):
        getattr(_ReadOnlyClient(object()), name)


def test_the_read_only_client_passes_its_six_calls():
    from tcw.migrate.jira import ALLOWED, _ReadOnlyClient

    class Client:
        pass
    client = Client()
    for name in ALLOWED:
        setattr(client, name, name)
    wrapped = _ReadOnlyClient(client)
    assert sorted(ALLOWED) == ["create_metadata", "edit_metadata", "issue", "myself",
                               "project", "search"]
    assert all(getattr(wrapped, name) == name for name in ALLOWED)


# ── spec Design 2.7: the Jira half of a run following a progress record ─────

def _stopped(tcw, monkeypatch, app):
    done = stop_after_phase_a(monkeypatch, lambda: tcw(["migrate"], app))
    assert done.code == 1, done.err
    assert (app / ".tcw/tcw-migration-progress.yaml").is_file()


def test_the_rerun_searches_before_its_first_write(tcw, fake, app, monkeypatch):
    _stopped(tcw, monkeypatch, app)
    order = []
    real = execute._write

    def write(path, text):
        order.append("write")
        return real(path, text)
    monkeypatch.setattr(execute, "_write", write)
    fake.before_request(lambda method, path: order.append(path))
    done = tcw(["migrate"], app)
    assert done.code == 0, done.err
    assert order.index("/rest/api/3/search/jql") < order.index("write")
    assert puts(fake) == ["APP-1", "APP-2", "APP-3"]


@pytest.mark.parametrize("patched", [False, True])
def test_the_rerun_writes_nothing_more_when_jira_fails(tcw, fake, app, monkeypatch, patched):
    _stopped(tcw, monkeypatch, app)
    if patched:
        monkeypatch.setattr("tcw.migrate.plan.make_plan",
                            lambda *a, **k: (_ for _ in ()).throw(AssertionError))
    stopped = snapshot(app, times=False)
    fake.unreachable()
    done = tcw(["migrate"], app)
    assert done.code == 5
    assert lines(done)[-1] == NOTHING_MORE
    assert snapshot(app, times=False) == stopped
    fake.down = None
    fake.off_edit_screen.add(("Task", ITEM))
    refused = tcw(["migrate"], app)
    assert refused.code == 3
    assert "  B16 APP-1:" in refused.err
    assert snapshot(app, times=False) == stopped and puts(fake) == []
    fake.off_edit_screen.clear()
    dry = tcw(["migrate", "--dry-run"], app)
    assert dry.code == 0, dry.err
    assert [line for line in lines(dry) if "edit " in line] == \
        [f"would {line}" for line in EDITS]
    assert any(line.startswith("would write .tcw/tcw-config.yaml: C1") for line in lines(dry))
    assert puts(fake) == [] and snapshot(app, times=False) == stopped


# ── Decided 11 and criterion 68: which Jira settings ─────────────────────────

def test_the_settings_are_read_from_tcw_once_the_root_files_are_gone(tcw, fake, app,
                                                                     monkeypatch):
    assert tcw(["migrate", "--no-jira"], app).code == 0
    monkeypatch.setitem(FIELDS, "Other Item", "customfield_10005")
    for ticket in fake.tickets.values():
        if ITEM in ticket.custom:
            ticket.custom["customfield_10005"] = ticket.custom[ITEM]
    shared = app / ".tcw/tcw-config.yaml"
    shared.write_text(shared.read_text().replace("item: TCW Item", "item: Other Item"))
    done = tcw(["migrate"], app)
    assert done.code == 0, done.err
    assert any("cf[10005]" in b["jql"] for m, p, b in fake.log if p.endswith("/search/jql"))
    assert [b for m, _, b in fake.log if m == "PUT"][0] == \
        {"fields": {"customfield_10005": "app.work/APP-1-a"}}


def test_credentials_only_in_the_3x_personal_file_are_used(tcw, fake, tmp_path, monkeypatch):
    """Also: the user-wide `not_tags` (A5) does not stop the Jira half."""
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG")
    root = build_f_single(tmp_path / "app", config_home=Path(os.environ["XDG_CONFIG_HOME"]))
    shared = root / "tcw-config.yaml"
    text = shared.read_text()
    block = (f"    credentials:\n      email-env: {fixtures.EMAIL_VARIABLE}\n"
             f"      token-env: {fixtures.TOKEN_VARIABLE}\n")
    assert block in text
    shared.write_text(text.replace(block, ""))
    local = root / "tcw-config.local.yaml"
    local.write_text(local.read_text() + "work:\n  jira:\n" + block)
    done = tcw(["migrate"], root)
    assert done.code == 0, done.err
    assert puts(fake) == ["APP-1", "APP-2", "APP-3"]


def test_a_missing_jira_project_key_is_exit_1_naming_it(tcw, fake, app):
    assert tcw(["migrate", "--no-jira"], app).code == 0
    fake.log.clear()
    shared = app / ".tcw/tcw-config.yaml"
    shared.write_text(shared.read_text().replace("    project: APP\n", ""))
    before = snapshot(app, times=False)
    done = tcw(["migrate"], app)
    assert done.code == 1, done.err
    assert ("error: .tcw/tcw-config.yaml: work.jira.project: required; 'tcw migrate "
            "--no-jira' converts the files without Jira") in done.err
    assert snapshot(app, times=False) == before and fake.log == []


# ── the way back (Design 9.3, 5.4; plan Step 26) ────────────────────────────

def test_the_way_back_puts_every_3_x_value_back(tcw, fake, app):
    from tcw.migrate.jira import edited_tickets, restore_tickets, settings
    from tcw.work.jira.client import JiraClient
    before = {key: ticket.custom.get(ITEM) for key, ticket in fake.tickets.items()}
    done = tcw(["migrate"], app)
    assert done.code == 0, done.err
    pairs = edited_tickets(done.err)
    assert [(k, o, n) for k, o, n in pairs] == [
        ("APP-1", "app/APP-1-a", "app.work/APP-1-a"),
        ("APP-2", "app/APP-2-b", "app.work/APP-2-b"),
        ("APP-3", "app/APP-3-gone", "app.work/APP-3-gone")]
    fake.log.clear()
    restored = restore_tickets(pairs, JiraClient(settings(app)), app, "app")
    assert restored == ["APP-1", "APP-2", "APP-3"]
    assert {key: ticket.custom.get(ITEM) for key, ticket in fake.tickets.items()} == before
    fake.log.clear()
    assert restore_tickets(pairs, JiraClient(settings(app)), app, "app") == []
    assert puts(fake) == []


def test_a_dry_run_s_lines_are_not_edits():
    from tcw.migrate.jira import edited_tickets
    assert edited_tickets("would edit APP-1: C17 TCW Item: app/APP-1-a -> app.work/APP-1-a\n"
                          "edit APP-2: C17 TCW Item: app/APP-2-b -> app.work/APP-2-b\n") == \
        [("APP-2", "app/APP-2-b", "app.work/APP-2-b")]


def test_the_way_back_offers_a_ticket_whose_answer_was_lost(tcw, fake, app):
    """Review round 1, finding 2: Jira applies APP-2's edit and its answer is
    lost, so run 1 lists APP-2 as not done and run 2, finding it converted,
    has nothing to migrate. The way back over both outputs puts every
    ticket back."""
    from tcw.migrate.jira import edited_tickets, restore_tickets, settings
    from tcw.work.jira.client import JiraClient
    before = {key: ticket.custom.get(ITEM) for key, ticket in fake.tickets.items()}
    writes = []

    def lose_the_second_answer(method, path):
        if method == "PUT":
            writes.append(path)
            if len(writes) == 2:
                fake.drop_after_next_write()
    fake.before_request(lose_the_second_answer)
    one = tcw(["migrate"], app)
    assert one.code != 0, one.err
    assert f"  {EDITS[1]}" in lines(one) and EDITS[1] not in lines(one)
    assert fake.tickets["APP-2"].custom[ITEM] == "app.work/APP-2-b"
    fake.before_request(None)
    two = tcw(["migrate"], app)
    assert two.code == 0, two.err
    assert "nothing to migrate" in lines(two)
    pairs = edited_tickets(one.err + two.err)
    assert sorted(k for k, _, _ in pairs) == ["APP-1", "APP-2", "APP-3"]
    assert sorted(restore_tickets(pairs, JiraClient(settings(app)), app, "app")) == \
        ["APP-1", "APP-2", "APP-3"]
    assert {key: ticket.custom.get(ITEM) for key, ticket in fake.tickets.items()} == before


def test_a_not_done_ticket_never_edited_is_left_alone(tcw, fake, app):
    """Offering a ticket listed as not done that Jira never edited changes
    nothing: it still holds its 3.x value."""
    from tcw.migrate.jira import edited_tickets, restore_tickets, settings
    from tcw.work.jira.client import JiraClient
    done = tcw(["migrate", "--no-jira"], app)
    assert done.code == 0, done.err
    fake.log.clear()
    assert restore_tickets(edited_tickets(f"not done:\n  {EDITS[0]}\n"),
                           JiraClient(settings(app)), app, "app") == []
    assert puts(fake) == []
    assert fake.tickets["APP-1"].custom[ITEM] == "app/APP-1-a"


def test_edited_tickets_names_each_ticket_once():
    from tcw.migrate.jira import edited_tickets
    assert edited_tickets(f"not done:\n  {EDITS[0]}\n{EDITS[0]}\n  would {EDITS[1]}\n") == \
        [("APP-1", "app/APP-1-a", "app.work/APP-1-a")]


def test_a_way_back_that_leaves_a_ticket_out_names_those_it_put_back(tcw, fake, app):
    """Review round 1, finding 3: APP-2 was edited by hand since the run, so
    it is left out; APP-1 and APP-3 are put back, and the error says
    which is which."""
    from tcw.errors import BackendError
    from tcw.migrate.jira import edited_tickets, restore_tickets, settings
    from tcw.work.jira.client import JiraClient
    done = tcw(["migrate"], app)
    assert done.code == 0, done.err
    fake.tickets["APP-2"].custom[ITEM] = "app.work/APP-2-renamed"
    with pytest.raises(BackendError) as raised:
        restore_tickets(edited_tickets(done.err), JiraClient(settings(app)), app, "app")
    assert raised.value.pending == ["APP-2"]
    assert raised.value.restored == ["APP-1", "APP-3"]
    assert fake.tickets["APP-1"].custom[ITEM] == "app/APP-1-a"
    assert fake.tickets["APP-2"].custom[ITEM] == "app.work/APP-2-renamed"
