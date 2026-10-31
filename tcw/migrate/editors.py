"""One 3.x YAML file turned into its 4.0 text (TCW-116 Design 2.8; Decided 9).

The text is edited, never regenerated, so its comments and layout stay. The
order on one file is fixed: the structural edits first (`edit_text`, checked
by its own `_verify`); then the reference values (`rewrite_yaml`, asked
through a `replace` function) on that output; then the final text is parsed
and compared with the mapping the plan intends. The text written is the text
checked, so the second step cannot undo the first unnoticed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import yaml

from tcw.project_files import version_problem
from tcw.reference_fields import Field
from tcw.rewrite import Replace, rewrite_yaml
from tcw.store.config_edit import ConfigEditRefused, Edit, edit_text


@dataclass
class Converted:
    """A file's 4.0 text, and what the edit took or changed on the way:
    the comments a removed block took with it, and each reference changed
    (`<field> <old> -> <new>`)."""

    text: str
    dropped: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)


def convert_text(path: Path | str, text: str | None, edits: list[Edit], *,
                 fields: Iterable[Field] = (), replace: Replace | None = None,
                 expect: dict | None = None) -> Converted:
    """`text` with `edits` made, `tcw-version` first, and each reference at
    one of `fields` replaced as `replace` says. `expect`, when given, is the
    mapping the result must parse to. Raises `ConfigEditRefused` for an edit
    that cannot be made in place, or a result that does not mean `expect`."""
    dropped: list[str] = []
    new = edit_text(Path(path), text, list(edits), versioned=True, dropped=dropped)
    if new is None:
        new = text or ""
    changed: list[str] = []
    if replace is not None:
        new, changed, _ = rewrite_yaml(new, list(fields), replace)
    _check(path, new, expect)
    return Converted(new, dropped, changed)


def _check(path: Path | str, text: str, expect: dict | None) -> None:
    from tcw.store.fs import _UniqueKeyLoader
    from tcw.store.yaml_source import load
    try:
        data = load(text, path, _UniqueKeyLoader)
    except yaml.YAMLError as error:
        raise ConfigEditRefused(f"{path}: the converted text does not parse: {error}") \
            from None
    problem = version_problem(data)
    if problem is not None:
        raise ConfigEditRefused(f"{path}: the converted text {problem}")
    if expect is not None and data != expect:
        raise ConfigEditRefused(f"{path}: the converted text would not mean what was "
                                f"intended")
