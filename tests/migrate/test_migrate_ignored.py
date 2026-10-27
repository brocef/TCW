"""A file the run would write that git would ignore refuses the run (B18).

A project whose root `.gitignore` is an allowlist (`/*`, then a `!/<name>`
line for each thing tracked) would otherwise get a `.tcw/` folder git
ignores, while the tracked root `tcw-config.yaml` is deleted: committing what
git shows would remove the project's configuration. Every file meant to be
committed is asked of git before anything is written; the personal files,
which `.tcw/.gitignore` ignores on purpose, are not.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

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


# ── Only a file that comes from one git tracks is checked (evaluation review 1)

def _capability(root: Path, gitignore: str, notes: dict[str, str]) -> dict[str, str]:
    """A 3.x project whose capability `x` has a loose folder `notes/`, which
    C13 moves into `resources/` with every file in it."""
    files = {".gitignore": gitignore, "tcw-config.yaml": CONFIG,
             "docs/capabilities/x/meta.yaml": "name: X\n"}
    return files | {f"docs/capabilities/x/notes/{name}": text for name, text in notes.items()}


def test_a_moved_file_ignored_by_the_users_own_git_rules_is_not_a_reason(tcw, tmp_path):
    """`.DS_Store` under a user-wide ignore file (a repository-local
    `core.excludesFile` here) and a `.log` under the project's `*.log` were
    never committed; moving them with their folder changes nothing git
    shows, so the run passes."""
    app = tmp_path / "app"
    make(app, {}, git=True)
    excludes = tmp_path / "excludes"
    excludes.write_text(".DS_Store\n")
    _git(app, "config", "core.excludesFile", str(excludes))
    _committed(app, _capability(app, "*.log\n", {"one.md": "One.\n", ".DS_Store": "x",
                                                  "run.log": "log\n"}))
    done = tcw(["migrate", "--no-jira"], app)
    assert done.code == 0, done.err
    assert not b18(done.err)
    moved = app / "docs/capabilities/x/resources/notes"
    assert (moved / ".DS_Store").read_text() == "x" and (moved / "run.log").is_file()


def test_a_project_keeping_its_tcw_files_out_of_git_is_not_refused(tcw, tmp_path):
    """The 3.x configuration and the stores ignored on purpose: the 4.0
    files they become would be ignored too, which is what the project
    already chose."""
    app = _committed(tmp_path / "app", {".gitignore": "tcw-config.yaml\n/docs/\n",
                                        "README.md": "App.\n", "tcw-config.yaml": CONFIG,
                                        "docs/capabilities/x/meta.yaml": "name: X\n"})
    assert _git(app, "ls-files").split() == [".gitignore", "README.md"]
    done = tcw(["migrate", "--no-jira"], app)
    assert done.code == 0, done.err
    assert not b18(done.err)
    assert (app / ".tcw/tcw-config.yaml").is_file()


def test_a_tracked_file_under_an_ignoring_rule_is_not_refused(tcw, tmp_path):
    """A file git tracks is shown whatever rule matches it: a 3.x
    configuration in `.tcw/`, added with `git add -f` under a rule that
    ignores it, is converted where it is."""
    app = make(tmp_path / "app", {".gitignore": "/.tcw/tcw-config.yaml\n",
                                  ".tcw/tcw-config.yaml": CONFIG}, git=True)
    _git(app, "add", "-f", ".")
    _git(app, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-qm", "3.x")
    done = tcw(["migrate", "--no-jira"], app)
    assert done.code == 0, done.err
    assert not b18(done.err)
    assert " M .tcw/tcw-config.yaml" in _git(app, "status", "--porcelain").splitlines()


# ── git's own environment and its failures (evaluation review 2, 3) ──────────

def test_a_git_location_in_the_environment_is_not_read(tcw, tmp_path, monkeypatch):
    """Under a git hook, GIT_DIR names the repository the hook runs for; the
    check still asks the project's own repository."""
    app = _committed(tmp_path / "app", {".gitignore": ALLOWLIST, "tcw-config.yaml": CONFIG})
    other = tmp_path / "other.git"
    subprocess.run(["git", "init", "-q", "--bare", str(other)], check=True)
    monkeypatch.setenv("GIT_DIR", str(other))
    done = tcw(["migrate", "--dry-run"], app)
    assert done.code == 3, done.err
    assert any(line.startswith("  B18 .tcw/tcw-config.yaml: ") for line in b18(done.err))


def test_git_failing_is_said_and_refuses_nothing(tcw, tmp_path):
    """A repository git cannot read: nothing is claimed about its ignore
    rules, and the summary says so, with git's own words."""
    app = _committed(tmp_path / "app", {".gitignore": ALLOWLIST, "tcw-config.yaml": CONFIG})
    (app / ".git/index").write_bytes(b"garbage")
    done = tcw(["migrate", "--dry-run"], app)
    assert done.code == 0, done.err
    assert not b18(done.err)
    found = [line for line in done.err.splitlines() if "ignore rules" in line]
    assert found == [f"the files written in {app.resolve()} were not checked against git's "
                     f"ignore rules: fatal: .git/index: index file smaller than expected"], \
        done.err


# ── Advice that works (evaluation review 4) ──────────────────────────────────

@pytest.mark.parametrize("rule", ["resources/", "**/resources/**"])
def test_the_advice_given_lets_git_see_the_files(tcw, tmp_path, rule):
    """A rule matching a folder the run makes (`resources/`) or only what is
    inside it: the lines B18 names, added after the rule, are enough for git
    to show every file the run writes."""
    app = _committed(tmp_path / "app", _capability(tmp_path / "app", rule + "\n",
                                                   {"one.md": "One.\n"}))
    done = tcw(["migrate", "--dry-run"], app)
    assert done.code == 3, done.err
    advice: list[str] = []
    for line in b18(done.err):
        assert f"by .gitignore:1:{rule}," in line, line
        advice += [a for a in re.findall(r"'(![^']*)'", line) if a not in advice]
    assert advice
    (app / ".gitignore").write_text(rule + "\n" + "".join(a + "\n" for a in advice))
    done = tcw(["migrate", "--no-jira"], app)
    assert done.code == 0, done.err
    assert not b18(done.err)
    status = _git(app, "status", "--porcelain", "--untracked-files=all").splitlines()
    assert "?? docs/capabilities/x/resources/notes/one.md" in status, status


# ── Advice as deep as the path, and the commonest allowlist (review 2) ───────

@pytest.mark.parametrize("rel, rule, lines", [
    ("tcw-config.yaml", "*.yaml", ["!/tcw-config.yaml"]),
    (".tcw/tcw-config.yaml", "*", ["!/.tcw/", "!/.tcw/tcw-config.yaml"]),
    ("a/b/c.md", "*", ["!/a/", "!/a/b/", "!/a/b/c.md"]),
    ("docs/a/b.md", "/docs/", ["!/docs/"]),
])
def test_the_lines_needed_may_be_as_many_as_the_paths_depth(tmp_path, rel, rule, lines):
    """One line for each folder the rule ignores and one for the file: the
    last line added is confirmed by asking git once more, so a path needing
    as many lines as it is deep still gets them; and git, given the rule and
    those lines, shows the file."""
    from tcw.migrate.plan import _reinclude
    top = make(tmp_path / "top", {}, git=True)
    assert _reinclude(top, top / rel, ".gitignore", rule) == lines
    (top / ".gitignore").write_text("".join(f"{line}\n" for line in [rule, *lines]))
    (top / rel).parent.mkdir(parents=True, exist_ok=True)
    (top / rel).write_text("x\n")
    assert f"?? {rel}" in _git(top, "status", "--porcelain", "--untracked-files=all"
                               ).splitlines()


STAR = "*\n!.gitignore\n!tcw-config.yaml\n"


def test_a_star_allowlist_gets_advice_that_lets_the_run_pass(tcw, tmp_path):
    """A root `.gitignore` of `*` that re-includes only `.gitignore` and
    `tcw-config.yaml`: B18 names the lines that re-include `.tcw/` and each
    file in it, and with them added after `*` the run passes and git shows
    the new files."""
    app = _committed(tmp_path / "app", {".gitignore": STAR, "tcw-config.yaml": CONFIG})
    done = tcw(["migrate", "--dry-run"], app)
    assert done.code == 3, done.err
    assert ("  B18 .tcw/tcw-config.yaml: git would ignore it, by .gitignore:1:*, so "
            "committing what git shows would leave it out; add the lines '!/.tcw/' and "
            "'!/.tcw/tcw-config.yaml', in that order, after that line of .gitignore, then "
            "run 'tcw migrate' again") in done.err, done.err
    advice: list[str] = []
    for line in b18(done.err):
        assert "change that rule" not in line, line
        advice += [a for a in re.findall(r"'(![^']*)'", line) if a not in advice]
    rest = STAR.split("\n", 1)[1]
    (app / ".gitignore").write_text("*\n" + "".join(a + "\n" for a in advice) + rest)
    done = tcw(["migrate", "--no-jira"], app)
    assert done.code == 0, done.err
    assert not b18(done.err)
    status = _git(app, "status", "--porcelain", "--untracked-files=all").splitlines()
    assert "?? .tcw/tcw-config.yaml" in status and "?? .tcw/.gitignore" in status, status


# ── A new file in a store object's folder comes from that object (review 2) ──

def test_new_files_in_an_ignored_store_are_not_refused(tcw, tmp_path):
    """The stores kept out of git, the configuration tracked: the empty
    description C12 writes and a state file written where TCW 3 had none
    come from their object's own files, which git does not track, so the
    run passes and `/docs/` is never advised."""
    app = _committed(tmp_path / "app", {".gitignore": "/docs/\n", "tcw-config.yaml": CONFIG,
                                        "docs/capabilities/x/meta.yaml": "name: X\n",
                                        "docs/taxonomy/t/notes.md": "T.\n"})
    assert _git(app, "ls-files").split() == [".gitignore", "tcw-config.yaml"]
    done = tcw(["migrate", "--no-jira"], app)
    assert done.code == 0, done.err
    assert not b18(done.err)
    assert (app / "docs/capabilities/x/description.md").is_file()
    assert (app / "docs/taxonomy/t/tcw-taxonomy.yaml").is_file()


def test_a_new_file_beside_a_tracked_state_file_is_still_refused(tcw, tmp_path):
    """The object's meta.yaml tracked and the configuration not: the new
    description git would ignore comes from a tracked file, so it is
    refused."""
    app = _committed(tmp_path / "app", {".gitignore": "tcw-config.yaml\ndescription.md\n",
                                        "tcw-config.yaml": CONFIG,
                                        "docs/capabilities/x/meta.yaml": "name: X\n"})
    assert "tcw-config.yaml" not in _git(app, "ls-files").split()
    done = tcw(["migrate", "--dry-run"], app)
    assert done.code == 3, done.err
    assert [line.split(":")[0] for line in b18(done.err)] == [
        "  B18 docs/capabilities/x/description.md"], done.err


# ── The plan's notes are said in every mode (review 2) ───────────────────────

GIT_NOTE = "were not checked against git's ignore rules"


def _broken_index(tmp_path: Path) -> Path:
    app = _committed(tmp_path / "app", {".gitignore": ALLOWLIST, "tcw-config.yaml": CONFIG})
    (app / ".git/index").write_bytes(b"garbage")
    return app


def test_a_real_run_says_the_note_before_it_writes(tcw, tmp_path):
    app = _broken_index(tmp_path)
    done = tcw(["migrate", "--no-jira"], app)
    assert done.code == 0, done.err
    lines = done.err.splitlines()
    note = [at for at, line in enumerate(lines) if GIT_NOTE in line]
    first = next(at for at, line in enumerate(lines) if line.startswith("write "))
    assert len(note) == 1 and note[0] < first, done.err


def test_a_run_another_blocker_refuses_still_says_the_note(tcw, tmp_path, monkeypatch):
    from tcw.migrate import plan
    from tcw.migrate.model import Blocker
    app = _broken_index(tmp_path)
    monkeypatch.setattr(plan, "other_checkout_blockers",
                        lambda root, steps: [Blocker("B19", "x", "a reason", "a fix")])
    for argv in (["migrate", "--dry-run"], ["migrate", "--no-jira"]):
        done = tcw(argv, app)
        assert done.code == 3, done.err
        assert "  B19 x: a reason; a fix" in done.err
        assert len([line for line in done.err.splitlines() if GIT_NOTE in line]) == 1, \
            done.err


def test_a_jira_failure_while_planning_still_says_the_note(tcw, tmp_path, monkeypatch):
    from tcw.errors import TcwError
    from tcw.migrate import plan

    def failing(*args, **kwargs):
        raise TcwError("Jira is down")
    app = _broken_index(tmp_path)
    monkeypatch.setattr(plan, "plan_jira_half", failing)
    for argv in (["migrate", "--dry-run"], ["migrate"]):
        done = tcw(argv, app)
        assert done.code != 0, done.err
        assert "error: Jira is down" in done.err
        assert len([line for line in done.err.splitlines() if GIT_NOTE in line]) == 1, \
            done.err
