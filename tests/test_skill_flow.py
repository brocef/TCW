"""The Spec 3 lifecycle handshake end-to-end, via the CLI — the worked dry-run
the tcw-work / tcw-capabilities skills prescribe, captured as a regression."""

import subprocess
from pathlib import Path

from tcw.store.fs import FsCapabilitiesStore, init


def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work", "capabilities"], root)
    return root


def test_product_first_lifecycle_handshake(tmp_path, monkeypatch, capsys):
    root = repo(tmp_path)
    monkeypatch.chdir(root)
    from tcw.cli import main

    # new → backlog
    assert main(["work", "new", "Add CSV export"]) == 0
    slug = capsys.readouterr().out.strip()
    assert (root / "docs/work/backlog" / slug).is_dir()

    # planning gate: declare the capability Missing + the Planning-doc back-pointer
    assert main(["capabilities", "add", "routes/csv-export", "Export CSV", "--status", "Missing"]) == 0
    assert main(["capabilities", "set", "routes/csv-export", "--field", f"Planning doc={slug}"]) == 0
    cap = FsCapabilitiesStore.open(root).get("routes/csv-export")
    assert cap.status == "Missing" and cap.fields.get("Planning doc") == slug

    # start → active
    capsys.readouterr()
    assert main(["work", "start", slug]) == 0
    assert (root / "docs/work/active" / slug).is_dir()

    # complete: flip the ledger, then close the item
    assert main(["capabilities", "set", "routes/csv-export", "--status", "Supported"]) == 0
    assert FsCapabilitiesStore.open(root).get("routes/csv-export").status == "Supported"
    capsys.readouterr()
    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 0
    assert (root / "docs/work/completed" / slug).is_dir()
