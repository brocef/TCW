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
