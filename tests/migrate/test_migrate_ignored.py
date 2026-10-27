"""A file the run would write that git would ignore refuses the run (B18).

A project whose root `.gitignore` is an allowlist (`/*`, then a `!/<name>`
line for each thing tracked) would otherwise get a `.tcw/` folder git
ignores, while the tracked root `tcw-config.yaml` is deleted: committing what
git shows would remove the project's configuration. Every file meant to be
committed is asked of git before anything is written; the personal files,
which `.tcw/.gitignore` ignores on purpose, are not.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from tests.migrate.fixtures import snapshot
from tests.migrate.test_migrate_config import make
from tests.objectcli import tcw  # noqa: F401  (a fixture)

ALLOWLIST = "/*\n!/.gitignore\n!/tcw-config.yaml\n!/docs/\n"
CONFIG = "id: app\n"
LOCAL = "user:\n  name: me\n"


def _git(root: Path, *argv: str) -> str:
    return subprocess.run(["git", "-C", str(root), *argv], check=True,
                          capture_output=True, text=True).stdout


def _committed(root: Path, files: dict[str, str]) -> Path:
    make(root, files, git=True)
    _git(root, "add", "-A")
    _git(root, "-c", "user.name=t", "-c", "user.email=t@example.invalid",
         "commit", "-qm", "3.x")
    return root


def b18(err: str) -> list[str]:
    return [line for line in err.splitlines() if line.startswith("  B18 ")]


def test_an_allowlist_gitignore_refuses_the_run_and_writes_nothing(tcw, tmp_path):
    app = _committed(tmp_path / "app", {".gitignore": ALLOWLIST, "tcw-config.yaml": CONFIG,
                                        "tcw-config.local.yaml": LOCAL})
    before = snapshot(app, times=False)
    for argv in (["migrate", "--dry-run"], ["migrate", "--no-jira"]):
        done = tcw(argv, app)
        assert done.code == 3, done.err
        assert "refused:" in done.err
        assert ("  B18 .tcw/tcw-config.yaml: git would ignore it, by .gitignore:1:/*, so "
                "committing what git shows would leave it out; add the line '!/.tcw/' "
                "after that line of .gitignore, then run 'tcw migrate' again") in done.err
        assert any(line.startswith("  B18 .tcw/.gitignore: ") for line in b18(done.err))
        # The personal file is ignored on purpose, so it is never named.
        assert not any("tcw-config.local.yaml" in line for line in b18(done.err))
    assert snapshot(app, times=False) == before


def test_with_the_tcw_folder_allowed_the_run_passes_and_git_sees_it(tcw, tmp_path):
    app = _committed(tmp_path / "app", {".gitignore": ALLOWLIST + "!/.tcw/\n",
                                        "tcw-config.yaml": CONFIG,
                                        "tcw-config.local.yaml": LOCAL})
    done = tcw(["migrate", "--no-jira"], app)
    assert done.code == 0, done.err
    assert not b18(done.err)
    status = _git(app, "status", "--porcelain", "--untracked-files=all").splitlines()
    assert "?? .tcw/tcw-config.yaml" in status and "?? .tcw/.gitignore" in status
    assert " D tcw-config.yaml" in status
    assert not any("local" in line for line in status), status


def test_a_plain_gitignore_is_unaffected(tcw, tmp_path):
    app = _committed(tmp_path / "app", {".gitignore": "*.log\n/build/\n",
                                        "tcw-config.yaml": CONFIG})
    done = tcw(["migrate", "--no-jira"], app)
    assert done.code == 0, done.err
    assert not b18(done.err)
    assert "?? .tcw/" in _git(app, "status", "--porcelain").splitlines()


def test_a_project_not_in_git_is_unaffected(tcw, tmp_path):
    app = make(tmp_path / "app", {".gitignore": ALLOWLIST, "tcw-config.yaml": CONFIG},
               git=False)
    done = tcw(["migrate", "--no-jira"], app)
    assert done.code == 0, done.err
    assert not b18(done.err)
    assert (app / ".tcw/tcw-config.yaml").is_file()


def test_a_rule_in_a_nested_gitignore_is_named_with_its_folder(tcw, tmp_path):
    """A tracked 3.x state file, added with `git add -f` under a rule that
    ignores its folder: its 4.0 files would be ignored; a folder the file
    re-includes is not named."""
    app = make(tmp_path / "app", {"tcw-config.yaml": CONFIG,
                                  "docs/.gitignore": "/taxonomy/*\n!/taxonomy/x/\n",
                                  "docs/taxonomy/x/meta.yaml": "name: X\n",
                                  "docs/taxonomy/invoice/meta.yaml": "name: Invoice\n"},
               git=True)
    _git(app, "add", "-f", ".")
    done = tcw(["migrate", "--dry-run"], app)
    assert done.code == 3, done.err
    found = b18(done.err)
    assert found and all("docs/taxonomy/invoice/" in line for line in found), found
    assert found[0].startswith("  B18 docs/taxonomy/invoice/tcw-taxonomy.yaml: git would "
                               "ignore it, by docs/.gitignore:1:/taxonomy/*,")
    assert ("add the line '!/taxonomy/invoice/' after that line of docs/.gitignore"
            in found[0])
