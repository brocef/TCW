"""`work.retain` — what happens to an item once it is resolved."""

import shutil
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


# ── nothing is removed that git does not hold ────────────────────────────────


def _log_shas(root: Path) -> list[str]:
    return subprocess.run(["git", "-C", str(root), "log", "--format=%H"],
                          capture_output=True, text=True, check=True).stdout.split()


def test_delete_refuses_an_item_no_commit_holds(tmp_path, monkeypatch, capsys):
    """The shipped ignore rules untrack a resolved item, so no commit has it.

    `tcw work delete` reaches the removal without passing the interlock the
    resolving transition consults, so this is the case where an item that git
    never held would be destroyed with a message naming a commit that does not
    contain it.
    """
    root = _node(tmp_path)                       # default: the rules are written
    slug = _resolve(root)
    folder = root / "docs" / "work" / "completed" / slug
    assert folder.is_dir()

    config_path = root / "tcw-config.yaml"
    config = yaml.safe_load(config_path.read_text())
    config.setdefault("work", {})["retain"] = {"completed": False}
    config_path.write_text(yaml.safe_dump(config, sort_keys=False))

    monkeypatch.chdir(root)
    assert main(["work", "delete", slug]) == 1
    err = capsys.readouterr().err
    assert "no commit holds" in err
    assert folder.is_dir(), "the item was destroyed"


def test_delete_refuses_an_item_with_uncommitted_content(tmp_path, monkeypatch, capsys):
    """A `pre` binding's receipt, or any edit since the resolving commit."""
    root = _node(tmp_path, retain={"completed": False})
    slug = _resolve(root)
    # Re-create the item as if a run had been interrupted before the removal.
    folder = root / "docs" / "work" / "completed" / slug
    subprocess.run(["git", "-C", str(root), "revert", "--no-edit", "HEAD"],
                   capture_output=True, check=True)
    assert folder.is_dir()
    (folder / "receipt.txt").write_text("uploaded\n")

    monkeypatch.chdir(root)
    assert main(["work", "delete", slug]) == 1
    err = capsys.readouterr().err
    assert "no commit holds" in err
    assert (folder / "receipt.txt").is_file()


def test_delete_refuses_when_the_move_was_never_committed(tmp_path, monkeypatch, capsys):
    root = _node(tmp_path, retain={"completed": False})
    config_path = root / "tcw-config.yaml"
    config = yaml.safe_load(config_path.read_text())
    config["work"]["auto-commit-transitions"] = False
    config_path.write_text(yaml.safe_dump(config, sort_keys=False))
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "config"], check=True)

    store = FsWorkStore.open(root)
    item = store.create("A thing", created="2026-01-01")
    store.start(item.slug)
    monkeypatch.chdir(root)
    assert main(["work", "complete", item.slug,
                 "--resolution", "done", "--confirm"]) == 1
    err = capsys.readouterr().err
    assert "no commit holds" in err
    assert "auto-commit-transitions is false" in err
    assert (root / "docs" / "work" / "completed" / item.slug).is_dir()


def test_a_re_run_keeps_the_commit_that_holds_the_item(tmp_path):
    """The second run's HEAD no longer holds it; recording HEAD again would
    replace a working reference with a useless one."""
    root = _node(tmp_path, retain={"completed": False})
    slug = _resolve(root)
    store = FsWorkStore.open(root)
    first = store.tombstone(slug).location
    assert first

    store.delete_resolved(slug)
    assert FsWorkStore.open(root).tombstone(slug).location == first
    listed = subprocess.run(
        ["git", "-C", str(root), "ls-tree", "-r", "--name-only", first],
        capture_output=True, text=True, check=True).stdout
    assert f"docs/work/completed/{slug}/state.yaml" in listed


def test_a_moved_away_item_still_has_its_removal_committed(tmp_path):
    """A `pre` binding that relocates the item leaves nothing for `_get_now`,
    and the removal used to be left out of the commit — so the remote kept an
    item the store had deleted."""
    root = _node(tmp_path, retain={"completed": False})
    elsewhere = tmp_path / "cold"
    elsewhere.mkdir()
    _bind(root, pre=[{"command": f'mv "$TCW_ITEM_PATH" {elsewhere}/"$TCW_SLUG"'}])
    slug = _resolve(root)

    assert (elsewhere / slug / "state.yaml").is_file()
    tracked = subprocess.run(["git", "-C", str(root), "ls-tree", "-r",
                              "--name-only", "HEAD"],
                             capture_output=True, text=True, check=True).stdout
    assert f"docs/work/completed/{slug}" not in tracked
    # Scoped to the store: `_bind` edits the config after the scaffold commit,
    # which is fixture noise and not what this asserts.
    assert subprocess.run(["git", "-C", str(root), "status", "--porcelain",
                           "--", "docs/work"],
                          capture_output=True, text=True,
                          check=True).stdout.strip() == "", \
        "the removal was left out of the commit"


# ── the state a failed archive leaves, and what still has to happen ──────────

def test_delete_finishes_a_removal_whose_binding_moved_the_item_and_failed(
        tmp_path, monkeypatch, capsys):
    """The half-deleted state: no folder, and no record of where it went.

    `delete_resolved` is documented safe to re-run precisely so this is
    finishable, but the CLI refused anything `get()` could not find — which is
    every item in this state — so the tree kept an unstaged deletion forever.
    """
    root = _node(tmp_path, retain={"completed": False})
    elsewhere = tmp_path / "cold"
    elsewhere.mkdir()
    _bind(root, pre=[{"command": f'mv "$TCW_ITEM_PATH" {elsewhere}/"$TCW_SLUG"; exit 3'}])
    store = FsWorkStore.open(root)
    item = store.create("A thing", created="2026-01-01")
    store.start(item.slug)
    monkeypatch.chdir(root)
    assert main(["work", "complete", item.slug,
                 "--resolution", "done", "--confirm"]) == 1
    capsys.readouterr()
    # Exactly the state the finding describes.
    assert FsWorkStore.open(root).get(item.slug) is None
    assert not FsWorkStore.open(root).tombstone(item.slug).location
    assert (elsewhere / item.slug / "state.yaml").is_file()

    _bind(root, pre=[{"command": "true"}])
    assert main(["work", "delete", item.slug]) == 0
    assert FsWorkStore.open(root).tombstone(item.slug).location
    assert subprocess.run(["git", "-C", str(root), "status", "--porcelain",
                           "--", "docs/work"],
                          capture_output=True, text=True,
                          check=True).stdout.strip() == ""


def test_delete_says_so_when_the_removal_is_already_finished(
        tmp_path, monkeypatch, capsys):
    """Idempotent rather than an error: the command finishes a removal, and one
    already finished is the state it was asked to reach."""
    root = _node(tmp_path, retain={"completed": False})
    slug = _resolve(root)
    monkeypatch.chdir(root)
    assert main(["work", "delete", slug]) == 0
    assert "already removed" in capsys.readouterr().out


def test_a_failed_auto_delete_still_reports_the_completion(
        tmp_path, monkeypatch, capsys):
    """`_complete` returned from the auto-delete branch, so the completion it
    had already committed was never reported and its `post` result discarded."""
    root = _node(tmp_path, retain={"completed": False})
    _bind(root, pre=[{"command": "exit 3"}])
    store = FsWorkStore.open(root)
    item = store.create("A thing", created="2026-01-01")
    store.start(item.slug)
    monkeypatch.chdir(root)
    assert main(["work", "complete", item.slug,
                 "--resolution", "done", "--confirm"]) == 1
    captured = capsys.readouterr()
    assert f"completed {item.slug} (done)" in captured.out
    assert "auto-delete pre" in captured.err


def test_a_failed_auto_delete_still_removes_the_worktree(tmp_path, monkeypatch,
                                                         capsys):
    """`merge_worktree` has already run by then, so an early return orphaned the
    worktree and its branch with nothing left that would clean them."""
    root = _node(tmp_path, retain={"completed": False})
    _bind(root, pre=[{"command": "exit 3"}])
    store = FsWorkStore.open(root)
    item = store.create("A thing", created="2026-01-01")
    monkeypatch.chdir(root)
    assert main(["work", "start", item.slug, "--worktree"]) == 0
    worktree = root / ".worktrees" / item.slug
    assert worktree.is_dir()
    capsys.readouterr()
    assert main(["work", "complete", item.slug,
                 "--resolution", "done", "--confirm"]) == 1
    assert not worktree.exists()


def test_a_publication_failure_after_the_removal_is_not_a_failed_removal(
        tmp_path, monkeypatch, capsys):
    """The push is the only thing that did not land. Reading that as "still
    here" made the caller print a location for a folder that is gone."""
    from tcw.store.base import PublicationError
    from tcw.store.fs import FsWorkStore as _Store

    root = _node(tmp_path, retain={"completed": False})
    store = _Store.open(root)
    item = store.create("A thing", created="2026-01-01")
    store.start(item.slug)
    # The removal's own push, not the completion's — the failure this is about
    # happens after the folder is already gone and its removal committed.
    calls = []

    def _publish(self, slug, to_status):
        calls.append(slug)
        if len(calls) > 1:
            raise PublicationError(
                f"{slug} moved to {to_status} and was committed — your work is "
                f"saved there — but publishing it to the declared remote failed:\n"
                f"no remote")

    monkeypatch.setattr(_Store, "_publish_after_transition", _publish)
    monkeypatch.chdir(root)
    assert main(["work", "complete", item.slug,
                 "--resolution", "done", "--confirm"]) == 1
    captured = capsys.readouterr()
    assert not (root / "docs" / "work" / "completed" / item.slug).exists()
    # The completion is reported, and never with a path to a folder that is gone.
    assert f"completed {item.slug} (done)" in captured.out
    assert "docs/work/completed" not in captured.out
    assert "publishing it to the declared remote failed" in captured.err


def test_show_json_on_a_removed_slug_prints_no_json_and_fails(
        tmp_path, monkeypatch, capsys):
    """The tombstone branch sat ahead of the `--json` branch, so a caller piping
    to `jq` got the human block under a success exit code."""
    root = _node(tmp_path, retain={"completed": False})
    slug = _resolve(root)
    monkeypatch.chdir(root)
    capsys.readouterr()
    assert main(["work", "show", slug, "--json"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "was resolved (done" in captured.err
    assert "no item document to project" in captured.err
    # The human form is unchanged.
    assert main(["work", "show", slug]) == 0
    assert "(resolved)" in capsys.readouterr().out


def test_every_transition_gives_a_hook_the_item_path(tmp_path, monkeypatch):
    """`hook_env` documents the variable as absent only when there is nothing to
    put in it, and `complete` had both an item path and a resolution and passed
    neither — so a binding testing `[ -n "$TCW_ITEM_PATH" ]` concluded there was
    no item folder for the transition most likely to want one."""
    root = _node(tmp_path)
    seen = tmp_path / "seen"
    seen.mkdir()
    config_path = root / "tcw-config.yaml"
    config = yaml.safe_load(config_path.read_text()) or {}
    record = f'printf "%s\\n" "$TCW_ITEM_PATH" "${{TCW_RESOLUTION:-<none>}}" > {seen}/"$TCW_TRANSITION"'
    config.setdefault("work", {}).setdefault("lifecycle", {})["transitions"] = {
        name: {"pre": [{"command": record}]}
        for name in ("start", "submit", "rework", "complete")
    }
    config_path.write_text(yaml.safe_dump(config, sort_keys=False))

    store = FsWorkStore.open(root)
    item = store.create("A thing", created="2026-01-01")
    monkeypatch.chdir(root)
    assert main(["work", "start", item.slug]) == 0
    assert main(["work", "submit", item.slug]) == 0
    assert main(["work", "rework", item.slug]) == 0
    assert main(["work", "submit", item.slug]) == 0
    assert main(["work", "complete", item.slug,
                 "--resolution", "done", "--confirm"]) == 0

    for name in ("start", "submit", "rework", "complete"):
        path, resolution = (seen / name).read_text().splitlines()
        assert path.endswith(item.slug), name
        assert Path(path).name == item.slug, name
        # Only the resolving transitions have one.
        assert resolution == ("done" if name == "complete" else "<none>"), name


def test_a_transition_over_a_concurrently_removed_item_says_so(tmp_path):
    """The fallback record claimed `work.retain: false` removes the item during
    the move. The store never deletes during a transition — that is a separate
    call the CLI makes — so the only way it is gone here is a concurrent
    removal, and fabricating a success for that returns the pre-move `owner` and
    `started` the move had just cleared."""
    import shutil

    root = _node(tmp_path)
    store = FsWorkStore.open(root)
    item = store.create("A thing", created="2026-01-01")
    store.start(item.slug)
    original = store._effect_transition

    def _and_then_vanish(slug, to_status, fields):
        original(slug, to_status, fields)
        shutil.rmtree(store._find(slug))

    store._effect_transition = _and_then_vanish
    with pytest.raises(ValueError) as excinfo:
        store.transition(item.slug, "review")
    assert "no such work item" in str(excinfo.value)


# ── a removal that started and did not finish ────────────────────────────────

def _refuse_removal_commits(root: Path) -> None:
    """A commit hook that rejects the removal commit and nothing else.

    Any commit failure produces the same state — an `index.lock`, a missing
    identity, a signing failure — so the hook is a stand-in for all of them.
    """
    hooks = root / ".git" / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    hook = hooks / "commit-msg"
    hook.write_text('#!/bin/sh\ngrep -q "tcw work: delete" "$1" && exit 1\nexit 0\n')
    hook.chmod(0o755)


def test_a_failed_removal_commit_is_reported_as_removed(tmp_path, monkeypatch,
                                                        capsys):
    """The folder is gone by the time the commit runs, so a commit failure is a
    removal that happened — the same distinction the publication case needed,
    and the reason it is now asked of the store instead of the exception."""
    root = _node(tmp_path, retain={"completed": False})
    _refuse_removal_commits(root)
    store = FsWorkStore.open(root)
    item = store.create("A thing", created="2026-01-01")
    store.start(item.slug)
    monkeypatch.chdir(root)
    assert main(["work", "complete", item.slug,
                 "--resolution", "done", "--confirm"]) == 1
    captured = capsys.readouterr()
    assert not (root / "docs" / "work" / "completed" / item.slug).exists()
    assert f"completed {item.slug} (done)" in captured.out
    assert "docs/work/completed" not in captured.out


def test_delete_finishes_a_removal_whose_commit_failed(tmp_path, monkeypatch,
                                                       capsys):
    """`tcw work delete` short-circuited on the tombstone's location — which is
    written *before* the removal is committed — so it reported success and left
    the tree holding an unstaged deletion forever."""
    root = _node(tmp_path, retain={"completed": False})
    _refuse_removal_commits(root)
    store = FsWorkStore.open(root)
    item = store.create("A thing", created="2026-01-01")
    store.start(item.slug)
    monkeypatch.chdir(root)
    assert main(["work", "complete", item.slug,
                 "--resolution", "done", "--confirm"]) == 1
    capsys.readouterr()
    assert FsWorkStore.open(root).pending_removal(item.slug) is True
    assert subprocess.run(["git", "-C", str(root), "status", "--porcelain",
                           "--", "docs/work"],
                          capture_output=True, text=True,
                          check=True).stdout.strip() != ""

    (root / ".git" / "hooks" / "commit-msg").unlink()
    assert main(["work", "delete", item.slug]) == 0
    assert FsWorkStore.open(root).pending_removal(item.slug) is False
    assert subprocess.run(["git", "-C", str(root), "status", "--porcelain",
                           "--", "docs/work"],
                          capture_output=True, text=True,
                          check=True).stdout.strip() == ""


def test_a_finished_removal_is_still_reported_as_already_done(tmp_path,
                                                              monkeypatch,
                                                              capsys):
    """The idempotent half the pending check must not cost."""
    root = _node(tmp_path, retain={"completed": False})
    slug = _resolve(root)
    monkeypatch.chdir(root)
    assert FsWorkStore.open(root).pending_removal(slug) is False
    assert main(["work", "delete", slug]) == 0
    out = capsys.readouterr().out
    assert "already removed" in out
    assert "last present in commit" in out


def test_no_commit_holding_the_item_records_no_commit(tmp_path, monkeypatch,
                                                      capsys):
    """Recording HEAD named a commit that demonstrably does not contain the
    item — the one thing a tombstone's handle must never do."""
    root = _node(tmp_path)                      # default rules ignore completed/
    store = FsWorkStore.open(root)
    item = store.create("A thing", created="2026-01-01")
    store.start(item.slug)
    monkeypatch.chdir(root)
    assert main(["work", "complete", item.slug,
                 "--resolution", "done", "--confirm"]) == 0
    # The folder is gone before the removal runs, so nothing can be refused over
    # it and no commit ever held it.
    shutil.rmtree(root / "docs" / "work" / "completed" / item.slug)
    capsys.readouterr()

    store = FsWorkStore.open(root)
    assert store.delete_resolved(item.slug, "completed") == ""
    assert FsWorkStore.open(root).tombstone(item.slug).location == ""
    assert "not retained" in store.describe_location("", item.slug)


def test_a_commit_that_does_not_hold_the_item_is_reported_unresolvable(
        tmp_path, monkeypatch, capsys):
    """The check probed `self.root.name` — `work`, against a repository where the
    store is at `docs/work` — and `git ls-tree <sha> -- <anything>` exits 0
    regardless, so the only detectable case was a missing commit object."""
    root = _node(tmp_path, retain={"completed": False})
    slug = _resolve(root)
    scaffold = subprocess.run(
        ["git", "-C", str(root), "rev-list", "--max-parents=0", "HEAD"],
        capture_output=True, text=True, check=True).stdout.strip()
    # A handle that resolves to a commit this clone has and which never held the
    # item — what a squash- or rebase-merge leaves behind.
    graveyard = root / "docs" / "work" / "graveyard.yaml"
    record = yaml.safe_load(graveyard.read_text()) or {}
    record[slug]["location"] = scaffold
    graveyard.write_text(yaml.safe_dump(record, sort_keys=False))
    monkeypatch.chdir(root)
    assert main(["work", "show", slug]) == 0
    out = capsys.readouterr().out
    assert "does not contain the item" in out
    assert "last present in commit" not in out


def test_the_item_s_own_resolution_survives_an_empty_graveyard(tmp_path):
    """`delete_resolved` read the resolution only from the graveyard, defaulting
    to empty and today's date — the overwrite `record_tombstone` refuses by
    name — on a board adopting retention before backfilling its records."""
    root = _node(tmp_path, retain={"completed": False, "discarded": False})
    store = FsWorkStore.open(root)
    item = store.create("A thing", created="2026-01-01")
    store.start(item.slug)
    store.complete(item.slug, "wontfix", [], force=True)
    (root / "docs" / "work" / "graveyard.yaml").write_text("{}\n")
    subprocess.run(["git", "-C", str(root), "commit", "-qam", "empty graveyard"],
                   check=True)

    FsWorkStore.open(root).delete_resolved(item.slug, "discarded")
    grave = FsWorkStore.open(root).tombstone(item.slug)
    assert grave.resolution == "wontfix"
    assert grave.resolved


def test_a_pre_binding_that_moves_the_item_and_fails_is_reported_as_removed(
        tmp_path, monkeypatch, capsys):
    """The `pre`-failure branch hard-coded "still there" while the binding that
    just failed is the one thing able to move the item — so the completion
    printed a path into `docs/work/completed/` for a folder the hook had already
    taken away."""
    root = _node(tmp_path, retain={"completed": False})
    elsewhere = tmp_path / "cold"
    elsewhere.mkdir()
    _bind(root, pre=[{"command": f'mv "$TCW_ITEM_PATH" {elsewhere}/"$TCW_SLUG"; exit 3'}])
    store = FsWorkStore.open(root)
    item = store.create("A thing", created="2026-01-01")
    store.start(item.slug)
    monkeypatch.chdir(root)
    assert main(["work", "complete", item.slug,
                 "--resolution", "done", "--confirm"]) == 1
    captured = capsys.readouterr()
    assert f"completed {item.slug} (done)" in captured.out
    assert "docs/work/completed" not in captured.out
    assert "moved the item before it failed" in captured.err


def test_delete_reports_an_ambiguous_slug_instead_of_crashing(tmp_path,
                                                              monkeypatch,
                                                              capsys):
    """`MultipleMatch` is an `Exception`, not a `ValueError`, so the CLI's
    catch-all does not see it and an unguarded read left a raw traceback where
    every other subcommand reports and exits 1."""
    root = _node(tmp_path, retain={"completed": False})
    store = FsWorkStore.open(root)
    item = store.create("A thing", created="2026-01-01")
    store.start(item.slug)
    store.complete(item.slug, "done", [], force=True)
    # The shape a bad merge leaves: the same slug under two status folders.
    shutil.copytree(root / "docs" / "work" / "completed" / item.slug,
                    root / "docs" / "work" / "discarded" / item.slug)
    monkeypatch.chdir(root)
    assert main(["work", "delete", item.slug]) == 1
    assert "resolves to 2 items" in capsys.readouterr().err


def test_a_first_attempt_does_not_sweep_someone_elses_graveyard_edit(
        tmp_path, monkeypatch, capsys):
    """`pending_removal` is true on a *first* attempt whose `pre` binding moved
    the item, where the graveyard is clean — so skipping the guard outright
    there let an unrelated uncommitted edit ride into this item's commit."""
    root = _node(tmp_path, retain={"completed": False})
    elsewhere = tmp_path / "cold"
    elsewhere.mkdir()
    _bind(root, pre=[{"command": f'mv "$TCW_ITEM_PATH" {elsewhere}/"$TCW_SLUG"; exit 3'}])
    store = FsWorkStore.open(root)
    item = store.create("A thing", created="2026-01-01")
    store.start(item.slug)
    monkeypatch.chdir(root)
    assert main(["work", "complete", item.slug,
                 "--resolution", "done", "--confirm"]) == 1
    capsys.readouterr()
    assert FsWorkStore.open(root).pending_removal(item.slug) is True

    # Somebody else's record, uncommitted. Not this item's, so it must refuse.
    graveyard = root / "docs" / "work" / "graveyard.yaml"
    doc = yaml.safe_load(graveyard.read_text()) or {}
    doc["2026-01-01-someone-elses-item"] = {"resolution": "done",
                                            "resolved": "2026-01-01"}
    graveyard.write_text(yaml.safe_dump(doc, sort_keys=False))

    _bind(root, pre=[{"command": "true"}])
    assert main(["work", "delete", item.slug]) == 1
    assert "has uncommitted changes" in capsys.readouterr().err
    tracked = subprocess.run(["git", "-C", str(root), "show", "HEAD:docs/work/graveyard.yaml"],
                             capture_output=True, text=True, check=True).stdout
    assert "someone-elses-item" not in tracked


def test_resuming_still_finishes_over_its_own_uncommitted_record(tmp_path,
                                                                 monkeypatch,
                                                                 capsys):
    """The other half. A removal whose commit failed left *its own* tombstone
    uncommitted, and refusing over that made the state unfinishable through the
    command that exists to finish it."""
    root = _node(tmp_path, retain={"completed": False})
    _refuse_removal_commits(root)
    store = FsWorkStore.open(root)
    item = store.create("A thing", created="2026-01-01")
    store.start(item.slug)
    monkeypatch.chdir(root)
    assert main(["work", "complete", item.slug,
                 "--resolution", "done", "--confirm"]) == 1
    capsys.readouterr()
    (root / ".git" / "hooks" / "commit-msg").unlink()
    assert main(["work", "delete", item.slug]) == 0
    assert subprocess.run(["git", "-C", str(root), "status", "--porcelain",
                           "--", "docs/work"],
                          capture_output=True, text=True,
                          check=True).stdout.strip() == ""


def test_a_removal_with_no_commit_says_so_in_the_commit_message():
    """`(retained in )` — an empty parenthesis where a SHA belongs. The history
    is the one place the contradiction survives, since the line the CLI prints
    alongside says plainly that no commit held the documents."""
    subject = FsWorkStore._removal_commit_subject
    assert subject("a-thing", "0123456789abcdef") == \
        "tcw work: delete a-thing (retained in 0123456789ab)"
    assert subject("a-thing", "") == "tcw work: delete a-thing (no commit held it)"
    assert "retained in )" not in subject("a-thing", "")


# ── the interface, not the adapter ──────────────────────────────────────────

def test_the_retention_operations_are_on_the_abstract_store():
    """The CLI that calls them is storage-neutral, so a second adapter driven
    through `tcw work complete` used to raise `AttributeError`. Each answers a
    question any store can answer — `parse_retention`'s own docstring makes the
    case for a tracker closing and dropping the ticket."""
    from tcw.store.base import WorkStore

    for name in ("retention", "retention_problems", "retention_conflicts",
                 "pending_deletion", "pending_removal", "delete_resolved",
                 "describe_location"):
        assert name in vars(WorkStore), name


def test_the_defaults_describe_a_store_that_does_not_retain_anything():
    """Concrete rather than abstract, and every default is a legitimate
    implementation: an adapter that keeps everything has nothing pending, so
    `delete_resolved` is unreachable through the CLI."""
    from tcw.store.base import RESOLVED_STATUSES, WorkStore

    # Every abstract method stubbed, so what is left to check is that none of
    # the seven is among them.
    class _Minimal(WorkStore):
        pass

    for name in WorkStore.__abstractmethods__:
        setattr(_Minimal, name, lambda self, *a, **k: None)
    _Minimal.__abstractmethods__ = frozenset()
    store = _Minimal()
    assert store.retention() == {s: True for s in RESOLVED_STATUSES}
    assert store.retention_problems() == []
    assert store.retention_conflicts() == []
    assert store.pending_deletion("anything") is False
    assert store.pending_removal("anything") is False
    assert store.describe_location("abc123") == "abc123"
    assert "no record" in store.describe_location("")
    with pytest.raises(NotImplementedError):
        store.delete_resolved("anything")


def test_show_says_when_no_commit_held_the_documents(tmp_path, monkeypatch,
                                                      capsys):
    """`_show` guarded on a non-empty location, so the one case the reader most
    needs told — an item whose documents were never retained anywhere — printed
    nothing at all, and `describe_location`'s wording for it was unreachable."""
    root = _node(tmp_path)                      # default rules ignore completed/
    store = FsWorkStore.open(root)
    item = store.create("A thing", created="2026-01-01")
    store.start(item.slug)
    monkeypatch.chdir(root)
    assert main(["work", "complete", item.slug,
                 "--resolution", "done", "--confirm"]) == 0
    shutil.rmtree(root / "docs" / "work" / "completed" / item.slug)
    assert FsWorkStore.open(root).delete_resolved(item.slug, "completed") == ""
    capsys.readouterr()

    assert main(["work", "show", item.slug]) == 0
    out = capsys.readouterr().out
    assert "content:" in out
    assert "not retained" in out
