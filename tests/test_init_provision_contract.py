"""`tcw init` and `tcw provision` on the output contract (TCW-73 Design 1.7,
2, 8.3, 8.4; AC 8 `init`, 17 `init`, 18): neither has a product, so stdout
stays empty and everything is said on stderr."""

import pytest

from tcw.cli import main
from tcw.store import fs
from tests.test_store_provisioning import _declared_against, _remote_with_store


def run(root, monkeypatch, capsys, *argv):
    monkeypatch.chdir(root)
    try:
        code = main(list(argv))
    except SystemExit as stop:
        code = stop.code
    printed = capsys.readouterr()
    return code, printed.out, printed.err


def test_init_prints_nothing_and_names_every_path(tmp_path, monkeypatch, capsys):
    code, out, err = run(tmp_path, monkeypatch, capsys,
                         "init", "--id", "fresh", "taxonomy", "work")
    assert (code, out) == (0, "")
    assert err.splitlines() == ["wrote tcw-config.yaml",
                                "created docs/taxonomy/", "wrote docs/taxonomy/.gitkeep",
                                "created docs/work/", "wrote docs/work/.gitkeep"]
    # Again: nothing left to do, so nothing to name.
    assert run(tmp_path, monkeypatch, capsys, "init", "taxonomy", "work") == (0, "", "")


def test_init_of_an_unknown_axis_lists_the_valid_ones(tmp_path, monkeypatch, capsys):
    code, out, err = run(tmp_path, monkeypatch, capsys, "init", "--id", "x", "nosuch")
    assert (code, out) == (2, "")
    assert "taxonomy, capabilities, work" in err
    assert not (tmp_path / "tcw-config.yaml").exists()


def test_provision_of_a_store_already_here_says_so_on_stderr_and_contacts_nothing(
        tmp_path, monkeypatch, capsys):
    remote = _remote_with_store(tmp_path)
    code_root = _declared_against(tmp_path, remote)
    assert run(code_root, monkeypatch, capsys, "provision")[0] == 0

    def no_git(*args, **kwargs):
        raise AssertionError(f"ran {args}")
    monkeypatch.setattr(fs, "_git", no_git)
    code, out, err = run(code_root, monkeypatch, capsys, "provision")
    assert (code, out) == (0, "")
    assert "already available" in err


def test_a_dry_run_says_its_plan_on_stderr(tmp_path, monkeypatch, capsys):
    remote = _remote_with_store(tmp_path)
    code_root = _declared_against(tmp_path, remote)
    code, out, err = run(code_root, monkeypatch, capsys, "provision", "--dry-run")
    assert (code, out) == (0, "")
    assert "would obtain" in err
