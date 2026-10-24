"""The references a move or rename rewrites in the repository, and the
mentions it lists (TCW-114 Design 6).

A move changes full identifiers; every reference the active project keeps in
its repository that names a changed one is rewritten to the new one: the
reference fields of every term's and capability's state file, every entry of
every item's `capabilities.yaml`, and every `tcw://` link in a Markdown file
of the three stores. Which fields hold references is read from the one table,
`tcw.reference_fields.FIELDS`, so a field `tcw validate` checks is a field a
move rewrites (Design 6.3).

A YAML value is replaced by its position in the text, only where it sits at a
field the table names for that record; every other byte stays, quoting
included (plan choice 6). A value equal to an old identifier anywhere else is
a mention: left as it is, and listed (Design 6.4).

The work items' own state files are not read here: they are the work
backend's, which rewrites them itself before it calls back (Design 7.2).
Nothing outside the active project's three stores is read (Design 6.5).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Iterator, Mapping

import yaml

from tcw.ids import FullId, IdError, parse_address, parse_full_id
from tcw.object_folders import STATE_FILES, read_state, walk
from tcw.reference_fields import Field, fields_of

#: `(old, new)` pairs of full identifiers a move changes.
Changes = Iterable[tuple[FullId, FullId]]

#: Given a field's row and a reference's text (a `!` taken off), the text
#: that replaces it, or None to leave it (TCW-116 Decided 9).
Replace = Callable[[Field, str], "str | None"]

#: The record each store's state files are, in the table.
_RECORDS = {"taxonomy": "term", "capabilities": "capability"}
_CAPABILITIES_FILE = "capabilities.yaml"


@dataclass
class Rewritten:
    """One file the rewrite read: the references it changed (`changed`, as
    `<field> <old> -> <new>`) and those that already named a new identifier
    (`done`, as `<field> <new>`), which an earlier run rewrote."""

    path: Path
    changed: list[str] = field(default_factory=list)
    done: list[str] = field(default_factory=list)


class RewriteStopped(OSError):
    """A file could not be written. `results` holds every file rewritten
    before it, and the ones found already done, for the stop message."""

    def __init__(self, error: OSError, path: Path, results: list[Rewritten]):
        super().__init__(error.errno, f"{path}: {error.strerror or error}")
        self.path = path
        self.results = results


# ---------------------------------------------------------------------------
# Where the records are


def store_roots(active_root: Path) -> dict[str, Path]:
    """The active project's own store folders, by namespace, those that
    exist. Its own: what it inherits is another project's (Design 6.5)."""
    from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore
    from tcw.work.open import work_path
    roots: dict[str, Path] = {}
    for namespace, cls in (("taxonomy", FsTaxonomyStore),
                           ("capabilities", FsCapabilitiesStore)):
        try:
            root = Path(cls.open(Path(active_root)).root)
        except Exception:     # no such store here, or one validate reports
            continue
        if root.is_dir():
            roots[namespace] = root
    try:
        root = work_path(Path(active_root))
    except Exception:
        root = None
    if root is not None and root.is_dir():
        roots["work"] = root
    return roots


def _records(roots: Mapping[str, Path]) -> Iterator[tuple[Path, tuple[Field, ...]]]:
    """Every YAML record the rewrite reads, with the table's rows for it:
    each term's and capability's state file, and each item's
    `capabilities.yaml`. Never an item's state file (the backend's)."""
    for namespace, record in _RECORDS.items():
        if namespace not in roots:
            continue
        rows = fields_of(record)
        for id_path in walk(roots[namespace], namespace).objects:
            yield roots[namespace] / id_path / STATE_FILES[namespace], rows
    if "work" in roots:
        rows = fields_of("capabilities-yaml")
        for id_path in walk(roots["work"], "work").objects:
            path = roots["work"] / id_path / _CAPABILITIES_FILE
            if path.is_file():
                yield path, rows


def _text_files(roots: Mapping[str, Path]) -> Iterator[Path]:
    """Every file under the three stores, `resources/` included, in name
    order: for links and mentions, not objects."""
    for root in roots.values():
        for path in sorted(root.rglob("*")):
            if path.is_file() and not any(p.startswith(".")
                                          for p in path.relative_to(root).parts):
                yield path


# ---------------------------------------------------------------------------
# Matching (Design 6.2)


def _swap(token: str, row: Field, changes: Mapping[FullId, FullId],
          news: set[FullId]) -> tuple[str, str | None]:
    """`(kind, new token)` for one reference: `changed` with the new text,
    `done` when it already names a new identifier, `other` otherwise. A
    negatable row's `!` stays outside the reference."""
    negated = row.negatable and token.startswith("!")
    body = token[1:] if negated else token
    try:
        found = parse_full_id(body, row.namespace)
    except IdError:
        return "other", None
    if found in changes:
        return "changed", ("!" if negated else "") + str(changes[found])
    if found in news:
        return "done", None
    return "other", None


def _key_paths(rows: Iterable[Field]) -> dict[tuple[str, ...], Field]:
    """The key path of every scalar the rows name: `(name,)` for a value at
    the key (one reference, or a comma list), `(name, [])` for a list item.
    A dotted name is a key inside a mapping."""
    out: dict[tuple[str, ...], Field] = {}
    for row in rows:
        keys = tuple(row.name.split(".")) if row.record == "capabilities-yaml" \
            else (row.name,)
        out[keys] = row
        if row.many:
            out[keys + ("[]",)] = row
    return out


def _scalars(text: str) -> Iterator[tuple[tuple[str, ...], yaml.ScalarEvent]]:
    """Every value scalar of a YAML document with its key path: the mapping
    keys above it, and `[]` for a sequence item."""
    stack: list[list] = []                      # ["map", key, want_key] / ["seq"]

    def path() -> tuple[str, ...]:
        out = []
        for frame in stack:
            if frame[0] == "map":
                out.append(str(frame[1]))
            else:
                out.append("[]")
        return tuple(out)

    def consumed() -> None:
        if stack and stack[-1][0] == "map":
            stack[-1][2] = True

    for event in yaml.parse(text, Loader=yaml.SafeLoader):
        if isinstance(event, (yaml.MappingStartEvent, yaml.SequenceStartEvent)):
            if stack and stack[-1][0] == "map" and stack[-1][2]:
                stack[-1][1], stack[-1][2] = None, False   # a mapping as a key
            stack.append(["map", None, True] if isinstance(
                event, yaml.MappingStartEvent) else ["seq"])
        elif isinstance(event, (yaml.MappingEndEvent, yaml.SequenceEndEvent)):
            stack.pop()
            consumed()
        elif isinstance(event, yaml.ScalarEvent):
            if stack and stack[-1][0] == "map" and stack[-1][2]:
                stack[-1][1], stack[-1][2] = event.value, False
                continue
            yield path(), event
            consumed()
        elif isinstance(event, yaml.AliasEvent):
            consumed()


def _scalar_text(value: str, style: str | None) -> str:
    """`value` written in `style` (plain, `'` or `"`); a plain value YAML
    would read differently is written in single quotes."""
    if style == "'":
        return "'" + value.replace("'", "''") + "'"
    if style == '"' or style in ("|", ">"):
        return json.dumps(value, ensure_ascii=False)
    # A plain value changes only in an identifier's characters, which need
    # no quotes where the old value needed none.
    try:
        same = yaml.safe_load(value) == value and "\n" not in value
    except yaml.YAMLError:
        same = False
    return value if same else "'" + value.replace("'", "''") + "'"


def _reads_as_text(value: str) -> bool:
    try:
        return isinstance(yaml.safe_load(value), str)
    except yaml.YAMLError:
        return True


def _asked(replace: Replace) -> Callable[[str, Field], tuple[str, str | None]]:
    """A `_swap` that asks `replace`; it never finds one already done."""
    def swap(token: str, row: Field) -> tuple[str, str | None]:
        negated = row.negatable and token.startswith("!")
        body = token[1:] if negated else token
        new = replace(row, body) if body else None
        if new is None or new == body:
            return "other", None
        return "changed", ("!" if negated else "") + new
    return swap


def rewrite_yaml(text: str, fields: Iterable[Field], changes: Changes | Replace
                 ) -> tuple[str, list[str], list[str]]:
    """`text` with every reference at a field `fields` names that equals an
    old identifier replaced by the new one, each value's quoting kept and
    every other byte unchanged; and the references changed and those found
    already naming a new identifier. A value at any other key is never
    changed. Raises `yaml.YAMLError` for text that is not YAML.

    `changes` may instead be a function, asked for every reference at a field
    `fields` names, which returns what replaces it (`tcw migrate`'s
    conversions, TCW-116 Decided 9). It is never asked about a plain value
    YAML reads as anything but text (`Roles: 5`), which names nothing."""
    asked = callable(changes)
    if callable(changes):
        swap = _asked(changes)
    else:
        pairs = dict(changes)
        news = set(pairs.values())

        def swap(token: str, row: Field) -> tuple[str, str | None]:
            return _swap(token, row, pairs, news)
    paths = _key_paths(fields)
    edits: list[tuple[int, int, str]] = []
    changed: list[str] = []
    done: list[str] = []
    for key_path, event in _scalars(text):
        row = paths.get(key_path)
        if row is None or not isinstance(event.value, str):
            continue
        if asked and event.style is None and not _reads_as_text(event.value):
            continue
        listed = row.many and key_path[-1] != "[]"
        pieces = event.value.split(",") if listed else [event.value]
        rebuilt = []
        touched = False
        for piece in pieces:
            token = piece.strip()
            kind, new = swap(token, row)
            if kind == "changed":
                lead = piece[:len(piece) - len(piece.lstrip())]
                trail = piece[len(piece.rstrip()):]
                rebuilt.append(lead + new + trail)
                changed.append(f"{row.name} {token} -> {new}")
                touched = True
            else:
                if kind == "done":
                    done.append(f"{row.name} {token}")
                rebuilt.append(piece)
        if touched:
            value = ",".join(rebuilt)
            edits.append((event.start_mark.index, event.end_mark.index,
                          _scalar_text(value, event.style)))
    for start, end, new_text in sorted(edits, reverse=True):
        text = text[:start] + new_text + text[end:]
    return text, changed, done


def rewrite_own_id(text: str, old_part: str, new_part: str) -> tuple[str, str | None]:
    """A state file's text with its own top-level `id` changed from the old
    last part to the new one, its quoting kept (Design 5.2); and `changed`,
    `done` (it already holds the new one) or None (no `id`, or another
    value, left as it is)."""
    for key_path, event in _scalars(text):
        if key_path != ("id",) or not isinstance(event.value, str):
            continue
        if event.value == new_part:
            return text, "done"
        if event.value != old_part:
            return text, None
        start, end = event.start_mark.index, event.end_mark.index
        return text[:start] + _scalar_text(new_part, event.style) + text[end:], "changed"
    return text, None


def rewrite_links(text: str, changes: Changes) -> tuple[str, list[str], list[str]]:
    """`text` with every `tcw://` object link outside code that names an old
    identifier pointing at the new one; the link's text and everything
    around its address unchanged."""
    from tcw.reference_fields import field as row_of
    from tcw.validate import links_outside_code
    changes = dict(changes)
    news = set(changes.values())
    row = row_of("markdown", "link")
    edits, changed, done = [], [], []
    for start, end, address in links_outside_code(text):
        try:
            found = parse_address(address)
        except IdError:
            continue
        if not isinstance(found, FullId):
            continue
        kind, new = _swap(str(found), row, changes, news)
        if kind == "changed":
            edits.append((start, end, changes[found].address()))
            changed.append(f"link {address} -> {changes[found].address()}")
        elif kind == "done":
            done.append(f"link {address}")
    for start, end, new_text in sorted(edits, reverse=True):
        text = text[:start] + new_text + text[end:]
    return text, changed, done


# ---------------------------------------------------------------------------
# The four operations tcw/move.py calls


def rewrite_references(active_root: Path, changes: Changes) -> list[Rewritten]:
    """Rewrite every reference the active project's repository keeps that
    names a changed identifier (Design 6.1), each file replaced in one step
    (Design 6.6). Returns, per file read, what it changed and what was
    already done; a file with neither is left out. A file that cannot be
    written raises `RewriteStopped`, carrying the files before it.

    The one file outside the stores it reads is the project's migration
    record, `.tcw/tcw-migration.yaml` (TCW-116 Design 7, 8.5): for a change
    of a capability, every `capability-ids` and `moved` value that is the
    old id-path, or lies below it, is given the new one, so that a project
    migrated later still finds the capability its override names."""
    from tcw.store.fs import _atomic_write_all
    changes = list(changes)
    roots = store_roots(active_root)
    plans: dict[Path, tuple[str, Rewritten]] = {}
    record = _migration_record(Path(active_root), changes)
    if record is not None:
        plans[record[1].path] = record
    for path, rows in _records(roots):
        try:
            text = path.read_text(encoding="utf-8")
            new, changed, done = rewrite_yaml(text, rows, changes)
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
            continue                 # `unreadable_records` refused it before
        if changed or done:
            plans[path] = (new if changed else text, Rewritten(path, changed, done))
    for path in _text_files(roots):
        if path.suffix != ".md":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        new, changed, done = rewrite_links(text, changes)
        if changed or done:
            plans[path] = (new if changed else text, Rewritten(path, changed, done))
    results: list[Rewritten] = []
    for path, (text, result) in plans.items():
        if result.changed:
            try:
                _atomic_write_all([(path, text)])
            except OSError as error:
                raise RewriteStopped(error, path, results) from error
        results.append(result)
    return results


#: The migration record and the sections of it that hold id-paths.
MIGRATION_RECORD = ".tcw/tcw-migration.yaml"
_RECORD_SECTIONS = ("capability-ids", "moved")


def _migration_record(active_root: Path, changes: list[tuple[FullId, FullId]]
                      ) -> tuple[str, Rewritten] | None:
    """The record's new text and what changed in it, or None when the
    project keeps no record or no value in it changes."""
    moves = sorted(((old.id_path, new.id_path) for old, new in changes
                    if old.namespace == "capabilities" and new.namespace == "capabilities"),
                   key=lambda pair: -len(pair[0]))
    path = active_root / MIGRATION_RECORD
    if not moves or not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
        found = list(_scalars(text))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return None
    edits, changed = [], []
    for key_path, event in found:
        if len(key_path) != 2 or key_path[0] not in _RECORD_SECTIONS \
                or not isinstance(event.value, str):
            continue
        value = event.value
        for old, new in moves:
            if value == old or value.startswith(old + "/"):
                now = new + value[len(old):]
                edits.append((event.start_mark.index, event.end_mark.index,
                              _scalar_text(now, event.style)))
                changed.append(f"{key_path[0]}.{key_path[1]} {value} -> {now}")
                break
    if not edits:
        return None
    for start, end, new_text in sorted(edits, reverse=True):
        text = text[:start] + new_text + text[end:]
    return text, Rewritten(path, changed)


def field_problems(active_root: Path, changes: Changes) -> list[str]:
    """Each reference a rewrite would make invalid for its field (Design 5.4
    f): a `Roles` or `When` value whose capability would leave `roles/` or
    `conditions/`. Named by field and record."""
    changes = dict(changes)
    problems = []
    roots = store_roots(active_root)
    for path, rows in _records(roots):
        grouped = [r for r in rows if r.group]
        if not grouped:
            continue
        try:
            text = path.read_text(encoding="utf-8")
            data = yaml.safe_load(text)
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
            continue
        from tcw.reference_fields import tokens
        for row in grouped:
            for token in tokens(row, data.get(row.name) if isinstance(data, dict) else None):
                body = token[1:] if row.negatable and token.startswith("!") else token
                try:
                    found = parse_full_id(body, row.namespace)
                except IdError:
                    continue
                new = changes.get(found)
                if new is not None and not new.id_path.startswith(row.group + "/"):
                    problems.append(
                        f"{row.name} in {path} names {found}, which would become "
                        f"{new}; {row.name} takes only {row.group}/ capabilities")
    return problems


def unreadable_records(active_root: Path) -> list[str]:
    """Every record that could hold a reference and cannot be read (Design
    5.4 e): any object's state file in the three stores, and any item's
    `capabilities.yaml`, each with why."""
    out = []
    roots = store_roots(active_root)
    for namespace, root in roots.items():
        for id_path in walk(root, namespace).objects:
            path = root / id_path / STATE_FILES[namespace]
            try:
                data, problem = read_state(path)
            except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
                out.append(f"{path}: cannot be read: {error}")
                continue
            if problem is not None:
                out.append(f"{path}: {problem}")
            if namespace == "work":
                declared = root / id_path / _CAPABILITIES_FILE
                if declared.is_file():
                    try:
                        yaml.safe_load(declared.read_text(encoding="utf-8"))
                    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
                        out.append(f"{declared}: cannot be read: {error}")
    return out


#: A character that can be part of an id-part, and so cannot bound one.
_PART = r"A-Za-z0-9_\-"


def mentions(active_root: Path, changes: Changes) -> list[str]:
    """Every line of a text file in the three stores that still names an
    old identifier, by full identifier or by its id-path as a whole sequence
    of parts (Design 6.4): `<file>:<line>: names <old>, not rewritten`. A
    file that is not UTF-8 is skipped."""
    olds = [old for old, _ in changes]
    right = rf"(?![{_PART}]|/[{_PART}])"
    patterns = [(old, re.compile(
        rf"(?<![{_PART}.]){re.escape(str(old))}{right}"
        rf"|(?<![{_PART}./]){re.escape(old.id_path)}{right}")) for old in olds]
    out = []
    for file in _text_files(store_roots(active_root)):
        try:
            lines = file.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for number, line in enumerate(lines, start=1):
            for old, pattern in patterns:
                if pattern.search(line):
                    out.append(f"{file}:{number}: names {old}, not rewritten")
    return out
