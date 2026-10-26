"""Moving and renaming an object, in every namespace (TCW-114 Design 5).

`move_object` is the one implementation behind `tcw work rename`, `tcw work
move`, and the taxonomy's and capabilities' `rename` and `move`. It runs in
one order everywhere (Design 5.8):

1. the checks of Design 5.4, writing nothing;
2. the work backend's or tree store's `move`, which writes what it owns,
   calls back `before_folder` (the repository's references, `tcw.rewrite`)
   and moves the folder last;
3. the tidy step: empty folders removed, mentions listed, and the changed
   identifiers printed.

A stop in step 2 leaves the object at its old place, and its message names
what was written so far, where the folder is, and what to do next. Nothing
written is ever set back: running the same command again finishes it.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

from tcw import exit as codes
from tcw.errors import BackendError, NotFound, Refused, TcwError, UsageError
from tcw.ids import ID_PART, FullId, IdError, length_problem
from tcw.object_folders import (exact_child, fixed_folders, is_object, is_reserved,
                                objects_below, remove_emptied, walk, RESOURCES)
from tcw.output import print_json, shown
from tcw.rewrite import (RewriteStopped, field_problems, mentions, rewrite_references,
                         unreadable_records)

#: The closing line of every move (Design 5.6).
OTHER_PROJECTS = ("references in other projects are not rewritten; tcw validate there "
                  "reports them: pass on the identifiers above")

def clash_advice() -> str:
    """Design 5.8's advice when a ticket was found set by another command.
    It names a git step, because the other command's folder move reaches
    this clone only through one, so `test_static_guards` exempts it."""
    return ("wait for the other command to finish (if it ran in another clone, pull "
            "its commit into this one); then run tcw validate --remote, and in Jira "
            "set each ticket it reports to the identifier its folder now has. To "
            "keep this command's result instead, run this command again naming the "
            "item at its new place")


@dataclass
class Target:
    """The object being moved, as the checks found it."""

    full_id: FullId
    store_root: Path           # its store's folder
    root: Path                 # the active project's root
    move: Callable             # the backend's or store's move(old, new, before_folder)
    reporter: object = None    # what has a `report` to collect, when it has one
    jira: bool = False
    store: object = None       # a tree store, for check g


def _stderr(line: str) -> None:
    print(line, file=sys.stderr)


# ---------------------------------------------------------------------------
# Finding the object (check a)


def _work_target(source: str) -> Target:
    from tcw.work.cli import project_root, resolve_item
    from tcw.work.open import open_backend
    try:
        slug, backend, root = resolve_item(source, writing=True)
    except (IdError, UsageError, NotFound):
        # Design 5.5: a folder whose name breaks the grammar is the object
        # when the walk lists exactly that folder.
        root = project_root()
        backend = open_backend(root)
        work_path = getattr(backend, "work_path", None)
        if work_path is None or source not in walk(work_path, "work").objects:
            raise
        from tcw.work.model import Slug
        slug = Slug(backend.project, source)
    return Target(FullId(slug.project, "work", slug.folder), Path(backend.work_path),
                  root, backend.move, backend, jira=hasattr(backend, "jira"))


def _tree_target(namespace: str, source: str) -> Target:
    from tcw.locate import find_tree_writable
    from tcw.store.fs import (FsCapabilitiesStore, FsTaxonomyStore, find_component_project,
                              no_store_here)
    root = find_component_project(namespace)
    if root is None:
        raise no_store_here(namespace)
    cls = FsTaxonomyStore if namespace == "taxonomy" else FsCapabilitiesStore
    store = cls.open(root)
    try:
        full_id = find_tree_writable(store, source, removing=True)
    except (IdError, UsageError, NotFound, ValueError):
        # Design 5.5: a folder whose name breaks the grammar is the object
        # when the walk lists exactly that folder.
        if source not in walk(store.root, namespace).objects:
            raise
        full_id = FullId(store.project_id, namespace, source)
    return Target(full_id, Path(store.root), Path(root), store.move, None, store=store)


# ---------------------------------------------------------------------------
# The new place (check b)


def _renamed(target: Target, namespace: str, words: str) -> str:
    """The id-path a rename gives: the same folder, a new last part."""
    under, _, last = target.full_id.id_path.rpartition("/")
    if namespace == "work":
        new_last = _item_name(last, words)
    else:
        if not isinstance(words, str) or not ID_PART.fullmatch(words):
            raise UsageError(f"{words!r} is not a name: one part, of letters, digits, "
                             f"'-' and '_', starting with a letter or digit")
        if is_reserved(words, namespace):
            raise UsageError(f"{words!r} is a reserved name in the {namespace} store")
        new_last = words
    return f"{under}/{new_last}" if under else new_last


def _item_name(last: str, words: str) -> str:
    """`<date or key>-<words>`, the date or key kept (Design 5.1)."""
    from tcw.work.fs_backend import WORDS
    from tcw.work.model import item_prefix, title_words
    prefix = item_prefix(last)
    if prefix is None:
        raise UsageError(f"{last} starts with no date or ticket key, so it cannot be "
                         f"renamed by words")
    kind = "key" if prefix[0].isalpha() else "date"
    given = item_prefix(words)
    if given is not None:
        if given != prefix:
            raise UsageError(f"a rename keeps the {kind} {prefix}; give the words "
                             f"alone, or {prefix}-<words>")
        words = words[len(prefix) + 1:]
    if not isinstance(words, str) or not WORDS.match(words):
        raise UsageError(f"{words!r} is not a folder name; did you mean "
                         f"{title_words(str(words))}?")
    return f"{prefix}-{words}"


def _moved_to(target: Target, namespace: str, into: str | None, top: bool) -> str:
    """The id-path a move gives: `<into>/<last part>`, or the last part at
    the top (Design 5.3). Every rule is checked here, before any write."""
    from tcw.ownership import check_owned
    old = target.full_id.id_path
    last = old.rpartition("/")[2]
    if top == (into is not None):
        raise UsageError("give exactly one of --into and --top")
    if top:
        return last
    destination = into
    if isinstance(into, str) and "." in into.partition("/")[0]:
        try:
            named = FullId(*_split_full(into))
        except ValueError:
            raise UsageError(f"{into!r} is not an id-path or a full identifier") from None
        check_owned(named, target.root)
        if named.namespace != namespace:
            raise UsageError(f"{into} is not in the {namespace} store")
        destination = named.id_path
    parts = destination.strip("/").split("/") if isinstance(destination, str) else []
    if not parts or any(not p for p in parts):
        raise UsageError(f"{into!r} is not an id-path")
    for part in parts:
        if not ID_PART.fullmatch(part):
            raise UsageError(f"{part!r} in {into} breaks the rule for a name: letters, "
                             f"digits, '-' and '_', starting with a letter or digit")
    joined = "/".join(parts)
    if joined == old or joined.startswith(old + "/"):
        raise UsageError(f"{into} is the object itself or lies below it")
    # Walk down: inside an object only a nested object may hold it, never a
    # fixed folder or resources/; a missing part must be an organising
    # folder, so it may not lie inside an object's folder.
    folder = target.store_root
    in_object = False
    for depth, part in enumerate(parts, start=1):
        rel = "/".join(parts[:depth])
        if in_object and (part in fixed_folders(namespace) or part == RESOURCES):
            raise UsageError(f"{into} lies inside an object's {part}/ folder")
        if is_reserved(part, namespace):
            raise UsageError(f"{part!r} in {into} is a reserved name")
        exists = (folder / part).is_dir() and exact_child(folder, part) is True
        if not exists and in_object:
            raise UsageError(f"{into}: {rel} would be a folder inside an object's "
                             f"folder that is not an object")
        folder = folder / part
        in_object = exists and is_object(target.store_root, namespace, rel)
    return f"{joined}/{last}"


def _split_full(text: str) -> tuple[str, str, str]:
    from tcw.ids import parse_full_id
    try:
        found = parse_full_id(text)
    except IdError as error:
        raise ValueError(str(error)) from None
    return found.project, found.namespace, found.id_path


# ---------------------------------------------------------------------------
# The checks, then the move


def _pairs(target: Target, namespace: str, new_path: str) -> list[tuple[FullId, FullId]]:
    old = target.full_id.id_path
    nested = objects_below(target.store_root, namespace, old)
    return [(target.full_id.with_id_path(p), target.full_id.with_id_path(new_path + p[len(old):]))
            for p in [old, *nested]]


def _check_free(target: Target, new_path: str) -> None:
    """Check c: no entry of the destination folder has the new name, letter
    case ignored; and the identifier changes."""
    if new_path == target.full_id.id_path:
        raise Refused(f"{target.full_id} already has that name")
    under, _, last = new_path.rpartition("/")
    folder = target.store_root / under if under else target.store_root
    if exact_child(folder, last) is not False:
        raise Refused(f"{shown(folder / last)} already exists")


def _check_lengths(pairs) -> None:
    """Check d: every changed identifier fits, nested ones included."""
    long = [new for _, new in pairs if length_problem(new) is not None]
    if long:
        raise UsageError(length_problem(max(long, key=lambda n: len(str(n)))))


def _check_records(target: Target, pairs) -> None:
    """Checks e and f."""
    unreadable = unreadable_records(target.root)
    if unreadable:
        raise BackendError("not moving, because a record that could name it cannot "
                           "be read: " + "; ".join(unreadable))
    problems = field_problems(target.root, pairs)
    if problems:
        raise Refused("; ".join(problems))


def _check_inherited(target: Target, namespace: str, pairs) -> None:
    """Check g, for terms and capabilities: not an override, and no new
    path an inherited object's (Design 5.4 g)."""
    if namespace == "work":
        return
    store = target.store
    for old, new in pairs[:1]:
        found = store.inherited_at(old.id_path)
        if found is not None:
            raise Refused(f"{old} overrides {found}, which is inherited; an override "
                          f"is not moved")
    for _, new in pairs:
        found = store.inherited_at(new.id_path)
        if found is not None:
            raise Refused(f"{new} is the path of {found}, which is inherited; moving "
                          f"there would make an override")


@contextmanager
def _collected(target: Target) -> Iterator[list[str]]:
    """Every line the backend reports while the move runs, printed and kept
    for a stop message."""
    lines: list[str] = []

    def collect(line: str) -> None:
        lines.append(line)
        _stderr(line)
    holder = target.reporter
    before = getattr(holder, "report", None)
    if holder is not None and before is not None:
        holder.report = collect
    try:
        yield lines
    finally:
        if holder is not None and before is not None:
            holder.report = before


def _stopped(error: BaseException, lines: list[str], target: Target,
             command: str) -> TcwError:
    """Design 5.8's message for a stop in step 2, raised as the class that
    stopped the run, so its exit code is kept."""
    if isinstance(error, TcwError):
        cls, message = type(error), str(error)
    elif isinstance(error, RewriteStopped):
        cls, message = BackendError, f"could not write {shown(error.path)}: {error.strerror}"
    else:
        cls, message = BackendError, str(error)
    old_folder = target.store_root / target.full_id.id_path
    parts = [message]
    if lines:
        parts.append("written so far, by this run or an earlier one: " + "; ".join(lines))
    pending = getattr(error, "pending", None)
    if pending:
        parts.append(f"still to be set: {', '.join(pending)}")
    if old_folder.is_dir():
        parts.append(f"the folder is still at {shown(old_folder)}")
        if getattr(error, "clash", False):
            parts.append(clash_advice())
        else:
            parts.append(f"run the same command again to finish the move: {command}")
    else:
        cls = NotFound
        parts.append(f"the folder is no longer at {shown(old_folder)}; another command "
                     f"may have moved it")
        parts.append(f"run tcw validate{' --remote' if target.jira else ''} to see what "
                     f"names it")
    try:
        stopped = cls("; ".join(parts))
    except TypeError:
        stopped = BackendError("; ".join(parts))
    stopped.name = getattr(error, "name", None)
    return stopped


def move_object(namespace: str, source: str, *, command: str,
                new_name: str | None = None, into: str | None = None,
                top: bool = False, as_json: bool = False) -> int:
    """Rename (`new_name`) or move (`into` or `top`) one object and every
    object nested in its folder (Design 5)."""
    # a. Found, and the active project's own.
    target = _work_target(source) if namespace == "work" else _tree_target(namespace, source)
    # b. The new name or place.
    if new_name is not None:
        new_path = _renamed(target, namespace, new_name)
    else:
        new_path = _moved_to(target, namespace, into, top)
    # c to g.
    _check_free(target, new_path)
    pairs = _pairs(target, namespace, new_path)
    _check_lengths(pairs)
    _check_records(target, pairs)
    _check_inherited(target, namespace, pairs)

    # 2. The backend's or store's move, which calls back the rewrite.
    old_path = target.full_id.id_path

    with _collected(target) as lines:
        def before_folder() -> None:
            try:
                results = rewrite_references(target.root, pairs)
            except RewriteStopped as stop:
                for result in stop.results:
                    lines.append(f"rewrote {shown(result.path)}: "
                                 f"{', '.join(result.changed)}")
                raise
            for result in results:
                if result.changed:
                    line = f"rewrote {shown(result.path)}: {', '.join(result.changed)}"
                    lines.append(line)
                    _stderr(line)
                if result.done:
                    lines.append(f"{shown(result.path)} already names the new "
                                 f"identifiers: {', '.join(result.done)}")
            if namespace != "work":
                _own_id(target, namespace, old_path, new_path, lines)

        try:
            if target.reporter is None:
                moved = target.move(old_path, new_path, before_folder, report=_reporter(lines))
            else:
                moved = target.move(old_path, new_path, before_folder)
        except (TcwError, OSError) as error:
            raise _stopped(error, lines, target, command) from None

    # 3. Tidy and report; a failure here does not undo the move.
    try:
        for rel in remove_emptied(target.store_root, old_path):
            _stderr(f"removed the empty folder {shown(target.store_root / rel)}/")
    except OSError as error:
        _stderr(f"warning: the move is done, but an empty folder it left could not be "
                f"removed: {error}")
    try:
        for line in mentions(target.root, moved):
            _stderr(line)
    except OSError as error:
        _stderr(f"warning: the move is done, but its mentions could not be listed: "
                f"{error}")
    if new_name is None:
        warning = _folder_warning(target, namespace, moved[0][1])
        if warning:
            _stderr(f"warning: {warning}")
    _stderr(OTHER_PROJECTS)
    if as_json:
        print_json(None, {"moved": [{"from": str(a), "to": str(b)} for a, b in moved]})
    else:
        for old, new in moved:
            print(f"{old} -> {new}")
    return codes.OK


def _reporter(lines: list[str]) -> Callable[[str], None]:
    def collect(line: str) -> None:
        lines.append(line)
        _stderr(line)
    return collect


def _own_id(target: Target, namespace: str, old_path: str, new_path: str,
            lines: list[str]) -> None:
    """A renamed term's or capability's own `id`, when it holds the old
    last part (Design 5.2): written with the repository's references."""
    from tcw.object_folders import STATE_FILES
    from tcw.rewrite import rewrite_own_id
    from tcw.store.fs import _atomic_write_all
    old_last, new_last = old_path.rpartition("/")[2], new_path.rpartition("/")[2]
    if old_last == new_last:
        return
    path = target.store_root / old_path / STATE_FILES[namespace]
    text = path.read_text(encoding="utf-8")
    new_text, own = rewrite_own_id(text, old_last, new_last)
    if own == "changed":
        _atomic_write_all([(path, new_text)])
        line = f"wrote {shown(path)}: id {old_last} -> {new_last}"
        lines.append(line)
        _stderr(line)


def _folder_warning(target: Target, namespace: str, new: FullId) -> str | None:
    """TCW-111 Design 3.2's warning, when the moved object's folder now sits
    in another object's folder that its `parent` does not name."""
    from tcw.object_folders import disagreement, folder_parent
    above = folder_parent(target.store_root, namespace, new.id_path)
    parent = None
    try:
        if namespace == "work":
            parent = target.reporter.read(new.id_path).parent
        else:
            from tcw.object_folders import read_state, STATE_FILES
            data, _ = read_state(target.store_root / new.id_path / STATE_FILES[namespace])
            value = (data or {}).get("parent")
            if isinstance(value, str):
                from tcw.ids import parse_full_id
                parent = parse_full_id(value, namespace)
    except (TcwError, OSError, IdError, ValueError):
        return None
    return disagreement(new, None if above is None else new.with_id_path(above), parent)


# ---------------------------------------------------------------------------
# The tree commands (Design 5.1)


def add_tree_commands(group, command, namespace: str, noun: str,
                      rename_example: str, move_example: str) -> None:
    """`rename` and `move` for the taxonomy or capabilities group, with the
    same shape as `tcw work rename` and `tcw work move`."""
    import shlex

    def given(args, *words: str) -> str:
        chdir = "".join(f" -C {shlex.quote(c)}" for c in getattr(args, "chdir", None) or [])
        return f"tcw{chdir} " + " ".join(shlex.quote(w) for w in words)

    def rename(args) -> int:
        return move_object(namespace, args.path, new_name=args.name, as_json=args.json,
                           command=given(args, namespace, "rename", args.path, args.name))

    def move(args) -> int:
        where = ["--top"] if args.top else ["--into", args.into]
        return move_object(namespace, args.path, into=args.into, top=args.top,
                           as_json=args.json,
                           command=given(args, namespace, "move", args.path, *where))

    prints = ("one `<old full id> -> <new full id>` line per identifier it changed, "
              f"the {noun} first")
    writes = (f"the {noun}'s folder, and every reference to it in this project's "
              f"records and documents")
    p = command(group, "rename", help=f"rename a local {noun}'s last part; those nested "
                                      f"in it move with it",
                prints=prints, writes=writes, examples=[rename_example])
    p.add_argument("path", help=f"the local {noun}: its full identifier or its path")
    p.add_argument("name", help="the new last part of its path")
    p.add_argument("--json", action="store_true", help="print the changed identifiers "
                                                       "as JSON")
    p.set_defaults(func=rename)
    p = command(group, "move", help=f"move a local {noun}'s folder into another folder, "
                                    f"or to the top; those nested in it move with it",
                prints=prints, writes=writes, examples=[move_example])
    p.add_argument("path", help=f"the local {noun}: its full identifier or its path")
    place = p.add_mutually_exclusive_group(required=True)
    place.add_argument("--into", metavar="<id-path>",
                       help=f"a {noun}, or an organising folder (made when missing), to "
                            f"put its folder in")
    place.add_argument("--top", action="store_true",
                       help="put its folder at the top of the store")
    p.add_argument("--json", action="store_true", help="print the changed identifiers "
                                                       "as JSON")
    p.set_defaults(func=move)
