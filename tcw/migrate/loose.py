"""Loose entries into `resources/` (TCW-116 Design 4.1, C13; plan Step 7).

A file or folder in a 3.x object's folder that TCW 4 would report as out of
place moves into that object's `resources/` by one rename, keeping its name
and its bytes. What names it is then rewritten where the name is exact: a
`prependedDocs` or `appendedDocs` entry, a relative Markdown link from a file
in the same object folder, and the text `<store path>/<id-path>/<entry>` in
any Markdown or YAML file of the project's stores. A shortened mention, the
object's folder name in full or cut after a `-` and followed by `…` or
`...`, then `/<entry>`, is A3.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from tcw.migrate.model import Move, Report, digest
from tcw.object_folders import RESOURCES, _skipped_in_object, fixed_files
from tcw.migrate.legacy import STATE_3X

#: Characters that continue a name, so cannot end a mention.
_NAME = r"A-Za-z0-9_\-"
_AFTER = rf"(?![{_NAME}]|\.[{_NAME}])"
#: The files whose text is searched and rewritten.
TEXT_SUFFIXES = (".md", ".yaml", ".yml")


@dataclass(frozen=True)
class Loose:
    """One entry moved: the store's folder relative to the project root, the
    object's id-path, and the entry's name."""

    store_rel: str
    id_path: str
    entry: str
    #: The object's id-path before the run, when an override's move (C14)
    #: takes the entry straight to the object's new place.
    origin: str | None = None

    @property
    def from_path(self) -> str:
        return self.origin or self.id_path

    @property
    def old(self) -> str:
        return f"{self.store_rel}/{self.from_path}/{self.entry}"

    @property
    def new(self) -> str:
        return f"{self.store_rel}/{self.id_path}/{RESOURCES}/{self.entry}"


def loose_entries(folder: Path, namespace: str, id_path: str, kept: set[str]) -> list[str]:
    """The names in an object's folder that TCW 4 reports as out of place
    (S111 Design 2.6 rows a and b): not hidden, not a fixed file or folder,
    not `resources/`, not the 3.x state file, and not a child object's
    folder or a folder on the way to one, which is left for `tcw validate`."""
    fixed = fixed_files(namespace) | {STATE_3X[namespace]}
    out = []
    try:
        entries = sorted(os.scandir(folder), key=lambda e: e.name)
    except OSError:
        return out
    for entry in entries:
        name = entry.name
        if name.startswith(".") or entry.is_symlink():
            continue
        if entry.is_file():
            if name not in fixed:
                out.append(name)
            continue
        if not entry.is_dir() or _skipped_in_object(name, namespace):
            continue
        child = f"{id_path}/{name}"
        if any(p == child or p.startswith(child + "/") for p in kept):
            continue
        out.append(name)
    return out


def files_of(path: Path) -> tuple[tuple[str, str], ...]:
    """What a move records of the entry at `path`: each file with its digest,
    the path within it empty for a file (`execute._files_of`'s form)."""
    if path.is_file():
        return (("", digest(path.read_bytes())),)
    found = []
    for dirpath, _, filenames in os.walk(path):
        for name in filenames:
            inner = Path(dirpath) / name
            found.append((inner.relative_to(path).as_posix(), digest(inner.read_bytes())))
    return tuple(sorted(found))


def move_of(root: Path, loose: Loose) -> Move:
    return Move(loose.old, loose.new, "B", files_of(Path(root) / loose.old), ("C13",))


class Mentions:
    """The rewrites and reports of every move of one run."""

    def __init__(self, moved: list[Loose], relocated: list[tuple[str, str]] = ()):
        self.moved = moved
        #: Every other entry a move takes elsewhere, `(old, new)` (C14).
        self.relocated = list(relocated)
        self._exact = [(re.compile(rf"(?<![{_NAME}./]){re.escape(m.old)}{_AFTER}"), m)
                       for m in moved]
        self._short = []
        for m in moved:
            folder = m.from_path.rsplit("/", 1)[-1]
            cuts = [re.escape(folder)] + [re.escape(folder[:i + 1]) + r"(?:…|\.\.\.)"
                                          for i, ch in enumerate(folder) if ch == "-"]
            pattern = rf"(?<![{_NAME}])(?:{'|'.join(cuts)})/{re.escape(m.entry)}{_AFTER}"
            self._short.append((re.compile(pattern), m))

    def final_path(self, rel: str) -> str:
        """Where the file at `rel` is after phase B."""
        for old, new in [(m.old, m.new) for m in self.moved] + self.relocated:
            if rel == old or rel.startswith(old + "/"):
                return new + rel[len(old):]
        return rel

    def rewrite(self, text: str) -> str:
        """Every exact mention made to name the new place."""
        for pattern, m in self._exact:
            text = pattern.sub(lambda _: m.new, text)
        return text

    def shortened(self, text: str, where: str) -> list[Report]:
        """A3, for each shortened mention left in `text` (already rewritten)."""
        out = []
        for number, line in enumerate(text.splitlines(), start=1):
            for pattern, m in self._short:
                for found in pattern.finditer(line):
                    out.append(Report("A3", f"{where}:{number}",
                                      f"names {found.group(0)}, which moved to {m.new}; "
                                      f"only the path in full is rewritten",
                                      predicts=(where, "mention")))
        return out


def relative_links(text: str, entries: list[str]) -> str:
    """A Markdown link from a file in the object's folder to an entry moved
    out of it, made to point into `resources/`."""
    for entry in entries:
        text = re.sub(rf"\]\(\s*(?:\./)?{re.escape(entry)}(?=[)/#\s])",
                      f"]({RESOURCES}/{entry}", text)
    return text


def docs_entry(value: str, entries: list[str]) -> str | None:
    """A `prependedDocs` or `appendedDocs` entry naming a moved entry, made
    to name it in `resources/`; None for any other."""
    stripped = value[2:] if value.startswith("./") else value
    if stripped.split("/", 1)[0] in entries:
        return f"{RESOURCES}/{stripped}"
    return None

