"""The 2.x work store is gone from the code (TCW-70 AC 13, and AC 10's
import check).

The packaged prompt and procedure texts are Markdown, not `.py`, and are
TCW-74's to rewrite, so they are not scanned.
"""

import importlib
import importlib.util
import re
from pathlib import Path

import pytest

import tcw
from tests.work.removed_2x import REMOVED_2X_COMMANDS

PACKAGE = Path(tcw.__file__).resolve().parent

NAMES = ("graveyard.yaml", "dod.yaml", "renames.yaml", "state.yaml",
         "tracker.yaml", "FsWorkStore", "WORK_STATUSES", "LIFECYCLE_STEPS")
COMMAND = re.compile(
    r"\b(" + "|".join(re.escape(c) for c in REMOVED_2X_COMMANDS) + r")\b")


def sources():
    return sorted(PACKAGE.rglob("*.py"))


def test_the_scan_sees_the_package():
    assert PACKAGE / "work" / "cli.py" in sources()


@pytest.mark.parametrize("path", sources(), ids=lambda p: str(p.relative_to(PACKAGE)))
def test_no_2x_name_or_removed_command(path):
    text = path.read_text(encoding="utf-8")
    found = [name for name in NAMES if name in text]
    found += sorted({m.group(1) for m in COMMAND.finditer(text)})
    assert found == [], f"{path.relative_to(PACKAGE)} names {', '.join(found)}"


def test_the_harness_module_is_gone():
    assert not (PACKAGE / "harness.py").exists()


def test_the_tracker_package_is_gone():
    """`import tcw.tracker` fails in an installed tree. Asked of this package
    rather than of the import alone: with a second editable install of another
    checkout on the path (a worktree beside the primary checkout), that
    install's import hook can still answer for `tcw.tracker`. A checkout that
    git moved past the package's deletion can keep its ignored `__pycache__/`,
    which Python then reports as a package with no file; that folder holds no
    source, so it is not the package coming back."""
    assert not (PACKAGE / "tracker").exists()
    try:
        spec = importlib.util.find_spec("tcw.tracker")
    except ModuleNotFoundError:
        return
    if spec is None:
        return
    if spec.origin is None:
        sources = [p for folder in spec.submodule_search_locations
                   for p in Path(folder).rglob("*.py")
                   if "__pycache__" not in p.parts]
        assert not sources, f"tcw.tracker still has source: {sources}"
        return
    assert PACKAGE not in Path(spec.origin).resolve().parents
