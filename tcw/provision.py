"""`tcw project provision`'s projects pass (TCW-115 Design 7.3 to 7.14): fetch
the projects the active project's family names that are not on this machine,
round by round, each into the folder its deciding manifest entry gives.

Deployment layer: what it fetches and where comes from manifests, which only
the filesystem registry has (Design 8.1). Everything it says goes to standard
error.

A **round** is the projects one reading of the registry finds not on this
machine, less those this run already attempted. Every check is made for the
whole round before any remote of it is contacted, and again for each project
just before its clone writes anything; then the registry is read again.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from tcw import exit as codes
from tcw.errors import ProjectGraphError, UnknownProject, Unreachable

#: The two manifests of a project, the personal one first, as the lookup
#: reads them (TCW-107 Design 2.2 (a)).
OWN_MANIFESTS = (".tcw/tcw-manifest.local.yaml (this machine) or "
                 ".tcw/tcw-manifest.yaml (everyone)")


class RepositoryUnknown(Exception):
    """A folder is inside a git repository (a `.git` entry is at it or above
    it), but git could not say which one (Design 7.8)."""


def same_folder(a, b) -> bool:
    """Whether `a` and `b` are one folder: by device and inode when both
    exist, else by the whole components of their resolved paths (Design 7.8,
    "Folders are compared by identity")."""
    from tcw.store.project import _below
    return _below(Path(os.path.realpath(a)), Path(os.path.realpath(b))) == Path(".")


def _below_folder(path, top) -> Path | None:
    from tcw.store.project import _below
    return _below(Path(os.path.realpath(path)), Path(os.path.realpath(top)))


def repository_top(root: Path) -> Path | None:
    """The top folder of the git repository holding `root`, or None when no
    folder from `root` up holds a `.git` entry (plan choice 24). Inside a git
    submodule, the submodule's own top. Raises `RepositoryUnknown` when there
    is a `.git` entry but git cannot answer."""
    from tcw.store.fs import _git, _git_reason
    root = Path(root)
    if not any(os.path.lexists(folder / ".git") for folder in (root, *root.parents)):
        return None
    try:
        done = _git(["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                    capture_output=True, text=True)
    except FileNotFoundError:
        raise RepositoryUnknown("git is not installed") from None
    if done.returncode != 0 or not done.stdout.strip():
        raise RepositoryUnknown(_git_reason(done) or f"git exited {done.returncode}")
    return Path(os.path.realpath(done.stdout.strip()))


@dataclass
class Planned:
    """A project a round will fetch, with what its checks found."""

    id: str
    placement: object
    target: Path                       # the resolved repository folder
    trusted: bool
    bound: Path | None = None
    comes_with: str | None = None      # the project whose clone brings it (7.7)
    group: frozenset = frozenset()


@dataclass
class _Run:
    root: Path
    prefix: str
    home: Path
    out: object = sys.stderr
    fetched: int = 0
    failed: int = 0
    kept: dict = field(default_factory=dict)       # id -> (folder, asked_by)
    cloned: dict = field(default_factory=dict)     # id -> resolved repository folder
    attempted: set = field(default_factory=set)

    def say(self, line: str) -> None:
        print(line, file=self.out)

    def refuse(self, line: str) -> None:
        print(f"{self.prefix}: {line}", file=self.out)
        self.failed += 1


def _written(placement) -> str:
    return placement.entry.path


def _file(placement):
    return placement.entry.file


def _way_out(placement, active_root: Path) -> str:
    """Design 7.8's way out: a manifest the lookup reads before `<file>`."""
    pid, asker = placement.id, placement.asked_by
    if same_folder(asker, active_root):
        return f"add an entry for '{pid}' to {OWN_MANIFESTS} in this project; they are read first"
    command = f"'tcw -C {asker} project provision {pid}'"
    first = ""
    if placement.owner is not None and same_folder(placement.owner, asker):
        first = (f"read {_file(placement)}; to fetch it as written, run {command}, where "
                 f"that manifest is the active project's own; ")
    return (f"{first}to place it elsewhere, add an entry for '{pid}' to "
            f"{asker}/.tcw/tcw-manifest.local.yaml, which is read before "
            f"{_file(placement)}, and run {command}")


def _hidden_below(bound: Path, home: Path) -> bool:
    inside = _below_folder(bound, home)
    return inside is not None and any(part.startswith(".") for part in inside.parts)


def _bound_problem(placement, active_root: Path, cloned: dict, home: Path
                   ) -> tuple[str | None, Path | None, bool, Path | None]:
    """Design 7.8 for one entry, as plan choice 8 orders it: `(problem,
    target, trusted, bound)`, `target` being the resolved repository folder
    the clone goes to and `problem` a refusal, or None."""
    pid = placement.id
    written = Path(placement.repository_path)
    file = _file(placement)
    if same_folder(placement.owner, active_root):
        return None, Path(os.path.realpath(written)), True, None
    shown = Path(os.path.realpath(written))
    way_out = _way_out(placement, active_root)

    def outside(bound) -> str:
        return (f"{pid}: {file} places it at {shown}, outside {bound}; a manifest that "
                f"is not this project's own may place a clone only in a folder directly "
                f"inside {bound}; {way_out}")

    raw = placement.entry.path
    owner = Path(placement.owner)
    if Path(raw).is_absolute() or raw.startswith("~"):
        return outside(_bound_of(owner, active_root, cloned, pid)[0] or owner.parent), \
            None, False, None
    bound, unknown = _bound_of(owner, active_root, cloned, pid)
    if unknown is not None:
        return (f"{pid}: {file} places it at {shown}, but git could not say which "
                f"repository holds '{owner}' ({unknown}), so the folder a manifest that is "
                f"not this project's own may use is not known; {way_out}"), None, False, None
    if written.name in ("", ".", ".."):
        return outside(bound), None, False, bound
    try:
        held = Path(os.path.realpath(written.parent, strict=True))
    except OSError:
        return outside(bound), None, False, bound
    target = held / written.name
    if not same_folder(held, bound) or target.name.startswith("."):
        return outside(bound), None, False, bound
    h = Path(os.path.realpath(home))
    if (any(same_folder(bound, a) for a in (h, *h.parents)) or bound == bound.parent
            or _hidden_below(bound, h)):
        return (f"{pid}: {file} places it at {target}; '{owner}' sits in {bound}, which is "
                f"the home folder, a folder above it, or inside a hidden folder below it, so "
                f"a manifest that is not this project's own may not place a clone there; "
                f"{way_out}"), None, False, bound
    return None, target, False, bound


def _bound_of(owner: Path, active_root: Path, cloned: dict, owner_id_hint=None
              ) -> tuple[Path | None, str | None]:
    """The bound of manifests `owner` holds, and git's reason when it cannot
    be known (plan choice 8: the owner's repository folder `R`, the first
    that applies, and `B` its parent)."""
    from tcw.store.project import worktree_anchors
    anchors = worktree_anchors(Path(active_root))
    repository = None
    if anchors is not None and _below_folder(owner, anchors[0]) is not None:
        repository = anchors[1]
    if repository is None:
        for folder in cloned.values():
            if _below_folder(owner, folder) is not None:
                repository = folder
                break
    if repository is None:
        try:
            repository = repository_top(owner)
        except RepositoryUnknown as error:
            return None, str(error)
    if repository is None:
        repository = owner
    return Path(os.path.realpath(repository)).parent, None


def _holding(fetched: list[Planned], files: list[Path]) -> Planned | None:
    """The project fetched this round whose own folder holds the first of
    `files` that any of them holds: the one whose files have the problem
    (Design 7.11). When one is in another's folder, as a project in the
    clone made for the one at its top is, the deeper one."""
    def folder(p: Planned) -> Path:
        return Path(os.path.realpath(p.placement.entry_folder or p.target))
    for file in files:
        holders = [p for p in fetched if _below_folder(file, folder(p)) is not None]
        if holders:
            return max(holders, key=lambda p: len(folder(p).parts))
    return None


def _folder_state(folder: Path) -> str:
    """`absent`, `empty`, `git-only`, `occupied` or `unreadable` (a folder
    that cannot be listed), without following a link at the folder's own
    name (Design 7.6)."""
    import stat
    try:
        found = os.lstat(folder)
    except FileNotFoundError:
        return "absent"
    except OSError:
        return "occupied"
    if not stat.S_ISDIR(found.st_mode):
        return "occupied"
    try:
        with os.scandir(folder) as entries:
            names = [entry.name for entry in entries]
    except OSError:
        return "unreadable"
    if not names:
        return "empty"
    return "git-only" if names == [".git"] else "occupied"


def _folder_problem(planned: Planned) -> str | None:
    state = _folder_state(planned.target)
    if state == "git-only":
        return (f"{planned.id}: {planned.target} holds only .git (a clone or a submodule "
                f"update that stopped); finish or remove it with git, then run again")
    if state == "unreadable":
        return (f"{planned.id}: {planned.target} cannot be listed, so whether it is "
                f"empty is not known; correct its permissions, or the manifest entry "
                f"in {_file(planned.placement)}")
    if state == "occupied":
        return (f"{planned.id}: {planned.target} is not empty; move it aside, or correct "
                f"the manifest entry in {_file(planned.placement)}")
    return None


def _dash_problem(placement) -> str | None:
    entry = placement.entry
    if entry.url.startswith("-") or (entry.branch or "").startswith("-"):
        return f"{placement.id}: {entry.file} gives a repository beginning with '-'"
    return None


def _check(placement, run: _Run) -> tuple[str | None, Planned | None]:
    """Checks (2) to (4) of plan choice 7, for one project."""
    problem = _dash_problem(placement)
    if problem:
        return problem, None
    problem, target, trusted, bound = _bound_problem(placement, run.root, run.cloned,
                                                     run.home)
    if problem:
        return problem, None
    planned = Planned(placement.id, placement, target, trusted, bound)
    problem = _folder_problem(planned)
    return problem, (None if problem else planned)


def _group_key(planned: Planned):
    parent = planned.target.parent
    try:
        found = os.stat(parent)
        place = (found.st_dev, found.st_ino)
    except OSError:
        place = str(parent)
    return place, planned.target.name


def _group_round(planned: list[Planned], run: _Run) -> list[Planned]:
    """Design 7.7: one clone per repository folder. Projects placed at one
    folder by the same repository share the first one's clone; different
    repositories at one folder refuse them all."""
    from tcw.store.checkouts import normalized_url
    groups: dict = {}
    for p in planned:
        groups.setdefault(_group_key(p), []).append(p)
    kept = []
    for members in groups.values():
        names = {(normalized_url(m.placement.entry.url), m.placement.entry.branch)
                 for m in members}
        if len(names) > 1:
            for m in members:
                others = ", ".join(f"{o.placement.entry.file} for '{o.id}'"
                                   for o in members if o is not m)
                run.refuse(f"{m.id}: {m.target} is placed by entries naming different "
                           f"repositories: {_file(m.placement)} gives "
                           f"{m.placement.entry.repository}, and so does not agree with "
                           f"{others}; none is fetched")
            continue
        ids = frozenset(m.id for m in members)
        first = members[0]
        for m in members:
            m.group = ids
            m.comes_with = None if m is first else first.id
        kept += members
    order = {p.id: i for i, p in enumerate(planned)}
    return sorted(kept, key=lambda p: order[p.id])


def _line(planned: Planned) -> str:
    entry = planned.placement.entry
    at = f" at {entry.branch}" if entry.branch else ""
    return f"→ {planned.id}: {entry.url}{at} → {planned.target}"


def _round_ids(registry, project_id: str | None, run: _Run) -> list[str]:
    """Plan choice 6: no argument, the family's projects not here; `<id>`,
    `<id>` itself while it is not here, then its load order's missing ones."""
    if project_id is None:
        ids = [u.id for u in registry.unreachable()]
    elif _not_here(registry, project_id, run.root):
        ids = [project_id]
    else:
        ids = list(registry.load_order(project_id).missing)
    # An entry folder holding files and no project is refused as occupied
    # by this run, not as a graph problem of the whole graph (Design 7.6).
    ids += [pid for pid in registry.occupied_ids()
            if project_id is None or pid in ids]
    seen, out = set(), []
    for pid in ids:
        if pid not in seen and pid not in run.attempted:
            seen.add(pid)
            out.append(pid)
    return out


def _not_here(registry, project_id: str, root: Path) -> bool:
    """Whether `project_id`, looked up from the active project, is not on
    this machine; raises the lookup's other errors."""
    try:
        registry.project_folder(project_id, root)
    except Unreachable:
        return True
    except ProjectGraphError:
        if project_id in registry.occupied_ids():
            return True
        raise
    return False


def _placement(registry, pid: str, project_id: str | None, root: Path):
    if pid == project_id:
        return registry.placement(pid, root)
    return registry.placement(pid)


def _unfetchable(registry, pid: str) -> str:
    record = registry.unreachable_project(pid)
    sentence = f"; {record.message}" if record is not None and record.message else ""
    return f"{pid}: not on this machine, and no manifest entry gives the repository to " \
           f"fetch it from{sentence}"


def _found_at_entry(registry, planned: Planned) -> bool:
    """Design 7.11: a fetched project is found by the lookup at its entry's
    folder; when the lookup meets a graph problem, the folder must declare
    it (the problem is reported next)."""
    try:
        found = registry.placement(planned.id, planned.placement.asked_by)
    except (ValueError, ProjectGraphError):
        found = None
    if found is not None and found.folder is not None:
        return same_folder(found.folder, planned.placement.entry_folder)
    return _declares(planned.placement.entry_folder, planned.id)


def _declares(folder: Path, project_id: str) -> bool:
    import yaml
    try:
        mapping = yaml.safe_load((Path(folder) / ".tcw" / "tcw-config.yaml")
                                 .read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return False
    return isinstance(mapping, dict) and mapping.get("id") == project_id


def _answer_of(registry, pid: str, asked_by: Path):
    """The recorded answer for `pid` asked by `asked_by`, read without a new
    lookup: what a lookup that met a graph problem decided."""
    return next((p for p in registry.placements()
                 if p.id == pid and same_folder(p.asked_by, asked_by)), None)


def _keep(registry, run: _Run) -> None:
    for placement in registry.placements():
        if placement.folder is not None and placement.id not in run.kept:
            run.kept[placement.id] = (placement.folder, placement.asked_by)


def _changed_answer(registry, run: _Run) -> str | None:
    """Design 7.4: a kept answer the new reading changed, as its refusal."""
    for pid, (folder, asked_by) in run.kept.items():
        try:
            now = registry.placement(pid, asked_by)
        except ValueError:
            now = registry.placement(pid, run.root)
        except ProjectGraphError:
            now = _answer_of(registry, pid, asked_by)
        if now is not None and now.folder is not None and same_folder(now.folder, folder):
            continue
        if now is None or now.entry is None:
            # A search answer a fetched manifest now disagrees with (Design
            # 3.4): that manifest's entry is what moved it.
            now = registry.entry_elsewhere(pid, asked_by) or now
        other = (now.folder or now.entry_folder) if now is not None else None
        decided = (f"{now.entry.file}, fetched in this run,"
                   if now is not None and now.entry is not None else "this run's fetches")
        return (f"{pid}: was at {folder} when this run started, but {decided} now places "
                f"it at {other}; add an entry for '{pid}' to .tcw/tcw-manifest.local.yaml in "
                f"{asked_by}, which that lookup reads first, to keep it where it is")
    return None


def _fetch(planned: Planned, registry_root: Path, run: _Run) -> bool:
    """Checks (2) to (4) again on folders resolved again, then the clone."""
    from tcw.store.fs import FetchRefused, fetch_project
    problem, again = _check(planned.placement, run)
    if problem is None and not same_folder(again.target, planned.target):
        problem = (f"{planned.id}: {_written(planned.placement)} led to {planned.target} "
                   f"when this round was checked, and now leads to {again.target}; nothing "
                   f"was fetched for it")
    if problem is not None:
        run.refuse(problem)
        return False
    entry = planned.placement.entry
    run.say(_line(planned))

    def recheck() -> Path:
        _, target, _, _ = _bound_problem(planned.placement, run.root, run.cloned, run.home)
        return target if target is not None else Path(os.path.realpath(
            planned.placement.repository_path))

    try:
        fetch_project(entry.url, entry.branch, planned.target, project_id=planned.id,
                      subfolder=entry.subfolder, trusted=planned.trusted,
                      bound=planned.bound,
                      kept={k: v[0] for k, v in run.kept.items()}, group=planned.group,
                      recheck=recheck, written=entry.path, file=entry.file,
                      warn=lambda line: run.say(f"{run.prefix}: warning: {line}"))
    except FetchRefused as refused:
        run.refuse(str(refused))
        return False
    run.cloned[planned.id] = planned.target
    return True


def provision_projects(root: Path, project_id: str | None = None, *, dry_run: bool = False,
                       prefix: str = "tcw project provision", stores: tuple = (0, 0),
                       home: Path | None = None, out=None) -> int:
    """The projects pass; returns the command's exit code (Design 7.13).
    `stores` is the stores pass's `(fetched, failed)`, counted in the last
    line. The registry must have been checked valid (Design 7.14)."""
    from tcw.store.project import FsProjectRegistry, forget_registries
    run = _Run(Path(root), prefix, Path(home) if home is not None else Path.home(),
               out=out or sys.stderr, fetched=stores[0], failed=stores[1])
    registry = FsProjectRegistry.open(run.root)
    active = registry.current.id
    if project_id is not None:
        try:
            folder = None if _not_here(registry, project_id, run.root) else \
                registry.project_folder(project_id, run.root)
        except UnknownProject:
            run.say(f"{prefix}: no project with ID '{project_id}' is known or found near "
                    f"this one; check the spelling, or, if a project that is not on this "
                    f"machine yet names it, fetch that project first")
            return codes.ERROR
        except ProjectGraphError as error:
            run.say(f"{prefix}: {error}")
            return codes.ERROR
        if folder is not None:
            run.say(f"{project_id}: already on this machine at {folder}")
    first = True
    missing_for_want: set[str] = set()
    while True:
        ids = _round_ids(registry, project_id, run)
        if not ids:
            if first:
                run.say("nothing to fetch: every project it names is on this machine")
            break
        if first:
            _keep(registry, run)
        first = False
        run.attempted.update(ids)
        planned: list[Planned] = []
        for pid in ids:
            placement = _placement(registry, pid, project_id, run.root)
            if placement is None or placement.entry is None or placement.entry.url is None:
                run.say(_unfetchable(registry, pid))
                missing_for_want.add(pid)
                continue
            problem, ok = _check(placement, run)
            if problem is not None:
                run.refuse(problem)
            else:
                planned.append(ok)
        planned = _group_round(planned, run)
        if dry_run:
            for p in planned:
                if p.comes_with is not None:
                    run.say(f"{p.id}: would come with the clone for '{p.comes_with}'")
                    continue
                run.say(_line(p))
                run.say(f"{p.id}: would fetch into {p.target}")
                run.say(f"{p.id}: any projects it names cannot be listed until it is fetched")
            break
        done = []
        for p in planned:
            if p.comes_with is not None:
                if p.comes_with in run.cloned:
                    done.append(p)
                continue
            if _fetch(p, run.root, run):
                done.append(p)
        forget_registries()
        registry = FsProjectRegistry.open(run.root)
        registry.unreachable()                     # the walk, which records problems
        fetched_here = []
        for p in done:
            if not _found_at_entry(registry, p):
                sub = p.placement.entry.subfolder or "."
                run.refuse(f"{p.id}: the clone of {p.placement.entry.url} made for "
                           f"'{p.comes_with or p.id}' at {p.target} has no TCW project at "
                           f"{sub}")
                continue
            run.fetched += 1
            fetched_here.append(p)
            run.say(f"{p.id}: fetched into {p.target}")
            problem = registry.link_problem(p.id)
            if problem:
                run.say(f"{prefix}: warning: {p.id}: its parent links cannot be read, so "
                        f"nothing above it can be followed: {problem}")
        # Design 7.4 first: a kept answer the fetched manifests changed is also
        # a graph problem, and this message says which run moved it.
        changed = _changed_answer(registry, run)
        if changed is not None:
            run.refuse(changed)
            break
        try:
            registry.require_valid(fetching=True)
        except ValueError as error:
            holder = _holding(fetched_here, getattr(error, "files", []))
            where = f"{holder.id}: fetched into {holder.target}, but " if holder else ""
            run.refuse(f"{where}{error}. Until it is corrected, commands in "
                       f"'{active}' that read the project graph refuse; "
                       + (f"remove {holder.target} to undo the fetch, or add an entry for "
                          f"'{holder.id}' to .tcw/tcw-manifest.local.yaml pointing elsewhere"
                          if holder else "correct it"))
            break
        _keep(registry, run)
    if run.failed:
        run.say(f"fetched {run.fetched}, failed {run.failed}; what was fetched stays, and "
                f"running the command again fetches the rest")
        return codes.ERROR
    if project_id is not None and project_id in missing_for_want:
        return codes.UNREACHABLE
    return codes.OK
