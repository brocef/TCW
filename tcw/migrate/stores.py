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
from tcw.migrate.references import (CAPABILITIES_YAML, Owners, applied, state_fields)
from tcw.migrate.loose import (TEXT_SUFFIXES, Loose, Mentions, docs_entry, files_of,
                               loose_entries, move_of, relative_links)
from tcw.migrate.model import (ABSENT, Blocker, Delete, Move, Report, Step, Write, digest,
                               file_digest)
from tcw.migrate.overrides import d2_reports, entry_moves, plan_overrides, reports_of
from tcw.config import dotted
from tcw.reference_fields import Field
from tcw.object_folders import (DESCRIPTION, RESOURCES, STATE_FILES, _skipped_in_object,
                                is_reserved, walk)
from tcw.project_files import VERSION_KEY, without_version
import yaml

from tcw.rewrite import rewrite_yaml
from tcw.store.config_edit import (ConfigEditRefused, RemoveTop, SetTop, intended,
                                   read_text)
from tcw.work.layout import CAPABILITIES_FILE

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
    owners: dict[str, str] = field(default_factory=dict)    # Design 2.7
    moved: dict[str, str] = field(default_factory=dict)     # C14: id-path -> id-path


def stores_of(root: Path, mapping: dict) -> list[Store]:
    """The project's three stores, where 3.x put them, wherever that is
    (Design 1.4): inside the project, in another project's folder, or in
    3.x's clone of a store's repository. `rel` is the folder relative to the
    project's root, `..` parts included; a store whose folder 3.x could not
    say, or that is not on this machine, is left out."""
    import os
    from tcw.migrate.legacy import cache_folder_3x, parse_repository_3x
    out = []
    base = Path(os.path.realpath(root))
    for namespace in NAMESPACES:
        section = mapping.get(namespace)
        found = store_folder_3x(root, namespace, section)
        folder = found.folder
        if found.form == "repository":
            declaration, _ = parse_repository_3x(section.get("repository"),
                                                 f"{namespace}.repository")
            folder = cache_folder_3x(root, declaration) if declaration else None
        if folder is None or found.problem:
            continue
        folder = Path(os.path.realpath(os.path.normpath(Path(folder).absolute())))
        rel = Path(os.path.relpath(folder, base)).as_posix()
        out.append(Store(namespace, rel, folder))
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
    # 3.x listed every taxonomy folder, hidden ones too, so a store at a
    # clone's root listed its `.git` folders as terms; no hidden folder is
    # converted.
    three = [p for p in objects_3x(store.folder, ns)
             if not any(part.startswith(".") for part in p.split("/"))
             and ((store.folder / p / STATE_3X[ns]).is_file()
                  or (bare_terms and p not in four))]
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


def related_stores(member) -> list[tuple[str, Path]]:
    """A related project's stores, each `(namespace, folder)`: a 3.x one's
    where 3.x put them, a 4.0 one's plain paths where 4.0 puts them (an
    address is left out: it names another project's folder)."""
    import os
    if member.three_x:
        return [(s.namespace, s.folder) for s in stores_of(member.folder, member.raw)]
    out = []
    for namespace in NAMESPACES:
        section = member.raw.get(namespace)
        configured = section.get("path") if isinstance(section, dict) else None
        if isinstance(configured, str) and configured.startswith("tcw://"):
            continue
        folder = Path(configured).expanduser() if isinstance(configured, str) \
            else Path("docs") / namespace
        folder = folder if folder.is_absolute() else member.folder / folder
        out.append((namespace, Path(os.path.realpath(os.path.normpath(folder)))))
    return out


def related_store_blockers(stores: list[Store], family) -> list[Blocker]:
    """B7 for one of the project's stores and a related project's store in
    one folder, or one inside the other (S110 Design 7.4)."""
    out = []
    fix = "give each store a folder of its own, then run 'tcw migrate' again"
    for pid in list(family.placed):
        member = family.quiet(pid)
        if member is None:
            continue
        for namespace, theirs in related_stores(member):
            for store in stores:
                mine = store.folder.resolve()
                if mine == theirs:
                    out.append(Blocker("B7", store.rel, f"the {store.namespace} store is "
                                                        f"'{pid}''s {namespace} store",
                                       fix))
                elif theirs in mine.parents:
                    out.append(Blocker("B7", store.rel, f"the {store.namespace} store is "
                                                        f"inside '{pid}''s {namespace} "
                                                        f"store {theirs}", fix))
                elif mine in theirs.parents:
                    out.append(Blocker("B7", store.rel, f"'{pid}''s {namespace} store "
                                                        f"{theirs} is inside the "
                                                        f"{store.namespace} store", fix))
    return out


def left_elsewhere(root: Path, mapping: dict, steps, git: Path | None) -> list[str]:
    """Design 1.4's lines: for each store outside the project's own
    repository, `left in another repository: <folder>`, then each file the
    run changes there."""
    from tcw.migrate.model import Move
    from tcw.store.fs import git_root
    out = []
    for store in stores_of(root, mapping):
        repository = git_root(store.folder) if store.folder.is_dir() else None
        if repository is not None and git is not None and \
                Path(repository).resolve() == Path(git).resolve():
            continue
        if repository is None and git is None and Path(root).resolve() in \
                (store.folder, *store.folder.parents):
            continue
        prefix = store.rel.rstrip("/") + "/"
        files = sorted({path for step in steps
                        for path in ((step.old, step.new) if isinstance(step, Move)
                                     else (step.path,))
                        if path.startswith(prefix)})
        if files:
            shown = repository if repository is not None else store.folder
            out.append(f"left in another repository: {shown}")
            out += [f"  {path}" for path in files]
    return out


# ---------------------------------------------------------------------------
# One object


def _plan_object(store: Store, id_path: str, kept: set[str], project: str,
                 out: StorePlan, mentions: Mentions, entries: list[str],
                 owners: Owners, work_backend: str, override=None) -> None:
    """One object's state file. `override` is the object's C14 resolution:
    its 4.0 state file is written at the original's id-path, without the
    `overrides` key, and keeps no `name` of its own when it had none, since
    3.x showed the original's."""
    ns = store.namespace
    folder = store.folder / id_path
    old_rel = f"{store.rel}/{id_path}/{STATE_3X[ns]}"
    if override is not None:
        id_path = override.target
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
    refs = state_fields(ns, work_backend)
    rows = refs + (DOCS_FIELDS if ns == "capabilities" else ())
    by_refs = owners.replace(old_rel, refs)

    def replace(row, value):
        return docs_entry(value, entries) if row in DOCS_FIELDS else by_refs(row, value)
    if source != text or applied(data, DOCS_FIELDS, replace) != data:
        conversions.append("C13")
    if applied(data, refs, replace) != data:
        conversions.append("C16")
    if override is not None:
        edits.append(RemoveTop("overrides"))
        conversions.append("C14")
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
        if not data.get("name") and override is None:
            edits.append(SetTop("name", fallback_name(id_path)))
            conversions.append("C12")
            out.reports.append(Report("D7", new_rel, f"name: {fallback_name(id_path)} "
                                                     f"written, the name TCW 3 showed"))
    if text is None:
        out.reports.append(Report("D7", new_rel, "written where TCW 3 had no state file"))
    expect = {VERSION_KEY: __version__, **applied(intended(data, edits), rows, replace)}
    if four_text is not None:
        _both(store, old_rel, new_rel, text, four_text, expect, out)
    else:
        try:
            new = convert_text(new_rel, source, edits, fields=rows, replace=replace,
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
    if ns != "work" and not (folder / DESCRIPTION).exists() and override is None:
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
                 covered: set[str], owners: Owners, out: StorePlan) -> None:
    """C13's rewrites of every other Markdown and YAML file of the stores,
    each at the place it has after phase B, and A3 for what is left."""
    entries: dict[str, list[str]] = {}
    for m in moved:
        entries.setdefault(f"{m.store_rel}/{m.from_path}", []).append(m.entry)
    converted = {f"{store.rel}/{p}" for store, convert, _ in planned for p in convert}
    kept_of = {store.rel: kept for store, _, kept in planned}
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
                codes = ("C13",) if new != text else ()
                ref_text = new
                if name.endswith(".md"):
                    ref_text = owners.links(new, rel)
                elif store.namespace == "work" and name == CAPABILITIES_FILE \
                        and folder.partition(store.rel + "/")[2] in kept_of[store.rel]:
                    try:
                        ref_text = rewrite_yaml(new, CAPABILITIES_YAML,
                                                owners.replace(rel, CAPABILITIES_YAML))[0]
                    except yaml.YAMLError:
                        pass
                if ref_text != new:
                    codes += ("C16",)
                if codes:
                    out.steps.append(Write(final, "C", digest(text), ref_text, codes))


def _own_ids(store: Store, convert: list[str]) -> dict[str, str]:
    """Each of the store's own 3.x capabilities' `cap-…` id, by id-path; an
    override is left out."""
    out = {}
    for id_path in convert:
        data = _meta_of(store, id_path)
        if data.get("overrides"):
            continue
        cap_id = data.get("id")
        if isinstance(cap_id, str) and cap_id:
            out[id_path] = cap_id
    return out


def _meta_of(store: Store, id_path: str) -> dict:
    path = store.folder / id_path / STATE_3X[store.namespace]
    try:
        text = read_text(path)
    except (OSError, UnicodeDecodeError):
        return {}
    data, _ = parse_mapping_3x(text, path) if text is not None else (None, None)
    return data if isinstance(data, dict) else {}


def plan_stores(root: Path, mapping: dict, project: str, *,
                three_x: bool = True, work_backend: str = "filesystem",
                family=None, ancestors: dict[str, list[str]] | None = None,
                middle: bool = False) -> StorePlan:
    """Every store's state files and loose entries. `three_x`: the project's
    configuration is still in 3.x form, so a bare taxonomy folder is a 3.x
    term. `family` is the project's related projects, whose stores B7 also
    compares with and whose capabilities an override's pointer is resolved
    among (C14); `ancestors`, the projects each axis is inherited from once
    converted (D2); `middle`, whether the project has children, below which
    4.0 applies its overrides (D4)."""
    out = StorePlan()
    stores = stores_of(root, mapping)
    out.blockers += nesting_blockers(stores)
    if family is not None:
        out.blockers += related_store_blockers(stores, family)
    planned, moved, relocated, override_moves = [], [], [], []
    found_overrides: dict[tuple[str, str], object] = {}
    for store in stores:
        convert, kept = objects(store, bare_terms=three_x)
        out.blockers += name_blockers(store, kept, project)
        planned.append((store, convert, kept))
        resolved = {}
        if store.namespace == "capabilities":
            own = {cap_id: path for path, cap_id in _own_ids(store, convert).items()}
            found = plan_overrides(store, convert, kept, mapping, family, own)
            out.blockers += found.blockers
            resolved = found.found
            overridden = {o.target for o in resolved.values()}
            for override in resolved.values():
                found_overrides[(store.rel, override.path)] = override
                out.reports += reports_of(store, override, _meta_of(store, override.path),
                                          middle)
        else:
            overridden = set()
        out.reports += d2_reports(store, kept, (ancestors or {}).get(store.namespace, []),
                                  family, overridden)
        for id_path in convert:
            override = resolved.get(id_path)
            loose = [entry for entry in loose_entries(store.folder / id_path,
                                                      store.namespace, id_path, kept)
                     # One already in `resources/` under that name is left
                     # where it is: a rename would replace it.
                     if not (store.folder / id_path / RESOURCES / entry).exists()]
            if override is None or not override.moves:
                moved += [Loose(store.rel, id_path, entry) for entry in loose]
                continue
            out.moved[override.path] = override.target
            moves, blockers = entry_moves(root, store, override, loose)
            out.blockers += blockers
            for old, new, codes in moves:
                entry = old.rsplit("/", 1)[1]
                if "C13" in codes:
                    moved.append(Loose(store.rel, override.target, entry, override.path))
                else:
                    relocated.append((old, new))
                override_moves.append(Move(old, new, "B", files_of(Path(root) / old), codes))
    mentions = Mentions(moved, relocated)
    owners = Owners(project, any(s.namespace == "capabilities" and s.folder.is_dir()
                                 for s in stores), moved=dict(out.moved))
    out.steps += override_moves
    out.steps += [move_of(root, m) for m in moved if m.origin is None]
    covered = set()
    for store, convert, kept in planned:
        for id_path in convert:
            entries = [m.entry for m in moved
                       if m.store_rel == store.rel and m.from_path == id_path]
            _plan_object(store, id_path, kept, project, out, mentions, entries, owners,
                         work_backend, found_overrides.get((store.rel, id_path)))
            covered.add(f"{store.rel}/{id_path}/{STATE_3X[store.namespace]}")
        out.reports += _resources_reports(store, kept)
    _text_writes(root, planned, moved, mentions, covered, owners, out)
    out.blockers += list({(b.code, b.where, b.why): b for b in owners.blockers}.values())
    out.owners = owners.given
    return out
