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
    its `.tcw/` place (`new`). `edits` are the structural edits part 2's
    conversions make to the shared file (C3, C5, C8), after the renames."""
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
    (`base`), against which a relative locator is read."""

    relation: Any
    base: Path


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
    M6), each planned manifest checked by 4.0's parser (B3). An entry is
    decided from the declared locations, never from `TCW_PROJECT_<ID>`
    (A11), and M6 compares only with what 4.0's search from this project
    would find, never a parent's manifests."""
    from tcw.migrate import family as family_module, legacy
    root = Path(root).resolve()
    out = ManifestPlan()
    for item in located:
        _plan_entry(root, item, out, legacy, family_module)
    out.steps, more = _manifest_writes(root, out.shared, out.personal)
    out.blockers += more
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
    if repo is None:
        found = family_module.search_4(root, pid)
        if declared is not None and len(found) == 1 and found[0] == declared:
            return                                      # M6
    shared: dict = {}
    personal: dict = {}
    locator = relation.locator
    subfolder = repo.path if repo is not None and repo.path else None
    m5 = None
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
        out.personal.setdefault(pid, personal)


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
