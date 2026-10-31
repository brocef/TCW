"""Writing and reading a fixture object's state file (TCW-111 Design 1).

A term, a capability or a work item is a folder holding its namespace's state
file, whose first line is the version of the TCW that wrote it. A fixture
that wrote `meta.yaml` or `item.yaml` now writes one of these through
`write_state`, by the same rule `tests/projectfiles.py` uses for a
configuration file: **the version line is added only to text that stays one
mapping**, so a test of a broken file, a list, bytes that are not UTF-8, or a
file that already says `tcw-version` gets exactly what it wrote.

The three names are written out here rather than taken from
`tcw.object_folders.STATE_FILES`, so the code's names and the tests' names
are two facts: moving one without the other turns the tests red.
`tests/test_statefiles_helper.py` checks that they agree.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from tcw.project_files import VERSION_KEY, version_line
from tests.projectfiles import _versioned

TAXONOMY_STATE = "tcw-taxonomy.yaml"
CAPABILITY_STATE = "tcw-capability.yaml"
ITEM_STATE = "tcw-work-item.yaml"


def write_state(path, data="", encoding: str | None = "utf-8", **_) -> Path:
    """Write `data` to the state file at `path`, with the version line in
    front by the module's rule, making its folder."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _versioned(data)
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(data, encoding=encoding or "utf-8")
    return path


def write_state_data(path, mapping) -> Path:
    """The version line, then `mapping` as the stores dump it."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {k: v for k, v in (mapping or {}).items() if k != VERSION_KEY}
    text = version_line() + (yaml.safe_dump(body, sort_keys=False, allow_unicode=True)
                             if body else "")
    path.write_text(text, encoding="utf-8")
    return path


def read_state(path) -> dict:
    """The state file's mapping without `tcw-version`, for an assertion that
    compares a whole file's mapping."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return {k: v for k, v in data.items() if k != VERSION_KEY}


#: Each store's state file, by the store's folder name under `docs/`.
STATE_OF = {"taxonomy": TAXONOMY_STATE, "capabilities": CAPABILITY_STATE,
            "work": ITEM_STATE}

#: The 3.x name of a taxonomy or capability record's state file.
LEGACY_RECORD = "meta.yaml"


def record_file(folder, namespace: str) -> Path:
    """The state file of the record in `folder`: its TCW 4 one when present,
    else its 3.x `meta.yaml` (TCW-116 Design 8.4), so a test of this
    repository's own records reads them in either form."""
    folder = Path(folder)
    four = folder / STATE_OF[namespace]
    return four if four.is_file() else folder / LEGACY_RECORD


def record_files(root, namespace: str) -> list[Path]:
    """Every record state file below `root`, in either form."""
    names = (STATE_OF[namespace], LEGACY_RECORD)
    return sorted(p for p in Path(root).rglob("*") if p.name in names and p.is_file())
