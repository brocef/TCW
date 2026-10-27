"""Working out the whole migration before anything is written (TCW-116
Design 2.1, 2.2; plan Step 5).

`make_plan` reads the active project's files in either format, asks each
part of the conversion for its steps, reports and blockers, and puts the
steps in the order of Design 2.4. Nothing here writes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from tcw.migrate import config, progress, record, stores
from tcw.errors import TcwError
from tcw.migrate.legacy import (ROOT_CONFIG, Layer3, Layers3, own_jira_layers,
                                read_3x_layers, read_layer_3x)
from tcw.migrate.model import PHASES, Blocker, Move, Plan, Write
from tcw.project_files import (LOCAL_MANIFEST, LOCAL_SENTINEL, SENTINEL, VERSION_KEY,
                               without_version)


@dataclass
class Read:
    """What the plan reads of the active project."""

    root: Path
    layers: Layers3                  # the root files and the user-wide one
    shared4: Layer3                  # .tcw/tcw-config.yaml
    personal4: Layer3                # .tcw/tcw-config.local.yaml
    git: Path | None

    @property
    def shared(self) -> tuple[str, dict]:
        """The shared configuration being converted, and the file it is in:
        the root file when there is one, else `.tcw/`'s."""
        if self.layers.shared.present:
            return ROOT_CONFIG, self.layers.shared.data or {}
        data = self.shared4.data or {}
        return SENTINEL, without_version(data) if VERSION_KEY in data else data

    @property
    def three_x(self) -> bool:
        """The shared configuration is still in 3.x form."""
        return self.layers.shared.present or VERSION_KEY not in (self.shared4.data or {})

    @property
    def work_backend(self) -> str:
        work = self.shared[1].get("work")
        backend = work.get("backend") if isinstance(work, dict) else None
        return "jira" if backend == "jira" else "filesystem"


def read_project(root: Path) -> Read:
    from tcw.store.fs import git_root
    root = Path(root)
    return Read(root, read_3x_layers(root), read_layer_3x(root / SENTINEL, "shared"),
                read_layer_3x(root / LOCAL_SENTINEL, "personal"), git_root(root))


# ---------------------------------------------------------------------------
# The part-1 refusal of part-2 forms (Decided 17)


# ---------------------------------------------------------------------------
# The planned files, checked as 4.0 reads them (B3; Decided 8)

B3_FIX = "correct it in the TCW 3 file it is converted from, then run 'tcw migrate' again"
#: Keys a personal layer may set, which the shared file alone may lack.
_PERSONAL_REQUIRED = (("work", "jira", "credentials"),)


def _refused(rel: str, detail: str) -> Blocker:
    return Blocker("B3", rel, f"TCW 4 would refuse the file as planned: {detail}", B3_FIX)


def planned_file_blockers(root: Path, steps) -> list[Blocker]:
    """B3 for each planned configuration or state file that 4.0's own parser
    of that kind of file refuses, given its planned text; nothing is read
    from the planned paths. The shared file is read as `load_config` reads
    it with no personal layer, so a key a personal layer may set (the Jira
    credentials) is not required of it; the personal file is checked as its
    layer is."""
    from tcw import config as layered
    from tcw import object_folders
    out = []
    for step in steps:
        if not isinstance(step, Write):
            continue
        path = Path(root) / step.path
        if step.path in (SENTINEL, LOCAL_SENTINEL):
            layer = "shared" if step.path == SENTINEL else "personal"
            for problem in layered.parse_project_file_text(step.text, path, layer=layer):
                if problem.file is not None and Path(problem.file) != path:
                    continue
                if problem.message == "required" and any(
                        tuple(problem.key_path[:len(k)]) == k for k in _PERSONAL_REQUIRED):
                    continue
                out.append(_refused(step.path, problem.detail))
        elif path.name in object_folders.STATE_FILES.values():
            try:
                _, problem = object_folders.parse_state_text(step.text, path)
            except yaml.YAMLError as error:
                problem = f"is not valid YAML: {' '.join(str(error).split())}"
            if problem is not None:
                out.append(_refused(step.path, problem))
    return out


# ---------------------------------------------------------------------------
# A planned file git would ignore (B18)

#: The planned files `.tcw/.gitignore` ignores on purpose: never committed.
_PERSONAL = (LOCAL_SENTINEL, LOCAL_MANIFEST, progress.PROGRESS)


def _before_moves(rel: str, moves: list[Move]) -> str:
    """Where the file a later step finds at `rel` is before the moves."""
    for move in moves:
        if rel == move.new:
            return move.old
        if rel.startswith(move.new + "/"):
            return move.old + rel[len(move.new):]
    return rel


def _new_file_sources(root: Path, rel: str, moves: list[Move], config_rel: str
                      ) -> list[str]:
    """What a new file at `rel` comes from: in the project's own folder or
    its `.tcw/`, the shared configuration `config_rel`; anywhere else, such
    as a store object's folder, the files already in its folder before the
    moves (the object's 3.x state file and its other files); for a folder
    that holds only subfolders, the files anywhere below it; and for one
    with no file below it at all, `config_rel`."""
    from tcw.migrate.model import resolve
    from tcw.project_files import TCW_FOLDER
    folder = rel.rpartition("/")[0]
    if folder in ("", TCW_FOLDER):
        return [config_rel]
    before = _before_moves(folder, moves)
    here = resolve(root, before)
    try:
        found = sorted(f"{before}/{entry.name}" for entry in here.iterdir()
                       if entry.is_file())
        if not found:
            found = sorted(f"{before}/{path.relative_to(here).as_posix()}"
                           for path in here.rglob("*") if path.is_file())
    except OSError:
        found = []
    return found or [config_rel]


def _planned_sources(root: Path, steps, config_rel: str) -> dict[str, list[str]]:
    """Each file the steps write or move into that is meant to be committed,
    as the plan names it, with the files it comes from: for a move, the file
    moved; for a write, the files its text was planned from, else the file
    it replaces, else (a new file) `_new_file_sources`."""
    from tcw.migrate.model import resolve
    moves = [step for step in steps if isinstance(step, Move)]
    out: dict[str, list[str]] = {}
    for step in steps:
        if isinstance(step, Write):
            if step.reads:
                found = [(step.path, rel) for rel, _ in step.reads]
            else:
                before = _before_moves(step.path, moves)
                found = [(step.path, source) for source in
                         ([before] if resolve(root, before).is_file()
                          else _new_file_sources(root, step.path, moves, config_rel))]
        elif isinstance(step, Move):
            found = [(f"{step.new}/{inner}", f"{step.old}/{inner}") if inner
                     else (step.new, step.old) for inner, _ in step.files]
        else:
            continue
        for path, source in found:
            if path not in _PERSONAL and source not in out.setdefault(path, []):
                out[path].append(source)
    return out


class _GitFailed(Exception):
    """git could not answer about the work tree `top`; its words are `reason`."""

    def __init__(self, top: Path, reason: str):
        super().__init__(reason)
        self.top, self.reason = top, reason


def _ask_git(top: Path, argv: list[str], listed: str = "", *, ok=(0,)) -> str:
    """git's output for `argv` in the work tree at `top`, given `listed` on
    its standard input; git's location variables are never passed on
    (TCW-115 Design 7.8)."""
    import subprocess
    from tcw.store.fs import git_environment
    try:
        done = subprocess.run(["git", "-C", str(top), *argv], input=listed,
                              capture_output=True, text=True, check=False,
                              env=git_environment(None))
    except OSError as error:
        raise _GitFailed(top, str(error)) from None
    if done.returncode not in ok:
        raise _GitFailed(top, " ".join(done.stderr.split()) or f"exit {done.returncode}")
    return done.stdout


def _tracked(top: Path, rels: list[str]) -> set[str]:
    """Those of `rels`, relative to the work tree at `top`, that git tracks."""
    out: set[str] = set()
    for at in range(0, len(rels), 500):
        out |= set(_ask_git(top, ["--literal-pathspecs", "ls-files", "-z", "--",
                                  *rels[at:at + 500]]).split("\0"))
    return out & set(rels)


def _git_ignoring(top: Path, rels: list[str], *, tracked: bool = False,
                  settings: tuple[str, ...] = ()) -> dict[str, tuple[str, int, str]]:
    """The rule git would ignore each of `rels` by, in the git work tree at
    `top`, as `(source, line, pattern)`; a path no rule ignores is left out,
    and so is one git tracks unless `tracked`. A path need not exist, but a
    folder is known to be one only if it does."""
    if not rels:
        return {}
    settings = tuple(arg for setting in settings for arg in ("-c", setting))
    fields = _ask_git(top, [*settings, "check-ignore", "-v", "-z", "--stdin",
                            *(["--no-index"] if tracked else [])],
                      "".join(f"{rel}\0" for rel in rels), ok=(0, 1)).split("\0")
    out = {}
    for at in range(0, len(fields) - 3, 4):
        source, line, pattern, rel = fields[at:at + 4]
        if pattern.startswith("!"):
            continue                         # a rule that re-includes the path
        out[rel] = (source, int(line), pattern)
    return out


def _reinclude(top: Path, path: Path, source: str, pattern: str) -> list[str] | None:
    """The lines that re-include `path` after the rule `pattern` of a
    `.gitignore` file, relative to that file's folder: `!/<folder>/` for the
    shortest folder above it the rule still ignores, until none is left, then
    `!/<path>` if the rule still ignores the file itself. Each is found by
    asking git in an empty repository holding only that rule and the lines
    so far, whose folders exist there, so a rule only for folders matches
    one the run has yet to make. None for a rule kept anywhere else, such as
    `.git/info/exclude`, or when git cannot be asked."""
    import tempfile
    if Path(source).name != ".gitignore" or Path(source).is_absolute():
        return None
    base = Path(source).parent
    try:
        inside = path.relative_to(top / base).parts
    except ValueError:
        return None
    prefix = "" if base == Path(".") else f"{base.as_posix()}/"
    rel = "/".join(inside)
    above = ["/".join(inside[:n]) for n in range(1, len(inside))]
    lines: list[str] = []
    with tempfile.TemporaryDirectory() as scratch:
        work = Path(scratch)
        try:
            _ask_git(work, ["init", "-q", "--template="])
            (work / prefix / rel).parent.mkdir(parents=True, exist_ok=True)
            # One line for each folder above and one for the file, then a
            # last round to confirm git no longer ignores it.
            for _ in range(len(inside) + 1):
                (work / source).write_text("".join(f"{line}\n" for line in [pattern, *lines]),
                                           encoding="utf-8")
                rules = _git_ignoring(work, [prefix + f for f in [*above, rel]], tracked=True,
                                      settings=(f"core.excludesFile={work / 'none'}",))
                folder = next((f for f in above if prefix + f in rules), None)
                if folder is not None:
                    lines.append(f"!/{folder}/")
                elif prefix + rel in rules:
                    lines.append(f"!/{rel}")
                else:
                    return lines or None
        except (_GitFailed, OSError):
            return None
    return None


def _shown(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _quoted(lines: list[str]) -> str:
    quoted = [f"'{line}'" for line in lines]
    if len(quoted) == 1:
        return f"the line {quoted[0]}"
    return f"the lines {', '.join(quoted[:-1])} and {quoted[-1]}, in that order,"


def ignored_blockers(root: Path, steps, config_rel: str = ROOT_CONFIG
                     ) -> tuple[list[Blocker], list[str]]:
    """B18 for each planned file meant to be committed that git would ignore
    where it is written, when a file it comes from (`_planned_sources`) is
    one git tracks; such as the whole of `.tcw/` under a root `.gitignore`
    that starts with `/*` and re-includes only what is tracked (an
    allowlist), while the tracked `tcw-config.yaml` is deleted. A file that
    comes only from files git does not track was never committed, so it is
    not a reason. A file outside any git work tree is not checked. Also the
    summary's lines for each work tree git could not answer about, where
    nothing is claimed."""
    from tcw.migrate.model import resolve
    from tcw.store.fs import git_root
    root = Path(root).resolve()
    tops: dict[Path, Path | None] = {}

    def located(rel: str) -> tuple[Path, str] | None:
        path = resolve(root, rel)
        path = path if path.is_absolute() else path.resolve()
        here = path.parent
        while not here.exists() and here != here.parent:
            here = here.parent
        if here not in tops:
            top = git_root(here)
            tops[here] = top.resolve() if top is not None else None
        top = tops[here]
        if top is None:
            return None
        try:
            return top, path.parent.resolve().relative_to(top).joinpath(path.name).as_posix()
        except ValueError:
            return None

    notes: list[str] = []
    failed: list[Path] = []

    def failure(error: _GitFailed) -> None:
        if error.top not in failed:
            failed.append(error.top)
            notes.append(f"the files written in {error.top} were not checked against "
                         f"git's ignore rules: {error.reason}")

    planned = _planned_sources(root, steps, config_rel)
    sources: dict[Path, set[str]] = {}
    for found in planned.values():
        for at in filter(None, map(located, found)):
            sources[at[0]] = sources.get(at[0], set()) | {at[1]}
    tracked: set[tuple[Path, str]] = set()
    for top, rels in sources.items():
        try:
            tracked |= {(top, rel) for rel in _tracked(top, sorted(rels))}
        except _GitFailed as error:
            failure(error)
    by_top: dict[Path, list[tuple[str, str]]] = {}
    for rel, found in planned.items():
        at = located(rel)
        if at is not None and any(located(source) in tracked for source in found):
            by_top.setdefault(at[0], []).append((rel, at[1]))
    out = []
    for top, found in by_top.items():
        if top in failed:
            continue
        try:
            rules = _git_ignoring(top, [inner for _, inner in found])
        except _GitFailed as error:
            failure(error)
            continue
        for rel, inner in found:
            if inner not in rules:
                continue
            source, line, pattern = rules[inner]
            shown = _shown(root, top / source)
            fix = _reinclude(top, top / inner, source, pattern)
            how = (f"add {_quoted(fix)} after that line of {shown}" if fix else
                   "change that rule so git does not ignore it")
            out.append(Blocker(
                "B18", rel, f"git would ignore it, by {shown}:{line}:{pattern}, so "
                            f"committing what git shows would leave it out",
                f"{how}, then run 'tcw migrate' again"))
    return out, notes


# ---------------------------------------------------------------------------
# Another checkout of a repository the project sits in (B19; Design 6.6)

B19_FIX = ("run 'tcw migrate' in that folder itself, or make the copy by cloning or by "
           "copying the folders, where a relative store path is read where it lands")


def other_checkout_blockers(root: Path, steps) -> list[Blocker]:
    """B19, once for each folder the plan would change files in that is a
    checkout of a repository the project sits in (its own, or one holding
    it) other than the checkout it sits in. A run in a linked checkout
    changes files only there (Design 6.6), but 3.x read a relative store
    path that leaves a linked checkout from beside its main checkout. A copy
    made of linked checkouts, one inside another, would so plan its store's
    changes in the folders it was copied from."""
    from tcw.migrate.model import Move
    from tcw.migrate.report import checkouts
    from tcw.store.project import _git_lines
    base = Path(os.path.realpath(root))
    common: dict[Path, Path | None] = {}

    def repository(top: Path) -> Path | None:
        if top not in common:
            out = _git_lines(top, "rev-parse", "--path-format=absolute",
                             "--git-common-dir")
            common[top] = Path(out[0]).resolve() if out else None
        return common[top]
    mine = {repository(top): top for top in reversed(checkouts(base))}
    mine.pop(None, None)
    found: dict[Path, set[str]] = {}
    for step in steps:
        for rel in ((step.old, step.new) if isinstance(step, Move) else (step.path,)):
            target = Path(os.path.normpath(base / rel))
            tops = checkouts(target.parent)
            top = tops[0] if tops else None
            if top is None or top in mine.values():
                continue
            if repository(top) in mine:
                found.setdefault(top, set()).add(rel)
    return [Blocker("B19", str(top),
                    f"the run would change {len(rels)} "
                    f"{'file' if len(rels) == 1 else 'files'} here, in another checkout "
                    f"of the repository checked out at {mine[repository(top)]}: TCW 3 "
                    f"read a relative store path that leaves a linked checkout from "
                    f"beside its main checkout", B19_FIX)
            for top, rels in found.items()]


# ---------------------------------------------------------------------------
# The Jira half (Decided 19)


def plan_jira_half(root: Path, project_id: str | None, *, jira_backed: bool,
                   no_jira: bool):
    """The Jira half of a run, fresh or following a progress record, or None
    under `--no-jira` and for a project whose work is kept in files. The only
    import of `tcw.migrate.jira`, made after those two tests, so a run with
    the flag never builds a Jira client or backend. A Jira failure raises the
    backend's own error."""
    if no_jira or not jira_backed or not project_id:
        return None
    from tcw.migrate import jira
    return jira.half(root, project_id)


def no_jira_line(root: Path, project_id: str | None) -> str:
    """The summary's line for a Jira-backed project run with `--no-jira`
    (Design 1.1), its Jira project read from the configuration alone."""
    jira = own_jira_layers(root).jira
    key = jira.get("project") if isinstance(jira, dict) else None
    board = f"Jira project {key}" if key else "its Jira project"
    return (f"tickets not converted (--no-jira): the TCW Item of every ticket of "
            f"{board} whose TCW Project is '{project_id}' and that holds a 3.x "
            f"value; run 'tcw migrate' to convert them")


# ---------------------------------------------------------------------------
# The plan


def _links(read: Read, mapping: dict):
    """The family of a 3.x shared file, and its links (C3, C8) when it has
    `projects:` or an `extends`."""
    has = "projects" in mapping or any(
        isinstance(mapping.get(axis), dict) and "extends" in mapping[axis]
        for axis in config.EXTENDED_AXES)
    project_id = mapping.get("id")
    if not (read.three_x and isinstance(project_id, str)):
        return config.Links(config.Relations()), None
    from tcw.migrate.family import read_family
    found = read_family(read.root, project_id, mapping)
    if not has:
        return config.Links(config.Relations()), found
    return config.plan_links(read.root, project_id, mapping, found), found


def make_plan(root: Path, *, no_jira: bool = False) -> Plan:
    """Everything one run will do and say, worked out before any write."""
    read = read_project(root)
    rel, mapping = read.shared
    links, family = _links(read, mapping)
    relations = links.relations
    project_id = mapping.get("id") if isinstance(mapping.get("id"), str) else None
    if project_id and read.three_x:
        manifests = config.plan_manifests(read.root, links.located, project_id)
    elif project_id:
        manifests = config.clone_entries(read.root)                 # Design 2.11
    else:
        manifests = config.ManifestPlan()
    locations = config.plan_locations(read.root, mapping, project_id, manifests) \
        if project_id and read.three_x else config.LocationPlan()
    config.finish_manifests(read.root, manifests)
    conversions = (("C3",) if relations.present else ()) + (
        ("C8",) if links.extends_edits else ()) + (("C5",) if locations.edits else ())
    shared = config.plan_file(read.root, read.layers.shared, read.shared4, shared=True,
                              edits=tuple(links.edits() + locations.edits),
                              conversions=conversions)
    personal = config.plan_file(read.root, read.layers.personal, read.personal4,
                                shared=False)
    plan = Plan(shared.project, read.work_backend)
    plan.blockers = (relations.blockers + shared.blockers
                     + personal.blockers)
    steps = shared.steps + personal.steps
    reports = relations.reports + shared.reports + personal.reports
    plan.summary += [f"a comment is dropped from {line}" for line in shared.dropped]
    plan.summary += links.already
    plan.blockers += manifests.blockers + locations.blockers
    reports += manifests.reports + locations.reports
    steps += manifests.steps
    if shared.project:
        found = stores.plan_stores(read.root, read.shared[1], shared.project,
                                   three_x=read.three_x, work_backend=read.work_backend,
                                   family=family, ancestors=links.ancestors,
                                   middle=bool(links.below))
        plan.owners = found.owners
        plan.blockers += found.blockers
        reports += found.reports
        written = record.plan_record(read.root, found.ids, found.moved,
                                     removed=relations.removed)
        # B5 for a source an override's pointer must be read in (C14).
        plan.blockers += [b for b in (family.blockers if family is not None else [])
                          if b not in plan.blockers]
        steps = ([written] if written else []) + steps + found.steps
    if steps and read.git is not None:
        steps += config.plan_ignore(read.root)
    plan.steps = sorted(steps, key=lambda step: PHASES.index(step.phase))
    plan.summary += stores.left_elsewhere(read.root, read.shared[1], plan.steps, read.git)
    from tcw.store.fs import passed_over_stores
    plan.summary += passed_over_stores(read.root, read.shared[1])
    plan.blockers += planned_file_blockers(read.root, plan.steps)
    if read.git is not None:
        ignored, notes = ignored_blockers(read.root, plan.steps, read.shared[0])
        plan.blockers += ignored
        plan.summary += notes
        plan.git_notes = notes
    plan.blockers += other_checkout_blockers(read.root, plan.steps)
    jira_backed = read.work_backend == "jira"
    if not plan.blockers:
        # A blocker refuses the run whatever Jira holds, so Jira is asked
        # only when there is none (decided by the implementing agent).
        try:
            plan.half = plan_jira_half(read.root, shared.project, jira_backed=jira_backed,
                                       no_jira=no_jira)
        except TcwError as error:
            plan.jira_failure = error
    if plan.half is not None:
        plan.tickets = list(plan.half.tickets)
        plan.blockers += plan.half.blockers
    if plan.steps or plan.blockers or plan.tickets:
        plan.reports = (reports + config.user_reports(read.layers.user)
                        + config.ignore_reports(read.root)
                        + config.worktree_reports(read.root)
                        + (plan.half.reports if plan.half is not None else []))
    if no_jira and jira_backed and plan.steps:
        plan.summary.append(no_jira_line(read.root, shared.project))
    return plan
