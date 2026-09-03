"""`work.retain` — what happens to an item once it is resolved."""

import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.cli import main
from tcw.store.base import parse_retention
from tcw.store.fs import FsWorkStore, init


def _node(tmp_path: Path, retain: dict | None = None, ignore: bool = True) -> Path:
    root = tmp_path / "repo"
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "commit.gpgsign", "false"],
                   check=True)
    if retain is not None:
        # Written before init, so the scaffolding sees the declaration.
        (root / "tcw-config.yaml").write_text(
            yaml.safe_dump({"id": "repo-project", "work": {"retain": retain}},
                           sort_keys=False))
    init(["work"], root, "repo-project")
    if not ignore:
        (root / ".gitignore").write_text("")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "scaffold"], check=True)
    return root


def _resolve(root: Path, title: str = "A thing") -> str:
    store = FsWorkStore.open(root)
    item = store.create(title, created="2026-01-01")
    store.start(item.slug)
    store.transition(item.slug, "completed", {"resolution": "done"})
    return item.slug


# ── the parser ───────────────────────────────────────────────────────────────

def test_nothing_declared_retains_everything():
    assert parse_retention(None) == ({"completed": True, "discarded": True}, [])


def test_a_partial_declaration_defaults_the_rest():
    retention, problems = parse_retention({"completed": False})
    assert retention == {"completed": False, "discarded": True}
    assert problems == []


@pytest.mark.parametrize(
    "raw, expected",
    [
        ([], "expected a mapping"),
        ({"nope": True}, "unknown status 'nope'"),
        ({"completed": "yes"}, "expected true or false"),
    ],
)
def test_a_malformed_retention_reports_and_still_reads_safe(raw, expected):
    retention, problems = parse_retention(raw)
    assert any(expected in p for p in problems)
    # The safe value, not the mistake: never silently a deletion.
    assert retention["completed"] is True


# ── the default is inert ─────────────────────────────────────────────────────

def test_a_node_declaring_nothing_is_scaffolded_exactly_as_before(tmp_path):
    root = _node(tmp_path)
    rules = (root / ".gitignore").read_text()
    assert "docs/work/completed/*" in rules and "docs/work/discarded/*" in rules


def test_a_node_declaring_nothing_keeps_todays_resolution(tmp_path):
    root = _node(tmp_path)
    slug = _resolve(root)
    # Untracked-but-present, which is what the ignore rules have always done.
    assert (root / "docs" / "work" / "completed" / slug).is_dir()
    assert FsWorkStore.open(root).tombstone(slug) is not None


# ── the interlock ────────────────────────────────────────────────────────────

def test_auto_delete_refuses_while_the_folder_is_gitignored(tmp_path):
    root = _node(tmp_path)
    config_path = root / "tcw-config.yaml"
    config = yaml.safe_load(config_path.read_text())
    config.setdefault("work", {})["retain"] = {"completed": False}
    config_path.write_text(yaml.safe_dump(config, sort_keys=False))

    store = FsWorkStore.open(root)
    item = store.create("A thing", created="2026-01-01")
    store.start(item.slug)
    with pytest.raises(ValueError) as excinfo:
        store.transition(item.slug, "completed", {"resolution": "done"})
    assert ".gitignore" in str(excinfo.value)
    # Refused before the move: nothing happened.
    assert FsWorkStore.open(root).get(item.slug).status == "active"


def test_declaring_retention_stops_the_rules_being_scaffolded(tmp_path):
    root = _node(tmp_path, retain={"completed": False})
    rules = (root / ".gitignore").read_text() if (root / ".gitignore").exists() else ""
    assert "docs/work/completed/*" not in rules
    # The status that was not spoken for keeps its rule.
    assert "docs/work/discarded/*" in rules


def test_validate_reports_an_explicit_retain_against_the_rules(tmp_path, monkeypatch, capsys):
    root = _node(tmp_path)
    config_path = root / "tcw-config.yaml"
    config = yaml.safe_load(config_path.read_text())
    config.setdefault("work", {})["retain"] = {"completed": True}
    config_path.write_text(yaml.safe_dump(config, sort_keys=False))
    monkeypatch.chdir(root)
    assert main(["validate"]) == 1
    assert "is gitignored" in capsys.readouterr().err


def test_validate_is_silent_for_the_default(tmp_path, monkeypatch, capsys):
    root = _node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["validate"]) == 0


# ── auto-delete ──────────────────────────────────────────────────────────────

def _log(root: Path) -> list[str]:
    out = subprocess.run(["git", "-C", str(root), "log", "--format=%s"],
                         capture_output=True, text=True, check=True).stdout
    return out.splitlines()


def test_auto_delete_makes_two_commits_and_leaves_the_content_in_history(tmp_path):
    root = _node(tmp_path, retain={"completed": False})
    slug = _resolve(root)

    subjects = _log(root)
    assert subjects[0].startswith(f"tcw work: delete {slug}")
    assert subjects[1] == f"tcw work: {slug} → completed"
    assert not (root / "docs" / "work" / "completed" / slug).exists()

    grave = FsWorkStore.open(root).tombstone(slug)
    assert grave is not None and grave.location
    listed = subprocess.run(
        ["git", "-C", str(root), "ls-tree", "-r", "--name-only", grave.location],
        capture_output=True, text=True, check=True).stdout
    assert f"docs/work/completed/{slug}/state.yaml" in listed


def test_the_recorded_commit_still_holds_the_documents(tmp_path):
    root = _node(tmp_path, retain={"completed": False})
    slug = _resolve(root)
    grave = FsWorkStore.open(root).tombstone(slug)
    shown = subprocess.run(
        ["git", "-C", str(root), "show",
         f"{grave.location}:docs/work/completed/{slug}/state.yaml"],
        capture_output=True, text=True, check=True).stdout
    assert "title: A thing" in shown and "resolution: done" in shown


def test_the_slug_cannot_be_reissued_after_deletion(tmp_path):
    root = _node(tmp_path, retain={"completed": False})
    slug = _resolve(root, "A thing")
    again = FsWorkStore.open(root).create("A thing", created="2026-01-01")
    assert again.slug != slug


def test_delete_resolved_is_re_runnable_after_an_interrupted_removal(tmp_path):
    """The crash window: recorded, still present. Finishable, not broken."""
    root = _node(tmp_path, retain={"completed": True})
    slug = _resolve(root)
    store = FsWorkStore.open(root)
    assert (root / "docs" / "work" / "completed" / slug).is_dir()
    store.delete_resolved(slug)
    assert not (root / "docs" / "work" / "completed" / slug).exists()
    # Again, with the folder already gone — the hook-moved-it-away case.
    store.delete_resolved(slug)
    assert FsWorkStore.open(root).tombstone(slug).location


def test_show_answers_from_the_tombstone(tmp_path, monkeypatch, capsys):
    root = _node(tmp_path, retain={"completed": False})
    slug = _resolve(root)
    monkeypatch.chdir(root)
    assert main(["work", "show", slug]) == 0
    out = capsys.readouterr().out
    assert "(resolved)" in out
    assert "last present in commit" in out


def test_show_says_when_a_recorded_commit_is_gone(tmp_path, monkeypatch, capsys):
    root = _node(tmp_path, retain={"completed": False})
    slug = _resolve(root)
    store = FsWorkStore.open(root)
    store._write_tombstone(slug, "done", "2026-01-01", location="0" * 40)
    monkeypatch.chdir(root)
    assert main(["work", "show", slug]) == 0
    assert "which this clone does not have" in capsys.readouterr().out


def test_a_slug_that_never_existed_still_reports_that(tmp_path, monkeypatch, capsys):
    root = _node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "show", "2026-01-01-nothing-here"]) == 1
    assert "no such work item" in capsys.readouterr().err
