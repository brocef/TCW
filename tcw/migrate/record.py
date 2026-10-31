"""The migration record, `.tcw/tcw-migration.yaml` (TCW-116 Design 7).

Written in phase A of the first run with something to record, and added to
by later runs: every `cap-…` id removed, with its id-path after the run;
every object an override's move put at a new id-path; and every value
removed with no 4.0 home. An entry already there is left as it is. Only
`tcw migrate` reads it.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from tcw.migrate.model import Write, file_digest
from tcw.project_files import TCW_FOLDER, VERSION_KEY, version_line
from tcw.store.config_edit import read_text

RECORD = f"{TCW_FOLDER}/tcw-migration.yaml"


def read_record(root: Path) -> dict:
    """The record of the project at `root`, without its version, or `{}`."""
    try:
        text = read_text(Path(root) / RECORD)
        data = yaml.safe_load(text) if text else None
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return {}
    return {k: v for k, v in data.items() if k != VERSION_KEY} \
        if isinstance(data, dict) else {}


def plan_record(root: Path, ids: dict[str, str], moved: dict[str, str] | None = None,
                removed: list[dict] | None = None) -> Write | None:
    """The record's one write, merged with what it already holds, or None
    when it would not change."""
    path = Path(root) / RECORD
    old = read_record(root)
    merged = {key: (dict(value) if isinstance(value, dict) else list(value))
              for key, value in old.items() if isinstance(value, (dict, list))}
    conversions = []
    for key, new in (("capability-ids", ids), ("moved", moved or {})):
        if not new:
            continue
        section = merged.setdefault(key, {})
        for k, v in new.items():
            section.setdefault(k, v)
        conversions.append("C10" if key == "capability-ids" else "C14")
    if removed:
        section = merged.setdefault("removed", [])
        section += [entry for entry in removed if entry not in section]
        conversions.append("C6")
    if merged == old:
        return None
    text = version_line() + yaml.safe_dump(merged, sort_keys=False, allow_unicode=True)
    try:
        if read_text(path) == text:
            return None
    except (OSError, UnicodeDecodeError):
        pass
    return Write(RECORD, "A", file_digest(path), text, tuple(conversions))
