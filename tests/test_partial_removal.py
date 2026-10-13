"""A removal that stops partway names every file it did delete and says the
removal was partial (TCW-73 review fix S2). Covers `taxonomy rm`,
`capabilities rm` and `capabilities reset`, which all delete through
`FsTreeStore._rm`."""

import os
import re
from pathlib import Path

import pytest
import yaml

from tcw.cli import main
from tcw.store.fs import FsCapabilitiesStore, init

pytestmark = pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root deletes from a read-only folder, so nothing fails partway")


def locked(folder: Path):
    """Make `folder` hold one file that cannot be deleted: the folder is
    read-only, so its entries cannot be unlinked."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "stuck.txt").write_text("x")
    folder.chmod(0o555)
    return folder


def unlock(folder: Path) -> None:
    folder.chmod(0o755)


def check(err: str, store_root: Path, top: Path) -> None:
    """Every `removed` line names a file now gone; every file gone is named;
    the error says the removal was partial and names what is still there."""
    named = {Path(line.split(" ", 1)[1]).resolve()
             for line in err.splitlines() if line.startswith("removed ")}
    assert named, err
    assert all(not p.exists() for p in named), err
    assert (top / "meta.yaml").resolve() in named or not (top / "meta.yaml").exists()
    for p in named:
        assert store_root.resolve() in p.parents
    errors = [line for line in err.splitlines() if line.startswith("tcw ")]
    assert len(errors) == 1, err
    assert "removal was partial" in errors[0] and "stuck.txt" in errors[0], err
    assert "Errno" not in errors[0].split("(")[0], err


def project(tmp_path: Path) -> Path:
    root = tmp_path / "solo"
    root.mkdir()
    init(["taxonomy", "capabilities"], root, "solo")
    return root


def test_taxonomy_rm_stopped_partway(tmp_path, monkeypatch, capsys):
    root = project(tmp_path)
    d = root / "docs" / "taxonomy" / "zed"
    d.mkdir()
    (d / "meta.yaml").write_text(yaml.safe_dump({"name": "zed"}))
    (d / "description.md").write_text("")
    kid = locked(d / "kid")
    monkeypatch.chdir(root)
    try:
        code = main(["taxonomy", "rm", "zed"])
    finally:
        unlock(kid)
    printed = capsys.readouterr()
    assert code == 1 and printed.out == "", printed
    check(printed.err, root / "docs" / "taxonomy", d)


def test_capabilities_rm_stopped_partway(tmp_path, monkeypatch, capsys):
    root = project(tmp_path)
    d = root / "docs" / "capabilities" / "pay"
    d.mkdir()
    (d / "meta.yaml").write_text(yaml.safe_dump({"id": "cap-pay001", "name": "Pay",
                                                 "Status": "Supported"}))
    (d / "description.md").write_text("")
    kid = locked(d / "files")
    monkeypatch.chdir(root)
    try:
        code = main(["capabilities", "rm", "pay"])
    finally:
        unlock(kid)
    printed = capsys.readouterr()
    assert code == 1 and printed.out == "", printed
    check(printed.err, root / "docs" / "capabilities", d)


def test_capabilities_reset_stopped_partway(tmp_path, monkeypatch, capsys):
    base = project(tmp_path)
    (base / "tcw-config.yaml").write_text(
        "id: base\nprojects:\n  parent:\n    child: ../child\n")
    d = base / "docs" / "capabilities" / "login"
    d.mkdir()
    (d / "meta.yaml").write_text(yaml.safe_dump({"id": "cap-aaa111", "name": "Login",
                                                 "Status": "Supported"}))
    (d / "description.md").write_text("")
    child = tmp_path / "child"
    child.mkdir()
    init(["taxonomy", "capabilities"], child, "child")
    (child / "tcw-config.yaml").write_text(
        "id: child\nprojects:\n  children:\n    base: ../solo\n")
    FsCapabilitiesStore.open(child).extends_add("base")
    FsCapabilitiesStore.open(child).set("login", {"Status": "Missing"})
    override = child / "docs" / "capabilities" / "login"
    assert (override / "meta.yaml").is_file()
    kid = locked(override / "files")
    monkeypatch.chdir(child)
    try:
        code = main(["capabilities", "reset", "login"])
    finally:
        unlock(kid)
    printed = capsys.readouterr()
    assert code == 1 and printed.out == "", printed
    check(printed.err, child / "docs" / "capabilities", override)
