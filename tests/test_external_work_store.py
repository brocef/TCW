from __future__ import annotations

import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import yaml

from tcw.cli import main
from tcw.store.fs import FsWorkStore, init
from tcw.store.base import AlreadyClaimed


def _repo(path: Path) -> Path:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test"], check=True)
    return path


def _external_node(tmp_path: Path, configured: str) -> tuple[Path, Path]:
    code = _repo(tmp_path / "code")
    work_repo = _repo(tmp_path / "orchestrator")
    work_root = work_repo / "stores" / "corelib"
    init(["work"], code, "corelib")
    for child in (code / "docs" / "work").iterdir():
        if child.is_dir():
            for entry in child.iterdir():
                entry.unlink()
            child.rmdir()
    (code / "docs" / "work").rmdir()
    work_root.mkdir(parents=True)
    for name in ("inbox", "backlog", "active", "review", "completed", "discarded"):
        (work_root / name).mkdir()
    config = yaml.safe_load((code / "tcw-config.yaml").read_text())
    config["work"] = {"path": configured}
    (code / "tcw-config.yaml").write_text(yaml.safe_dump(config, sort_keys=False))
    return code, work_root


def test_relative_external_store_routes_items_and_git_effects(tmp_path):
    code, work_root = _external_node(tmp_path, "../orchestrator/stores/corelib")
    store = FsWorkStore.open(code)
    assert store.node_root == code.resolve()
    assert store.root == work_root.resolve()
    assert store.store_git_root == (tmp_path / "orchestrator").resolve()
    item = store.create("External", created="2026-08-08")
    assert store.path(item.slug).is_relative_to(work_root)


def test_cli_path_commands_print_configured_external_store_roots(tmp_path, monkeypatch,
                                                                  capsys):
    code, work_root = _external_node(tmp_path, "../orchestrator/stores/corelib")
    monkeypatch.chdir(code)

    assert main(["work", "path"]) == 0
    output = capsys.readouterr()
    assert output.out == f"{work_root.resolve()}\n"
    assert output.err == ""

    assert main(["work", "inbox", "path"]) == 0
    output = capsys.readouterr()
    assert output.out == f"{(work_root / 'inbox').resolve()}\n"
    assert output.err == ""


def test_absolute_and_symlinked_default_store(tmp_path):
    code, work_root = _external_node(tmp_path, str(tmp_path / "orchestrator/stores/corelib"))
    assert FsWorkStore.open(code).root == work_root.resolve()

    linked = _repo(tmp_path / "linked")
    init([], linked, "linked")
    (linked / "docs").mkdir()
    (linked / "docs" / "work").symlink_to(work_root, target_is_directory=True)
    assert FsWorkStore.open(linked).root == work_root.resolve()


def test_broken_symlink_has_actionable_diagnostic(tmp_path):
    code = _repo(tmp_path / "code")
    init([], code, "corelib")
    (code / "docs").mkdir()
    (code / "docs" / "work").symlink_to(tmp_path / "missing", target_is_directory=True)
    with pytest.raises(ValueError, match="work.path is a broken symlink"):
        FsWorkStore.open(code)


def test_work_init_path_scaffolds_external_store_and_target_ignore(tmp_path, monkeypatch):
    code = _repo(tmp_path / "code")
    orchestrator = _repo(tmp_path / "orchestrator")
    monkeypatch.chdir(code)
    assert main(["work", "init", "--id", "corelib", "--path", str(orchestrator / "CoreLib/work")]) == 0
    store = FsWorkStore.open(code)
    assert store.root == (orchestrator / "CoreLib/work").resolve()
    assert yaml.safe_load((code / "tcw-config.yaml").read_text())["work"]["path"] == str(orchestrator / "CoreLib/work")
    ignore = (orchestrator / ".gitignore").read_text()
    assert "CoreLib/work/completed/*" in ignore
    assert not (code / ".gitignore").exists()


def test_two_store_claim_has_one_winner_and_visible_metadata(tmp_path):
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    config = yaml.safe_load((code / "tcw-config.yaml").read_text())
    config.setdefault("work", {})["auto-commit-transitions"] = False
    (code / "tcw-config.yaml").write_text(yaml.safe_dump(config, sort_keys=False))
    first = FsWorkStore.open(code)
    item = first.create("Claim me", created="2026-08-08")

    def claim(owner: str):
        try:
            return FsWorkStore.open(code).start(item.slug, owner=owner)
        except AlreadyClaimed as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(claim, ["one@example.com", "two@example.com"]))
    assert sum(not isinstance(result, AlreadyClaimed) for result in results) == 1
    active = FsWorkStore.open(code).get(item.slug)
    assert active.status == "active"
    assert active.owner in {"one@example.com", "two@example.com"}
    assert active.started.endswith("Z")


def test_claim_lost_at_find_takes_the_recovery_path_not_a_typeerror(tmp_path, monkeypatch):
    """The other way to lose the claim race — the one that used to crash.

    A loser finds out at one of two moments: `os.replace` raises
    `FileNotFoundError`, or `_find` has already returned `None` because the
    competitor's folder is sitting in `.claiming/`, where nothing looks. Only the
    first reached the recovery block; the second hit `os.replace(None, ...)` and
    raised `TypeError`.

    No arrangement of files reproduces it, because whatever makes `get()` succeed
    also makes `_find` succeed — the bug lives in the gap *between* those two
    calls. So the gap is forced: `_find` is real for the status read and `None`
    for the claim lookup that follows.

    Asserting on the recovery path rather than on `AlreadyClaimed` keeps this
    about the defect. Which error ends the recovery depends on whether the
    competitor finishes, and the threaded test above already covers that.
    """
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    store = FsWorkStore.open(code)
    item = store.create("Claim me", created="2026-08-08")

    real_find = FsWorkStore._find
    calls = {"n": 0}

    def find_missing_at_the_claim(self, slug):
        calls["n"] += 1
        return None if calls["n"] == 2 else real_find(self, slug)

    monkeypatch.setattr(FsWorkStore, "_find", find_missing_at_the_claim)

    with pytest.raises(ValueError, match="interrupted claim") as caught:
        FsWorkStore.open(code).start(item.slug, owner="loser@example.com")
    assert not isinstance(caught.value, TypeError)
    # If start() ever stops taking exactly two lookups before the claim, this
    # test would silently stop exercising the window it was written for.
    assert calls["n"] >= 2, "the claim lookup was never reached"


def test_takeover_replaces_claim_and_submit_clears_it(tmp_path):
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    store = FsWorkStore.open(code)
    item = store.create("Claim me", created="2026-08-08")
    store.start(item.slug, owner="first@example.com")
    taken = store.start(item.slug, owner="second@example.com", take_over=True)
    assert taken.owner == "second@example.com"
    submitted = store.submit(item.slug)
    assert submitted.owner == ""
    assert submitted.started == ""


def test_takeover_lost_at_the_commit_lookup_is_a_valueerror(tmp_path, monkeypatch):
    """The take-over commit path resolves the item a third time (fs.py:2005).

    Losing the item between the `started` write and that lookup used to hit
    `None.relative_to(...)` and raise `AttributeError`, which the CLI does not
    handle. Forced by patching `_find` away once the `started` write has landed —
    deterministic regardless of how many lookups precede it.
    """
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    store = FsWorkStore.open(code)
    item = store.create("Claim me", created="2026-08-08")
    store.start(item.slug, owner="first@example.com")

    real_set_field = FsWorkStore.set_field

    def vanish_after_started(self, slug, key, value):
        real_set_field(self, slug, key, value)
        if key == "started":
            monkeypatch.setattr(FsWorkStore, "_find", lambda self, slug: None)

    monkeypatch.setattr(FsWorkStore, "set_field", vanish_after_started)

    with pytest.raises(ValueError, match="no such work item"):
        FsWorkStore.open(code).start(item.slug, owner="second@example.com",
                                     take_over=True)


def test_takeover_recovers_interrupted_private_claim(tmp_path):
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    store = FsWorkStore.open(code)
    item = store.create("Interrupted", created="2026-08-08")
    private = store.root / ".claiming" / f"{item.slug}-dead-process"
    private.parent.mkdir()
    store.path(item.slug).replace(private)
    recovered = store.start(item.slug, owner="recovery@example.com", take_over=True)
    assert recovered.status == "active"
    assert recovered.owner == "recovery@example.com"
    assert not private.exists()


def _reviewed(tmp_path: Path) -> tuple[Path, FsWorkStore, str]:
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    store = FsWorkStore.open(code)
    item = store.create("Race me", created="2026-08-08")
    store.start(item.slug, owner="me@example.com")
    store.submit(item.slug)
    return code, store, item.slug


def test_effect_transition_lost_at_find_reports_where_the_item_went(tmp_path, monkeypatch):
    """`_effect_transition` resolves the item twice and only tolerated a miss on
    the first. Against the unfixed code this failed with `FileNotFoundError` from
    `shutil.move("None", ...)` — *not* the `TypeError` the bug report assumed,
    because `completed/` is gitignored by default so `_mv` takes its non-git
    branch and `git_mv` stringifies `None` into the literal path "None".

    The competitor moves the item to `backlog` so the reported status differs from
    both ends of the attempted move, and the folder assertion pins the guard above
    `_mv` (acceptance criterion 3).
    """
    code, store, slug = _reviewed(tmp_path)
    real_find = FsWorkStore._find
    calls = {"n": 0}
    moved = store.root / "backlog" / slug

    def competitor_wins_at_the_move(self, item_slug):
        calls["n"] += 1
        if calls["n"] == 2:
            shutil.move(str(store.root / "review" / item_slug), str(moved))
            return None
        return real_find(self, item_slug)

    monkeypatch.setattr(FsWorkStore, "_find", competitor_wins_at_the_move)
    with pytest.raises(ValueError) as caught:
        store._effect_transition(slug, "completed")

    assert slug in str(caught.value)
    assert "is now in 'backlog'" in str(caught.value)
    assert moved.is_dir()
    assert not (store.root / "completed" / slug).exists()


def test_cli_complete_losing_the_race_exits_1_without_a_traceback(tmp_path, monkeypatch,
                                                                  capsys):
    code, store, slug = _reviewed(tmp_path)
    monkeypatch.chdir(code)
    real_find = FsWorkStore._find
    real_effect = FsWorkStore._effect_transition

    def lose_the_race_inside_the_transition(self, item_slug, to_status):
        calls = {"n": 0}

        def missing_at_the_move(inner, inner_slug):
            calls["n"] += 1
            return None if calls["n"] == 2 else real_find(inner, inner_slug)

        monkeypatch.setattr(FsWorkStore, "_find", missing_at_the_move)
        return real_effect(self, item_slug, to_status)

    monkeypatch.setattr(FsWorkStore, "_effect_transition",
                        lose_the_race_inside_the_transition)

    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 1
    err = capsys.readouterr().err
    assert "tcw work complete: cannot move" in err
    assert "Traceback" not in err


def test_cli_submit_losing_the_race_exits_1_without_a_traceback(tmp_path, monkeypatch,
                                                                capsys):
    """The other half of the CLI surface: `submit` and `rework` share one handler
    that prints `tcw work:` with no subcommand (`work/cli.py:583`, `605`), where
    `complete` prints `tcw work complete:` (`work/cli.py:923`). That prefix
    inconsistency is pre-existing and deliberately not changed here, so this
    asserts what the code does rather than what would be tidier. Only `submit` is
    covered — `rework` reaches the identical handler by the identical route, so a
    third test would assert the same branch twice.

    Against the unfixed code this failed with `CalledProcessError` from
    `git add -- None` (exit 128, `fatal: pathspec 'None' did not match any
    files`) — the *other* `git_mv` branch from the one the `complete` tests hit.
    `review/` is tracked while `completed/` is gitignored, so between them the
    two tests pin both failure modes the guard replaces.
    """
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    store = FsWorkStore.open(code)
    item = store.create("Race me", created="2026-08-08")
    store.start(item.slug, owner="me@example.com")
    monkeypatch.chdir(code)
    real_find = FsWorkStore._find
    real_effect = FsWorkStore._effect_transition

    def lose_the_race_inside_the_transition(self, item_slug, to_status):
        calls = {"n": 0}

        def missing_at_the_move(inner, inner_slug):
            calls["n"] += 1
            return None if calls["n"] == 2 else real_find(inner, inner_slug)

        monkeypatch.setattr(FsWorkStore, "_find", missing_at_the_move)
        return real_effect(self, item_slug, to_status)

    monkeypatch.setattr(FsWorkStore, "_effect_transition",
                        lose_the_race_inside_the_transition)

    assert main(["work", "submit", item.slug]) == 1
    err = capsys.readouterr().err
    assert "tcw work: cannot move" in err
    assert "tcw work submit:" not in err          # the prefix really is bare
    assert "Traceback" not in err


def test_lost_complete_leaves_its_resolution_written(tmp_path, monkeypatch):
    """A DOCUMENTED LIMITATION, pinned — not a behavior worth keeping.

    `complete()` stamps `resolution` with `set_field` (`base.py:1397`) *before*
    `_effect_transition` moves the item, so a transition that loses the race
    reports the loss with the loser's resolution already on disk. Two agents
    completing one `review` item with different resolutions can therefore leave
    one's `resolution` on the item the other moved — exactly the
    status/resolution disagreement `_status_resolution_problems` still describes
    as something "no code path can produce". That docstring is now known to be
    optimistic.

    Fixing it means rolling back or reordering the pre-move writes, which
    collides with the ordering deliberately documented at `work/cli.py:915-918`.
    Tracked as
    `2026-08-11-roll-back-or-reorder-the-pre-move-set-field-writes-on-a-lost-transition`.
    When that lands, this test should be inverted, not deleted.
    """
    code, store, slug = _reviewed(tmp_path)
    real_find = FsWorkStore._find
    real_effect = FsWorkStore._effect_transition

    def lose_the_race_inside_the_transition(self, item_slug, to_status):
        calls = {"n": 0}

        def missing_at_the_move(inner, inner_slug):
            calls["n"] += 1
            return None if calls["n"] == 2 else real_find(inner, inner_slug)

        monkeypatch.setattr(FsWorkStore, "_find", missing_at_the_move)
        return real_effect(self, item_slug, to_status)

    monkeypatch.setattr(FsWorkStore, "_effect_transition",
                        lose_the_race_inside_the_transition)
    with pytest.raises(ValueError, match="cannot move"):
        store.complete(slug, "done", dod_ack=[])
    monkeypatch.undo()

    item = FsWorkStore.open(code).get(slug)
    assert item.status == "review"          # the move did not happen...
    assert item.resolution == "done"        # ...but the write before it did
