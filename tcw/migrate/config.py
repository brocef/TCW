"""The configuration's half of the plan (TCW-116 Design 3: C1, C2, C7; plan
Step 5).

The root `tcw-config.yaml` and `tcw-config.local.yaml` become `.tcw/`'s two
files, each with the version line first and every `not_tags` key renamed,
their text edited in place. Inside a git repository `.tcw/.gitignore` gets
the progress record's line in phase A and the two personal files' lines in
phase D, planned here as writes, never by `ignore_personal_files`, which
would write the file itself. The root files are deleted in phase E, each
once its `.tcw/` copy holds what the plan wrote.

The user-wide file is read, never written (C7): a `not_tags` in it is A5.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import yaml

from tcw import __version__
from tcw.config import dotted
from tcw.migrate import progress
from tcw.migrate.editors import convert_text
from tcw.migrate.legacy import ROOT_CONFIG, ROOT_LOCAL, Layer3
from tcw.migrate.model import (ABSENT, Blocker, Delete, Report, Step, Write, digest,
                               file_digest)
from tcw.project_files import (_RENAMED_KEYS, LOCAL_SENTINEL, SENTINEL, TCW_FOLDER,
                               VERSION_KEY, key_problems, version_line,
                               without_version)
from tcw.store.base import MIGRATION_GUIDE, RETIRED_PROJECTS_KEY
from tcw.cli_suggest import REMOVED_COMMANDS
from tcw.store.config_edit import ConfigEditRefused, RenameKey
from tcw.store.fs import LOCAL_CONFIG_RULE, LOCAL_MANIFEST_RULE

IGNORE = f"{TCW_FOLDER}/.gitignore"
RECORD_NAME = f"{TCW_FOLDER}/tcw-migration.yaml"

#: The commands and flags TCW 4 removes, for A13 (S115 Design 1.2; TCW-114):
#: the commands from the one table that names them (TCW-115's guard allows
#: no other), then the two flags.
_REMOVED = (*(f"tcw {name}" for name in REMOVED_COMMANDS), "--project", "--blocks")
_REMOVED_RE = re.compile(r"(?<![\w-])(" + "|".join(re.escape(w) for w in _REMOVED)
                         + r")(?![\w-])")
#: The keys whose value is a command TCW runs.
_COMMAND_KEYS = ("command", "generate")


@dataclass
class ConfigPlan:
    """What the configuration contributes to the plan."""

    steps: list[Step] = field(default_factory=list)
    reports: list[Report] = field(default_factory=list)
    blockers: list[Blocker] = field(default_factory=list)
    project: str | None = None
    #: Each comment a replaced block took with it (Design 2.8), as a line.
    dropped: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Reading positions


def key_lines(text: str) -> dict[tuple, int]:
    """The line (from 1) each key path of `text` is written on. A key an
    alias reaches is given the line it is written on."""
    found: dict[tuple, int] = {}
    try:
        top = yaml.compose(text)
    except yaml.YAMLError:
        return found

    def walk(held, path, seen):
        if id(held) in seen:
            return
        if isinstance(held, yaml.MappingNode):
            seen = seen | {id(held)}
            for key, value in held.value:
                if isinstance(key, yaml.ScalarNode):
                    here = (*path, key.value)
                    found.setdefault(here, key.start_mark.line + 1)
                    walk(value, here, seen)
        elif isinstance(held, yaml.SequenceNode):
            seen = seen | {id(held)}
            for i, entry in enumerate(held.value):
                found.setdefault((*path, i), entry.start_mark.line + 1)
                walk(entry, (*path, i), seen)

    walk(top, (), frozenset())
    return found


def _leaves(value: Any, path: tuple = ()) -> Iterator[tuple[tuple, Any]]:
    if isinstance(value, dict):
        for key, inner in value.items():
            yield (*path, key), inner
            yield from _leaves(inner, (*path, key))
    elif isinstance(value, list):
        for i, inner in enumerate(value):
            yield (*path, i), inner
            yield from _leaves(inner, (*path, i))


def first_difference(a: Any, b: Any, path: tuple = ()) -> tuple | None:
    """The first key path at which `a` and `b` differ, or None."""
    if isinstance(a, dict) and isinstance(b, dict):
        for key in [*a, *(k for k in b if k not in a)]:
            if key not in a or key not in b:
                return (*path, key)
            found = first_difference(a[key], b[key], (*path, key))
            if found is not None:
                return found
        return None
    if isinstance(a, list) and isinstance(b, list):
        for i, (x, y) in enumerate(zip(a, b)):
            found = first_difference(x, y, (*path, i))
            if found is not None:
                return found
        return None if len(a) == len(b) else (*path, min(len(a), len(b)))
    return None if a == b else path


# ---------------------------------------------------------------------------
# One file


def renames(mapping: dict) -> list[RenameKey]:
    """C2: every key 4.0 renames, wherever it is a key."""
    return [RenameKey(path, _RENAMED_KEYS[path[-1]]) for path, _ in key_problems(mapping)
            if isinstance(path[-1], str) and path[-1] in _RENAMED_KEYS]


def _renamed(mapping: dict) -> dict:
    from tcw.store.config_edit import intended
    return intended(mapping, renames(mapping))


def _empty(layer: Layer3) -> bool:
    """0 bytes, or YAML that reads as nothing (Design 3, C1's empty files)."""
    return layer.present and not layer.problem and not layer.data


def _b1(rel: str, mapping: dict) -> list[Blocker]:
    return [Blocker("B1", rel, f"{dotted(path)}: {message}",
                    "rename it by hand to a key TCW 4 reads, then run 'tcw migrate' again")
            for path, message in key_problems(_renamed(mapping))]


def _b14(rel: str, layer: Layer3) -> Blocker:
    return Blocker("B14", rel, layer.problem or "cannot be read",
                   "correct the file by hand, then run 'tcw migrate' again")


def plan_file(root: Path, old: Layer3, new: Layer3, *, shared: bool,
              edits: tuple = (), conversions: tuple[str, ...] = ()) -> ConfigPlan:
    """One of the two project files: the 3.x file at the root (`old`) and
    its `.tcw/` place (`new`). `edits` are the structural edits the
    relation and location conversions make to the shared file (C3, C5, C8), after the renames."""
    out = ConfigPlan()
    old_rel, new_rel = (ROOT_CONFIG, SENTINEL) if shared else (ROOT_LOCAL, LOCAL_SENTINEL)
    for rel, layer in ((old_rel, old), (new_rel, new)):
        if layer.problem:
            out.blockers.append(_b14(rel, layer))
    if out.blockers:
        return out
    new_versioned = new.present and not _empty(new) and VERSION_KEY in (new.data or {})
    if old.present:
        source, source_rel, mapping = old, old_rel, old.data or {}
    elif new.present and not _empty(new) and not new_versioned:
        source, source_rel, mapping = new, new_rel, new.data or {}    # 3.x text in .tcw/
    elif shared and _empty(new):
        out.blockers.append(Blocker(
            "B15", new_rel, "is empty and there is no root tcw-config.yaml to give it an id",
            f"write the project's id in it as 'id: <id>', after '{VERSION_KEY}: "
            f"{__version__}' as its first line"))
        return out
    elif not shared and _empty(new):
        out.steps.append(Write(new_rel, "D", digest(new.text), version_line(), ("C1",)))
        return out
    else:
        if new_versioned and shared:
            out.project = (new.data or {}).get("id")
        return out
    if shared:
        out.project = mapping.get("id")
        if not out.project:
            out.blockers.append(Blocker("B15", source_rel, "has no id",
                                        "add 'id: <id>' to it, then run 'tcw migrate' again"))
        if RETIRED_PROJECTS_KEY in mapping:
            out.blockers.append(Blocker(
                "B2", source_rel,
                f"{RETIRED_PROJECTS_KEY}: is the TCW 2.x name of 'projects', which TCW 3 "
                f"refuses too", f"convert it with TCW 3.0 as {MIGRATION_GUIDE} says, then "
                                f"run 'tcw migrate'"))
    out.blockers += _b1(source_rel, mapping)
    out.reports += command_reports(source_rel, source.text or "", mapping)
    out.reports += credential_reports(source_rel, mapping)
    if shared:
        out.reports += null_reports(source_rel, mapping)
    if out.blockers:
        return out
    from tcw.store.config_edit import intended
    target = {VERSION_KEY: __version__, **intended(_renamed(mapping), list(edits))}
    if new_versioned:
        if without_version(new.data) != without_version(target):
            where = first_difference(without_version(target), without_version(new.data))
            out.blockers.append(Blocker(
                "B11", old_rel, f"differs from {new_rel} at {dotted(where or ())}",
                f"make the two files agree, or delete the one that is wrong, then run "
                f"'tcw migrate' again"))
            return out
        out.steps.append(Delete(old_rel, "E", digest(old.text), new_rel, digest(new.text),
                                ("C1",)))
        return out
    try:
        converted = convert_text(new_rel, source.text, renames(mapping) + list(edits),
                                 expect=target)
        text = converted.text
        out.dropped = [f"{source_rel}: {comment}" for comment in converted.dropped]
    except ConfigEditRefused as refused:
        out.blockers.append(Blocker("B12" if "anchor" in str(refused) else "B3", source_rel,
                                    str(refused), "edit the file by hand"))
        return out
    expect = file_digest(root / new_rel)
    made = ("C1",) + (("C2",) if renames(mapping) else ()) + tuple(conversions)
    out.steps.append(Write(new_rel, "D", expect, text, made,
                           ((source_rel, digest(source.text)),) if source is old else ()))
    if source is old:
        out.steps.append(Delete(old_rel, "E", digest(old.text), new_rel, digest(text),
                                ("C1",)))
    return out


# ---------------------------------------------------------------------------
# Reports


def command_reports(rel: str, text: str, mapping: dict) -> list[Report]:
    """A13: a bound command naming a command or flag 4.0 removes."""
    lines = key_lines(text)
    out = []
    for path, value in _leaves(mapping):
        if not path or path[-1] not in _COMMAND_KEYS or not isinstance(value, str):
            continue
        found = _REMOVED_RE.search(value)
        if found is None:
            continue
        out.append(Report("A13", f"{rel}:{lines.get(path, 0)}",
                          f"{dotted(path)}: '{value}' uses {found.group(1)}, which TCW 4 "
                          f"removes; it is left as written"))
    return _unique(out)


def credential_reports(rel: str, mapping: dict) -> list[Report]:
    """A9: a credential variable 4.0 would read as an override."""
    jira = ((mapping.get("work") or {}) if isinstance(mapping.get("work"), dict) else {})
    jira = jira.get("jira") if isinstance(jira.get("jira"), dict) else {}
    credentials = jira.get("credentials") if isinstance(jira.get("credentials"), dict) else {}
    return [Report("A9", rel, f"work.jira.credentials.{key}: {name} starts with TCW_ and "
                              f"holds __, which TCW 4 reads as an override of a "
                              f"configuration value; name another variable")
            for key, name in credentials.items()
            if isinstance(name, str) and name.startswith("TCW_") and "__" in name]


def null_reports(rel: str, mapping: dict) -> list[Report]:
    """D5: a null at `work.tags`, `work.jira` or below, which in TCW 4
    removes a value a parent passes down."""
    work = mapping.get("work") if isinstance(mapping.get("work"), dict) else {}
    out = []
    for key in ("tags", "jira"):
        if key not in work:
            continue
        here = ("work", key)
        pairs = [(here, work[key]), *((here + p, v) for p, v in _leaves(work[key]))]
        for path, value in pairs:
            if value is None:
                out.append(Report("D5", rel, f"{dotted(path)}: null now removes the value "
                                             f"a parent project passes down"))
    return out


def user_reports(user: Layer3 | None) -> list[Report]:
    """A5: `not_tags` in the user-wide file, left as written (C7)."""
    if user is None or not user.present or not user.data:
        return []
    lines = key_lines(user.text or "")
    return _unique([Report("A5", f"{user.path}:{lines.get(path, 0)}",
                           f"{dotted(path)}: TCW 4 refuses not_tags; write not-tags (this "
                           f"file is shared with any TCW 3.x on this machine, which needs "
                           f"not_tags, so tcw migrate leaves it)",
                           predicts=(str(user.path), "not_tags"))
                    for path, _ in key_problems(user.data)
                    if path and path[-1] in _RENAMED_KEYS])


def worktree_reports(root: Path) -> list[Report]:
    """A7: in a linked git worktree, a 3.x personal file only in the main
    checkout, which this run does not convert (Design 6.6)."""
    from tcw.store.project import _below, worktree_anchors
    root = Path(root)
    anchors = worktree_anchors(root)
    if not anchors or (root / ROOT_LOCAL).is_file():
        return []
    top, main = anchors
    inside = _below(root.resolve(), top)
    theirs = main / inside / ROOT_LOCAL if inside is not None else None
    if theirs is None or not theirs.is_file():
        return []
    return [Report("A7", str(theirs), "a 3.x personal file in the main checkout, which "
                                      "this run does not convert; run 'tcw migrate' there")]


def ignore_reports(root: Path) -> list[Report]:
    """A4: a root `.gitignore` line for the 3.x personal file."""
    path = Path(root) / ".gitignore"
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    return [Report("A4", f".gitignore:{number}",
                   f"{LOCAL_CONFIG_RULE} now ignores nothing: the personal file is "
                   f"{LOCAL_SENTINEL}, which {IGNORE} ignores")
            for number, line in enumerate(text.splitlines(), start=1)
            if line.strip() == LOCAL_CONFIG_RULE]


def _unique(reports: list[Report]) -> list[Report]:
    """Each report once (a key two aliases reach is one line of the file)."""
    return list({(r.code, r.where, r.text): r for r in reports}.values())


# ---------------------------------------------------------------------------
# .tcw/.gitignore


def _missing(text: str, rules: tuple[str, ...]) -> list[str]:
    """The rules a `.gitignore` text lacks, by the test `ignore_personal_files`
    uses: a line reading the rule, or its name without the `/`."""
    lines = {line.strip() for line in text.splitlines()}
    return [rule for rule in rules if not {rule, rule[1:]} & lines]


def _appended(text: str, rules: list[str]) -> str:
    if text and not text.endswith("\n"):
        text += "\n"
    return text + "".join(rule + "\n" for rule in rules)


def plan_ignore(root: Path) -> list[Write]:
    """C1's `.tcw/.gitignore` (inside a git repository only): the progress
    record's line in phase A, the personal files' lines in phase D."""
    from tcw.store.config_edit import read_text
    path = Path(root) / IGNORE
    try:
        text = read_text(path)
    except (OSError, UnicodeDecodeError):
        text = None
    now = text or ""
    out = []
    first = _missing(now, (progress.IGNORE_RULE,))
    if first:
        after = _appended(now, first)
        out.append(Write(IGNORE, "A", ABSENT if text is None else digest(now), after, ("C1",)))
        expect, now = digest(after), after
    else:
        expect = ABSENT if text is None else digest(now)
    rest = _missing(now, (LOCAL_CONFIG_RULE, LOCAL_MANIFEST_RULE))
    if rest:
        out.append(Write(IGNORE, "D", expect, _appended(now, rest), ("C1",)))
    return out


# ---------------------------------------------------------------------------
# `projects:` becomes `parents:` and `children:` (C3, C6; plan Step 17)

#: The axes an `extends` can name, in the order TCW 4 lists them.
EXTENDED_AXES = ("taxonomy", "capabilities")


@dataclass
class Link:
    """One planned entry of `parents:`: a project, and the axes it passes,
    None for all of them (a plain ID)."""

    id: str
    inherit: tuple[str, ...] | None = None

    def value(self) -> Any:
        """The entry as `parents:` holds it."""
        if self.inherit is None:
            return self.id
        return {"id": self.id, "inherit": list(self.inherit) if self.inherit else "none"}

    def passes(self, axis: str) -> bool:
        return self.inherit is None or axis in self.inherit

    def with_axis(self, axis: str) -> "Link":
        if self.passes(axis):
            return self
        axes = {*(self.inherit or ()), axis}
        return Link(self.id, tuple(a for a in EXTENDED_AXES if a in axes))


@dataclass
class Relations:
    """What a 3.x `projects:` block becomes: the parent links and children
    to write, the entries their locations come from (for C4), the values
    removed with no 4.0 home (Design 7's `removed:`), and the reports."""

    present: bool = False
    parents: list[Link] = field(default_factory=list)
    children: list[str] = field(default_factory=list)
    entries: list = field(default_factory=list)
    removed: list[dict] = field(default_factory=list)
    reports: list[Report] = field(default_factory=list)
    blockers: list[Blocker] = field(default_factory=list)

    def edits(self) -> list:
        """The edits of the shared file (Decided 9): `projects:` removed, and
        `parents:` and `children:` set after `id`."""
        from tcw.store.config_edit import RemoveTop, SetTop
        if not self.present:
            return []
        out: list = [RemoveTop("projects")]
        if self.parents:
            out.append(SetTop("parents", [link.value() for link in self.parents],
                              after="id"))
        if self.children:
            out.append(SetTop("children", list(self.children),
                              after="parents" if self.parents else "id"))
        return out


def extended_by(mapping: dict) -> dict[str, list[str]]:
    """Each axis's 3.x `extends` list, read as 3.x read it; an axis whose
    list 3.x refused is left out (its B14 comes from `extends_blockers`)."""
    from tcw.migrate.legacy import extends_3x
    out = {}
    for axis in EXTENDED_AXES:
        try:
            out[axis] = extends_3x(mapping.get(axis), f"{axis}.extends")
        except ValueError:
            out[axis] = []
    return out


def plan_relations(rel: str, mapping: dict) -> Relations:
    """C3 and C6 on the shared file `rel`, read as `mapping`: each
    `projects.parent` entry a plain parent ID; each `projects.upstream` one
    a parent passing the axes whose `extends` names it, or none; each
    `projects.children` one a child. Every `jira` block is dropped, recorded
    and reported (D6), its credential names checked first (A9). Entries are
    kept in the order written within each relation, parents before
    upstreams."""
    from tcw.migrate.legacy import relations_3x
    out = Relations(present="projects" in mapping)
    if not out.present:
        return out
    found, problems = relations_3x(mapping, rel)
    if problems:
        out.blockers += [Blocker("B14", rel, problem.removeprefix(f"{rel}: "),
                                 "correct the projects: block by hand, then run "
                                 "'tcw migrate' again") for problem in problems]
        return out
    extends = extended_by(mapping)
    out.entries = found
    for kind in ("parent", "upstream"):
        for relation in (r for r in found if r.kind == kind):
            if kind == "parent":
                out.parents.append(Link(relation.id))
            else:
                axes = tuple(a for a in EXTENDED_AXES if relation.id in extends[a])
                out.parents.append(Link(relation.id, axes))
    out.children = [r.id for r in found if r.kind == "children"]
    for relation in found:
        if relation.jira is None:
            continue
        key = f"projects.{relation.kind}.{relation.id}.jira"
        out.removed.append({"file": rel, "key": key, "value": relation.jira})
        out.reports.append(Report("D6", rel, f"{key}: dropped; it filed work into "
                                             f"another project's Jira, which TCW 4 removes "
                                             f"(kept in {RECORD_NAME})"))
        out.reports += _jira_block_credentials(rel, key, relation.jira)
    return out


def _jira_block_credentials(rel: str, key: str, block: Any) -> list[Report]:
    """A9 for a `projects:` entry's `jira` block (Design 2.9)."""
    credentials = block.get("credentials") if isinstance(block, dict) else None
    if not isinstance(credentials, dict):
        return []
    return [Report("A9", rel, f"{key}.credentials.{name}: {value} starts with TCW_ and "
                              f"holds __, which TCW 4 reads as an override of a "
                              f"configuration value; name another variable")
            for name, value in credentials.items()
            if isinstance(value, str) and value.startswith("TCW_") and "__" in value]


# ---------------------------------------------------------------------------
# Manifest entries (C4: M1-M6; plan Step 18)


@dataclass(frozen=True)
class Located:
    """A project a manifest entry may be written for: the 3.x entry that
    names it (`relation`), and the folder of the project whose entry it is
    (`base`), against which a relative locator is read. `folder` is where it
    was found, for an entry that holds no location of its own (a project a
    migrated project's manifest placed)."""

    relation: Any
    base: Path
    folder: Path | None = None


@dataclass
class ManifestPlan:
    steps: list[Step] = field(default_factory=list)
    reports: list[Report] = field(default_factory=list)
    blockers: list[Blocker] = field(default_factory=list)
    shared: dict = field(default_factory=dict)
    personal: dict = field(default_factory=dict)


def _posix(path: Path | str) -> str:
    return Path(path).as_posix()


def _absolute_text(text: str) -> bool:
    return text.startswith(("/", "~", "\\")) or (len(text) > 1 and text[1] == ":")


def _repository_name(url: str) -> str:
    """M5's `<name>`: the URL's last part without `.git`."""
    tail = re.split(r"[/:]", url.strip().rstrip("/"))[-1]
    return tail[:-4] if tail.endswith(".git") else tail


def _relative(root: Path, folder: Path) -> str:
    import os
    return _posix(os.path.relpath(folder, root))


def plan_manifests(root: Path, located: list[Located], project_id: str) -> ManifestPlan:
    """C4: for each project `located` names, the 3.x entry's location as an
    entry of `.tcw/tcw-manifest.yaml` (shared) or
    `.tcw/tcw-manifest.local.yaml` (personal), by TCW-107's mapping (M1 to
    M6); `finish_manifests` plans their writes, each checked by 4.0's parser
    (B3), once C5 has added its entries. An entry is
    decided from the declared locations, never from `TCW_PROJECT_<ID>`
    (A11), and M6 compares only with what 4.0's search from this project
    would find, never a parent's manifests."""
    from tcw.migrate import family as family_module, legacy
    root = Path(root).resolve()
    out = ManifestPlan()
    for item in located:
        _plan_entry(root, item, out, legacy, family_module)
    return out


def _plan_entry(root: Path, item: Located, out: ManifestPlan, legacy, family_module) -> None:
    import os
    relation = item.relation
    pid = relation.id
    base = Path(item.base).resolve()
    if os.environ.get(_variable(pid), "").strip():
        out.reports.append(Report(
            "A11", _variable(pid), f"is set while migrating; the manifest entry for "
                                   f"'{pid}' is decided from where its projects: entry "
                                   f"says it is, not from the variable"))
    declared = _declared_folder(base, relation, legacy)
    repo = relation.repository
    if relation.locator is None and repo is None:
        # Placed by a migrated project's manifest or search: its folder.
        if item.folder is None:
            return
        declared = Path(os.path.realpath(item.folder))
        found = family_module.search_4(root, pid)
        if not (len(found) == 1 and Path(os.path.realpath(found[0])) == declared):
            out.shared.setdefault(pid, {"path": _relative(root, declared)})
        return
    if repo is None:
        found = family_module.search_4(root, pid)
        if declared is not None and len(found) == 1 and found[0] == declared:
            return                                      # M6
    shared: dict = {}
    personal: dict = {}
    locator = relation.locator
    subfolder = repo.path if repo is not None and repo.path else None
    m5 = None
    only_here = None
    if repo is not None:
        if "#" in repo.url:
            out.blockers.append(Blocker(
                "B3", f"projects.{relation.kind}.{pid}.repository.url",
                f"TCW 4 would refuse the manifest entry as planned: {repo.url!r} holds "
                f"'#', which a manifest reads as the end of the address",
                "write the address without '#' in the TCW 3 file, then run "
                "'tcw migrate' again"))
            return
        shared["repository"] = repo.url + (f"#{repo.ref}" if repo.ref else "")
        m5 = "../" + _repository_name(repo.url) + (f"/{subfolder}" if subfolder else "")
        if subfolder:
            shared["subfolder"] = subfolder
    if locator is not None:
        if _absolute_text(locator):
            personal["path"] = locator                                      # M1
            only_here = _only_here(root, base, relation, locator)
            if m5 is not None:
                shared["path"] = m5
        else:
            shared["path"] = locator if base == root else \
                _relative(root, base / locator)
    elif repo is not None and repo.checkout:
        written = _posix(Path(repo.checkout) / subfolder) if subfolder else repo.checkout
        if _absolute_text(repo.checkout):                                   # M4
            personal["path"] = written
            shared["path"] = m5
            only_here = _only_here(root, base, relation, written)
        else:
            shared["path"] = written if base == root else _relative(root, base / written)
    elif repo is not None:                                                  # M5
        shared["path"] = m5
        target = Path(os.path.normpath(root / m5))
        if target.exists() and family_module.declared_id(target) != pid \
                and any(target.iterdir() if target.is_dir() else [target]):
            out.blockers.append(Blocker(
                "B13", ".tcw/tcw-manifest.yaml",
                f"projects.{pid}.path: the shared manifest's path {m5} already holds "
                f"something other than the project '{pid}'",
                f"move what is at {target} elsewhere, then run 'tcw migrate' again"))
            return
        clone = legacy.cache_folder_3x(base, repo)
        if legacy.holds_project(clone):
            personal["path"] = str(clone)
            out.reports.append(Report(
                "A6", ".tcw/tcw-manifest.local.yaml",
                f"projects.{pid}.path: names TCW 3's clone of '{pid}' at {clone}, a "
                f"cache folder that cleaning tools may empty; moving the clone to "
                f"{target} and deleting this entry keeps it safe"))
        else:
            out.reports.append(Report(
                "A6", ".tcw/tcw-manifest.yaml",
                f"projects.{pid}: TCW 3's clone of '{pid}' is not on this machine; "
                f"'tcw project provision' will fetch it into {target}"))
    if "path" not in shared and "path" not in personal:
        return
    if shared:
        out.shared.setdefault(pid, shared)
    if personal:
        if only_here is not None and pid not in out.personal:
            out.reports.append(only_here)
        out.personal.setdefault(pid, personal)


def _only_here(root: Path, base: Path, relation, path: str) -> Report:
    """A14: an absolute or `~` path (M1, M4) that TCW 3's shared file held
    for everyone, now only in this person's untracked personal manifest. No
    other person's run can recover it, since the shared file it came from
    is converted, so each must write their own entry."""
    source = ROOT_CONFIG if base == root else _posix(Path(_relative(root, base)) /
                                                     ROOT_CONFIG)
    pid = relation.id
    return Report(
        "A14", ".tcw/tcw-manifest.local.yaml",
        f"projects.{pid}.path: {path}, which {source}'s projects.{relation.kind}.{pid} "
        f"held for everyone, is now only in this file, which is not shared; every "
        f"other person must add their own .tcw/tcw-manifest.local.yaml entry for "
        f"'{pid}'")


def _variable(project_id: str) -> str:
    from tcw.store.project import override_variable
    return override_variable(project_id)


def _declared_folder(base: Path, relation, legacy) -> Path | None:
    """The folder the declared locations give, ignoring `TCW_PROJECT_<ID>`."""
    import os
    saved = os.environ.pop(_variable(relation.id), None)
    try:
        folder, how = legacy.locate_3x(base, relation)
    finally:
        if saved is not None:
            os.environ[_variable(relation.id)] = saved
    return Path(os.path.realpath(folder)) if how != "absent" else None


def _manifest_writes(root: Path, shared: dict, personal: dict
                     ) -> tuple[list[Step], list[Blocker]]:
    """The two manifests' writes in phase D, merged with what each already
    holds (an entry already there is kept as it is), each checked by
    `parse_manifest` (B3)."""
    from tcw.project_files import LOCAL_MANIFEST, MANIFEST
    from tcw.store.config_edit import read_text
    from tcw.store.manifest import parse_manifest
    steps: list[Step] = []
    blockers: list[Blocker] = []
    for rel, entries, personal_file in ((MANIFEST, shared, False),
                                        (LOCAL_MANIFEST, personal, True)):
        if not entries:
            continue
        path = root / rel
        try:
            old_text = read_text(path)
            old = yaml.safe_load(old_text) if old_text else None
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
            old_text, old = None, None
        projects = dict((old or {}).get("projects") or {}) if isinstance(old, dict) else {}
        merged = dict(projects)
        for pid, entry in entries.items():
            merged.setdefault(pid, entry)
        if merged == projects and old_text is not None:
            continue
        text = version_line() + yaml.safe_dump({"projects": merged}, sort_keys=False,
                                               allow_unicode=True)
        _, problems = parse_manifest(yaml.safe_load(text), path, personal=personal_file)
        if problems:
            blockers += [Blocker("B3", rel, f"TCW 4 would refuse the file as planned: "
                                            f"{problem}", B3_FIX) for problem in problems]
            continue
        steps.append(Write(rel, "D", ABSENT if old_text is None else digest(old_text),
                           text, ("C4",)))
    return steps, blockers


B3_FIX = "correct it in the TCW 3 file it is converted from, then run 'tcw migrate' again"


# ---------------------------------------------------------------------------
# `extends` becomes parent links (C8: E1-E5; D1, D6, D8, B4; plan Step 19)


@dataclass
class Links:
    """One project's converted links: Relations, extended by C8, with the
    projects whose manifest entries C4 writes (`located`), the E1 lines,
    and the edits removing each `extends`."""

    relations: Relations
    located: list[Located] = field(default_factory=list)
    already: list[str] = field(default_factory=list)
    extends_edits: list = field(default_factory=list)
    #: The projects each axis is inherited from once converted, in load
    #: order, the project itself left out (D2).
    ancestors: dict[str, list[str]] = field(default_factory=dict)
    #: The projects of the family, found on this machine, that inherit
    #: capabilities from this one once converted (D4).
    below: list[str] = field(default_factory=list)

    def edits(self) -> list:
        """`projects:` removed and the links set (only when the file has
        `projects:`), then each `extends` removed."""
        return self.relations.edits() + self.extends_edits


def _parent_links(links: list[Link]):
    """`links` as 4.0's own `ParentLink`s, which `passing`, `find_loop` and
    `load_order_of` take: a plain ID passes every axis, `config` included."""
    from tcw.store.base import AXES, ParentLink
    return [ParentLink(l.id, frozenset(AXES) if l.inherit is None
                       else frozenset(l.inherit)) for l in links]


def _from_parent_links(found) -> list[Link]:
    from tcw.store.base import AXES
    return [Link(l.id, None if set(l.inherit) == set(AXES)
                 else tuple(a for a in EXTENDED_AXES if a in l.inherit)) for l in found]


def _extends_listed_child(member, child_id: str) -> bool:
    """Design 6.1: whether `member`, in either form, extends `child_id` as
    its listed child; once migrated, it has `child_id` among its parents and
    no longer lists it as a child."""
    from tcw.migrate.legacy import relations_3x
    if member.three_x:
        listed = {r.id for r in relations_3x(member.raw, ".")[0] if r.kind == "children"}
        extends = extended_by(member.raw)
        return child_id in listed and any(child_id in ids for ids in extends.values())
    from tcw.store.links import parse_parents
    parents = parse_parents(member.raw.get("parents"), ".")[0] or []
    children = member.raw.get("children") or []
    return any(l.id == child_id for l in parents) and child_id not in children


class _Converter:
    """C3 and C8 over a family, one project at a time, each related 3.x
    project's links predicted by the same conversion (Design 6.1)."""

    def __init__(self, family):
        self.family = family
        self.memo: dict[str, list[Link]] = family.predicted
        self.absent: set[str] = set()
        self.busy: set[str] = set()

    def links_of(self, project_id: str) -> list[Link]:
        """`project_id`'s parent links in 4.0: its own when migrated, the
        predicted ones when 3.x; none for a project not here."""
        if project_id in self.memo:
            return self.memo[project_id]
        if project_id in self.busy:
            return []
        member = self.family.quiet(project_id)
        if member is None:
            self.absent.add(project_id)
            return []
        if not member.three_x:
            from tcw.store.links import parse_parents
            found = _from_parent_links(parse_parents(member.raw.get("parents"), ".")[0]
                                       or [])
        else:
            self.busy.add(project_id)
            try:
                found = self.convert(member).relations.parents
            finally:
                self.busy.discard(project_id)
        self.memo[project_id] = found
        return found

    def graph(self, start: str, own: list[Link]) -> dict:
        """The parent links of `start`, given as `own`, and of every project
        above it, as 4.0's helpers take them."""
        links = {start: _parent_links(own)}
        frontier = [l.id for l in own]
        while frontier:
            pid = frontier.pop()
            if pid in links:
                continue
            found = self.links_of(pid)
            links[pid] = _parent_links(found)
            frontier += [l.id for l in found]
        return links

    def ancestors(self, project_id: str) -> set[str]:
        graph = self.graph(project_id, self.links_of(project_id))
        return {pid for pid in graph if pid != project_id}

    def convert(self, subject) -> Links:
        """`subject`'s links: C3 (with Design 6.1's drop of a parent that
        extends it as its listed child), then each `extends` entry by E1 to
        E5, taxonomy first, each in the order written."""
        from tcw.store.base import find_loop, passing
        rel = ROOT_CONFIG if subject.three_x else SENTINEL
        relations = plan_relations(rel, subject.raw)
        out = Links(relations)
        if relations.blockers:
            return out
        by_id = {r.id: r for r in relations.entries}
        upstreams = {r.id for r in relations.entries if r.kind == "upstream"}
        for link in list(relations.parents):
            if by_id.get(link.id) is None or by_id[link.id].kind != "parent":
                continue
            parent = self.family.quiet(link.id)
            if parent is not None and _extends_listed_child(parent, subject.id):
                relations.parents.remove(link)
                relations.reports.append(Report(
                    "D6", rel, f"projects.parent.{link.id}: dropped; '{link.id}' extends "
                               f"this project as its listed child, which TCW 4 writes as "
                               f"this project being one of its parents"))
        extends = extended_by(subject.raw)
        for axis in EXTENDED_AXES:
            for target in extends[axis]:
                self._classify(subject, out, axis, target, upstreams, rel)
        if not out.relations.blockers:
            graph = self.graph(subject.id, relations.parents)
            loop = find_loop(graph, [subject.id])
            if loop is not None:
                relations.blockers.append(Blocker(
                    "B4", rel, f"extends: the parent links it converts to make a loop: "
                               f"{' -> '.join(loop)}", "remove one of the extends entries "
                                                       "that make the loop, then run "
                                                       "'tcw migrate' again"))
        named = {l.id for l in relations.parents} | set(relations.children)
        for entry in relations.entries:
            if entry.id in named and all(l.relation.id != entry.id for l in out.located):
                out.located.append(Located(entry, subject.folder))
        out.located = [l for l in out.located if l.relation.id in named]
        return out

    def _classify(self, subject, out: Links, axis: str, target: str, upstreams: set,
                  rel: str) -> None:
        from tcw.store.base import passing
        relations = out.relations
        key = f"{axis}.extends"
        if target in upstreams:                                             # E2
            return
        if target in relations.children:                                    # E3
            relations.children.remove(target)
            self._add(relations, Link(target, (axis,)), axis)
            relations.reports.append(Report(
                "D6", rel, f"projects.children.{target}: dropped; {key} names it, so "
                           f"'{target}' becomes a parent passing {axis} instead"))
            return
        graph = self.graph(subject.id, relations.parents)
        if target in passing(axis, subject.id, graph):                      # E1
            out.already.append(f"{key}: '{target}' is already inherited through "
                               f"parents")
            return
        absent = sorted(self.absent & set(graph))
        if absent:
            for pid in absent:
                self.family.member(pid, f"{key}: E1", rel)
            relations.blockers += [b for b in self.family.blockers
                                   if b not in relations.blockers]
            return
        member = self.family.member(target, f"{key}: E4", rel)
        if member is None:
            if not self.family.blockers or self.family.place(target) is None:
                relations.blockers.append(Blocker(
                    "B14", rel, f"{key}: names project '{target}', which no projects: "
                                f"entry of the family names; TCW 3 refused it too",
                    "remove the entry, or name the project under projects:, then run "
                    "'tcw migrate' again"))
            relations.blockers += [b for b in self.family.blockers
                                   if b not in relations.blockers]
            return
        if subject.id in self.ancestors(target) and target not in relations.children:
            relations.blockers.append(Blocker(                                # E5
                "B4", rel, f"{key}: '{target}' is a descendant of this project and not "
                           f"its listed child; TCW 4 has no link for a project extending "
                           f"its descendant", "remove the entry, then run 'tcw migrate' "
                                              "again"))
            return
        self._add(relations, Link(target, (axis,)), axis)                   # E4
        placed = self.family.place(target)
        if placed is not None:
            out.located.append(Located(placed.relation, self.family.base_of(placed),
                                       placed.folder if placed.here else None))

    def _add(self, relations: Relations, link: Link, axis: str) -> None:
        """A new parent appended, or `axis` added to the entry already made
        for it; a new one that is an ancestor of an existing parent goes
        before the first such parent, so that C3 keeps its order."""
        for index, existing in enumerate(relations.parents):
            if existing.id == link.id:
                relations.parents[index] = existing.with_axis(axis)
                return
        at = len(relations.parents)
        for index, existing in enumerate(relations.parents):
            if link.id in self.ancestors(existing.id):
                at = index
                break
        relations.parents.insert(at, link)


def plan_links(root: Path, project_id: str, mapping: dict, family) -> Links:
    """The active project's links (C3, C8), its D1 and D8 reports, and the
    edits of its shared file: `projects:` and each `extends` removed,
    `parents:` and `children:` set."""
    from tcw.store.base import load_order_of, passing
    from tcw.store.config_edit import Remove
    converter = _Converter(family)
    out = converter.convert(family.active)
    relations = out.relations
    rel = ROOT_CONFIG if family.active.three_x else SENTINEL
    if relations.blockers:
        return out
    graph = converter.graph(project_id, relations.parents)
    order = load_order_of(project_id, graph, missing=frozenset(converter.absent))
    if order.warning:
        relations.reports.append(Report("D8", rel, order.warning))
    relations.reports += _d1(rel, project_id, mapping, graph, family, converter)
    out.ancestors = {axis: [pid for pid in order.ids if pid != project_id
                            and pid in passing(axis, project_id, graph)]
                     for axis in EXTENDED_AXES}
    out.below = _below(project_id, family, converter, relations.children)
    # After `_below`, which has placed every project the 3.x walk reaches.
    relations.reports += still_3x_reports(family, order.ids)
    out.extends_edits = [Remove(axis, "extends") for axis in EXTENDED_AXES
                         if isinstance(mapping.get(axis), dict)
                         and "extends" in mapping[axis]]
    return out


def _below(project_id: str, family, converter, children: list[str]) -> list[str]:
    """The projects that inherit capabilities from `project_id` once the
    family is converted: its listed children, and each project the 3.x
    registry walk reaches from it whose converted links pass capabilities
    from it (D4's middle project, which 3.x did not apply its overrides
    below)."""
    from tcw.store.base import passing
    family._walk_to("\0")                  # place every project the walk reaches
    out = list(children)
    for pid in list(family.placed):
        if pid in out or pid == project_id or family.quiet(pid) is None:
            continue
        graph = converter.graph(pid, converter.links_of(pid))
        if project_id in passing("capabilities", pid, graph):
            out.append(pid)
    return out


def _d1(rel: str, project_id: str, mapping: dict, graph: dict, family,
        converter) -> list[Report]:
    """D1: the projects and axes newly inherited, and each key of
    `INHERITED_KEYS` a parent passing configuration sets and this project
    does not."""
    from tcw.config import INHERITED_KEYS
    from tcw.store.base import passing
    out = []
    extends = extended_by(mapping)
    for axis in EXTENDED_AXES:
        new = sorted(passing(axis, project_id, graph) - {project_id} - set(extends[axis]))
        if new:
            out.append(Report("D1", rel, f"parents: now inherits {axis} from "
                                         f"{', '.join(repr(n) for n in new)}, which "
                                         f"TCW 3 did not pass to this project"))
    work = mapping.get("work") if isinstance(mapping.get("work"), dict) else {}
    for pid in sorted(passing("config", project_id, graph) - {project_id}):
        member = family.quiet(pid)
        their = member.raw.get("work") if member is not None else None
        if not isinstance(their, dict):
            continue
        for dotted_key in INHERITED_KEYS:
            key = dotted_key.split(".", 1)[1]
            if key not in their:
                continue
            if key not in work or not isinstance(their[key], dict):
                paths = [] if key in work else [()]
            else:
                # `work.jira` is merged key by key (S109 Design 3.1-3.3).
                mine = work[key] if isinstance(work[key], dict) else {}
                paths = [path for path, value in _leaves(their[key])
                         if not isinstance(value, dict) and not any(
                             isinstance(p, int) for p in path)
                         and _at(mine, path) is _MISSING]
            for path in paths:
                shown = ".".join(("work", key, *map(str, path)))
                out.append(Report("D1", rel, f"{shown}: set by parent '{pid}' and not "
                                             f"by this project, which now inherits it"))
    return out


_MISSING = object()


def _at(mapping: Any, path: tuple) -> Any:
    for part in path:
        if not isinstance(mapping, dict) or part not in mapping:
            return _MISSING
        mapping = mapping[part]
    return mapping


def still_3x_reports(family, order: tuple[str, ...] = ()) -> list[Report]:
    """A8 (Design 2.10, 6.2): each related project found on this machine that
    is still in 3.x form, with the command that migrates it, parents first:
    the active project's ancestors in load order, then the rest in the order
    they were found. Each predicts 4.0's finding that the folder is a 3.x
    project."""
    from tcw.migrate.legacy import ROOT_CONFIG as THREE_X
    seen: dict[str, Path] = {}
    for pid in (*order, *family.placed, *family.read):
        if pid == family.active.id or pid in seen:
            continue
        placed = family.placed.get(pid)
        member = family.read.get(pid)
        folder = member.folder if member is not None else (
            placed.folder if placed is not None and placed.here else None)
        if folder is not None and (Path(folder) / THREE_X).is_file():
            seen[pid] = Path(folder)
    return [Report("A8", str(folder), f"'{pid}' is still a TCW 3.x project; migrate it "
                                      f"with 'tcw -C {folder} migrate'",
                   predicts=(str(folder), "legacy"))
            for pid, folder in seen.items()]


# ---------------------------------------------------------------------------
# Store locations (C5, B6; plan Step 20)


@dataclass
class LocationPlan:
    edits: list = field(default_factory=list)
    reports: list[Report] = field(default_factory=list)
    blockers: list[Blocker] = field(default_factory=list)


def enclosing_project(folder: Path) -> Path | None:
    """The nearest folder at or above `folder` that holds a TCW project in
    either form, or None."""
    from tcw.migrate.legacy import holds_project
    folder = Path(folder)
    for candidate in (folder, *folder.parents):
        if holds_project(candidate):
            return candidate
    return None


def plan_locations(root: Path, mapping: dict, project_id: str,
                   manifests: ManifestPlan) -> LocationPlan:
    """C5: each store location so that 4.0 accepts it and it names the
    folder 3.x resolved: a relative path inside the project unchanged; one
    leading out of it, into a project 4.0 locates from here at the same
    folder, as that project's `.path` address, else kept; an absolute or `~`
    one inside the project as the relative path, inside another project as
    its address (with a personal manifest entry for that project when
    nothing else places it), inside no project B6. A store's `repository`
    is kept unchanged."""
    import os
    from tcw.ids import FolderAddress
    from tcw.migrate import family as family_module
    from tcw.migrate.legacy import store_folder_3x
    from tcw.store.config_edit import SetScalar
    out = LocationPlan()
    here = Path(os.path.realpath(root))
    for component in ("taxonomy", "capabilities", "work"):
        section = mapping.get(component)
        configured = section.get("path") if isinstance(section, dict) else None
        if not isinstance(configured, str):
            continue
        found = store_folder_3x(root, component, section)
        if found.folder is None:
            continue
        absolute = os.path.isabs(configured) or configured.startswith("~")
        if not absolute and found.form != "outside":
            continue
        folder = Path(os.path.realpath(os.path.normpath(found.folder.absolute())))
        if folder == here or here in folder.parents:
            out.edits.append(SetScalar(component, "path", _relative(here, folder)))
            continue
        owner = enclosing_project(folder)
        owner_id = family_module.declared_id(owner) if owner is not None else None
        if owner is None or owner_id is None or owner_id == project_id:
            if absolute:
                out.blockers.append(Blocker(
                    "B6", ROOT_CONFIG, f"{component}.path: {configured} lies inside no "
                                       f"TCW project; TCW 4 takes a store's path relative "
                                       f"to the project, or as a .path address of another "
                                       f"project", "move the store into a project and set "
                                                   "the path to it, then run 'tcw migrate' "
                                                   "again"))
            continue
        owner = Path(os.path.realpath(owner))
        if not _locates(here, owner_id, owner, manifests):
            if not absolute:
                continue                        # kept: 4.0 accepts it as written
            manifests.personal.setdefault(owner_id, {"path": str(owner)})
        rest = folder.relative_to(owner).as_posix()
        address = str(FolderAddress(owner_id, None, "" if rest == "." else rest))
        out.edits.append(SetScalar(component, "path", address))
    return out


def _locates(root: Path, project_id: str, folder: Path, manifests: ManifestPlan) -> bool:
    """Whether 4.0, from the project at `root`, would find `project_id` at
    `folder`: through an entry the run writes, or by its search."""
    import os
    from tcw.migrate import family as family_module
    for entries in (manifests.personal, manifests.shared):
        entry = entries.get(project_id)
        if entry is not None:
            target = Path(entry["path"]).expanduser()
            target = target if target.is_absolute() else root / target
            return Path(os.path.realpath(target)) == folder
    found = family_module.search_4(root, project_id)
    return len(found) == 1 and Path(os.path.realpath(found[0])) == folder


def finish_manifests(root: Path, manifests: ManifestPlan) -> None:
    """The manifests' writes, once every entry is known."""
    steps, blockers = _manifest_writes(Path(root).resolve(), manifests.shared,
                                       manifests.personal)
    manifests.steps = steps
    manifests.blockers += blockers


def clone_entries(root: Path) -> ManifestPlan:
    """Design 2.11, for a project already in 4.0 form: each entry of its
    shared manifest that names a repository, whose folder is not there, and
    for which TCW 3's per-machine clone is on this machine and holds the
    project, gets the personal entry M5 gives the first person, with A6. An
    entry the personal manifest already has is left. The other per-machine
    paths (M1, M4) came from the 3.x shared file and are not recoverable
    from the converted one, so the person writes those by hand, as the
    first person's run said in its A14 lines."""
    import os
    from tcw.migrate import legacy
    from tcw.migrate.family import manifest_entries_4
    from tcw.project_files import LOCAL_MANIFEST, MANIFEST
    from tcw.store.manifest import parse_manifest
    out = ManifestPlan()
    path = Path(root) / MANIFEST
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return out
    entries, problems = parse_manifest(data, path, personal=False)
    if problems:
        return out
    personal = {pid for pid, (_, entry) in manifest_entries_4(root).items()
                if entry.file is not None and Path(str(entry.file)).name ==
                Path(LOCAL_MANIFEST).name}
    for pid, entry in entries.items():
        if entry.url is None or pid in personal:
            continue
        target = Path(os.path.normpath(Path(root) / Path(entry.path).expanduser()))
        if legacy.holds_project(target):
            continue
        repository = legacy.RepoDecl3(entry.url, entry.branch, entry.subfolder or "")
        clone = legacy.cache_folder_3x(Path(root), repository)
        if not legacy.holds_project(clone):
            continue
        out.personal[pid] = {"path": str(clone)}
        out.reports.append(Report(
            "A6", ".tcw/tcw-manifest.local.yaml",
            f"projects.{pid}.path: names TCW 3's clone of '{pid}' at {clone}, a cache "
            f"folder that cleaning tools may empty; moving the clone to {target} and "
            f"deleting this entry keeps it safe"))
    return out
