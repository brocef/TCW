"""Creation commits its own files, as a status move does (spec:
2026-09-29-make-work-new-and-work-escalate-commit-their-own-files-as-status-moves-do)."""

import subprocess
from http import HTTPStatus
from pathlib import Path

import yaml

from tcw.cli import main
from tcw.store.fs import FsWorkStore
from tcw.work.recursion import delegate, escalate

from test_recursion import _refuse_commits, commit_all, mk_node
from test_serve_write import _req, _start_server


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                          text=True, check=True).stdout


def head(root: Path) -> str:
    return git(root, "rev-parse", "HEAD").strip()


def last_commit(root: Path) -> tuple[str, list[str]]:
    subject = git(root, "log", "-1", "--format=%s").strip()
    files = git(root, "show", "--name-only", "--format=", "HEAD").split()
    return subject, files


def staged(root: Path) -> list[str]:
    return git(root, "diff", "--cached", "--name-only").split()


def node(tmp_path: Path) -> Path:
    root = mk_node(tmp_path, "repo")
    commit_all(root)
    return root


def set_work(root: Path, **keys) -> None:
    cfg = yaml.safe_load((root / "tcw-config.yaml").read_text()) or {}
    cfg.setdefault("work", {}).update(keys)
    (root / "tcw-config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    commit_all(root, "config")


def new(root: Path, monkeypatch, capsys, title: str = "First thing") -> tuple[int, str, str]:
    monkeypatch.chdir(root)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True, raising=False)
    code = main(["work", "new", title])
    out = capsys.readouterr()
    return code, out.out.strip(), out.err


# ── 1: new ───────────────────────────────────────────────────────────────────

def test_new_commits_the_item_and_nothing_else(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    (root / "unrelated.txt").write_text("mine")
    git(root, "add", "unrelated.txt")
    before = head(root)

    code, slug, err = new(root, monkeypatch, capsys)
    assert code == 0, err

    assert git(root, "rev-list", "--count", f"{before}..HEAD").strip() == "1"
    subject, files = last_commit(root)
    assert subject == f"tcw work: new {slug}"
    assert files and all(f.startswith(f"docs/work/backlog/{slug}/") for f in files), files
    assert staged(root) == ["unrelated.txt"]                 # still staged, not swept in


# ── 2: inbox accept ──────────────────────────────────────────────────────────

def test_inbox_accept_commits_the_item_and_the_entrys_removal(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    inbox = root / "docs" / "work" / "inbox"
    inbox.mkdir(exist_ok=True)
    (inbox / "2026-01-01-some-request.md").write_text("# Some request\n\nbody\n")
    commit_all(root, "entry")
    monkeypatch.chdir(root)

    assert main(["work", "inbox", "accept", "2026-01-01-some-request"]) == 0
    slug = capsys.readouterr().out.strip()

    subject, files = last_commit(root)
    assert subject == f"tcw work: 2026-01-01-some-request.md → {slug}", subject
    assert "docs/work/inbox/2026-01-01-some-request.md" in files, files
    assert any(f.startswith(f"docs/work/backlog/{slug}/") for f in files), files
    assert git(root, "status", "--porcelain").strip() == ""


# ── 3: escalate and delegate ─────────────────────────────────────────────────

def test_escalate_commits_in_the_parent_and_leaves_the_child_alone(tmp_path):
    parent = mk_node(tmp_path, "parent")
    child = mk_node(parent, "child")
    commit_all(child)                          # first: git cannot add an
    commit_all(parent)                         # embedded repository with no commit
    child_head = head(child)

    doc = escalate(child, "Needs a decision", body="details")

    subject, files = last_commit(parent)
    assert subject == f"tcw work: request from child → inbox/{doc.name}", subject
    assert files == [f"docs/work/inbox/{doc.name}"], files
    assert head(child) == child_head


def test_delegate_commits_in_the_child(tmp_path):
    parent = mk_node(tmp_path, "parent")
    child = mk_node(parent, "child")
    commit_all(child)                          # first: git cannot add an
    commit_all(parent)                         # embedded repository with no commit
    parent_head = head(parent)

    doc = delegate(parent, "child", "Do a thing", body="details")

    subject, files = last_commit(child)
    assert subject == f"tcw work: request from parent → inbox/{doc.name}", subject
    assert files == [f"docs/work/inbox/{doc.name}"], files
    assert head(parent) == parent_head


# ── 4: the switch off ────────────────────────────────────────────────────────

def test_with_the_switch_off_every_creation_is_staged_not_committed(
        tmp_path, monkeypatch, capsys):
    parent = mk_node(tmp_path, "parent")
    child = mk_node(parent, "child")
    commit_all(child)                          # first: git cannot add an
    commit_all(parent)                         # embedded repository with no commit
    set_work(parent, **{"auto-commit-transitions": False})
    before = head(parent)

    code, slug, err = new(parent, monkeypatch, capsys)
    assert code == 0, err
    doc = escalate(child, "Needs a decision", body="details")

    assert head(parent) == before
    names = staged(parent)
    assert f"docs/work/inbox/{doc.name}" in names, names      # escalate stages now
    assert any(n.startswith(f"docs/work/backlog/{slug}/") for n in names), names


# ── 5: a refused commit ──────────────────────────────────────────────────────

def test_a_refused_commit_still_reports_the_item_and_exits_0(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    _refuse_commits(root)
    before = head(root)

    code, slug, err = new(root, monkeypatch, capsys)

    assert code == 0
    assert slug and FsWorkStore.open(root).get(slug) is not None
    assert f"created {slug}, but committing it failed" in err, err
    assert "Commit it yourself" in err
    assert head(root) == before
    assert any(n.startswith(f"docs/work/backlog/{slug}/") for n in staged(root))


# ── 6: the tracker binding is in the same commit ─────────────────────────────

def test_an_owed_ticket_record_is_in_the_creation_commit(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    set_work(root, tracker={
        "provider": "jira-cloud",
        "base-url": "https://example.invalid",
        "candidate-query": "assignee = currentUser()",
        "credentials": {"email-env": "TCW_PROBE_EMAIL", "token-env": "TCW_PROBE_TOKEN"},
        "transitions": {"start": "Start Progress"},
        "statuses": {"backlog": "To Do", "active": "In Progress"},
        "create": {"project": "PROBE", "issue-type": "Task", "on-new": True},
    })
    monkeypatch.delenv("TCW_PROBE_EMAIL", raising=False)
    monkeypatch.delenv("TCW_PROBE_TOKEN", raising=False)

    code, slug, err = new(root, monkeypatch, capsys)
    assert code == 0, err

    _, files = last_commit(root)
    assert f"docs/work/backlog/{slug}/tracker.yaml" in files, (files, err)
    assert git(root, "status", "--porcelain").strip() == ""


# ── 7: the web app ───────────────────────────────────────────────────────────

def test_the_web_apps_creation_commits(tmp_path):
    root = node(tmp_path)
    httpd, base = _start_server(root)
    try:
        status, body = _req(base, "POST", "/api/work", {"title": "Filed on the web"})
    finally:
        httpd.shutdown()
        httpd.server_close()
    assert status == HTTPStatus.CREATED
    slug = body["item"]["slug"]
    assert last_commit(root)[0] == f"tcw work: new {slug}"


def test_the_web_app_still_creates_when_the_commit_is_refused(tmp_path):
    root = node(tmp_path)
    _refuse_commits(root)
    httpd, base = _start_server(root)
    try:
        status, body = _req(base, "POST", "/api/work", {"title": "Filed on the web"})
    finally:
        httpd.shutdown()
        httpd.server_close()
    assert status == HTTPStatus.CREATED
    assert FsWorkStore.open(root).get(body["item"]["slug"]) is not None
