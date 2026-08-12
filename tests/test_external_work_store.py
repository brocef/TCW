from __future__ import annotations

import shutil
import subprocess
import time
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


def _vanishing_find(monkeypatch, on_call: int):
    """Force the third claim window: `_find` answers with a folder that is gone
    by the time the caller reads inside it.

    Same technique as the test above, for the same reason — the defect lives in
    the gap between `_find` and the read that follows it, so no arrangement of
    files on disk can produce it. Here `_find` is truthful about the *name* and
    stale about the *existence*, which is exactly what a competing claim's
    `os.replace` leaves behind.
    """
    real_find = FsWorkStore._find
    calls = {"n": 0}

    def find_a_vanished_dir(self, slug):
        calls["n"] += 1
        found = real_find(self, slug)
        if calls["n"] == on_call and found is not None:
            shutil.rmtree(found)
        return found

    monkeypatch.setattr(FsWorkStore, "_find", find_a_vanished_dir)
    return calls


def test_get_returns_none_when_the_folder_vanishes_mid_read(tmp_path, monkeypatch):
    """CI failure 2: `get()` → `_item_from_dir` → `_safe_yaml` → FileNotFoundError.

    Every read inside `_item_from_dir` guards with `exists()`/`is_file()` and
    then opens the file, so any of them can be the one that loses. "Not here" is
    the honest answer at that instant; the crash was not.
    """
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    store = FsWorkStore.open(code)
    item = store.create("Claim me", created="2026-08-08")

    _vanishing_find(monkeypatch, on_call=1)
    assert store.get(item.slug) is None


def test_get_returns_none_when_state_yaml_goes_inside_load_yaml_s_guard(tmp_path, monkeypatch):
    """CI failure 2 exactly: `FileNotFoundError` out of `get()` → `_item_from_dir`
    → `_safe_yaml` → `load_yaml`'s `read_text`.

    The test above removes the folder *before* any read, which `load_yaml`'s own
    `exists()` guard absorbs into `{}` — so it exercises the re-check, not this.
    Only a vanish landing *between* that guard and the read it protects produces
    the traceback CI actually reported.
    """
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    store = FsWorkStore.open(code)
    item = store.create("Claim me", created="2026-08-08")

    real_exists = Path.exists
    fired = {"did": False}

    def vanish_inside_the_guard(self):
        answer = real_exists(self)
        if answer and self.name == "state.yaml" and self.parent.name == item.slug:
            shutil.rmtree(self.parent)
            fired["did"] = True
        return answer

    monkeypatch.setattr(Path, "exists", vanish_inside_the_guard)
    assert store.get(item.slug) is None
    # Without this the test could silently stop reaching the window it exists for.
    assert fired["did"], "the read never happened, so nothing was exercised"


def test_query_skips_an_item_that_vanishes_mid_scan(tmp_path, monkeypatch):
    """The board has the same window through `_item_dirs`, not `_find`."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    store = FsWorkStore.open(code)
    doomed = store.create("Claim me", created="2026-08-08")
    survivor = store.create("Leave me", created="2026-08-08")

    real_item_dirs = FsWorkStore._item_dirs

    def remove_the_first_after_scanning(self):
        dirs = real_item_dirs(self)
        shutil.rmtree(next(d for d in dirs if d.name == doomed.slug))
        return dirs

    monkeypatch.setattr(FsWorkStore, "_item_dirs", remove_the_first_after_scanning)
    assert [i.slug for i in store.query()] == [survivor.slug]


def test_board_artifact_flags_survive_a_concurrent_claim(tmp_path, monkeypatch):
    """`tcw work list` renders its R/S/P/O letters through `artifacts()`, which
    tests each file and then reads it. The board is where a concurrent claim is
    most visible, so it is the last place that should answer with a traceback."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    store = FsWorkStore.open(code)
    item = store.create("Claim me", created="2026-08-08")

    # The window is between `is_file()` and the `read_text()` it guards — a
    # folder already gone just reads as absent, so the vanish has to land
    # *inside* the guard to reproduce anything.
    real_is_file = Path.is_file

    def vanish_between_the_test_and_the_read(self):
        answer = real_is_file(self)
        if answer and self.name == "initial-request.md":
            shutil.rmtree(self.parent)
        return answer

    monkeypatch.setattr(Path, "is_file", vanish_between_the_test_and_the_read)
    assert store.artifacts(item.slug) == []


def test_claim_loser_is_told_the_winner_not_no_such_work_item(tmp_path, monkeypatch):
    """The other half of window 3, and the reason a local `get()` fix is not enough.

    Once `get()` degrades to `None`, `start()`'s next line reports `no such work
    item` — a worse answer than the crash it replaced, and a criterion 3 failure
    of its own. A claim still sitting in `.claiming/` is the evidence that the
    slug exists and someone else has it.
    """
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    store = FsWorkStore.open(code)
    item = store.create("Claim me", created="2026-08-08")

    winner = FsWorkStore.open(code)
    claiming = winner.root / ".claiming"
    claiming.mkdir(exist_ok=True)
    # The winner mid-flight: out of `backlog`, not yet published to `active`.
    (winner.root / "backlog" / item.slug).rename(claiming / f"{item.slug}-{'ef' * 16}")

    with pytest.raises(ValueError) as caught:
        FsWorkStore.open(code).start(item.slug, owner="loser@example.com")
    assert "no such work item" not in str(caught.value)
    assert "take-over" in str(caught.value)


def test_claim_loser_waits_for_the_winner_and_is_told_who_won(tmp_path):
    """Criterion 3 through the new probe: not just "someone has it" but *who*.

    The test above covers the claimant that never comes back. This one covers
    the ordinary case — the winner is mid-flight and lands a moment later — and
    asserts the loser receives the winner's owner and start time, which is the
    whole point of the typed result.
    """
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    store = FsWorkStore.open(code)
    item = store.create("Claim me", created="2026-08-08")

    claiming = store.root / ".claiming"
    claiming.mkdir(exist_ok=True)
    private = claiming / f"{item.slug}-{'ab' * 16}"
    (store.root / "backlog" / item.slug).rename(private)

    def publish_a_moment_later():
        time.sleep(0.05)
        state = yaml.safe_load((private / "state.yaml").read_text())
        state["owner"] = "winner@example.com"
        state["started"] = "2026-08-12T00:00:00Z"
        (private / "state.yaml").write_text(yaml.safe_dump(state, sort_keys=False))
        private.rename(store.root / "active" / item.slug)

    with ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(publish_a_moment_later)
        with pytest.raises(AlreadyClaimed) as caught:
            FsWorkStore.open(code).start(item.slug, owner="loser@example.com")
    assert caught.value.owner == "winner@example.com"
    assert caught.value.started == "2026-08-12T00:00:00Z"


def test_claim_loser_reads_the_winner_that_landed_while_it_was_asking(tmp_path, monkeypatch):
    """The second escape: nothing is left in `.claiming/` because the winner
    already published, so only a re-read of `get()` finds it. Without that
    re-read this path reports `no such work item` for an item plainly sitting in
    `active/`."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    store = FsWorkStore.open(code)
    item = store.create("Claim me", created="2026-08-08")
    store.start(item.slug, owner="winner@example.com")

    real_find = FsWorkStore._find
    calls = {"n": 0}

    def missing_on_the_first_lookup(self, slug):
        calls["n"] += 1
        return None if calls["n"] == 1 else real_find(self, slug)

    monkeypatch.setattr(FsWorkStore, "_find", missing_on_the_first_lookup)

    with pytest.raises(AlreadyClaimed) as caught:
        FsWorkStore.open(code).start(item.slug, owner="loser@example.com")
    assert caught.value.owner == "winner@example.com"
    assert calls["n"] >= 2, "the re-read never happened"


def test_a_claim_on_a_longer_slug_does_not_answer_for_a_shorter_one(tmp_path):
    """`_unique_slug` mints `{base}-2` for a duplicate title, so slugs are
    prefixes of each other by construction. A `-*` glob over `.claiming/` spans
    the `-` and lets a longer slug's claim answer for a shorter one — turning a
    plain typo into a 500 ms stall and a bogus offer to recover an interrupted
    claim, for as long as the stale claim folder sits there."""
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    store = FsWorkStore.open(code)
    long_item = store.create("Claim me twice over", created="2026-08-08")

    claiming = store.root / ".claiming"
    claiming.mkdir(exist_ok=True)
    (store.root / "backlog" / long_item.slug).rename(
        claiming / f"{long_item.slug}-{'cd' * 16}")

    shorter = long_item.slug[:len(long_item.slug) - len("-twice-over")]
    assert store._claiming_dirs(shorter) == []
    with pytest.raises(ValueError, match="no such work item"):
        FsWorkStore.open(code).start(shorter, owner="someone@example.com")


def test_repeated_claim_races_have_exactly_one_winner(tmp_path):
    """Criterion 2, which one race per session never demonstrated.

    A single-shot version of this passed 1202 of 1203 local runs *with a genuine
    bug present*, so a green single race is close to no evidence. Both known CI
    failures were windows of a few microseconds on a 2-core runner; the only
    thing that finds those is repetition.
    """
    code = _repo(tmp_path / "code")
    init(["work"], code, "corelib")
    config = yaml.safe_load((code / "tcw-config.yaml").read_text())
    config.setdefault("work", {})["auto-commit-transitions"] = False
    (code / "tcw-config.yaml").write_text(yaml.safe_dump(config, sort_keys=False))
    seed = FsWorkStore.open(code)
    slugs = [seed.create(f"Claim me {n}", created="2026-08-08").slug for n in range(25)]

    def claim(args):
        slug, owner = args
        try:
            return FsWorkStore.open(code).start(slug, owner=owner)
        except AlreadyClaimed as error:
            return error

    for slug in slugs:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(claim, [(slug, "one@example.com"), (slug, "two@example.com")]))
        winners = [r for r in results if not isinstance(r, AlreadyClaimed)]
        assert len(winners) == 1, f"{slug}: {results}"
        # Never both backlog and active, and never active without its metadata.
        board = FsWorkStore.open(code)
        assert board.path(slug).parent.name == "active"
        active = board.get(slug)
        assert active.owner == winners[0].owner and active.started.endswith("Z")


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
    private = store.root / ".claiming" / f"{item.slug}-{'1a' * 16}"
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
