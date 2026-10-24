"""The stores' half of the plan (TCW-116 Design 4: C9 to C12; plan Step 6).

The objects of each store are the ones 3.x lists (`legacy.objects_3x`) and
the ones already in 4.0 form (`object_folders.walk`), read together so that
"is there an object here" is answered over both (Design 2.6). Each 3.x
state file becomes its 4.0 one in one write, its text edited in place: the
version first, a `cap-…` id removed (C10), `parent:` for an object inside
another's folder (C11), and `name:` for one with none (C12). Its 3.x file is
deleted after, once the 4.0 one holds what was written.

A folder named `resources` directly in an object's folder is that object's
`resources/` folder in 4.0, whatever 3.x read it as: nothing in it becomes an
object, and a file in it named like a state file is A2.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from tcw import __version__
from tcw.ids import FullId, id_part_problem, length_problem
from tcw.migrate.config import first_difference
from tcw.migrate.editors import convert_text
from tcw.migrate.legacy import STATE_3X, objects_3x, parse_mapping_3x, store_folder_3x
from tcw.migrate.loose import (TEXT_SUFFIXES, Loose, Mentions, docs_entry, loose_entries,
                               move_of, relative_links)
from tcw.migrate.model import ABSENT, Blocker, Delete, Report, Step, Write, digest, file_digest
from tcw.config import dotted
from tcw.reference_fields import Field
from tcw.object_folders import (DESCRIPTION, RESOURCES, STATE_FILES, _skipped_in_object,
                                is_reserved, walk)
from tcw.project_files import VERSION_KEY, without_version
from tcw.store.config_edit import (ConfigEditRefused, RemoveTop, SetTop, intended,
                                   read_text)

NAMESPACES = ("taxonomy", "capabilities", "work")
#: Names a file under `resources/` may not take without A2 (S111 Design 2.5).
_STATE_LIKE = {*STATE_FILES.values(), *STATE_3X.values()}
#: A capability's lists of attached documents, rewritten by C13 like a
#: reference field, by position in the text.
DOCS_FIELDS = (Field("capability", "prependedDocs", True, None),
               Field("capability", "appendedDocs", True, None))


@dataclass
class Store:
    """One of the active project's stores: its namespace and its folder,
    relative to the project's root."""

    namespace: str
    rel: str
    folder: Path


@dataclass
class StorePlan:
    steps: list[Step] = field(default_factory=list)
    reports: list[Report] = field(default_factory=list)
    blockers: list[Blocker] = field(default_factory=list)
    ids: dict[str, str] = field(default_factory=dict)       # cap-… -> id-path


def stores_of(root: Path, mapping: dict) -> list[Store]:
    """The project's three stores, where 3.x put them; one whose location
    part 1 cannot convert is left out (it is B5)."""
    out = []
    for namespace in NAMESPACES:
        found = store_folder_3x(root, namespace, mapping.get(namespace))
        if found.folder is None or found.form is not None:
            continue
        try:
            rel = found.folder.resolve().relative_to(Path(root).resolve()).as_posix()
        except ValueError:
            continue
        out.append(Store(namespace, rel, found.folder))
    return out


def fallback_name(id_path: str) -> str:
    """The name 3.x showed for an object with none (`tcw/store/fs.py:1716`,
    `:2316` at v3.0.2)."""
    return id_path.rsplit("/", 1)[-1].replace("-", " ").title()


# ---------------------------------------------------------------------------
# Which objects


def objects(store: Store, *, bare_terms: bool) -> tuple[list[str], set[str]]:
    """The id-paths to convert (3.x objects, in name order) and every
    object the store will hold, in either form. A path inside an object's
    `resources/` or fixed folder is no object. A taxonomy folder with no
    state file of either kind is a 3.x term only when `bare_terms`: in a
    project already in 4.0 form it is an organising folder."""
    ns = store.namespace
    four = set(walk(store.folder, ns).objects)
    three = [p for p in objects_3x(store.folder, ns)
             if (store.folder / p / STATE_3X[ns]).is_file()
             or (bare_terms and p not in four)]
    kept: set[str] = set()
    for id_path in sorted({*three, *four}, key=lambda p: (p.count("/"), p)):
        parts = id_path.split("/")
        inside = any("/".join(parts[:i]) in kept
                     and _skipped_in_object(parts[i], store.namespace)
                     for i in range(1, len(parts)))
        if not inside:
            kept.add(id_path)
    return [p for p in three if p in kept], kept


def name_blockers(store: Store, kept: set[str], project: str) -> list[Blocker]:
    """B8 over every object and every folder on the way to one."""
    out, seen = [], set()
    for id_path in sorted(kept):
        parts = id_path.split("/")
        for i in range(1, len(parts) + 1):
            prefix = "/".join(parts[:i])
            if prefix in seen:
                continue
            seen.add(prefix)
            part = parts[i - 1]
            where = f"{store.rel}/{prefix}"
            fix = "rename the folder by hand, then run 'tcw migrate' again"
            problem = id_part_problem(part)
            if problem:
                out.append(Blocker("B8", where, problem, fix))
            elif is_reserved(part, store.namespace):
                out.append(Blocker("B8", where, f"'{part}' is reserved in the "
                                                f"{store.namespace} store", fix))
        problem = length_problem(FullId(project, store.namespace, id_path))
        if problem:
            out.append(Blocker("B8", f"{store.rel}/{id_path}", problem,
                               "give the folder a shorter name by hand, then run "
                               "'tcw migrate' again"))
    return out


def nesting_blockers(stores: list[Store]) -> list[Blocker]:
    """B7: two of the project's stores in one folder, or one inside the
    other."""
    out = []
    for i, a in enumerate(stores):
        for b in stores[i + 1:]:
            pa, pb = a.folder.resolve(), b.folder.resolve()
            fix = "give each store a folder of its own, then run 'tcw migrate' again"
            if pa == pb:
                out.append(Blocker("B7", a.rel, f"the {a.namespace} and {b.namespace} "
                                                f"stores are one folder", fix))
            elif pb in pa.parents:
                out.append(Blocker("B7", a.rel, f"the {a.namespace} store is inside the "
                                                f"{b.namespace} store {b.rel}", fix))
            elif pa in pb.parents:
                out.append(Blocker("B7", b.rel, f"the {b.namespace} store is inside the "
                                                f"{a.namespace} store {a.rel}", fix))
    return out


# ---------------------------------------------------------------------------
# One object


def _with_docs(data: dict, entries: list[str]) -> dict:
    """`data` with each attached-document entry naming a moved entry made to
    name it in `resources/`, as `rewrite_yaml` will write it."""
    out = dict(data)
    for row in DOCS_FIELDS:
        value = out.get(row.name)
        if isinstance(value, list):
            out[row.name] = [docs_entry(v, entries) or v if isinstance(v, str) else v
                             for v in value]
        elif isinstance(value, str):
            out[row.name] = ",".join(
                piece.replace(piece.strip(), docs_entry(piece.strip(), entries))
                if docs_entry(piece.strip(), entries) else piece
                for piece in value.split(","))
    return out


def _plan_object(store: Store, id_path: str, kept: set[str], project: str,
                 out: StorePlan, mentions: Mentions, entries: list[str]) -> None:
    ns = store.namespace
    folder = store.folder / id_path
    old_rel = f"{store.rel}/{id_path}/{STATE_3X[ns]}"
    new_rel = f"{store.rel}/{id_path}/{STATE_FILES[ns]}"
    fix = "correct the file by hand, then run 'tcw migrate' again"
    try:
        text = read_text(folder / STATE_3X[ns])
        four_text = read_text(folder / STATE_FILES[ns])
    except (OSError, UnicodeDecodeError) as error:
        out.blockers.append(Blocker("B14", old_rel, f"cannot be read: {error}", fix))
        return
    source = mentions.rewrite(text) if text is not None else None
    data, problem = parse_mapping_3x(source, Path(old_rel)) if text is not None else ({}, None)
    if problem:
        out.blockers.append(Blocker("B14", old_rel, problem, fix))
        return
    data = data or {}
    name = id_path.rsplit("/", 1)[-1]
    edits, conversions = [], ["C9" if text is not None else "C11"]
    if source is not None:
        out.reports += mentions.shortened(source, new_rel)
    docs = _with_docs(data, entries) if ns == "capabilities" else data
    if source != text or docs != data:
        conversions.append("C13")
    own_id = data.get("id")
    if ns == "capabilities" and isinstance(own_id, str) and own_id.startswith("cap-"):
        edits.append(RemoveTop("id"))
        out.ids[own_id] = id_path
        conversions.append("C10")
    elif own_id is not None and own_id != name:
        out.reports.append(Report("A1", new_rel, f"id {own_id!r} is not its folder's name, "
                                                 f"{name!r}; an object's ID is its "
                                                 f"folder's name, so remove id or set it "
                                                 f"to {name!r}",
                                  predicts=(new_rel, "id")))
    if ns != "work":
        above = id_path.rpartition("/")[0]
        if above and above in kept and "parent" not in data:
            edits.append(SetTop("parent", str(FullId(project, ns, above)), after="name"))
            conversions.append("C11")
        if not data.get("name"):
            edits.append(SetTop("name", fallback_name(id_path)))
            conversions.append("C12")
            out.reports.append(Report("D7", new_rel, f"name: {fallback_name(id_path)} "
                                                     f"written, the name TCW 3 showed"))
    if text is None:
        out.reports.append(Report("D7", new_rel, "written where TCW 3 had no state file"))
    expect = {VERSION_KEY: __version__,
              **(_with_docs(intended(data, edits), entries) if ns == "capabilities"
                 else intended(data, edits))}
    if four_text is not None:
        _both(store, old_rel, new_rel, text, four_text, expect, out)
    else:
        try:
            new = convert_text(new_rel, source, edits, fields=DOCS_FIELDS,
                               replace=lambda row, value: docs_entry(value, entries),
                               expect=expect).text
        except ConfigEditRefused as refused:
            out.blockers.append(Blocker("B12" if "anchor" in str(refused) else "B3",
                                        old_rel, str(refused), "edit the file by hand"))
            return
        reads = ((old_rel, digest(text)),) if text is not None else ()
        out.steps.append(Write(new_rel, "C", ABSENT, new,
                               tuple(sorted(set(conversions), key=lambda c: int(c[1:]))),
                               reads))
        if text is not None:
            out.steps.append(Delete(old_rel, "C", digest(text), new_rel, digest(new), ("C9",)))
    if ns != "work" and not (folder / DESCRIPTION).exists():
        rel = f"{store.rel}/{id_path}/{DESCRIPTION}"
        out.steps.append(Write(rel, "C", ABSENT, "", ("C12",)))
        out.reports.append(Report("D7", rel, "written empty, where TCW 3 had none"))


def _both(store: Store, old_rel: str, new_rel: str, text: str | None, four_text: str,
          expect: dict, out: StorePlan) -> None:
    """Design 2.7's both-files rule, for a state file."""
    data4, problem = parse_mapping_3x(four_text, Path(new_rel))
    if problem:
        out.blockers.append(Blocker("B14", new_rel, problem,
                                    "correct the file by hand, then run 'tcw migrate' again"))
        return
    if without_version(data4 or {}) != without_version(expect):
        where = first_difference(without_version(expect), without_version(data4 or {}))
        out.blockers.append(Blocker(
            "B11", old_rel, f"differs from {new_rel} at {dotted(where or ())}",
            "make the two files agree, or delete the one that is wrong, then run "
            "'tcw migrate' again"))
        return
    if text is not None:
        out.steps.append(Delete(old_rel, "C", digest(text), new_rel, digest(four_text),
                                ("C9",)))


def _resources_reports(store: Store, kept: set[str]) -> list[Report]:
    """A2: a file under an object's `resources/` named like a state file."""
    out = []
    for id_path in sorted(kept):
        folder = store.folder / id_path / RESOURCES
        if not folder.is_dir():
            continue
        for path in sorted(folder.rglob("*")):
            name = path.name
            if path.is_file() and (name in _STATE_LIKE or
                                   (name.startswith("tcw-") and name.endswith(".yaml"))):
                rel = f"{store.rel}/{path.relative_to(store.folder).as_posix()}"
                out.append(Report("A2", rel, "is named like a state file, so removing "
                                             "its object with rm is refused; rename it "
                                             "if the object may be removed",
                                  predicts=(rel, "resources")))
    return out


def _text_writes(root: Path, planned, moved: list[Loose], mentions: Mentions,
                 covered: set[str], out: StorePlan) -> None:
    """C13's rewrites of every other Markdown and YAML file of the stores,
    each at the place it has after phase B, and A3 for what is left."""
    entries: dict[str, list[str]] = {}
    for m in moved:
        entries.setdefault(f"{m.store_rel}/{m.id_path}", []).append(m.entry)
    converted = {f"{store.rel}/{p}" for store, convert, _ in planned for p in convert}
    for store, _, _ in planned:
        for dirpath, dirnames, filenames in os.walk(store.folder):
            dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
            for name in sorted(filenames):
                if name.startswith(".") or not name.endswith(TEXT_SUFFIXES):
                    continue
                path = Path(dirpath) / name
                rel = f"{store.rel}/{path.relative_to(store.folder).as_posix()}"
                if rel in covered:
                    continue
                try:
                    text = read_text(path)
                except (OSError, UnicodeDecodeError):
                    continue
                new = mentions.rewrite(text)
                final = mentions.final_path(rel)
                folder = rel.rpartition("/")[0]
                if final == rel and folder in converted and name.endswith(".md"):
                    new = relative_links(new, entries.get(folder, []))
                out.reports += mentions.shortened(new, final)
                if new != text:
                    out.steps.append(Write(final, "C", digest(text), new, ("C13",)))


def plan_stores(root: Path, mapping: dict, project: str, *,
                three_x: bool = True) -> StorePlan:
    """Every store's state files and loose entries. `three_x`: the project's
    configuration is still in 3.x form, so a bare taxonomy folder is a 3.x
    term."""
    out = StorePlan()
    stores = stores_of(root, mapping)
    out.blockers += nesting_blockers(stores)
    planned, moved = [], []
    for store in stores:
        convert, kept = objects(store, bare_terms=three_x)
        out.blockers += name_blockers(store, kept, project)
        planned.append((store, convert, kept))
        for id_path in convert:
            for entry in loose_entries(store.folder / id_path, store.namespace, id_path, kept):
                # One already in `resources/` under that name is left where it
                # is: a rename would replace it.
                if not (store.folder / id_path / RESOURCES / entry).exists():
                    moved.append(Loose(store.rel, id_path, entry))
    mentions = Mentions(moved)
    out.steps += [move_of(root, m) for m in moved]
    covered = set()
    for store, convert, kept in planned:
        for id_path in convert:
            entries = [m.entry for m in moved
                       if m.store_rel == store.rel and m.id_path == id_path]
            _plan_object(store, id_path, kept, project, out, mentions, entries)
            covered.add(f"{store.rel}/{id_path}/{STATE_3X[store.namespace]}")
        out.reports += _resources_reports(store, kept)
    _text_writes(root, planned, moved, mentions, covered, out)
    return out
