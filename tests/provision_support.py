"""What the provisioning tests share (TCW-115 plan, Step 11): the stand-in
`git`, remotes made in the test's own folder, and project files to commit
into them.

**The stand-in `git`** is a script put first on `PATH` that records every
call and refuses `clone`, `fetch`, `ls-remote` and `pull` (exit 97, "stand-in
git: network call") unless the test allows `clone`, which it then passes to
the real git. Every other call goes to the real git, since the registry runs
`git rev-parse` and `git config` to find a project. `HOME` is set outside the
test's folder (plan choice 27).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.project_files import version_line

REAL_GIT = shutil.which("git")

_SCRIPT = """#!/bin/sh
log='{log}'
{{ for a in "$@"; do printf '%s\\037' "$a"; done; printf '\\n'; }} >> "$log"
skip=0
sub=""
for a in "$@"; do
  if [ "$skip" = 1 ]; then skip=0; continue; fi
  case "$a" in
    -C|-c) skip=1 ;;
    -*) ;;
    *) sub="$a"; break ;;
  esac
done
case "$sub" in
  clone)
    if [ -f '{allow}' ]; then exec '{git}' "$@"; fi
    echo "stand-in git: network call" >&2; exit 97 ;;
  fetch|ls-remote|pull)
    echo "stand-in git: network call" >&2; exit 97 ;;
esac
exec '{git}' "$@"
"""


class StandInGit:
    def __init__(self, folder: Path):
        self.folder = folder
        self.log = folder / "calls.log"
        self.allow = folder / "allow-clone"

    def allow_clone(self, allowed: bool = True) -> None:
        if allowed:
            self.allow.write_text("")
        elif self.allow.exists():
            self.allow.unlink()

    def calls(self, kind: str | None = None) -> list[list[str]]:
        """Every call recorded, or those whose git command is `kind`."""
        if not self.log.exists():
            return []
        out = []
        for line in self.log.read_text().splitlines():
            argv = line.split("\x1f")[:-1]
            if kind is None or _subcommand(argv) == kind:
                out.append(argv)
        return out

    def reset(self) -> None:
        if self.log.exists():
            self.log.unlink()


def _subcommand(argv: list[str]) -> str | None:
    skip = False
    for arg in argv:
        if skip:
            skip = False
            continue
        if arg in ("-C", "-c"):
            skip = True
            continue
        if not arg.startswith("-"):
            return arg
    return None


@pytest.fixture
def stand_in_git(tmp_path, tmp_path_factory, monkeypatch) -> StandInGit:
    folder = tmp_path_factory.mktemp("stand-in-bin")
    git = StandInGit(folder)
    script = folder / "git"
    script.write_text(_SCRIPT.format(log=git.log, allow=git.allow, git=REAL_GIT))
    script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{folder}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("HOME", str(tmp_path_factory.mktemp("home")))
    return git


def real_git(cwd: Path, *argv: str) -> str:
    return subprocess.run([REAL_GIT, "-C", str(cwd), *argv], check=True,
                          capture_output=True, text=True,
                          stdin=subprocess.DEVNULL).stdout


def config_text(project_id: str, **keys) -> str:
    """A `.tcw/tcw-config.yaml` declaring `project_id`, then `keys`."""
    return version_line() + yaml.safe_dump({"id": project_id, **keys}, sort_keys=False)


def manifest_text(entries: dict) -> str:
    return version_line() + yaml.safe_dump({"projects": entries}, sort_keys=False)


def project_files(project_id: str, *, at: str = "", manifest: dict | None = None,
                  **keys) -> dict:
    """The files of a project at `at` in a repository, for `make_remote`."""
    base = f"{at}/" if at else ""
    files = {f"{base}.tcw/tcw-config.yaml": config_text(project_id, **keys)}
    if manifest is not None:
        files[f"{base}.tcw/tcw-manifest.yaml"] = manifest_text(manifest)
    return files


def make_remote(tmp_path: Path, name: str, files: dict, branch: str = "main") -> Path:
    """A bare repository at `<tmp>/remotes/<name>.git` holding `files` on
    `branch`, each value text or `("link", target)` for a symbolic link."""
    work = tmp_path / "remote-work" / name
    work.mkdir(parents=True)
    for relative, content in files.items():
        path = work / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, tuple) and content[0] == "link":
            os.symlink(content[1], path)
        else:
            path.write_text(content)
    real_git(work, "init", "-q", "-b", branch)
    real_git(work, "add", "-A")
    real_git(work, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "remote")
    bare = tmp_path / "remotes" / f"{name}.git"
    bare.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([REAL_GIT, "clone", "-q", "--bare", str(work), str(bare)], check=True,
                   capture_output=True, stdin=subprocess.DEVNULL)
    return bare
