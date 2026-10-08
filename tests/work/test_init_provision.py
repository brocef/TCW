"""`tcw init` and `tcw provision` on the 3.0 work store (TCW-70 AC 18)."""

import yaml

from tcw.cli import main
from tests.work.projects import git, write_item


def run(capsys, monkeypatch, cwd, *argv):
    monkeypatch.chdir(cwd)
    try:
        code = main(list(argv))
    except SystemExit as stop:
        code = stop.code
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def repository(path):
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q")
    git(path, "config", "user.email", "t@t")
    git(path, "config", "user.name", "t")
    return path


def test_init_makes_the_work_folder_and_nothing_else(tmp_path, capsys, monkeypatch):
    root = repository(tmp_path / "p")
    code, _, err = run(capsys, monkeypatch, root, "init", "--id", "p", "work")
    assert code == 0, err
    work = root / "docs" / "work"
    assert sorted(p.name for p in work.iterdir()) == [".gitkeep"]
    ignore = root / ".gitignore"
    lines = ignore.read_text().splitlines() if ignore.exists() else []
    assert not [line for line in lines if "docs/work" in line]


def test_init_refuses_to_move_a_store_holding_an_item(tmp_path, capsys, monkeypatch):
    root = repository(tmp_path / "p")
    assert run(capsys, monkeypatch, root, "init", "--id", "p", "work")[0] == 0
    write_item(root, "2026-10-01-a", {"title": "a", "stage": "request"})
    code, _, err = run(capsys, monkeypatch, root, "init", "work",
                       "--work-path", "elsewhere")
    assert code == 1 and "non-pristine" in err
    assert (root / "docs/work/2026-10-01-a/item.yaml").exists()


def test_init_moves_an_empty_store(tmp_path, capsys, monkeypatch):
    root = repository(tmp_path / "p")
    assert run(capsys, monkeypatch, root, "init", "--id", "p", "work")[0] == 0
    code, _, err = run(capsys, monkeypatch, root, "init", "work",
                       "--work-path", "elsewhere")
    assert code == 0, err
    assert (root / "elsewhere" / ".gitkeep").exists()
    assert not (root / "docs" / "work").exists()


def test_provision_accepts_a_store_of_item_folders(tmp_path, capsys, monkeypatch):
    remote = repository(tmp_path / "remote")
    write_item(remote, "2026-10-01-a", {"title": "a", "stage": "request"})
    git(remote, "add", "-A")
    git(remote, "commit", "-qm", "seed")
    root = repository(tmp_path / "p")
    (root / "tcw-config.yaml").write_text(yaml.safe_dump({
        "id": "p",
        "work": {"repository": {"url": str(remote), "path": "docs/work",
                                "checkout": str(tmp_path / "co")}}}))
    code, out, err = run(capsys, monkeypatch, root, "provision",
                         "--component", "work")
    assert code == 0, out + err
    assert (tmp_path / "co" / "docs/work/2026-10-01-a/item.yaml").exists()
    code, out, err = run(capsys, monkeypatch, root, "work", "list")
    assert (code, out) == (0, "p/2026-10-01-a\n"), err
