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
    """Create, start and complete an item **through the CLI**.

    The deletion is orchestrated by the CLI rather than by the store, because it
    carries `pre`/`post` bindings and running a command is a CLI concern. A test
    that called `store.transition` directly would be exercising a path that
    deliberately stops short of removing anything.
    """
    import os

    store = FsWorkStore.open(root)
    item = store.create(title, created="2026-01-01")
    store.start(item.slug)
    cwd = os.getcwd()
    try:
        os.chdir(root)
        assert main(["work", "complete", item.slug,
                     "--resolution", "done", "--confirm"]) == 0
    finally:
        os.chdir(cwd)
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


# ── the auto-delete step and its bindings ────────────────────────────────────


def _bind(root: Path, **phases: list) -> None:
    config_path = root / "tcw-config.yaml"
    config = yaml.safe_load(config_path.read_text()) or {}
    config.setdefault("work", {}).setdefault("lifecycle", {}).setdefault(
        "transitions", {})["auto-delete"] = phases
    config_path.write_text(yaml.safe_dump(config, sort_keys=False))


def test_the_step_is_bindable_and_listed(tmp_path, monkeypatch, capsys):
    root = _node(tmp_path, retain={"completed": False})
    _bind(root, pre=[{"command": "true"}])
    monkeypatch.chdir(root)
    assert main(["validate"]) == 0
    assert main(["work", "lifecycle"]) == 0
    out = capsys.readouterr().out
    assert "auto-delete  [transition]" in out
    assert "completed | discarded → (removed)" in out


def test_a_pre_binding_sees_the_item_and_its_resolution(tmp_path, monkeypatch):
    root = _node(tmp_path, retain={"completed": False})
    witness = tmp_path / "witness"
    _bind(root, pre=[{"command":
                      f'printf "%s\\n%s\\n" "$TCW_ITEM_PATH" "$TCW_RESOLUTION" '
                      f'> {witness}; test -d "$TCW_ITEM_PATH"'}])
    slug = _resolve(root)
    item_path, resolution = witness.read_text().splitlines()
    assert item_path == str(root / "docs" / "work" / "completed" / slug)
    assert resolution == "done"


def test_the_archive_sees_a_committed_artifact(tmp_path, monkeypatch):
    """The tar an S3 upload would make, taken at hook time."""
    root = _node(tmp_path, retain={"completed": False})
    archive = tmp_path / "cold"
    archive.mkdir()
    _bind(root, pre=[{"command":
                      f'tar -czf {archive}/"$TCW_SLUG".tgz -C "$TCW_ITEM_PATH" .'}])
    slug = _resolve(root)
    assert (archive / f"{slug}.tgz").is_file()
    listed = subprocess.run(["tar", "-tzf", str(archive / f"{slug}.tgz")],
                            capture_output=True, text=True, check=True).stdout
    assert "./state.yaml" in listed
    assert not (root / "docs" / "work" / "completed" / slug).exists()


def test_a_binding_that_moves_the_item_away_is_not_an_error(tmp_path):
    root = _node(tmp_path, retain={"completed": False})
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    _bind(root, pre=[{"command": f'mv "$TCW_ITEM_PATH" {elsewhere}/"$TCW_SLUG"'}])
    slug = _resolve(root)
    assert (elsewhere / slug / "state.yaml").is_file()
    assert FsWorkStore.open(root).tombstone(slug).location


def test_a_failing_pre_keeps_the_item_and_says_so(tmp_path, monkeypatch, capsys):
    import os

    root = _node(tmp_path, retain={"completed": False})
    _bind(root, pre=[{"command": "exit 3"}])
    store = FsWorkStore.open(root)
    item = store.create("A thing", created="2026-01-01")
    store.start(item.slug)
    monkeypatch.chdir(root)
    assert main(["work", "complete", item.slug,
                 "--resolution", "done", "--confirm"]) == 1
    err = capsys.readouterr().err
    assert "auto-delete pre" in err
    assert f"tcw work delete {item.slug}" in err
    # Resolved, recorded, committed — and still here.
    assert (root / "docs" / "work" / "completed" / item.slug).is_dir()
    assert FsWorkStore.open(root).tombstone(item.slug) is not None


def test_delete_finishes_what_a_failed_archive_left(tmp_path, monkeypatch, capsys):
    root = _node(tmp_path, retain={"completed": False})
    _bind(root, pre=[{"command": "exit 3"}])
    store = FsWorkStore.open(root)
    item = store.create("A thing", created="2026-01-01")
    store.start(item.slug)
    monkeypatch.chdir(root)
    assert main(["work", "complete", item.slug,
                 "--resolution", "done", "--confirm"]) == 1
    _bind(root, pre=[{"command": "true"}])
    assert main(["work", "delete", item.slug]) == 0
    assert not (root / "docs" / "work" / "completed" / item.slug).exists()


def test_delete_refuses_a_live_item_and_a_retained_one(tmp_path, monkeypatch, capsys):
    root = _node(tmp_path)
    store = FsWorkStore.open(root)
    live = store.create("Live", created="2026-01-01")
    monkeypatch.chdir(root)
    assert main(["work", "delete", live.slug]) == 1
    assert "not resolved" in capsys.readouterr().err

    store.start(live.slug)
    assert main(["work", "complete", live.slug,
                 "--resolution", "done", "--confirm"]) == 0
    capsys.readouterr()
    assert main(["work", "delete", live.slug]) == 1
    assert "keeps resolved items" in capsys.readouterr().err


def test_a_retained_status_runs_no_auto_delete_bindings(tmp_path, monkeypatch):
    root = _node(tmp_path)
    witness = tmp_path / "witness"
    _bind(root, pre=[{"command": f"touch {witness}"}])
    _resolve(root)
    assert not witness.exists()


def test_post_runs_after_the_removal(tmp_path):
    root = _node(tmp_path, retain={"completed": False})
    witness = tmp_path / "witness"
    _bind(root,
          pre=[{"command": "true"}],
          post=[{"command": f'test ! -e "$TCW_ITEM_PATH" && touch {witness}'}])
    _resolve(root)
    assert witness.exists()


def test_a_skill_binding_is_reported_not_executed(tmp_path, monkeypatch, capsys):
    root = _node(tmp_path, retain={"completed": False})
    _bind(root, pre=[{"skill": "some:archiver"}])
    slug = _resolve(root)
    assert "invoke the some:archiver skill" in capsys.readouterr().err
    assert not (root / "docs" / "work" / "completed" / slug).exists()
