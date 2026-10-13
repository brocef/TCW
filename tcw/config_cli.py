"""`tcw config show [--origin]` — the configuration a command in this project
actually runs with, every layer merged (TCW-72 Design 8).

The output is YAML that reads back as exactly the merged values. Each list
entry is written on one line, so a comment can follow it: `--origin` adds one
after every value and list entry, naming the layer it came from, and a
trailing block of comments lists what a personal file set that was refused or
skipped. Comments change nothing a YAML reader sees.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from tcw import exit as codes
from tcw.errors import NO_PROJECT, BackendError, ConfigError

NAME = "config"

#: A string YAML reads back as itself when written bare: no quoting needed.
_PLAIN = re.compile(r"[A-Za-z0-9_./][A-Za-z0-9_./ -]*")


def _scalar(value: Any) -> str:
    """One value on one line, as YAML reads it back. A string is written bare
    when that reads back as the same string, and otherwise in JSON's
    double-quoted form, which YAML reads the same way."""
    import yaml
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return json.dumps(value)
    text = str(value)
    if (_PLAIN.fullmatch(text) and not text.endswith(" ")
            and yaml.safe_load(text) == text):
        return text
    return json.dumps(text)


def _flow(value: Any) -> str:
    """A mapping or list in YAML's one-line flow form."""
    if isinstance(value, dict):
        return "{" + ", ".join(f"{_scalar(k)}: {_flow(v)}"
                               for k, v in value.items()) + "}"
    if isinstance(value, list):
        return "[" + ", ".join(_flow(v) for v in value) + "]"
    # A bare string never holds a comma, bracket, brace, colon or `#`
    # (`_PLAIN`), so it cannot end a flow value early.
    return _scalar(value)


def _entry(value: Any) -> str:
    """A list entry: a mapping of one plain key and value in block form
    (`builtin: true`, `file: a.md`), anything larger in flow form."""
    if isinstance(value, dict) and len(value) == 1:
        (key, inner), = value.items()
        if not isinstance(inner, (dict, list)):
            return f"{_scalar(key)}: {_scalar(inner)}"
    if isinstance(value, (dict, list)):
        return _flow(value)
    return _scalar(value)


def _packaged(path: tuple) -> str | None:
    """The packaged file a built-in entry stands for."""
    if path[:2] == ("work", "stages") and len(path) >= 4 and path[3] == "prompt":
        return f"tcw/work/prompts/{path[2]}.md"
    if path[:2] == ("work", "procedures") and len(path) >= 3:
        return f"tcw/work/procedures/{path[2]}.md"
    return None


class _Writer:
    def __init__(self, config, *, origin: bool):
        self.config = config
        self.origin = origin
        self.lines: list[str] = []

    def comment(self, path: tuple, value: Any) -> str:
        """What follows a value: its layer with `--origin`; the packaged file
        for a built-in entry always."""
        from tcw.config import shown_in
        packaged = (_packaged(path) if isinstance(value, dict)
                    and value.get("builtin") is True else None)
        parts = []
        if self.origin:
            found = self.config.origins.get(path)
            if found is None and path and isinstance(path[-1], int):
                found = self.config.origins.get(path[:-1])
            if found is not None:
                parts.append(found.layer if found.file is None
                             or found.layer == "project"
                             else f"{found.layer}: "
                                  f"{shown_in(found.file, self.config.root)}")
        if packaged:
            parts.append(packaged)
        return f"  # {', '.join(parts)}" if parts else ""

    def mapping(self, values: dict, path: tuple, indent: str) -> None:
        for key, value in values.items():
            here = (*path, key)
            label = f"{indent}{_scalar(key)}:"
            if isinstance(value, dict) and value:
                self.lines.append(label)
                self.mapping(value, here, indent + "  ")
            elif isinstance(value, list) and value:
                self.lines.append(label)
                for i, entry in enumerate(value):
                    self.lines.append(f"{indent}  - {_entry(entry)}"
                                      f"{self.comment((*here, i), entry)}")
            else:
                text = "{}" if isinstance(value, dict) else \
                    "[]" if isinstance(value, list) else _scalar(value)
                self.lines.append(f"{label} {text}{self.comment(here, value)}")


def _set_aside(config) -> list[str]:
    """One comment line for each value a personal file set that was not used."""
    from tcw.config import dotted, shown_in
    lines = []
    for kind, settings in (("skipped", config.skipped), ("refused", config.refused)):
        for s in settings:
            hidden = s.key_path and str(s.key_path[-1]).endswith("-env")
            value = "(value not shown)" if hidden else _flow(s.value)
            where = shown_in(s.file, config.root) if s.file is not None else ""
            lines.append(f"# {kind}: {dotted(s.key_path)}: {value} "
                         f"({s.reason}, {where})")
    return lines


def render(config, *, origin: bool) -> str:
    """The configuration's merged values as YAML; with `origin`, a comment on
    each value naming its layer and the set-aside block after them."""
    writer = _Writer(config, origin=origin)
    writer.mapping(config.values, (), "")
    lines = writer.lines
    if origin:
        lines += _set_aside(config)
    return "\n".join(lines) + "\n"


def _show(args: argparse.Namespace) -> int:
    from tcw.config import effective
    from tcw.store.fs import find_project_root
    root = find_project_root(Path.cwd())
    if root is None:
        raise BackendError(NO_PROJECT)
    config = effective(root)
    # Without `--origin`, a problem stops the command as it stops every
    # other. With it, everything that could be merged is still printed, so a
    # person can find the line that is stopping the others (Design 8.3). A
    # project file that cannot be read leaves nothing to print.
    if config.problems and (not args.origin or config.unreadable):
        raise ConfigError(config.problems)
    sys.stdout.write(render(config, origin=args.origin))
    if config.problems:
        for problem in config.problems:
            print(f"tcw config show: {problem}", file=sys.stderr)
        return codes.ERROR
    return codes.OK


def add_subparser(sub: argparse._SubParsersAction) -> None:
    from tcw.cli_help import command, group
    p = group(sub, NAME, help="the configuration this project runs with")
    verbs = p.add_subparsers(dest="config_verb", required=True)
    p = command(verbs, "show",
                help="the effective configuration: TCW's defaults, "
                     "tcw-config.yaml and your personal files, merged",
                prints="the effective configuration as YAML; with --origin, where "
                       "each value came from",
                writes="nothing",
                examples=["config show", "config show --origin"])
    p.add_argument("--origin", action="store_true",
                   help="name the layer of every value, and list what your "
                        "personal files set that was not used; prints even when "
                        "something is wrong")
    p.set_defaults(own_config=True, func=_show)
