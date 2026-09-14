"""`tcw work tracker import`: claim a ticket, then create a backlog item bound to it.

The claim's own decisions are tested in `test_tracker_claim.py`. This file tests
what the command adds around them: no item without a claim, one item per ticket
and part, a claim that did not finish locally completing on a re-run, a binding
never taken as proof, and no credential anywhere.
"""

from __future__ import annotations

import contextlib
import io
import os
import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.store.fs import FsWorkStore, init
from tcw.tracker import jira
from tracker_fake import BASE_URL, FakeJira

SENTINEL = "sentinel-token-do-not-print"
A, B = "acct-a", "acct-b"
TICKET = "TCWCLAIM-6"
DESCRIPTION = "h2. Problem\n\nThe product text."


def _tracker(email_env: str) -> dict:
    return {
        "provider": "jira-cloud",
        "base-url": BASE_URL,
        "candidate-query": "assignee = currentUser()",
        "credentials": {"email-env": email_env, "token-env": "TCW_PROBE_TOKEN"},
        "transitions": {"claim": "Start Progress"},
    }


def make_node(tmp_path: Path, name: str, *, email_env: str | None) -> Path:
    """A git-backed work node. `email_env` is the account axis and has no default:
    `None` means no tracker is configured at all."""
    root = tmp_path / name
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root, project_id=name)
    config = yaml.safe_load((root / "tcw-config.yaml").read_text(encoding="utf-8"))
    if email_env is not None:
        config.setdefault("work", {})["tracker"] = _tracker(email_env)
    (root / "tcw-config.yaml").write_text(yaml.safe_dump(config, sort_keys=False),
                                          encoding="utf-8")
    return root


def run(root: Path, *argv: str) -> tuple[int, str, str]:
    """The CLI in-process, from `root`. Restores the working directory, so one run
    can happen inside another's request."""
    from tcw.cli import main
    previous = os.getcwd()
    out, err = io.StringIO(), io.StringIO()
    os.chdir(root)
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = main(["work", "tracker", *argv])
            except SystemExit as exit_:
                code = exit_.code or 0
    finally:
        os.chdir(previous)
    return code, out.getvalue(), err.getvalue()


@pytest.fixture()
def fake(monkeypatch):
    monkeypatch.setenv("TCW_A_EMAIL", "a@example.test")
    monkeypatch.setenv("TCW_B_EMAIL", "b@example.test")
    monkeypatch.setenv("TCW_PROBE_TOKEN", SENTINEL)
    fake = FakeJira()
    fake.account("a@example.test", A, "Alice")
    fake.account("b@example.test", B, "Bob")
    fake.ticket(id="10052", key=TICKET, summary="A ready ticket", description=DESCRIPTION)
    return fake.install(monkeypatch)


@pytest.fixture()
def node(tmp_path, fake):
    return make_node(tmp_path, "alpha", email_env="TCW_A_EMAIL")


def items(root: Path) -> list:
    return [i for i in FsWorkStore.open(root).query()]


def binding(root: Path, slug: str) -> dict:
    return yaml.safe_load(FsWorkStore.open(root).read_sidecar(slug, "tracker.yaml").content)


def assert_no_item(root: Path) -> None:
    assert items(root) == [], [i.slug for i in items(root)]


def write_binding(root: Path, title: str, **overrides) -> str:
    st = FsWorkStore.open(root)
    slug = st.create(title).slug
    doc = {"schema": 1, "provider": "jira-cloud", "project": "alpha", "part": "default",
           "ticket": {"id": "10052", "key": TICKET, "url": f"{BASE_URL}/browse/{TICKET}"},
           "claimed-by": {"account-id": A, "name": "Alice"}, "bound": "2026-09-14",
           "unlinked": []}
    doc.update(overrides)
    st.write_sidecar(slug, "tracker.yaml", yaml.safe_dump(doc, sort_keys=False))
    return slug


# ── no tracker ───────────────────────────────────────────────────────────────


def test_with_no_tracker_import_refuses_naming_the_key(tmp_path, fake):
    root = make_node(tmp_path, "alpha", email_env=None)
    code, out, err = run(root, "import", TICKET)
    assert code == 1 and "work.tracker" in err and out == ""
    assert_no_item(root)
    assert fake.requests == []


# ── the ordinary path ────────────────────────────────────────────────────────


def test_import_claims_the_ticket_and_creates_one_bound_backlog_item(node, fake):
    code, out, err = run(node, "import", TICKET)
    assert code == 0, err
    [item] = items(node)
    assert out.strip() == item.slug
    assert item.status == "backlog" and not item.owner
    assert item.title == f"{TICKET} — A ready ticket"
    assert TICKET.lower() in item.slug
    assert fake.writes() == [("POST", "/rest/api/3/issue/10052/transitions"),
                             ("PUT", "/rest/api/3/issue/10052/assignee")]

    folder = FsWorkStore.open(node).path(item.slug)
    assert not (folder / "initial-request.md").exists()
    intake_md = (folder / "intake.md").read_text(encoding="utf-8")
    assert f"[{TICKET}]({BASE_URL}/browse/{TICKET})" in intake_md
    assert DESCRIPTION in intake_md

    doc = binding(node, item.slug)
    assert doc["schema"] == 1 and doc["provider"] == "jira-cloud"
    assert (doc["project"], doc["part"]) == ("alpha", "default")
    assert doc["ticket"] == {"id": "10052", "key": TICKET,
                             "url": f"{BASE_URL}/browse/{TICKET}"}
    assert doc["claimed-by"] == {"account-id": A, "name": "Alice"}
    assert doc["unlinked"] == []
    assert "claimed" in err and "In Progress" in err


def test_a_ticket_with_no_description_says_so(node, fake):
    fake.tickets["10052"].description = None
    assert run(node, "import", TICKET)[0] == 0
    [item] = items(node)
    text = (FsWorkStore.open(node).path(item.slug) / "intake.md").read_text(encoding="utf-8")
    assert "The ticket has no description." in text


def test_a_title_can_be_given(node, fake):
    assert run(node, "import", TICKET, "--title", "Build the API half")[0] == 0
    [item] = items(node)
    assert item.title == "Build the API half"


def test_a_refused_claim_creates_no_item(node, fake):
    fake.tickets["10052"].assignee = B
    code, out, err = run(node, "import", TICKET)
    assert code == 1 and "Bob" in err and out == ""
    assert fake.writes() == []
    assert_no_item(node)


@pytest.mark.parametrize("argv", [["--part", "A B"], ["--title", ""]])
def test_bad_arguments_are_refused_before_the_tracker_is_asked(node, fake, argv):
    code, _out, _err = run(node, "import", TICKET, *argv)
    assert code == 1
    assert fake.requests == []
    assert_no_item(node)


# ── two accounts, one ticket ─────────────────────────────────────────────────


def test_order_a_across_two_nodes_gives_one_item(tmp_path, fake):
    alpha = make_node(tmp_path, "alpha", email_env="TCW_A_EMAIL")
    beta = make_node(tmp_path, "beta", email_env="TCW_B_EMAIL")
    assert run(alpha, "import", TICKET)[0] == 0
    code, out, err = run(beta, "import", TICKET)
    assert code == 1 and "Alice" in err
    assert len(items(alpha)) == 1 and items(beta) == []
    assert fake.writes(B) == []


def test_order_c_across_two_nodes_gives_one_item(tmp_path, fake):
    """Beta reads the ready ticket; alpha then claims it completely; beta's
    transition is refused and its read-back shows alpha's assignment."""
    alpha = make_node(tmp_path, "alpha", email_env="TCW_A_EMAIL")
    beta = make_node(tmp_path, "beta", email_env="TCW_B_EMAIL")
    inner = []
    fake.before("POST", "/transitions", lambda: inner.append(run(alpha, "import", TICKET)),
                account=B)
    code, out, err = run(beta, "import", TICKET)
    assert inner[0][0] == 0
    assert code == 1 and "Alice" in err
    assert len(items(alpha)) == 1 and items(beta) == []
    assert ("PUT", "/rest/api/3/issue/10052/assignee") not in fake.writes(B)


# ── one item per ticket and part ─────────────────────────────────────────────


def test_importing_twice_returns_the_same_item(node, fake):
    first = run(node, "import", TICKET)
    writes = len(fake.writes())
    code, out, err = run(node, "import", TICKET)
    assert code == 0 and out == first[1] and "already bound" in err
    assert len(fake.writes()) == writes
    assert len(items(node)) == 1


def test_different_parts_make_different_items(node, fake):
    assert run(node, "import", TICKET, "--part", "api")[0] == 0
    writes = len(fake.writes())
    code, _out, err = run(node, "import", TICKET, "--part", "web")
    assert code == 0, err
    assert len(fake.writes()) == writes              # already yours: no write
    parts = sorted(binding(node, i.slug)["part"] for i in items(node))
    assert parts == ["api", "web"]


# ── a claim that did not finish locally ──────────────────────────────────────


def _re_run_finishes(node, fake):
    writes = len(fake.writes())
    code, out, err = run(node, "import", TICKET)
    assert code == 0, err
    assert "not claimed by this run" in err
    assert len(fake.writes()) == writes
    [item] = items(node)
    assert binding(node, item.slug)["ticket"]["id"] == "10052"


def test_a_binding_that_cannot_be_written_removes_the_item(node, fake, monkeypatch):
    original = FsWorkStore.write_sidecar

    def refuse(*args, **kwargs):
        raise subprocess.CalledProcessError(128, ["git", "add"], "index.lock exists")
    monkeypatch.setattr(FsWorkStore, "write_sidecar", refuse)
    code, _out, err = run(node, "import", TICKET)
    assert code == 1 and f"claimed {TICKET}" in err
    assert "run this command again" in err.lower()
    assert_no_item(node)
    monkeypatch.setattr(FsWorkStore, "write_sidecar", original)
    _re_run_finishes(node, fake)


def test_an_item_that_cannot_be_removed_either_is_named(node, fake, monkeypatch):
    def refuse(*args, **kwargs):
        raise subprocess.CalledProcessError(128, ["git"], "index.lock exists")
    monkeypatch.setattr(FsWorkStore, "write_sidecar", refuse)
    monkeypatch.setattr(FsWorkStore, "drop", refuse)
    code, _out, err = run(node, "import", TICKET)
    [item] = items(node)
    assert code == 1
    assert item.slug in err and f"tcw work drop {item.slug} --confirm" in err


def test_an_item_that_cannot_be_created_says_the_ticket_is_claimed(node, fake, monkeypatch):
    original = FsWorkStore.create_work

    def refuse(*args, **kwargs):
        raise ValueError("not inside a git repository")
    monkeypatch.setattr(FsWorkStore, "create_work", refuse)
    code, _out, err = run(node, "import", TICKET)
    assert code == 1 and f"claimed {TICKET}" in err and "not inside a git repository" in err
    monkeypatch.setattr(FsWorkStore, "create_work", original)
    _re_run_finishes(node, fake)


# ── a binding is not proof ───────────────────────────────────────────────────


def test_a_hand_written_binding_for_someone_elses_ticket_is_refused(node, fake):
    slug = write_binding(node, "Forged")
    fake.tickets["10052"].assignee = B
    code, out, err = run(node, "import", TICKET)
    assert code == 1
    assert slug in out + err and "Bob" in err
    assert fake.writes() == []


# ── bindings that cannot be read ─────────────────────────────────────────────


@pytest.mark.parametrize("content", ["- TCWCLAIM-6\n", "ticket: TCWCLAIM-6\n"])
def test_a_malformed_binding_refuses_import_and_names_the_item(node, fake, content):
    st = FsWorkStore.open(node)
    slug = st.create("Broken").slug
    # Written as a person with a text editor would, past the sidecar validation.
    (st.path(slug) / "tracker.yaml").write_text(content, encoding="utf-8")
    code, _out, err = run(node, "import", TICKET)
    assert code == 1 and slug in err
    assert fake.writes() == []


def test_two_items_holding_the_key_refuse_import_and_name_both(node, fake):
    first, second = write_binding(node, "First"), write_binding(node, "Second")
    code, _out, err = run(node, "import", TICKET)
    assert code == 1 and first in err and second in err
    assert fake.writes() == []


def test_problems_on_completed_items_do_not_stop_an_import(node, fake):
    st = FsWorkStore.open(node)
    for title in ("Finished one", "Finished two"):
        slug = write_binding(node, title)
        st.start(slug)
        st.complete(slug, "done", ["acked"])
    code, _out, err = run(node, "import", TICKET)
    assert code == 0, err


# ── no credential anywhere ───────────────────────────────────────────────────


def test_no_import_path_prints_or_stores_the_token(node, fake, monkeypatch):
    outputs = []
    outputs += run(node, "import", TICKET)[1:]                 # claims
    outputs += run(node, "import", TICKET)[1:]                 # already bound
    outputs += run(node, "import", TICKET, "--part", "web")[1:]  # already yours
    fake.tickets["10052"].assignee = B
    outputs += run(node, "import", TICKET, "--part", "api")[1:]  # refused
    fake.fail("GET", "/myself", jira._for_status(401, {}, "", "/myself"))
    outputs += run(node, "import", TICKET, "--part", "ops")[1:]  # error path
    assert all(SENTINEL not in text for text in outputs)
    store_root = FsWorkStore.open(node).root
    for path in store_root.rglob("*"):
        if path.is_file():
            assert SENTINEL not in path.read_text(encoding="utf-8", errors="replace"), path


def test_a_description_that_cannot_be_read_says_the_ticket_is_claimed(node, fake):
    fake.fail("GET", "/rest/api/2/issue/", jira.TrackerUnavailable("down"))
    code, _out, err = run(node, "import", TICKET)
    assert code == 1 and f"claimed {TICKET}" in err
    assert_no_item(node)
    _re_run_finishes(node, fake)
