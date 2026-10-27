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


def _committed_paths(steps) -> list[str]:
    """Each file the steps write or move into that is meant to be committed,
    as the plan names it."""
    out: list[str] = []
    for step in steps:
        if isinstance(step, Write):
            found = [step.path]
        elif isinstance(step, Move):
            found = [f"{step.new}/{inner}" if inner else step.new
                     for inner, _ in step.files]
        else:
            continue
        out += [path for path in found if path not in _PERSONAL and path not in out]
    return out


def _git_ignoring(top: Path, paths: list[Path], *, tracked: bool = False
                  ) -> dict[Path, tuple[str, int, str]]:
    """The rule git would ignore each of `paths` by, in the git work tree at
    `top`, as `(source, line, pattern)`; a path no rule ignores is left out,
    and so is one git tracks unless `tracked`. A path need not exist."""
    import subprocess
    if not paths:
        return {}
    listed = "".join(f"{path.relative_to(top).as_posix()}\0" for path in paths)
    try:
        done = subprocess.run(["git", "-C", str(top), "check-ignore", "-v", "-z", "--stdin",
                               *(["--no-index"] if tracked else [])], input=listed, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return {}
    if done.returncode not in (0, 1):
        return {}
    fields = done.stdout.split("\0")
    out = {}
    for at in range(0, len(fields) - 3, 4):
        source, line, pattern, path = fields[at:at + 4]
        if pattern.startswith("!"):
            continue                         # a rule that re-includes the path
        out[top / path] = (source, int(line), pattern)
    return out


def _reinclude(top: Path, path: Path, source: str, line: int, pattern: str) -> str | None:
    """The line that re-includes `path` after the rule in a `.gitignore`
    file: `!/<folder>/` for the shortest folder above it the same rule
    ignores, else `!/<path>`, relative to that file's folder; None for a
    rule kept anywhere else, such as `.git/info/exclude`."""
    if Path(source).name != ".gitignore" or Path(source).is_absolute():
        return None
    base = (top / source).parent
    inside = path.relative_to(base).parts
    folders = [base.joinpath(*inside[:n]) for n in range(1, len(inside))]
    # A folder holding tracked files is matched by the rule all the same.
    rules = _git_ignoring(top, folders, tracked=True)
    for folder in folders:
        if rules.get(folder) == (source, line, pattern):
            return f"!/{folder.relative_to(base).as_posix()}/"
    return f"!/{path.relative_to(base).as_posix()}"


def _shown(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def ignored_blockers(root: Path, steps) -> list[Blocker]:
    """B18 for each planned file meant to be committed that git would ignore
    where it is written, such as the whole of `.tcw/` under a root
    `.gitignore` that starts with `/*` and re-includes only what is tracked
    (an allowlist). Committing what git then shows would leave the 4.0 files
    out while the 3.x ones are deleted. A file outside any git work tree is
    not checked."""
    from tcw.migrate.model import resolve
    from tcw.store.fs import git_root
    root = Path(root).resolve()
    by_top: dict[Path, list[tuple[str, Path]]] = {}
    for rel in _committed_paths(steps):
        path = resolve(root, rel)
        path = path if path.is_absolute() else path.resolve()
        here = path.parent
        while not here.exists() and here != here.parent:
            here = here.parent
        top = git_root(here)
        if top is None:
            continue
        top = top.resolve()
        try:
            path = top / path.resolve().relative_to(top)
        except ValueError:
            continue
        by_top.setdefault(top, []).append((rel, path))
    out = []
    for top, found in by_top.items():
        rules = _git_ignoring(top, [path for _, path in found])
        for rel, path in found:
            if path not in rules:
                continue
            source, line, pattern = rules[path]
            shown = _shown(root, top / source)
            fix = _reinclude(top, path, source, line, pattern)
            how = (f"add the line '{fix}' after that line of {shown}" if fix else
                   "change that rule so git does not ignore it")
            out.append(Blocker(
                "B18", rel, f"git would ignore it, by {shown}:{line}:{pattern}, so "
                            f"committing what git shows would leave it out",
                f"{how}, then run 'tcw migrate' again"))
    return out


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
    plan.blockers += planned_file_blockers(read.root, plan.steps)
    if read.git is not None:
        plan.blockers += ignored_blockers(read.root, plan.steps)
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
