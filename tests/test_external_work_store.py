from __future__ import annotations

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
