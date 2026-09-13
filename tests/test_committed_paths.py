"""No committed data file carries a path that only exists on one machine.

The eval grading fixtures did. `timing.json` records where the runner put the
fixture tree, the runner writes that path absolutely, and four example runs were
committed with the author's home directory baked in. Every test reading them
passed locally and all ten failed in CI — the only place the path did not exist.

Scoped to data files, which are read as configuration or as fixtures, rather
than to everything tracked. Prose naming an absolute path is illustrating a
command for a human, and a test may legitimately use one as a literal string it
never opens; neither can break a run somewhere else.
"""

from __future__ import annotations

import subprocess

# A per-user directory on the platforms anyone builds this on. A data file
# naming one can only be read on the machine that wrote it.
HOME_PREFIXES = ("/Users/", "/home/", "C:\\Users\\")

DATA_SUFFIXES = (".json", ".yaml", ".yml", ".toml")


def test_no_committed_data_file_names_a_home_directory(request):
    root = request.config.rootpath
    listed = subprocess.run(["git", "-C", str(root), "ls-files", "-z"],
                            capture_output=True, text=True, check=True).stdout
    offenders = []
    for rel in (p for p in listed.split("\0") if p.endswith(DATA_SUFFIXES)):
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        offenders += [(rel, p) for p in HOME_PREFIXES if p in text]
    assert not offenders, (
        "a committed data file names a machine-specific home directory, so it "
        f"cannot be read anywhere else, CI included: {offenders}")
