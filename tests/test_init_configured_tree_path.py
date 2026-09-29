"""`tcw init` scaffolds a taxonomy or capabilities store where
`<component>.path` says, and refuses one whose repository is declared
(spec: 2026-09-26-make-tcw-init-honor-a-configured-taxonomy-or-capabilities-path)."""

import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.cli import main
from tcw.store.fs import init


@pytest.fixture
def root(tmp_path, monkeypatch, capsys):
    r = tmp_path / "node"
    r.mkdir()
    for args in (["init", "-q"], ["config", "user.email", "t@t"], ["config", "user.name", "t"]):
        subprocess.run(["git", "-C", str(r), *args], check=True)
    init(["work"], r, "node")
    monkeypatch.chdir(r)
    capsys.readouterr()
    return r


def configure(root: Path, **sections) -> None:
    p = root / "tcw-config.yaml"
    cfg = yaml.safe_load(p.read_text()) or {}
    cfg.update(sections)
    p.write_text(yaml.safe_dump(cfg, sort_keys=False))


def cli(capsys, *argv):
    code = main(list(argv))
    out = capsys.readouterr()
    return code, out.out, out.err


@pytest.mark.parametrize("component, where", [("taxonomy", "knowledge/terms"),
                                              ("capabilities", "ledger")])
def test_init_scaffolds_at_the_configured_path(root, capsys, component, where):
    configure(root, **{component: {"path": where}})
    code, _out, err = cli(capsys, component, "init")
    assert code == 0, err
    assert (root / where).is_dir()
    assert not (root / "docs" / component).exists()
    assert yaml.safe_load((root / "tcw-config.yaml").read_text())[component] == {"path": where}
    code, _out, err = cli(capsys, component, "list")
    assert code == 0 and "run `tcw init`" not in err, err


def test_init_of_both_at_once_honors_both(root, capsys):
    configure(root, taxonomy={"path": "knowledge/terms"}, capabilities={"path": "ledger"})
    code, _out, err = cli(capsys, "init", "taxonomy", "capabilities", "--id", "node")
    assert code == 0, err
    assert (root / "knowledge" / "terms").is_dir() and (root / "ledger").is_dir()


def test_a_path_that_is_not_a_string_is_refused(root, capsys):
    configure(root, taxonomy={"path": 7})
    code, _out, err = cli(capsys, "taxonomy", "init")
    assert code == 1 and "taxonomy.path" in err, err
    assert not (root / "docs" / "taxonomy").exists()


def test_a_declared_repository_is_not_shadowed_by_an_empty_local_store(root, capsys):
    configure(root, taxonomy={"repository": {"url": "git@host:o/terms.git"}})
    code, _out, err = cli(capsys, "taxonomy", "init")
    assert code == 1 and "tcw provision" in err, err
    assert not (root / "docs" / "taxonomy").exists()


def test_init_in_a_linked_worktree_builds_where_the_readers_look(tmp_path):
    """A relative path that leaves the checkout is anchored at the primary
    checkout (`anchor_configured_path`); `init` must build it there too, not
    beside the worktree."""
    from tcw.store.fs import FsTaxonomyStore
    main_root = tmp_path / "a" / "main"
    main_root.mkdir(parents=True)
    for args in (["init", "-q", "-b", "main"], ["config", "user.email", "t@t"],
                 ["config", "user.name", "t"]):
        subprocess.run(["git", "-C", str(main_root), *args], check=True)
    init(["work"], main_root, "node")
    configure(main_root, taxonomy={"path": "../shared/terms"})
    subprocess.run(["git", "-C", str(main_root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(main_root), "commit", "-qm", "c"], check=True)
    wt = tmp_path / "b" / "wt"
    subprocess.run(["git", "-C", str(main_root), "worktree", "add", "-q", str(wt), "-b", "w"],
                   check=True)
    init(["taxonomy"], wt, "node")
    expected = tmp_path / "a" / "shared" / "terms"
    assert expected.is_dir()
    assert not (tmp_path / "b" / "shared").exists()
    assert FsTaxonomyStore.open(wt).root.resolve() == expected.resolve()
