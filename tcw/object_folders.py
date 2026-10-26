"""Object folders: how a folder of files marks and bounds a TCW object
(TCW-111 Design 1 and 2).

An **object** is a taxonomy entry, a capability or a work item. A folder in a
namespace's store is one exactly when it holds that namespace's **state
file** (`STATE_FILES`) as a file. An object's folder holds its fixed files
and folders (`fixed_files`, `fixed_folders`), the folders of its child
objects, and one `resources/` folder for anything else. A folder with no
state file directly in the store root, or in another such folder, is an
**organising folder**: it is not an object, but its name is part of the
id-path of every object below it.

This module is the one place that holds these names, the reserved names, and
the walk that finds a store's objects; every reader and writer of a store
takes them from here. It is the deployment layer of the TCW-99 design ("state
files marking which folders are objects"): a store that is not a folder of
files needs none of it.

It imports nothing from the store or work layers at load time, so both can
use it; the work stage names are read inside the one function that needs
them.
"""

from __future__ import annotations

import errno
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import yaml

from tcw.findings import Finding
from tcw.ids import FullId
from tcw.project_files import VERSION_KEY, version_line, version_problem, without_version

#: Each namespace's state file (Design 1.1).
STATE_FILES = {"taxonomy": "tcw-taxonomy.yaml",
               "capabilities": "tcw-capability.yaml",
               "work": "tcw-work-item.yaml"}
#: The TCW 3.x files they replace, recognised only to report them (row f) and
#: to refuse a removal that would delete one unseen (Design 2.5).
LEGACY_STATE_FILES = {"taxonomy": "meta.yaml", "capabilities": "meta.yaml",
                      "work": "item.yaml"}
RESOURCES = "resources"
DESCRIPTION = "description.md"
#: A work item's comments folder.
COMMENTS = "comments"


def fixed_files(namespace: str) -> frozenset[str]:
    """The files an object's folder holds besides its children and
    `resources/` (Design 2.1)."""
    if namespace == "work":
        from tcw.work.layout import CAPABILITIES_FILE
        return frozenset({STATE_FILES["work"], CAPABILITIES_FILE})
    return frozenset({STATE_FILES[namespace], DESCRIPTION})


def fixed_folders(namespace: str) -> frozenset[str]:
    """The folders an object's folder holds besides its children and
    `resources/`: for a work item, `comments/` and one folder per stage."""
    if namespace != "work":
        return frozenset()
    from tcw.work.model import STAGES
    return frozenset({COMMENTS, *(s.name for s in STAGES)})


def reserved_names(namespace: str) -> frozenset[str]:
    """The names no object or organising folder may take, in lower case;
    compared ignoring letter case (Design 2.4)."""
    return frozenset({RESOURCES, *fixed_folders(namespace)})


def is_reserved(name: str, namespace: str) -> bool:
    return name.casefold() in reserved_names(namespace)


def _skipped_in_object(name: str, namespace: str) -> bool:
    """A folder inside an object's folder that the walk does not enter: a
    fixed folder or `resources/`, each by its exact spelling."""
    return name == RESOURCES or name in fixed_folders(namespace)


# ---------------------------------------------------------------------------
# Exact spelling (TCW-110 Design 1.1)


def exact_child(parent: Path, name: str) -> "bool | str":
    """Whether `parent` holds an entry spelled exactly `name`: True when it
    does, the entry's own spelling when one differs from `name` only in
    letter case, and False when there is none. A disk that ignores case
    finds `Cli` for `cli`; reading the listing keeps an id-path
    case-sensitive there (TCW-110 Design 1.1)."""
    try:
        names = os.listdir(parent)
    except OSError:
        return False
    if name in names:
        return True
    folded = name.casefold()
    return next((entry for entry in names if entry.casefold() == folded), False)


def exact_path(root: Path, id_path: str) -> "bool | str":
    """`exact_child` for each part of `id_path` below `root`: True when every
    folder is spelled as given, the spelling on disk when some differ only in
    case, False when one is missing."""
    spelled, folder = [], Path(root)
    for part in id_path.split("/"):
        found = exact_child(folder, part)
        if found is False:
            return False
        name = part if found is True else found
        spelled.append(name)
        folder = folder / name
    on_disk = "/".join(spelled)
    return True if on_disk == id_path else on_disk


# ---------------------------------------------------------------------------
# The walk (Design 2.5)

#: How the walk classes a folder that is not an object.
ORGANISING = "organising"      # directly in the root or another organising folder
MISPLACED = "misplaced"        # no state file, inside an object's folder (row b)
RESERVED = "reserved"          # a reserved name outside its own place (row c)
LEGACY = "legacy"              # a 3.x state file and no state file (row f)
UNMADE = "unmade"              # work: named as an item, no state file (row h)
INSIDE = "inside"              # below a folder already reported, or an unmade one's own
#: How it classes a file.
LOOSE = "loose"                # directly in the root or an organising folder (row d)
ROOT_STATE = "root-state"      # a state file directly in the root (row g)
EXTRA = "extra"                # in an object's folder, not one of its fixed files (row a)


@dataclass(frozen=True)
class Walk:
    """What one walk of a store found. Every path is relative to the store
    root, its parts joined with `/`.

    - `objects`: the id-paths of the object folders, in name order;
    - `folders`: `(path, class, detail)` for every other folder visited: the
      3.x file's name for `LEGACY`, the object's id-path for `MISPLACED`;
    - `files`: `(path, class, owner)` for the files that are no object's own,
      `owner` the object's id-path for `EXTRA`;
    - `resources`: each object's `resources/` folder, which is not entered.
    """

    objects: tuple[str, ...]
    folders: tuple[tuple[str, str, str], ...]
    files: tuple[tuple[str, str, str], ...]
    resources: tuple[str, ...]


def _entries(folder: Path) -> list[os.DirEntry]:
    try:
        with os.scandir(folder) as found:
            return sorted((e for e in found if not e.name.startswith(".")),
                          key=lambda e: e.name)
    except OSError:
        return []


def _holds_file(folder: Path, name: str) -> bool:
    return (folder / name).is_file()


def walk(root: Path, namespace: str, *,
         item_named: Callable[[str], bool] | None = None) -> Walk:
    """Every object folder in the store at `root`, and how every other folder
    and file it met is placed. The only code in TCW that lists a store's
    folders to find objects (Design 2.5).

    From the root, in name order, skipping hidden names and never entering a
    folder reached through a symbolic link: a folder holding the state file
    is an object, and inside it its fixed folders and `resources/` are not
    entered; every other folder is, so a misplaced folder hides nothing.
    `item_named`, a work backend's rule for an item folder's name, marks a
    folder named as an item but holding no state file (row h); it changes no
    object.
    """
    state, legacy = STATE_FILES[namespace], LEGACY_STATE_FILES[namespace]
    fixed_f = fixed_files(namespace)
    objects: list[str] = []
    folders: list[tuple[str, str, str]] = []
    files: list[tuple[str, str, str]] = []
    resources: list[str] = []
    root = Path(root)

    def visit(folder: Path, rel: str, context: str, owner: str) -> None:
        # `context` is how the folder itself was classed: the root, an
        # organising folder, an object, an unmade or 3.x folder, or a folder
        # already reported (or inside one).
        for entry in _entries(folder):
            path = f"{rel}/{entry.name}" if rel else entry.name
            if entry.is_symlink():
                if entry.is_dir():
                    continue
            if not entry.is_dir():
                if not entry.is_file():
                    continue
                if context in ("root", ORGANISING):
                    kind = ROOT_STATE if (context == "root" and entry.name == state) \
                        else LOOSE
                    files.append((path, kind, ""))
                elif context == "object" and entry.name not in fixed_f:
                    files.append((path, EXTRA, owner))
                continue
            child = folder / entry.name
            if context == "object" and _skipped_in_object(entry.name, namespace):
                if entry.name == RESOURCES:
                    resources.append(path)
                continue
            if _holds_file(child, state):
                objects.append(path)
                if is_reserved(entry.name, namespace):
                    folders.append((path, RESERVED, ""))
                visit(child, path, "object", path)
                continue
            if _holds_file(child, legacy):
                folders.append((path, LEGACY, legacy))
                visit(child, path, LEGACY, "")
                continue
            if item_named is not None and item_named(entry.name):
                folders.append((path, UNMADE, ""))
                visit(child, path, UNMADE, "")
                continue
            if context in (INSIDE, LEGACY, UNMADE):
                # A 3.x or unmade folder is not an object, so the walk enters
                # all its folders, as `is_object` reads it; they are its own,
                # or below a folder already reported, and are not reported.
                visit(child, path, INSIDE, "")
                continue
            if is_reserved(entry.name, namespace):
                folders.append((path, RESERVED, ""))
                visit(child, path, INSIDE, "")
                continue
            if context == "object":
                folders.append((path, MISPLACED, owner))
                visit(child, path, INSIDE, "")
                continue
            folders.append((path, ORGANISING, ""))
            visit(child, path, ORGANISING, "")

    if root.is_dir():
        visit(root, "", "root", "")
    return Walk(tuple(objects), tuple(folders), tuple(files), tuple(resources))


def object_paths(root: Path, namespace: str) -> list[str]:
    """The id-paths of every object in the store at `root`, in name order."""
    return list(walk(root, namespace).objects)


def id_path_refused(id_path: str) -> bool:
    """Whether `id_path` is refused before the disk is read: empty, starting
    or ending with `/`, or with an empty, `.`, `..` or hidden part."""
    if not isinstance(id_path, str) or not id_path:
        return True
    return any(part in ("", ".", "..") or part.startswith(".") or "\\" in part
               or "\x00" in part for part in id_path.split("/"))


def is_object(root: Path, namespace: str, id_path: str) -> bool:
    """Whether `id_path` is an object of the store at `root`, by the walk's
    rule but without listing the store (Design 2.5, last paragraph): each
    part spelled exactly as given; no folder on the way down a symbolic link,
    or a fixed folder or `resources/` of an object above it; and the last
    folder holding the state file as a file. So it agrees with `walk`."""
    if id_path_refused(id_path):
        return False
    state = STATE_FILES[namespace]
    folder = Path(root)
    above_is_object = False                 # the store root is never an object
    for part in id_path.split("/"):
        if above_is_object and _skipped_in_object(part, namespace):
            return False
        if exact_child(folder, part) is not True:
            return False
        folder = folder / part
        if folder.is_symlink() or not folder.is_dir():
            return False
        above_is_object = _holds_file(folder, state)
    return above_is_object


def objects_below(root: Path, namespace: str, id_path: str) -> list[str]:
    """The id-paths of the objects nested anywhere below `id_path`, from one
    walk: what a rename of a work item refuses on (Design 5, row 7)."""
    prefix = id_path + "/"
    return [p for p in walk(root, namespace).objects if p.startswith(prefix)]


def folder_parent(root: Path, namespace: str, id_path: str) -> str | None:
    """The id-path of the object whose folder directly holds `id_path`'s
    folder, or None: when it sits in the store root, or in any folder that
    holds no state file (Design 3.2)."""
    above = id_path.rpartition("/")[0]
    return above if above and is_object(root, namespace, above) else None


def removal_blockers(folder: Path, store_root: Path) -> list[tuple[str, str]]:
    """What a removal of `folder` must refuse on (Design 2.5): every file
    below it, not in `folder` itself, named as any namespace's state file or
    a 3.x one, wherever it is, hidden folders, fixed folders and
    `resources/` included. Each as `(its folder relative to the store root,
    "state" or the 3.x file's name)`, sorted. This lists nothing: it searches
    everything the removal would delete."""
    names = {*STATE_FILES.values()}
    legacy = {*LEGACY_STATE_FILES.values()}
    found: set[tuple[str, str]] = set()
    for path in folder.rglob("*"):
        if path.parent == folder or path.name not in names | legacy:
            continue
        if not path.is_file():
            continue
        where = path.parent.relative_to(store_root).as_posix()
        found.add((where, "state" if path.name in names else path.name))
    return sorted(found)


# ---------------------------------------------------------------------------
# What `tcw validate` reports about a store's shape (Design 2.6, rows a-h)


def shape_problems(found: Walk, root: Path, namespace: str, project: str, *,
                   where: Callable[[Path], str] = str,
                   skip: Iterable[Path] = (),
                   unmade_message: str | None = None) -> list[Finding]:
    """Rows a to h of Design 2.6 for one walk, each folder reported once: a
    3.x folder (f) before an unmade one (h), before a misplaced (b) or
    reserved (c) one. `skip` holds files another check already reports, which
    row d leaves out. `unmade_message` is row h's message, at the folder's
    state file; a backend that names no rule for items gives none."""
    state = STATE_FILES[namespace]
    skipped = {Path(p) for p in skip}
    root = Path(root)
    problems: list[Finding] = []

    def full(id_path: str) -> FullId:
        return FullId(project, namespace, id_path)

    for path, kind, owner in found.files:
        at = root / path
        if kind == EXTRA:
            problems.append(Finding("error", where(at),
                                    f"is not one of {full(owner)}'s files; move it "
                                    f"into {RESOURCES}/"))
        elif kind == ROOT_STATE:
            problems.append(Finding("error", where(at),
                                    "the store's root is not an object; move this "
                                    "file into an object's folder"))
        elif at not in skipped:
            problems.append(Finding("warning", where(at), "is not part of any object"))
    below = [*found.objects,
             *(path for path, kind, _ in found.folders if kind in (LEGACY, UNMADE))]
    for path, kind, detail in found.folders:
        at = root / path
        name = path.rpartition("/")[2]
        if kind == LEGACY:
            problems.append(Finding("error", where(at),
                                    f"holds a TCW 3.x {detail}; run 'tcw migrate' in "
                                    f"this project"))
        elif kind == UNMADE:
            if unmade_message is not None:
                problems.append(Finding("error", where(at / state), unmade_message))
        elif kind == MISPLACED:
            problems.append(Finding("error", where(at),
                                    f"is not a child object of {full(detail)}: it has "
                                    f"no {state}; give it one, or move it into "
                                    f"{RESOURCES}/"))
        elif kind == RESERVED:
            message = f"'{name}' is reserved in the {namespace} store"
            if namespace == "work":
                # A 2.x work store is the one layout that holds stage folders,
                # and `tcw migrate` does not convert 2.x: point to its guide.
                from tcw.store.base import MIGRATION_GUIDE
                message += f"; see {MIGRATION_GUIDE} for the work store layout"
            problems.append(Finding("error", where(at), message))
        elif kind == ORGANISING:
            prefix = path + "/"
            if not any(p.startswith(prefix) for p in below):
                problems.append(Finding("warning", where(at), "holds no TCW object"))
    return problems


def length_problems(id_paths: Iterable[str], root: Path, namespace: str, project: str,
                    *, where: Callable[[Path], str] = str) -> list[Finding]:
    """Row n of Design 2.6: each object of `id_paths` whose full identifier is
    longer than `ID_LIMIT`, as an error at its state file. The limit is kept by
    what makes objects; one placed by hand beyond it is still listed and read,
    and reported here (TCW-111 Design 4.2)."""
    from tcw.ids import length_problem
    state = STATE_FILES[namespace]
    found = []
    for id_path in id_paths:
        problem = length_problem(FullId(project, namespace, id_path))
        if problem:
            found.append(Finding("error", where(Path(root) / id_path / state), problem))
    return found


def under_resources(found: Walk, root: Path, path: Path) -> bool:
    """Whether `path` lies in one of the walk's `resources/` folders."""
    for folder in found.resources:
        try:
            Path(path).relative_to(Path(root) / folder)
        except ValueError:
            continue
        return True
    return False


# ---------------------------------------------------------------------------
# Reading and writing a state file (Design 1.2-1.5)

_VERSION_LINE = re.compile(rf"^{re.escape(VERSION_KEY)}\s*:")


def read_state(path: Path, load: Callable[[Path], object] | None = None
               ) -> tuple[dict | None, str | None]:
    """A state file's mapping without `tcw-version` and None, or None and
    `version_problem`'s message (TCW-106 Design 3.4). An absent file reads
    as `({}, None)`. `load` reads the file (`yaml.safe_load` of its text by
    default); what it raises is the caller's."""
    path = Path(path)
    if not path.is_file():
        return {}, None
    if load is not None:
        return _versioned(load(path))
    return parse_state_text(path.read_text(encoding="utf-8"), path)


def parse_state_text(text: str, file: Path) -> tuple[dict | None, str | None]:
    """`read_state` of a state file whose text is `text`, read from no disk
    (TCW-116 B3; plan Decided 8). What `yaml.safe_load` raises is the
    caller's, as for `read_state`."""
    return _versioned(yaml.safe_load(text))


def _versioned(data) -> tuple[dict | None, str | None]:
    problem = version_problem(data, state=True)
    if problem is not None:
        return None, problem
    return without_version(data), None


def existing_version_line(path: Path) -> str | None:
    """The `tcw-version` line of the file at `path`, exactly as written and
    wherever it stands, or None."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    for line in text.splitlines():
        if _VERSION_LINE.match(line):
            return line + "\n"
    return None


def state_text(path: Path, mapping: dict) -> str:
    """What a writer writes to the state file at `path`: its existing
    `tcw-version` line exactly as written, or `version_line()` for a new
    file (Design 1.4), then `mapping` without `tcw-version`."""
    first = existing_version_line(path) or version_line()
    body = without_version(mapping)
    return first + (yaml.safe_dump(body, sort_keys=False, allow_unicode=True)
                    if body else "")


def id_problem(mapping: dict, id_path: str) -> str | None:
    """Row k (Design 1.3): an `id` in a state file must be its folder's name
    exactly; the folder's name is what every command reads the object by."""
    if not isinstance(mapping, dict) or "id" not in mapping:
        return None
    name = id_path.rpartition("/")[2]
    if mapping["id"] == name:
        return None
    return (f"id {mapping['id']!r} is not its folder's name, {name!r}; an object's "
            f"ID is its folder's name, so remove id or set it to {name!r}")


# ---------------------------------------------------------------------------
# Where the folder and `parent` disagree (Design 3.2)


def disagreement(child: FullId, folder_parent: FullId | None,
                 parent: FullId | str | None) -> str | None:
    """Design 3.2's warning when `child` sits in the folder of
    `folder_parent` but its `parent` names another object or none; None when
    it has no folder parent or the two agree."""
    if folder_parent is None:
        return None
    if parent is not None and str(parent) == str(folder_parent):
        return None
    named = str(parent) if parent is not None else "not set"
    return (f"{child} sits in the folder of {folder_parent}, but its parent is "
            f"{named}; parent: decides (set it to {folder_parent}, or move the folder)")


# ---------------------------------------------------------------------------
# Moving an object's folder (TCW-114 Design 5.3, 5.8 step 2.4)


def move_object_folder(store_root: Path, old_path: str, new_path: str) -> list[str]:
    """Move the object folder at `old_path` to `new_path`, both relative to
    `store_root`: each missing folder above `new_path` is made, in order,
    then one `os.rename` carries the folder and everything in it. Returns
    the folders made. When any of it fails, each folder this call made that
    is still empty is removed, deepest first, before the error is raised;
    a source that is no longer there is `NotFound`."""
    from tcw.errors import NotFound
    root = Path(store_root)
    created: list[str] = []
    try:
        parts = new_path.split("/")[:-1]
        for depth in range(1, len(parts) + 1):
            rel = "/".join(parts[:depth])
            if not (root / rel).is_dir():
                os.mkdir(root / rel)
                created.append(rel)
        try:
            os.rename(root / old_path, root / new_path)
        except FileNotFoundError:
            if not (root / old_path).exists():
                raise NotFound(f"{root / old_path} is no longer there") from None
            raise
    except BaseException:
        for rel in reversed(created):
            try:
                os.rmdir(root / rel)
            except OSError:
                pass
        raise
    return created


def remove_emptied(store_root: Path, old_path: str) -> list[str]:
    """Remove each folder above `old_path` that a move left completely
    empty, from the deepest up to the store root or the first that still
    holds anything, hidden files included (Design 5.3). Returns them."""
    root = Path(store_root)
    removed: list[str] = []
    parts = old_path.split("/")[:-1]
    for depth in range(len(parts), 0, -1):
        rel = "/".join(parts[:depth])
        # `rmdir` removes only an empty folder, so nothing is listed.
        try:
            os.rmdir(root / rel)
        except OSError as error:
            if error.errno in (errno.ENOTEMPTY, errno.EEXIST):
                break
            raise
        removed.append(rel)
    return removed
