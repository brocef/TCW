"""Filesystem store adapters + the FS-local helpers they share.

`git_root`/`init` (Phase 1) scaffold; `FsTaxonomyStore` (Phase 2) realizes the
`TaxonomyStore` interface over `docs/taxonomy/`. The capabilities and work
adapters land here in their phases; the genuinely-shared primitives get factored
into a tree-store core in Phase 4 (don't pre-abstract —
`docs/lifecycle/implementation.md`).
"""

# Defer annotation evaluation (PEP 563) so forward refs like `"TermDetail" | None`
# don't raise at class-definition time on Python 3.11–3.13. See tcw/store/base.py.
from __future__ import annotations

import dataclasses
import hashlib
import os
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from contextlib import suppress
from functools import cached_property
from pathlib import Path

import yaml

from tcw.errors import (BackendError, InheritedUnavailable, NotFound, Refused,
                        StateFileProblem, TcwError,
                        Unreachable, UsageError)
from tcw.findings import Finding
from tcw.ids import (FolderAddress, FullId, IdError, MalformedId, has_scheme,
                     id_path_problem, length_problem, parse_address, parse_stored, sort_input)
from tcw.reference_fields import field as ref_field, fields_of as ref_rows, names as ref_names
from tcw.object_folders import (EXTRA, LEGACY, MISPLACED, RESERVED, RESOURCES, STATE_FILES,
                                Walk, disagreement, exact_child, exact_path, folder_parent,
                                id_path_refused, id_problem, is_object, is_reserved,
                                length_problems,
                                object_paths, read_state, removal_blockers, shape_problems,
                                state_text, walk)
from tcw.output import shown as _shown
from tcw.store.yaml_source import UniqueKeyLoader, load as _load_named_yaml
from tcw.store.base import (
    CAP_FIELDS, CAP_LIFECYCLES, MIGRATION_GUIDE, CAP_PRIORITIES, CAP_STATUSES,
    RETIRED_CAP_FIELDS, RETIRED_PROJECTS_KEY, retired_key_problem,
    TAXONOMY_EDITABLE_FIELDS, _UNSET, Capability, CapabilitiesStore,
    CapabilityDetail, Combined, Declaration, NotASlug, clash_warning, combine,
    is_slug, missing_parts, slugify, StaleRevision,
    parse_repository_declaration, ProvisionResult, RepositoryDeclaration,
    StoreDeclarationError, StoreLocationUnusable, StoreNotProvisioned,
    StoreProvisioner, TaxonomyStore, Term, TermDetail, text_matches,
)
from tcw.store import config_edit
from tcw.store.checkouts import (
    checkout_root, provisioned_root as provisioned_store_root,
)
from tcw.project_files import (CONFIG_NAME, LOCAL_CONFIG_NAME, LOCAL_MANIFEST,
                               LOCAL_MANIFEST_NAME, LOCAL_SENTINEL, MANIFEST_NAME,
                               LEGACY_SENTINEL, SENTINEL, TCW_FOLDER, V3, V4,
                               find_marker, legacy_message, version_problem,
                               without_version)
from tcw.store.project import (FsProjectRegistry, _below, forget_registries, git_environment,
                               validate_project_id, worktree_anchors)

# Component trees `tcw project new` scaffolds. `work` gets a status-folder skeleton;
# `taxonomy` and `capabilities` are flat trees that fill in per their phases.
COMPONENTS = ("taxonomy", "capabilities", "work")


def _store_classes() -> dict:
    """Component → filesystem store class. A function, and consulted through the
    `STORE_CLASSES` mapping below, because the classes are defined further down
    this module than the helpers that need them."""
    return {"taxonomy": FsTaxonomyStore,
            "capabilities": FsCapabilitiesStore,
            "work": WorkLocation}


class WorkLocation:
    """The work store as the location ladder sees it (TCW-70 Design 3.4-3.5).

    The work path is found as every store's location is (`work.path`, else
    `docs/work`, re-anchored in a linked worktree, else a declared repository's
    provisioned checkout). It is usable when the directory is there: an empty
    store is a real state, and nothing inside it is required.
    """

    COMPONENT = "work"

    def __init__(self, root: Path):
        self.root = root

    @classmethod
    def open(cls, project_root: Path, active_root: Path | None = None) -> "WorkLocation":
        """`active_root` is the active project's folder when this is another
        project's work store, as `resolve_store` takes it."""
        return resolve_store(cls, Path(project_root), active_root=active_root)

    @classmethod
    def _local_root(cls, project_root: Path, configured: str | None, *,
                    locator=None) -> Path:
        return store_location(project_root, cls.COMPONENT, configured, locator=locator)

    @classmethod
    def _open_at(cls, raw_root: Path, project_root: Path, config_path: Path, *,
                 external: bool, must_exist: bool = True, declaration=None,
                 active_root=None) -> "WorkLocation":
        if not raw_root.is_dir():
            raise StoreLocationUnusable(
                f"{config_path}: work.path is not a directory: {raw_root}")
        return cls(raw_root.resolve())


class _StoreClasses:
    """Lazy view over `_store_classes()`, so `find_component_project` and `run_provision` name
    one mapping instead of each growing its own `if component ==` ladder — the
    shape that once left `run_provision` opening the work store for every
    component it looped over."""

    def __getitem__(self, component: str):
        try:
            return _store_classes()[component]
        except KeyError:
            raise ValueError(
                f"unknown component '{component}'; "
                f"choose from: {', '.join(COMPONENTS)}") from None

    def __contains__(self, component: str) -> bool:
        return component in _store_classes()


STORE_CLASSES = _StoreClasses()


def _modified_timestamp(resources: list[Path]) -> str:
    existing = [path for path in resources if path.is_file()]
    if not existing:
        return ""
    modified = max(path.stat().st_mtime for path in existing)
    return datetime.fromtimestamp(modified, timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )


def _capability_resources(folder: Path, meta: dict) -> list[Path]:
    names = [
        STATE_FILES["capabilities"],
        "description.md",
        *_as_list(meta.get("prependedDocs")),
        *_as_list(meta.get("appendedDocs")),
    ]
    return [folder / name for name in names]


# ── git + project helpers (FS-adapter local details, not store-interface ops) ──

def _git(*args, **kwargs):
    """Run a `git` command with stdin closed.

    None of these calls take input on stdin and none contact a remote, so this
    closes no *known* hang — git redirects its own hooks' stdin, which was the
    failure this was first written for and which turned out not to exist.

    It stands as an invariant instead: a child process that reads no stdin does
    not get the parent's. Every `subprocess` call in this module is a git call,
    so this is the single place that has to hold it, and
    `tests/test_subprocess_stdin.py` enforces the same rule package-wide — which
    is what caught the three `serve` spawns that do matter.
    """
    stdin = kwargs.pop("stdin", subprocess.DEVNULL)
    # Never the repository a git hook was run for: git's location variables
    # are removed from every call (TCW-115 Design 7.8).
    kwargs["env"] = git_environment(kwargs.get("env"))
    return subprocess.run(*args, stdin=stdin, **kwargs)


def _no_prompt_env() -> dict[str, str]:
    """This process's environment, changed so that git and ssh never ask.

    `GIT_TERMINAL_PROMPT=0` stops git's own prompt for HTTPS credentials and
    `GCM_INTERACTIVE=never` Git Credential Manager's; a credential helper that
    answers without asking still answers. git asks the first of `GIT_ASKPASS`,
    `core.askPass` and `SSH_ASKPASS` that is set, and skips the step when the
    one it finds is empty, so `GIT_ASKPASS` is set to the empty string, which
    also stops a configured `core.askPass`, and `SSH_ASKPASS`, which ssh would
    run too, is removed. For ssh,
    `BatchMode=yes` makes it fail instead of asking for a passphrase or to
    trust a new host, but only when the user has set no ssh command of their
    own, which is never replaced: `GIT_SSH_COMMAND` or `GIT_SSH`, or a
    `core.sshCommand` in the global, system or command-line configuration
    (`git -c`, `GIT_CONFIG_PARAMETERS`, `GIT_CONFIG_COUNT`), which are what a
    clone into a new folder uses. One read with `--show-scope` finds them all;
    a value in the `local` or `worktree` scope belongs to the repository the
    command runs in, whose own setting the clone does not use, so it must not
    turn `BatchMode` off.
    """
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never",
           "GIT_ASKPASS": ""}
    env.pop("SSH_ASKPASS", None)
    if not env.get("GIT_SSH_COMMAND") and not env.get("GIT_SSH"):
        done = _git(["git", "config", "--show-scope", "--includes", "--get-all",
                     "core.sshCommand"], capture_output=True, text=True, env=env)
        found = [line.split("\t", 1) for line in (done.stdout or "").splitlines()]
        if not any(len(f) == 2 and f[1].strip() and f[0] not in ("local", "worktree")
                   for f in found):
            env["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes"
    return env


#: The personal file beside `.tcw/tcw-config.yaml` (TCW-72 Design 1; TCW-106),
#: relative to the project root.
LOCAL_CONFIG = LOCAL_SENTINEL
#: The lines `tcw project new` writes in `.tcw/.gitignore` for the two personal
#: files (TCW-107 Design 1.9); the leading `/` limits each rule to that folder.
LOCAL_CONFIG_RULE = "/" + LOCAL_CONFIG_NAME
LOCAL_MANIFEST_RULE = "/" + LOCAL_MANIFEST_NAME


def personal_file_tracked(root: Path, relative: str = LOCAL_CONFIG) -> bool:
    """Whether the personal file `relative` (by default
    `.tcw/tcw-config.local.yaml`) in `root` is under version control
    (TCW-72 Design 10.3). Read only: the status command run here takes no
    lock and changes nothing. The file is tracked when it exists and the
    status reports it neither as untracked (`??`) nor as ignored (`!!`).
    `--untracked-files=all` overrides a `status.showUntrackedFiles=no`
    setting, under which git prints nothing for an untracked or ignored file,
    just as for a tracked one. False when the file is absent or `root` is not
    in a repository."""
    if not (root / relative).is_file() or git_root(root) is None:
        return False
    done = _git(["git", "--no-optional-locks", "-C", str(root), "status",
                 "--porcelain", "--ignored", "--untracked-files=all", "--",
                 relative],
                capture_output=True, text=True)
    if done.returncode != 0:
        return False
    return not any(line[:2] in ("??", "!!") for line in done.stdout.splitlines())


def ignore_personal_files(root: Path) -> list[tuple[str, Path]]:
    """Add `/tcw-config.local.yaml` and `/tcw-manifest.local.yaml` to
    `.tcw/.gitignore` in `root`, each unless a line there already reads it or
    the file's name without the `/` (TCW-72 Design 10.2; TCW-106 Design 1.5;
    TCW-107 Design 1.9). Returns what it wrote, for the caller to name.
    Writes the file only; nothing is staged."""
    ignore = root / TCW_FOLDER / ".gitignore"
    text = ignore.read_text(encoding="utf-8") if ignore.exists() else ""
    lines = {line.strip() for line in text.splitlines()}
    missing = [rule for rule in (LOCAL_CONFIG_RULE, LOCAL_MANIFEST_RULE)
               if not {rule, rule[1:]} & lines]
    if not missing:
        return []
    if text and not text.endswith("\n"):
        text += "\n"
    ignore.write_text(text + "".join(rule + "\n" for rule in missing), encoding="utf-8")
    return [("wrote", ignore)]


def git_root(start: Path | None = None) -> Path | None:
    """Top of the git work-tree containing `start` (cwd by default), or None.

    Shells out to git so worktrees/submodules resolve correctly — more correct
    on edge cases than walking up looking for a literal `.git` dir.
    """
    start = (start or Path.cwd()).resolve()
    try:
        out = _git(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return Path(out)


def write_sentinel(root: Path, project_id: str | None = None) -> bool:
    """Create or backfill the project sentinel without discarding configuration.

    Backfilling adds one `id:` line and touches nothing else in the file. `True`
    only when it wrote.
    """
    p = root / SENTINEL
    existing = load_config(p) if p.exists() else {}
    text = config_edit.edit_text(p, config_edit.read_text(p),
                                 _sentinel_edits(p, existing, project_id))
    if text is None:
        return False
    p.parent.mkdir(exist_ok=True)
    _atomic_write_all([(p, text)])
    return True


def _sentinel_edits(p: Path, existing: dict, project_id: str | None) -> list:
    """The edit that gives the sentinel its `id`, or none when it has one.

    `id: null` counts as none. It used to be read that way and then written
    back unchanged — `{"id": new, **existing}` let the old `None` win — while
    reporting a successful backfill.
    """
    configured = existing.get("id")
    if configured is not None:
        if not isinstance(configured, str):
            raise ValueError(f"{p}: project ID must be a string")
        configured = validate_project_id(configured)
        if project_id is not None and validate_project_id(project_id) != configured:
            raise ValueError(
                f"project already has id '{configured}'; refusing conflicting id '{project_id}'"
            )
        return []
    # Direct adapter callers (principally isolated store tests) receive a stable
    # fixture identity. The public CLI enforces explicit --id before calling us.
    return [config_edit.SetId(validate_project_id(project_id or "test-project"))]


def find_project_root(start: Path | None = None) -> Path | None:
    """The nearest ancestor of `start` (cwd by default) holding a
    `.tcw/tcw-config.yaml` *file* — the project root, or None. FS-adapter-local:
    realizes 'locate the project'. Resolves `start` (like `git_root`) so a
    symlinked cwd chains identically.

    None, too, when the nearest marker is a TCW 3.x project's root
    `tcw-config.yaml`: the walk never passes a 3.x project to reach an outer
    4.0 one, which would act on the wrong project. Every command refuses a 3.x
    project first (`refuse_legacy_project`), naming `tcw migrate`."""
    found = find_marker(start)
    return found[0] if found is not None and found[1] == V4 else None


def refuse_legacy_project(start: Path | None = None) -> None:
    """Refuse, exit 1, when the nearest project marker above `start` is a TCW
    3.x project (TCW-106 Design 4.1). Run once for every command, first."""
    found = find_marker(start)
    if found is not None and found[1] == V3:
        raise BackendError(legacy_message(found[0]))


def refuse_retired_config(start: Path | None = None) -> None:
    """Refuse when the current project's own `tcw-config.yaml` still holds a key
    TCW 3.0 retired (TCW-73 Design 9.3): a config error, exit 1, naming the
    migration guide. Run once for every command, before the command reads
    anything, so no command treats the old key as "no connected projects".

    Outside a project, or with a config that does not parse, it says nothing:
    the command's own reading reports those. Another project's config is not
    read here, so a parent's own links stay its own business (TCW-108 Design
    6.6).
    """
    root = find_project_root(start)
    if root is None:
        return
    try:
        config = load_config(root / SENTINEL)
    except (ValueError, OSError):
        return
    retired = retired_key_problem(config, (RETIRED_PROJECTS_KEY,))
    if retired:
        # Named from where the command runs, which may be a sub-folder.
        raise BackendError(f"{os.path.relpath(root / SENTINEL)}: {retired}")


def no_store_here(component: str, start: Path | None = None) -> BackendError:
    """The refusal of a command that needs `component`'s store where none is
    found from `start`. `tcw project new <axis>` reads the ID from the
    project's own file, so `--id <id>` is named only where no project with
    an ID is found."""
    root = find_project_root(start)
    try:
        configured = load_config(root / SENTINEL) if root is not None else {}
    except ValueError:
        configured = {}
    has_id = isinstance(configured, dict) and bool(configured.get("id"))
    command = f"tcw project new {component}" + ("" if has_id else " --id <id>")
    return BackendError(f"no {component} store here — run `{command}` in the project "
                        f"folder")


def find_component_project(component: str, start: Path | None = None,
                           opener=None) -> Path | None:
    """The project owning `component`'s store, or None. A project is the nearest
    ancestor marked by a `tcw-config.yaml` sentinel (FS-adapter-local). Returns
    the project iff it has that component, preserving the prior contract.

    "Has that component" is asked of the *resolved* store, never of a literal
    `docs/<component>` folder. The two answers differ in exactly the case this
    feature exists for: a checkout that cloned only the code repository has no
    `docs/taxonomy/`, because the taxonomy is in the other repository — so
    looking for the folder answered None before the resolution ladder could read
    the declaration, and the project's own config went unread.

    `opener(root)`, when given, opens the store asked about, so a command that
    holds one `Locator` opens its own store once (TCW-113 plan choice 4).
    """
    nr = find_project_root(start)
    if nr is None:
        return None
    FsProjectRegistry.open(nr).require_valid()
    try:
        store = (opener or STORE_CLASSES[component].open)(nr)
    except (StoreNotProvisioned, StoreDeclarationError):
        # Not "no project here" — the project is right in front of us and says where
        # its store comes from. Flattening this to None is what made `tcw work
        # list` answer a declared-but-absent store with "run `tcw project new`", which
        # would scaffold a second, empty store beside the real one.
        #
        # A *malformed* declaration is the same project with the same hazard, only
        # the actionable message is "fix this line" rather than "run this
        # command", so it travels the same way.
        raise
    except StoreLocationUnusable:
        # The one failure that means "there is no store at this location" — the
        # ladder's own definition (see `resolve_store`). Anything else, a removed
        # key or a malformed `<component>.path`, is a project that is here and
        # wrong, and "run `tcw project new`" is the wrong advice for it.
        return None
    # A work store that opened is a work store; a tree store's `open` validates
    # nothing when nothing is configured (rule 4), so the "is this component
    # here at all?" question is still this function's to ask. Asked of the
    # resolved root rather than the default one, which is the whole point.
    return nr if component == "work" or store.root.is_dir() else None


def tree_store_present(project_root: Path, component: str) -> bool:
    """Whether this project has a `component` tree store to check: its default
    folder is there, or its config says where the store is (`<c>.path` or
    `<c>.repository`, any value but null — a malformed one is present and must
    be reported, not skipped). FS-adapter-local, like `find_component_project`.

    Asked by `FsCapabilitiesStore._taxonomy` instead of
    `(project_root / "docs" / component).is_dir()`, which is true of neither a moved
    store nor one kept in another repository — so capabilities never checked
    Subject or Feature against a moved taxonomy. Deliberately not "open it and
    see", which `tcw validate` uses: a project that only inherits a taxonomy
    should not have its capability checks fail on that inheritance. It resolves no location: presence is read from
    the configuration's keys (TCW-110 Design 7.5).
    """
    if store_location(project_root, component, None).is_dir():
        return True
    try:
        config = load_config(project_root / SENTINEL)
    except ValueError:
        return False            # a broken config is reported where it is read
    section = config.get(component) if isinstance(config, dict) else None
    return isinstance(section, dict) and (
        section.get("path") is not None or section.get("repository") is not None)


def _has_work_store(project_root: Path) -> bool:
    """Whether `project_root` has a usable work store. The *configured* store is the
    only authority: a literal `docs/work` folder must not vouch for a project whose
    `work.path` points somewhere else (or somewhere broken).

    A declared-but-unprovisioned store answers `False` here rather than raising,
    unlike `find_component_project`. The difference is whose store is being asked about: this
    one is asked about *other* projects while listing a topology, and one
    unprovisioned child must not turn a parent's listing into a hard failure.
    "No usable store here" is true of such a project, and it is the answer every
    caller of this function actually wants.
    """
    try:
        WorkLocation.open(project_root)
        return True
    except ValueError:                     # StoreNotProvisioned included, by design
        return False


def unreachable_project_note(registry, project_id: str) -> str | None:
    """"Declared but not reachable here" for `project_id`, or None.

    One renderer for every site that resolves a project id and got None back.
    Without it each message says the project was never registered, which sends
    the reader to their config to add a declaration that is already there.
    """
    absent = registry.unreachable_project(project_id)
    if absent is None:
        return None
    if absent.message:
        return absent.message                # TCW-107 Design 6.2
    return (f"project '{project_id}' is declared in {absent.declared_in} but is "
            f"not reachable in this checkout ({absent.locator})")


def _same_folder(a: Path, b: Path) -> bool:
    """Whether `a` and `b` are one folder. One gone since it was listed or
    resolved is not a match; any other error leaves the question open, so it
    propagates and the caller's delete stops."""
    try:
        return a.samefile(b)
    except FileNotFoundError:
        return False


def _in_folder(a: Path, target: Path, root: Path) -> bool:
    """Whether `a` is the folder `target` or a folder inside it, walking up no
    further than `root`. Compared by folder identity, like `_same_folder`."""
    while True:
        if _same_folder(a, target):
            return True
        if a == root or a.parent == a or root not in a.parents:
            return False
        a = a.parent


def init(components: list[str], root: Path, project_id: str | None = None,
         work_path: Path | None = None,
         paths: dict[str, Path] | None = None) -> list[tuple[str, Path]]:
    """Scaffold `docs/<component>/` skeletons under `root` and mark it a project.
    Returns what it changed, as `(verb, path)` pairs (`wrote`, `created`,
    `removed`) for the caller to name. A `.gitkeep` lands in each folder so
    the empty skeleton survives a commit (git doesn't track empty
    directories).

    The work component is one directory and its `.gitkeep`, nothing else: no
    status folders and no ignore rules (TCW-70 Design 11). Unstaged, like
    everything else init writes.
    """
    # Read ahead of `write_sentinel`, so its own mapping check no longer runs
    # first — a malformed config used to come back from it as a `ValueError` and
    # would otherwise surface here as an `AttributeError` from `.get`.
    existing_config = load_config(root / SENTINEL)
    # `work_path` kept as its own parameter rather than folded into `paths`:
    # it is the fourth positional argument every existing caller passes, and
    # this component's location has a name in the CLI (`--work-path`,
    # `tcw project new work --work-path`) that predates the mapping.
    paths = dict(paths or {})
    if work_path is not None:
        paths["work"] = work_path
    # Refused before anything is written: the location is written into the
    # shared file, where only a relative path or a folder address works on
    # every machine (TCW-110 Design 7.1).
    from tcw.config import store_location_problem
    for c, given in paths.items():
        problem = store_location_problem(f"{c}.path", str(given), address=False)
        if problem:
            raise UsageError(problem)
    work_path = paths.get("work")
    # A location read back from the file is used, never written: writing it
    # would replace what the user typed (`./store`, `~/store`) with its
    # normalized, home-expanded form.
    read_from_config: set[str] = set()
    # Every component, not only `work`: initializing the taxonomy alone used to
    # scaffold `docs/taxonomy` under a configured `taxonomy.path`, so the "run
    # `tcw project new`" advice for a configured-but-absent store never came true.
    configured_text: dict[str, str] = {}
    for c in components:
        if c in paths:
            continue
        section = existing_config.get(c) or {}
        # `in`, not truthiness: `work.path: []` and `work.path: false` used to
        # fall through to the default store without a word, so a configuration
        # mistake read as a deliberate choice.
        if isinstance(section, dict) and "path" in section:
            configured_path = section["path"]
            if (not isinstance(configured_path, str)
                    or not configured_path.strip()):
                raise ValueError(f"{root / SENTINEL}: {c}.path must be a string")
            problem = store_location_problem(f"{c}.path", configured_path)
            if problem:
                raise ValueError(f"{root / SENTINEL}: {problem}")
            paths[c] = Path(configured_path)
            configured_text[c] = configured_path
            read_from_config.add(c)
    # Where each store is, as the readers find it (`store_location`): a
    # relative path leaving a linked worktree re-anchors there, and a folder
    # address resolves, so a store is built where it will be looked for.
    located = {c: store_location(root, c, configured_text.get(c, str(given)))
               for c, given in paths.items() if c in components}
    work_path = paths.get("work")
    # Everything `init` can refuse over, decided before it writes anything at
    # all — the sentinel included. It writes two locations, and each of these
    # checks used to sit next to the write it protects rather than ahead of all
    # of them, so a refusal left `tcw-config.yaml` rewritten with the bad path,
    # or a new sentinel in a project that had none, or the whole status tree.
    default_root = root / "docs" / "work"
    replacing_default_store = False
    if work_path is not None and "work" in components:
        target = located["work"]
        if default_root.exists() and default_root.resolve() != target.resolve():
            # `is_symlink` first: replacing a default store means deleting it,
            # and a symlink is someone else's directory. Anything in it but
            # `.gitkeep`, Finder's `.DS_Store` or an empty hidden file may be
            # someone's work — an item, a 2.x status folder, a note — and work
            # is moved by a person, never deleted by init.
            def disposable(entry: Path) -> bool:
                return (entry.name.startswith(".") and entry.is_file()
                        and not entry.is_symlink()
                        and (entry.name in (".gitkeep", ".DS_Store")
                             or entry.stat().st_size == 0))
            held = [] if default_root.is_symlink() else sorted(
                entry.name for entry in default_root.iterdir()
                if not disposable(entry))
            if default_root.is_symlink() or held:
                shown = ", ".join(held[:5]) + (f" and {len(held) - 5} more"
                                               if len(held) > 5 else "")
                raise ValueError(
                    f"refusing to replace non-pristine {default_root}"
                    + (f" (it holds {shown})" if held else "")
                    + "; move existing work manually, update work.path, then "
                    "re-run init"
                )
            replacing_default_store = True
    # The exact directories this call will create, worked out before it creates
    # any of them — the pre-flight below needs the list, and so does the loop
    # that makes them, so there is only one of it.
    plan: list[tuple[str, Path, list[Path]]] = []
    for c in components:
        base = located.get(c) or store_location(root, c, None)
        section = existing_config.get(c)
        if (c != "work" and isinstance(section, dict)
                and section.get("repository") is not None and not base.exists()):
            # A local tree always wins over a declared home (`resolve_store`
            # rule 1), so an empty one scaffolded here would hide the real store
            # from then on. Whether the home is already provisioned decides the
            # advice: "run `tcw project provision`" after it succeeded sends the user in
            # a circle.
            others = [o for o in components if o != c]
            rest = (f" To scaffold the rest, name them: `tcw project new {' '.join(others)}`."
                    if others else "")
            try:
                resolve_store(STORE_CLASSES[c], root)
            except ValueError:
                raise ValueError(
                    f"{root / SENTINEL}: {c} declares a repository; run `tcw project provision` "
                    f"to fetch it rather than scaffolding an empty local store.{rest}"
                ) from None
            raise ValueError(
                f"{root / SENTINEL}: {c} is already provided by its declared "
                f"repository; there is nothing to scaffold.{rest}")
        plan.append((c, base, [base]))
    for component, _, leaves in plan:
        for leaf in leaves:
            # `mkdir(parents=True, exist_ok=True)` raises on a leaf that exists as
            # a file and on a parent that does — and it raised after the sentinel
            # and the earlier leaves had landed. The nearest path that exists
            # decides: if it is a directory, everything below it is still to be
            # created. `is_symlink` again, because a dangling one is not a
            # directory to `mkdir` either.
            occupied = next((c for c in (leaf, *leaf.parents)
                             if c.exists() or c.is_symlink()), None)
            if occupied is not None and not occupied.is_dir():
                raise ValueError(f"cannot scaffold {leaf}: {occupied} is not a directory")
    # The config's whole change — `id` and every `<component>.path` — decided
    # and verified as one edit before anything is written. It used to be two
    # writes with the default store's deletion between them, so a refusal at
    # the second would have left `id` written and the store already gone.
    config_path = root / SENTINEL
    configured = {c: p for c, p in paths.items() if c in components}
    for component in configured:
        section = existing_config.get(component)
        if section is not None and not isinstance(section, dict):
            # Used to be replaced by `{path: …}`, discarding what was typed.
            raise ValueError(f"{config_path}: {component} must be a mapping, "
                             f"found {type(section).__name__}")
    config_text = config_edit.edit_text(
        config_path, config_edit.read_text(config_path),
        _sentinel_edits(config_path, existing_config, project_id)
        + [config_edit.SetScalar(c, "path", str(location))
           for c, location in configured.items() if c not in read_from_config])
    changed: list[tuple[str, Path]] = []
    if config_text is not None:
        config_path.parent.mkdir(exist_ok=True)
        _atomic_write_all([(config_path, config_text)])
        changed.append(("wrote", config_path))
    if replacing_default_store:
        shutil.rmtree(default_root)
        changed.append(("removed", default_root))
    for c, base, leaves in plan:
        for leaf in leaves:
            if not leaf.is_dir():
                leaf.mkdir(parents=True, exist_ok=True)
                changed.append(("created", leaf))
            keep = leaf / ".gitkeep"
            if not keep.exists():
                keep.touch()
                changed.append(("wrote", keep))
    return changed


# ── YAML helpers ────────────────────────────────────────────────────────────

# The duplicate-key refusal lives with the named-file loader, so the project
# registry and this module share one copy.
_UniqueKeyLoader = UniqueKeyLoader


#: The YAML filenames TCW writes as records, held to `load_yaml`'s mapping
#: contract by `tcw validate`. Named rather than inferred and kept in one place,
#: because naming what TCW owns is narrower than exempting what it does not.
#:
#: They are the three state files (TCW-111 Design 1.1), a work item's among
#: them (TCW-70 Design 3.2). The project sentinel
#: `tcw-config.yaml` sits outside the scanned trees and is refused by
#: `load_config` the moment anything reads it. A work item's `capabilities.yaml`
#: is checked by the work checks in `tcw validate`, not by this list. A leftover
#: per-store `config.yaml` is not a record of ours: `check()` names any copy at a
#: store root as no longer read (`FsTreeStore._legacy_config_problems`).
OWNED_YAML_NAMES = frozenset(STATE_FILES.values())


class NotAMapping(yaml.YAMLError):
    """A YAML document that parsed perfectly well and is not a mapping.

    A **subclass** of `yaml.YAMLError` on purpose. The eleven sites that already
    catch one keep catching this without being touched, which is what makes a
    corrupt record degrade to empty instead of crashing the board. The subclass
    exists only so a caller that can say something better — `load_config` — can
    tell "your file is not a mapping" apart from "your file is not YAML".
    """


class NotUtf8(UnicodeDecodeError):
    """A YAML file holding a byte that is not valid UTF-8, worded with its path.

    A **subclass** of `UnicodeDecodeError`, and so of `ValueError`, so every
    site that catches either keeps catching it; only the message changes, from
    codec words that name no file to the file and the byte, as `tcw.config`
    words the same problem.
    """

    def __init__(self, path: Path, error: UnicodeDecodeError):
        super().__init__(error.encoding, error.object, error.start, error.end,
                         error.reason)
        self.path = path

    def __str__(self) -> str:
        bad = self.object[self.start:self.start + 1].hex()
        return (f"{self.path}: is not valid UTF-8 text (byte 0x{bad} at "
                f"position {self.start})")


def read_yaml_text(path: Path) -> str:
    """The text of a YAML file, or `NotUtf8` naming it."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise NotUtf8(path, error) from None


def load_yaml(path: Path, unique: bool = False) -> dict:
    """Load a YAML **mapping**. `{}` when the file is absent or has no content;
    `yaml.YAMLError` when it holds anything that is not a mapping.

    This used to end in ``return data or {}``, which kept neither half of that
    promise. A falsy document — ``[]``, ``false``, ``0`` — became a mapping, so a
    malformed ``tcw-config.yaml`` read as "no configuration" and `init`
    overwrote it, while the same file holding ``- a`` was refused and left alone.
    A truthy non-mapping came back unchanged and reached ``.get``, so one corrupt
    record crashed `tcw work list` and took the whole board down.

    **The raised type is `yaml.YAMLError` deliberately, not `ValueError`.** Ten
    sites already catch it around a load — `_safe_yaml` above all, whose whole
    job is that "a malformed state file degrades to empty rather than crashing
    the board". A well-formed non-mapping never raised one, so that promise had
    never applied to this case; raising the type they already expect keeps it at
    every one of them without touching any.

    Degrading is not reporting. `tcw validate` is what names a TCW-owned file
    that is not a mapping — see `tcw/validate.py`.
    """
    if not path.exists():
        return {}
    text = read_yaml_text(path)
    data = _load_named_yaml(text, path,
                            _UniqueKeyLoader if unique else yaml.SafeLoader)
    if data is None:                       # absent content: empty file, or `null`
        return {}
    if not isinstance(data, dict):
        raise NotAMapping(
            f"{path}: expected a mapping, found {type(data).__name__}")
    return data


def load_config(path: Path) -> dict:
    """The project sentinel, read as a mapping, refusing as a `ValueError`.

    A config the user has broken is their mistake, not a failure of the YAML
    layer, and `ValueError` is the channel `tcw`'s top level already renders as
    a plain message. Every reader of the sentinel that must refuse goes through
    here, so `init`, a store resolving and the tag registry all say one thing
    about one file.

    The reader that must *not* refuse — `declared_repository`, which exists to
    answer for a graph that cannot be fully loaded — deliberately does not use
    this.
    """
    try:
        data = load_yaml(path, unique=True)
    except NotAMapping as error:
        raise ValueError(f"malformed {path}: config must be a mapping") from error
    except yaml.YAMLError as error:
        raise ValueError(f"malformed {path}: {error}") from error
    # A file whose format this TCW cannot read is refused before anything
    # reads or edits it (TCW-106 Design 3.4a). An absent file reads as `{}`.
    if path.exists():
        version = version_problem(data)
        if version:
            raise ValueError(f"{path}: {version}")
    return without_version(data)


# ── Revision tokens & atomic writes (FS-adapter private details) ─────────────

def _revision(content: str) -> str:
    """Cheap content-hash revision token (16 hex chars of SHA-256).

    `surrogateescape` so a file read by `_read_revision_text` hashes back to its
    own bytes: identical to a strict encode for any valid UTF-8 text, and a
    stable token, distinct per byte sequence, for a file that is not."""
    return hashlib.sha256(content.encode("utf-8", "surrogateescape")).hexdigest()[:16]


def _read_revision_text(path: Path) -> str:
    """A file's text for computing its revision — never for display or parsing.

    Lossless: bytes that are not UTF-8 survive as escapes, so a damaged file
    still has a revision, and the snapshot that hands one out and the guard that
    checks it agree. A guarded save can therefore replace a damaged file, which
    is how an editor repairs it. `read_text` keeps its newline handling, so no
    valid file's token changes."""
    return path.read_text(encoding="utf-8", errors="surrogateescape")


def _require_detail(detail, kind: str, ref: str):
    """The detail a composite operation promised to return, or a handled error.

    `get_detail` and its siblings are `-> … | None` because a concurrent move or
    delete can outlast their retries. `create_work` / `update_work` /
    `update_term` / `update_capability` are not: they declare a value. Handing
    `None` through anyway relocates the failure to whichever caller dereferences
    it first — a 500 out of `serve`, an `AttributeError` out of the CLI.

    The message does not claim the write landed, because at one of the five call
    sites (`update_work`'s no-change early return) nothing was written. It always
    names the ref: after a failed `tcw work new` that is the only place the user
    learns the slug of the item that now exists.
    """
    if detail is None:
        raise BackendError(f"{kind} '{ref}' could not be read back: another process "
                         f"moved or removed it. Re-read it.")
    return detail


def _revision_multi(*contents: str) -> str:
    """Revision for multiple resources concatenated (core = fields + body)."""
    return _revision("\x00".join(contents))


def _safe_store_id(value: str, label: str) -> str:
    """Validate a caller-supplied identifier that will be joined into a store
    path. Nested ids ('web/editing') are allowed; traversal is not — reject
    absolute paths, '..'/'.'/empty segments, backslashes, and NUL bytes. Returns
    the trimmed id. (Web writes reach these with arbitrary input; the bounded-
    input rule in the spec forbids escaping the store root.)"""
    v = (value or "").strip()
    if not v:
        raise UsageError(f"{label} is required")
    if v.startswith(("/", "\\")) or "\\" in v or "\x00" in v:
        raise UsageError(f"invalid {label}: {value!r}")
    for seg in v.split("/"):
        if seg in ("", ".", "..") or seg != seg.strip():
            raise UsageError(f"invalid {label}: {value!r}")
    return v


def _check_id_path(id_path: str, label: str) -> None:
    """Refuse a new object's id-path that breaks the identifier rule (TCW-110
    Design 1.6), before anything is written."""
    problem = id_path_problem(id_path)
    if problem:
        raise MalformedId(f"invalid {label} {id_path!r}: {problem}")


def _check_length(project: str, ns: str, id_path: str) -> None:
    """Refuse a new object whose full identifier would be longer than
    `ID_LIMIT`, before anything is written (TCW-111 Design 4.2)."""
    problem = length_problem(FullId(project, ns, id_path))
    if problem:
        raise UsageError(problem)


def _check_reserved(id_path: str, namespace: str, label: str) -> None:
    """Refuse a new object's id-path with a part that is one of the store's
    reserved names, ignoring letter case (TCW-111 Design 2.4), before anything
    is written."""
    for part in id_path.split("/"):
        if is_reserved(part, namespace):
            raise UsageError(f"invalid {label} {id_path!r}: '{part}' is reserved in "
                             f"the {namespace} store")


def _blocked_removal(d: Path, root: Path, namespace: str, id_path: str) -> None:
    """Refuse the removal of the object folder `d` while anything below it is
    an object of any store, or a TCW 3.x one (TCW-111 Design 2.5, review
    decision 16): `Refused`, before anything is deleted. The search is of the
    folder itself, not the walk, because `git rm -rf` deletes hidden folders,
    fixed folders and `resources/` all the same."""
    blockers = removal_blockers(d, root)
    legacy = [(where, name) for where, name in blockers if name != "state"]
    if legacy:
        where, name = legacy[0]
        raise Refused(f"cannot remove '{id_path}': {where} holds a TCW 3.x {name}; "
                      f"run 'tcw migrate' in this project first")
    nested = [where for where, _ in blockers]
    if nested:
        raise Refused(f"cannot remove '{id_path}': nested under it: "
                      f"{', '.join(nested)} (remove those first)")


def _bad_name(id_path: str) -> str | None:
    """Why a folder's name breaks the identifier rule, as `check` reports it
    (Design 1.6), or None."""
    problem = id_path_problem(id_path)
    return (f"its folder name breaks the identifier rule ({problem}); rename it "
            f"by hand") if problem else None


def _umask() -> int:
    """The process umask, read without leaving it changed."""
    current = os.umask(0)
    os.umask(current)
    return current


#: The files the project registry reads: a change to one drops it.
_GRAPH_FILES = (CONFIG_NAME, MANIFEST_NAME, LOCAL_MANIFEST_NAME)


def _atomic_write_all(pairs: list[tuple[Path, str]]) -> None:
    """Write several files as one unit: stage every temp, then promote each.

    `pairs` is `(target path, content)` in promote order. The failure class this
    closes is content production — ENOSPC, EACCES, a serialization error — which
    can only happen in the staging phase, before anything is promoted, so the
    targets are left untouched. One handler spans both phases and unlinks every
    temp, so no temp file is left beside a real file in the user's git tree.
    Temps are `mkstemp`-unique rather than `<target>.tmp`, so an existing file
    or symlink at a predictable name is never truncated, promoted, or deleted.
    `BaseException` on purpose: a `KeyboardInterrupt` mid-batch still cleans up.

    # ponytail: the promote loop is not atomic across files — a process death
    # between two replace() calls still leaves a partial update. Upgrade path is
    # a journal or a whole-directory swap (the `accept_inbox` shape, fs.py:2246);
    # neither is worth its cost for the failure class actually reachable here.
    """
    staged = []
    try:
        for path, content in pairs:
            # A unique temp beside the target, not `<target>.tmp`: the
            # deterministic name is a real path a user (or a symlink) can
            # already occupy, and this would truncate it, promote it over the
            # target, and delete it on failure. `mkstemp` refuses to reuse an
            # existing name and never follows a symlink.
            fd, tmp_name = tempfile.mkstemp(dir=path.parent,
                                            prefix=path.name + ".", suffix=".tmp")
            os.close(fd)                     # mkstemp is for the *name*
            tmp = Path(tmp_name)
            staged.append((tmp, path, content))
            tmp.write_text(content, encoding="utf-8", newline="")
            # `mkstemp` is 0600 by design. Carry the target's mode when it has
            # one, so promoting does not silently re-permission a file someone
            # chmod'ed; otherwise fall back to what an ordinary write would give.
            try:
                os.chmod(tmp, path.stat().st_mode)
            except OSError:
                os.chmod(tmp, 0o666 & ~_umask())
        for tmp, path, _ in staged:
            tmp.replace(path)
    except BaseException:
        for tmp, _, _ in staged:
            tmp.unlink(missing_ok=True)
        raise
    finally:
        # A configuration or a manifest changed under this command's project
        # registry (TCW-107 Design 2.13); also when a promote failed part way.
        if any(path.name in _GRAPH_FILES for _, path, _ in staged):
            forget_registries()


# ── Shared tree-store core (Phase 4) ─────────────────────────────────────────

def _mkdir_owned(d: Path) -> bool:
    """Create `d`, returning whether *this call* made it.

    `exist_ok=False` is the ownership proof: exactly one process's `mkdir`
    succeeds, so there is no check-then-act window. That is what lets a failed
    write remove the folder outright — knowing it removes nothing it did not
    create — where an `existed = d.exists()` probe beforehand could not.
    """
    try:
        d.mkdir(parents=True)
        return True
    except FileExistsError:
        return False


def anchor_configured_path(project_root: Path, value: Path) -> Path:
    """The directory a relative `<component>.path` is resolved against.

    Inside a *linked worktree* this follows the same rule
    `FsProjectRegistry._locator_path` applies to a manifest entry's path, and
    for the same reasons:

    - **Re-anchor only on escape.** A relative path that stays inside the
      worktree is this project's store on this branch and belongs to the worktree,
      exactly as the default `docs/<component>` does. Only a path that leaves
      the checkout was authored against the primary checkout's position on disk.
      Re-anchoring an inside-staying path used to send a worktree user to the
      primary checkout's store while the *identical* default did not.
    - **Anchor at this project's counterpart, not at the main worktree root.**
      `worktree_anchors` returns `(current top, main root)`; using the second
      alone drops the sub-path of a project nested inside the repository, so
      `apps/server`'s relative path got applied from the repository root and the
      store could not be found at all (GitHub #26).

    One function, not one per store class: both `_local_root` hooks had their
    own copy of this and only the work store's was ever fixed, which is the
    drift `resolve_store` exists to prevent. Getting it wrong silently swaps a
    worktree user's real store for a cache clone.

    Returns `project_root` unchanged outside a worktree, for a project that is not in
    a git repository, and for a path that stays inside the checkout.
    """
    anchors = worktree_anchors(project_root)
    if anchors is None:
        return project_root
    top, main = anchors
    resolved = (project_root / value).resolve()
    inside = _below(project_root, top)
    if inside is not None and _below(resolved, top) is None:
        return main / inside
    return project_root


class FsTreeStore:
    """Common FS-adapter base for the three bounded-tree stores.

    Captures the boilerplate every component shares — the store root, the
    enclosing project (repo) root, config loading, the `open(project_root)` entry
    point, and the git-plumbing methods that *effect* transitions. Component
    specifics (project = dir vs file, identifier resolution, the status state
    machine) stay in the subclasses (phase-4-shared-core: don't over-pull).

    Subclasses set `COMPONENT` (the `docs/<COMPONENT>/` dir) and optionally
    `LEGACY_CONFIG_NAME` (the per-store config file this component used to
    write, retained so it stays out of the attachment surface and so `check`
    can report a leftover copy).
    """
    COMPONENT: str
    #: The filename this component once kept the projects it inherited from
    #: in, before TCW 2.5.0. Nothing reads or writes the file
    #: any more. The name survives on the class so `_legacy_config_problems`
    #: reports a copy left at the store root, and so the store's shape check
    #: leaves that copy to it rather than reporting it a second time.
    LEGACY_CONFIG_NAME: str | None = None
    #: The file whose presence makes a folder one of this store's objects
    #: (TCW-111 Design 1.1).
    STATE_FILE: str

    def __init__(self, root: Path, *, project_root: Path | None = None,
                 store_git_root: Path | None = None, active_root: Path | None = None):
        self.root = root                       # docs/<component>/, or wherever configured
        # Two roots, because they answer different questions and diverge the
        # moment a store leaves its project's repository — the same split the
        # work store has carried since `work.path` existed.
        #
        # `project_root` is the *project*: whose config this is, and whose
        # parent links decide what it inherits. `store_git_root` is the repository a write
        # here has to land in. They are the same directory for a store sitting
        # in its own project, and are not for a configured or provisioned one.
        self.project_root = project_root or root.parent.parent
        self.store_git_root = store_git_root or git_root(root) or self.project_root
        # What this store's writes changed on disk, in order: `("wrote", path)`,
        # `("removed", path)` or `("created", path)`. The filesystem adapter's
        # own record (TCW-73 Design 1.2), read by the commands to name every
        # file they touched; a store kept somewhere else has nothing to list.
        self.changed: list[tuple[str, Path]] = []
        # Each object a listing left out because its state file's version is
        # one this TCW cannot read, by file, with the version check's message
        # (TCW-111 Design 1.5). Filled only by a listing, so `check` lists
        # first, and a command that lists says so on stderr and exits 1.
        self.unreadable: dict[Path, str] = {}
        # This component's section of the *project's* config, not a file inside the
        # store. Re-read here rather than threaded down from `resolve_store`,
        # because `tcw/validate.py` builds a store by calling `_open_at`
        # directly: a threaded section would arrive empty there and that store
        # would silently resolve no inheritance at all.
        self.config = self._component_config()
        # The owner of every entry this store holds itself (TCW-110 Design
        # 1.4): the `id:` of its own project's file, read here rather than
        # through a project registry, which would walk the owner's whole
        # family only to learn what that one file holds.
        project_id = self._config().get("id")
        self.project_id = project_id if isinstance(project_id, str) else ""
        # The project the command acts on: this store's own unless it was
        # opened for another (`active_root`), as a source of the active
        # project's view or an owner's store read by `Locator.read` is. Such a
        # store is "another project's" (TCW-112 choice 4): its file's
        # `extends` is not read, and its own view is built only if asked for.
        self._active_root = active_root or self.project_root
        self._as_other = active_root is not None
        # The view (TCW-112 Design 1.4): built on first use, once per store,
        # and forgotten when this store writes.
        self._view_cache: _View | None = None
        self._decl_cache: dict | None = None
        # What a listing of the view left out because a source's object at
        # that path cannot be read (Design 1.3), by file, with its message.
        self._view_unreadable: dict[Path, str] = {}
        # Why the view could not be built, when a reader fell back to this
        # project's own declarations (Design 3.4): the `InheritedUnavailable`.
        self.view_error: InheritedUnavailable | None = None
        if not self._as_other and "extends" in self.config:
            # Design 1.5: refused in the active project's own file only, as
            # a configuration line to fix.
            raise StoreDeclarationError(
                f"{self._config_path()}: '{self.COMPONENT}.extends' was removed in "
                f"TCW 4.0: a project inherits its {self.COMPONENT} from its parents; "
                f"name each project it inherits from under 'parents:' with an "
                f"'inherit' that includes {self.COMPONENT}, and delete this key")

    @property
    def locator(self):
        """The command's one `Locator`, for the active project (TCW-110
        Design 6.1): a reference read here, or a location written in this
        project's file, is looked up on that project's registry."""
        from tcw.locate import Locator
        return Locator.of(self._active_root)

    def _stored_ref(self, value, namespace: str, store=None):
        """What a reference stored in this project's records names (TCW-110
        Design 5.2, 6): a `tcw.locate.Outcome`. Whether it names an object
        is asked of the owner's own store alone (TCW-112 Design 3.1, second
        consequence), so a project missing above the owner never makes it
        "could not check"; the object itself, for a check of its kind, is
        read as its owner sees it, and is None when that cannot be read
        here. `store` is the store of `namespace` already open for this
        project (this one for its own namespace). A value in a 3.x form or
        none at all is an `error` outcome naming why."""
        from tcw.locate import ERROR, FOUND, MISSING, Outcome
        try:
            full_id = parse_stored(value, namespace)
        except IdError as error:
            return Outcome(ERROR, message=str(error))
        if store is None and namespace == self.COMPONENT:
            store = self
        try:
            if store is not None and full_id.project == store.project_id:
                if not store.has_own(full_id.id_path):
                    return Outcome(MISSING)
                owner = store
            else:
                outcome = self.locator.exists(full_id, named_by=self.project_root)
                if outcome.kind != FOUND or namespace == "work":
                    return outcome
                owner = self.locator.owner_store(full_id.project, namespace,
                                                 self.project_root)
            try:
                return Outcome(FOUND, owner.get_local(full_id.id_path))
            except InheritedUnavailable:
                return Outcome(FOUND, None)
        except (ValueError, OSError, TcwError) as error:
            return Outcome(ERROR, message=str(error))

    def _local_ref(self, value) -> str | None:
        """The id-path of this store's own object that a stored reference of
        its namespace names, or None for any other value: what a removal
        compares against, never looking another project up."""
        try:
            full_id = parse_stored(value, self.COMPONENT)
        except IdError:
            return None
        return full_id.id_path if full_id.project == self.project_id \
            and self.has_own(full_id.id_path) else None

    def find_parent(self, text) -> "Term | Capability":
        """The object a `--parent` names, read as command input is (TCW-110
        Design 3.1): this store's own, an inherited one, or another
        project's. Raises `NotFound` (exit 4) when there is none."""
        from tcw.locate import find_tree
        return find_tree(self, str(text))

    def folder_disagreement(self, obj) -> str | None:
        """Design 3.2's warning for a local object of this store whose folder
        sits in another object's folder that its `parent` does not name, or
        None (TCW-111 row m). A `parent` naming the object at the folder
        parent's id-path in a project that passes the axis to this one
        agrees with the folder: the folder parent is its override (TCW-112
        Design 6.7)."""
        id_path = getattr(obj, "slug", None) or obj.path
        above = folder_parent(self.root, self.COMPONENT, id_path)
        parent = obj.parent
        if above is not None and isinstance(parent, FullId) \
                and parent.id_path == above and parent.project != self.project_id \
                and parent.project in self._source_ids():
            return None
        return disagreement(obj.full_id, None if above is None else
                            FullId(self.project_id, self.COMPONENT, above), obj.parent)

    def _parent_findings(self, objects, selected: str | None = None,
                         declared: dict | None = None) -> list[Finding]:
        """Rows l and m of TCW-111 Design 2.6 for this store's own `objects`:
        a `parent` that is malformed, of another namespace, names the object
        itself or nothing, or forms a loop among this project's own objects,
        is an error; one in a project not on this machine is `unresolved`;
        a folder parent that `parent` does not name is a warning. With
        `selected`, only that object's are kept. `declared` holds, by
        id-path, the `parent` each object's own declaration sets, when it
        differs from the object as the project sees it: only a reference the
        project declares is checked here (TCW-112 Design 6.2)."""
        out: list[Finding] = []
        own: dict[str, str] = {}
        for obj in objects:
            id_path = getattr(obj, "slug", None) or obj.path
            where = self._where(id_path)
            keep = selected is None or id_path == selected
            parent = obj.parent
            if isinstance(parent, FullId) and parent.project == self.project_id:
                own[id_path] = parent.id_path
            if not keep:
                continue
            if declared is not None:
                parent = declared.get(id_path)
            if parent is not None:
                if isinstance(parent, FullId) and parent == obj.full_id:
                    out.append(Finding("error", where, "parent names the object itself"))
                else:
                    outcome = self._stored_ref(str(parent), self.COMPONENT)
                    problem = _ref_finding("parent", parent, outcome)
                    if problem:
                        out.append(Finding(problem[0], where, problem[1]))
            warning = self.folder_disagreement(obj)
            if warning:
                out.append(Finding("warning", self._where(self.root / id_path /
                                                          self.STATE_FILE), warning))
        def parent_of(id_path: str) -> str | None:
            # A scoped check reads only the objects up the selected one's
            # chain, never the whole store, which may hold a broken file.
            if id_path not in own and selected is not None:
                try:
                    obj = self.declaration(id_path)
                except (TcwError, OSError, ValueError, yaml.YAMLError):
                    obj = None
                parent = getattr(obj, "parent", None)
                own[id_path] = (parent.id_path if isinstance(parent, FullId)
                                and parent.project == self.project_id else None)
            return own.get(id_path)
        # A loop among this project's own objects (choice 13), each member
        # named once, at every member.
        for start in sorted(own):
            chain, at = [start], parent_of(start)
            while at is not None and at not in chain:
                chain.append(at)
                at = parent_of(at)
            if at != start or len(chain) == 1:      # one naming itself is said above
                continue
            if selected is not None and selected not in chain:
                continue
            loop = " -> ".join(str(FullId(self.project_id, self.COMPONENT, p))
                               for p in [*chain, start])
            out.append(Finding("error", self._where(start), f"parent forms a loop: {loop}"))
        return out

    def _input_ref(self, text, label: str):
        """The entry a reference value given to a write names, read as command
        input is (TCW-110 Design 3.1), for the full identifier the write
        stores (Design 5.3). A value naming nothing is a usage error."""
        from tcw.locate import find_tree
        try:
            return find_tree(self, str(text))
        except NotFound:
            raise _DanglingRef(f"{label} ref '{text}' does not resolve") from None

    @classmethod
    def open(cls, project_root: Path, locator=None):
        """Resolve this project's store for this component. The ladder is
        `resolve_store`, shared with the work store.

        `locator` is the command's `Locator` when the store opened is not the
        active project's own (TCW-110 Design 6.1): the store then looks
        projects up on that one registry, and is another project's store
        (TCW-112 choice 4). None means it is the active one.
        """
        return resolve_store(cls, project_root,
                             active_root=None if locator is None else locator.root)

    @classmethod
    def _local_root(cls, project_root: Path, configured: str | None, *,
                    locator=None) -> Path:
        """Where this component's tree sits on this machine, per
        `<component>.path`, or the default `docs/<component>`
        (`store_location`)."""
        return store_location(project_root, cls.COMPONENT, configured, locator=locator)

    @classmethod
    def _open_at(cls, raw_root: Path, project_root: Path, config_path: Path, *,
                 external: bool, must_exist: bool = True,
                 declaration: "RepositoryDeclaration | None" = None,
                 active_root: Path | None = None):
        """Build the store at a candidate root, validating it only when
        something points at it.

        `declaration` is accepted and deliberately ignored: a tree store never
        publishes. A taxonomy term or a capability status is a claim *about the
        code*, realized when the code implementing it merges, so the edit belongs
        to that change and lands with it. Publishing one on its own would
        announce a capability to everyone reading the ledger while the code
        making it true is still unmerged. Work is different — an item's state is
        the record of a session and changes independently of any code.

        A tree store has no layout to check — see `_is_store_layout` — so
        "usable" is "the directory is there", and that is the strongest honest
        answer rather than a shortcut. When `must_exist` is false this validates
        nothing at all, which is the pre-ladder behaviour for a component's bare
        default and the contract every existing project relies on.
        """
        if must_exist:
            # `StoreLocationUnusable`, not a bare `ValueError`: the ladder falls
            # through on "there is no store here" and must *not* fall through on
            # anything the store itself reports while opening.
            if raw_root.is_symlink() and not raw_root.exists():
                raise StoreLocationUnusable(
                    f"{config_path}: {cls.COMPONENT}.path is a broken symlink: {raw_root}")
            if not raw_root.is_dir():
                raise StoreLocationUnusable(
                    f"{config_path}: {cls.COMPONENT}.path is not a directory: {raw_root}")
        root = raw_root.resolve() if raw_root.exists() else raw_root
        owner = (git_root(root) if external else project_root) or project_root
        # The project stays the project — its parent links decide what it
        # inherits — while writes follow the store into whatever repository holds it.
        return cls(root, project_root=project_root, store_git_root=owner,
                   active_root=active_root)

    # -- containment: a store id never names a file outside its own store --
    #
    # `_safe_store_id` closes every *syntactic* escape and never touches the
    # filesystem, so a symlink planted inside a store is lexically clean and the
    # join lands wherever it points. These two restore the bound. Not race-safe
    # and not claiming to be: nothing binds the later open()/mkdir to the object
    # resolved here, so an attacker who can swap a directory for a symlink mid
    # command defeats it — and one with write access to the store has cheaper
    # attacks. What this restores is the stated property, against a symlink that
    # is already on disk when the command runs.

    @cached_property
    def _resolved_root(self) -> Path:
        """The store root with symlinks resolved.

        A `cached_property` rather than an `__init__` assignment, so a subclass
        whose `__init__` does not chain to this one still has it. Cached for the life of
        the instance — one CLI command, one HTTP request.
        """
        return self.root.resolve()

    def _entry_readable(self, d: Path) -> bool:
        """Whether `d` is an entry this store may read — folder *and* own meta.

        Two questions, because they fail apart: the folder can be reached
        through a symlink out of the store, or the folder can be ordinary while
        its state file is the symlink. Guarding only the folder leaves the
        second open, and an escaped meta reads as `{}`, which `_term` would turn
        into a *phantom* term named after its own slug rather than a miss.
        """
        return self._within_store(d) and self._within_store(d / self.STATE_FILE)

    def _state(self, d: Path) -> dict:
        """The object folder `d`'s state file, without `tcw-version`: `{}`
        when it has none or the file escapes the store, and `StateFileProblem`
        (exit 1) when its version is one this TCW cannot read, so such a file
        is never interpreted or rewritten (TCW-111 Design 1.5)."""
        path = d / self.STATE_FILE
        if not self._within_store(path):
            return {}
        data, problem = read_state(path, load_yaml)
        if problem is not None:
            raise StateFileProblem(path, problem)
        return data

    def _listable(self, d: Path) -> bool:
        """Whether a listing may show the object folder `d`: not when its
        state file's version cannot be read, which is recorded in
        `unreadable` instead (Design 1.5). A file that cannot be parsed at
        all stays listed, as in 3.x: the readers that parse it report it."""
        try:
            self._state(d)
        except StateFileProblem as problem:
            self.unreadable[problem.path] = problem.problem
            return False
        except (OSError, UnicodeDecodeError, yaml.YAMLError, ValueError):
            return True
        return True

    def unreadable_files(self) -> dict[Path, str]:
        """`unreadable`, with each source's object a listing of the view left
        out because it is a member of an id-path's chain (TCW-112 Design
        1.3): what a `list` left out."""
        return {**self.unreadable, **self._view_unreadable}

    def _unreadable_findings(self) -> list[Finding]:
        """An error for each object of this store a listing left out (Design
        1.5); no other check of its file runs."""
        return [Finding("error", self._where(path), problem)
                for path, problem in sorted(self.unreadable.items())]

    def _within_store(self, path: Path) -> bool:
        """True iff `path` stays inside the store root once symlinks resolve.

        Both sides are resolved: taxonomy and capabilities roots keep whatever
        lexical spelling they were opened with, so comparing a resolved path to
        an unresolved root would reject a checkout reached through a symlinked
        ancestor.

        `RuntimeError` as well as `OSError`: a symlink loop raises `RuntimeError`
        on Python < 3.13 — not an `OSError` — and since 3.13 raises nothing,
        returning the path unresolved. The floor is 3.11, so both eras are live.
        A loop answering True is harmless and deliberately not pinned: every read
        through one fails with ELOOP, and every caller stats before it reads.
        """
        try:
            return path.resolve().is_relative_to(self._resolved_root)
        except (OSError, RuntimeError):       # broken symlink; loop on < 3.13
            return False


    # -- the project's own `tcw-config.yaml` --
    #
    # On `FsTreeStore` rather than on one component: it is the project's file,
    # not any store's, and the two roots vary independently.

    def _config_path(self) -> Path:
        """The project sentinel's path. Not resolved — `FsTreeStore` keeps
        `project_root` as it was handed over, and a plain join is correct either
        way."""
        return self.project_root / SENTINEL

    def _config(self) -> dict:
        """Read the project sentinel config, tolerant of absence/emptiness. A
        malformed file raises a clear error naming the path rather than a raw
        YAML traceback. Plain board listing never calls this, so a broken config
        only fails operations that actually need it."""
        return load_config(self._config_path())

    def _component_config(self) -> dict:
        """This component's section of the project config, as a mapping.

        Mirrors `resolve_store` exactly, and has to: a section that is present
        but not a mapping normalizes to `{}` there (see the `isinstance` guard
        beside `<component>.path`), so doing anything else here would turn
        `taxonomy: docs/tax` into an `AttributeError` on a path `resolve_store`
        answers calmly.
        """
        section = self._config().get(self.COMPONENT)
        return section if isinstance(section, dict) else {}

    def _write_project_config(self, edits: list) -> None:
        """Apply `edits` to the project sentinel and write it. Nothing is staged:
        TCW 3.0 writes files and leaves git to the user (TCW-73 Design 8.1).

        Only the lines of the keys being changed are touched — comments and
        formatting everywhere else survive — and a file that cannot be edited
        that way is refused, not rewritten (`config_edit`). Edits that change
        nothing write nothing.
        """
        config_path = self._config_path()
        self._config()                           # a malformed file refuses as before
        text = config_edit.edit_text(config_path, config_edit.read_text(config_path), edits)
        if text is None:
            return
        self._write_files([(config_path, text)])

    def _write_files(self, pairs: list[tuple[Path, str]], *,
                     owned_dir: Path | None = None,
                     removed: tuple[Path, ...] = ()) -> None:
        """Write every `(path, content)`, undoing what *this call* created if
        the write fails, then re-raising; on success, record each path written
        and each path in `removed` (a deletion the caller made just before).

        **Never removes a path that was already there.** `owned_dir` is a
        directory the caller proved it created (`_mkdir_owned`) and is removed
        whole; everything else is per file, and only files absent when this
        call began. Best-effort and silent: the undo must not mask the original
        error.
        """
        # `exists() or is_symlink()`: `exists()` follows the link, so a
        # pre-existing *dangling* symlink read as absent, was replaced by a real
        # file, and was then unlinked here — destroying a path this call did not
        # create. Same idiom `init`'s ancestor walk uses for the same reason.
        new = [p for p, _ in pairs if not (p.exists() or p.is_symlink())]
        try:
            _atomic_write_all(pairs)
        except BaseException:
            if owned_dir is not None:
                shutil.rmtree(owned_dir, ignore_errors=True)
            else:
                for p in new:
                    with suppress(OSError):
                        p.unlink()
            raise
        self.changed += [("removed", p) for p in removed]
        self.changed += [("wrote", p) for p, _ in pairs]
        self._forget()

    def _rm(self, path: Path) -> None:
        """Delete a folder entry from disk, whatever git knows of it, recording
        one `removed` line per file it held."""
        self._forget()
        if path.is_symlink():
            path.unlink()
            self.changed.append(("removed", path))
            return
        files = sorted(f for f in path.rglob("*") if f.is_file() or f.is_symlink())
        # Every entry that can be deleted is, and each failure is kept: a bare
        # `rmtree` stops at the first one, so what it had deleted by then
        # depended on the order the folder lists its entries in.
        errors: list[BaseException] = []
        if sys.version_info >= (3, 12):
            shutil.rmtree(path, onexc=lambda _f, _p, exc: errors.append(exc))
        else:
            shutil.rmtree(path, onerror=lambda _f, _p, info: errors.append(info[1]))
        if errors:
            # A delete that stops partway has still deleted files, and each one
            # must be named. Which ones went is read back from the disk, so the
            # lines name exactly what changed.
            e = errors[0]
            gone = [f for f in files if not (f.exists() or f.is_symlink())]
            self.changed += [("removed", f) for f in gone]
            left = [f for f in files if f not in gone]
            what = (", ".join(_shown(f) for f in left) if left
                    else f"the folder {_shown(path)}")
            reason = getattr(e, "strerror", None) or e
            raise BackendError(f"the removal was partial: {len(gone)} of {len(files)} "
                               f"files removed; still present: {what} "
                               f"({reason})") from None
        self.changed += [("removed", f) for f in files]


    # -- shared folder-entry anatomy (state file + description.md + attachments) --
    #
    # A "entry" is a folder holding its state file (named fields), a
    # `description.md` (the body), and zero or more named attachment files. Both
    # the taxonomy and capabilities adapters realize their items this way; the
    # read/write mechanics live here so they are defined once. (Abstract spine:
    # body + named fields + named attachments — bounded, never globbed open.)

    def _entry_texts(self, d: Path) -> list[str]:
        """A folder entry's [meta, description] texts; empty strings when absent."""
        return [f.read_text(encoding="utf-8")
                if f.is_file() and self._within_store(f) else ""
                for f in (d / self.STATE_FILE, d / "description.md")]

    def _resource_files(self, d: Path) -> list[str]:
        """The files under the entry folder `d`'s `resources/`, at any depth,
        as paths relative to `d`, sorted: its attachments (TCW-111 Design 2.2).

        `exact_child`, so a `Resources/` folder on a disk that ignores letter
        case is never read as it. Hidden names are left out, as they were from
        the 3.x loose-file listing, and each file is asked `_within_store`, so
        one that is a symbolic link out of the store is not an attachment. Only
        `resources/` is read: a file loose in the folder is no attachment
        whatever its name, so the leftover per-store config files (`config.yaml`,
        `.config.yaml`) that the 3.x listing had to leave out by name are left
        out by construction, and reported as loose files by the shape check."""
        if exact_child(d, RESOURCES) is not True:
            return []
        folder = d / RESOURCES
        if folder.is_symlink() or not folder.is_dir():
            return []
        found = []
        for f in folder.rglob("*"):
            rel = f.relative_to(d)
            if any(part.startswith(".") for part in rel.parts):
                continue
            if f.is_file() and self._within_store(f):
                found.append(rel.as_posix())
        return sorted(found)

    def _in_resources(self, d: Path, name: str) -> bool:
        """Whether the listed document `name` resolves inside the entry folder
        `d`'s own `resources/` (TCW-111 Design 2.2), and inside the store.
        With no `resources/` yet, by its spelling, so a document listed there
        and not written is a missing attachment rather than a misplaced one."""
        spelled = exact_child(d, RESOURCES)
        if spelled is False:
            parts = Path(name).parts
            return bool(parts) and parts[0] == RESOURCES and ".." not in parts \
                and len(parts) > 1
        if spelled is not True:
            return False
        folder = d / RESOURCES
        try:
            (d / name).resolve().relative_to(folder.resolve())
        except (ValueError, OSError, RuntimeError):
            return False
        return self._within_store(d / name)

    def _shape_findings(self, id_path: str | None = None) -> list[Finding]:
        """Rows a to g of TCW-111 Design 2.6 for this store: a whole store's
        when `id_path` is None, else only the rows naming a file or folder
        directly inside that object's own folder (a, b, c and f), which is how
        `tcw serve` checks the object it just wrote. Row d leaves out the
        leftover config file `_legacy_config_problems` already reports."""
        found = walk(self.root, self.COMPONENT)
        if id_path is not None:
            def own(path: str) -> bool:
                return path.rpartition("/")[0] == id_path
            found = Walk(found.objects,
                         tuple(f for f in found.folders
                               if own(f[0]) and f[1] in (MISPLACED, RESERVED, LEGACY)),
                         tuple(f for f in found.files if own(f[0]) and f[1] == EXTRA),
                         found.resources)
        skip = {self.root / self.LEGACY_CONFIG_NAME} if self.LEGACY_CONFIG_NAME else set()
        named = [p for p in found.objects if id_path is None or p == id_path]
        return shape_problems(found, self.root, self.COMPONENT, self.project_id,
                              where=self._where, skip=skip) + \
            length_problems(named, self.root, self.COMPONENT, self.project_id,
                            where=self._where)

    def _where(self, path: Path | str) -> str:
        """A finding's `where`: `path`, or an entry's slug joined onto the store
        root, relative to the project root when it is inside it."""
        path = self.root / path if isinstance(path, str) else path
        try:
            return str(path.relative_to(self.project_root))
        except ValueError:
            return str(path)

    def _store_finding(self, message: str, level: str = "error") -> Finding:
        """A finding about what the project inherits, which its
        `tcw-config.yaml` configures."""
        return Finding(level, self._where(self._config_path()), message)

    def _legacy_config_problems(self) -> list[Finding]:
        """The pre-2.5.0 config file at this store's root, reported, or `[]`.

        An upgraded project that never moved its inheritance out of this file
        silently lost every inherited entry, and nothing said why. So a copy at
        the store root is a problem whatever it holds. Existence only: the file
        is never opened, so a corrupt copy cannot make `check` raise, and it is
        never rewritten or deleted (TCW-112 Design 6.8).

        Only the root: a file of the same name inside a folder entry is an
        ordinary file of that entry.
        """
        if not self.LEGACY_CONFIG_NAME:
            return []
        path = self.root / self.LEGACY_CONFIG_NAME
        if not path.is_file():
            return []
        return [Finding("error", self._where(path),
                        "no longer read since TCW 2.5.0; a project inherits taxonomy "
                        "and capabilities from its parents (parents: in "
                        ".tcw/tcw-config.yaml); delete this file")]

    # -- inheritance: the view (TCW-112 Design 1, 2) --
    #
    # The active project's objects at each id-path are combined over its
    # sources by `combine` (`tcw/store/base.py`), which reads no file; what
    # is read here is each source's own declarations, and the files their
    # folders hold. Nothing is read from another project until a reader
    # asks for something that needs it (Design 1.4).

    def _forget(self) -> None:
        """Drop what was read of this store, after a write changed it."""
        self._view_cache = None
        self._decl_cache = None

    def _has_parent_links(self) -> bool:
        """Whether this project's own file names any parent. A project with
        none is its own only source (UC-1), so no registry is asked."""
        return bool(self._config().get("parents"))

    def _source_entries(self) -> list:
        """`source_entries` of this store's project for its axis, gaps
        included, ending with the project; just the project when it has no
        parent links."""
        if not self._has_parent_links():
            return []
        registry = self.locator.registry
        if self._as_other:
            return registry.source_entries(self.COMPONENT, self.project_id,
                                           root=self.project_root)
        return registry.source_entries(self.COMPONENT)

    def _source_ids(self) -> set[str]:
        """The IDs of the projects that pass this store's axis to its project,
        whether or not each is here, read without opening any store."""
        try:
            return {entry.id for entry in self._source_entries()} - {self.project_id}
        except (TcwError, ValueError):
            return set()

    def _source_stores(self) -> list[tuple[str, "FsTreeStore"]]:
        """Each source of this store's project for its axis other than the
        project itself (Design 1.1), in load order, with its store, opened
        from its own committed configuration through the command's one
        registry. A source with no store for the axis is left out (Design
        1.2). Raises `InheritedUnavailable` when a source is not here, or its
        links or its store cannot be read (Design 1.3)."""
        entries = self._source_entries()
        if not entries:
            return []
        registry = self.locator.registry
        for entry in entries:
            if entry.state != "here":
                raise registry.unavailable(self.project_id, entry.id, self.COMPONENT,
                                           missing=entry.state == "missing")
        found = []
        for entry in entries[:-1]:
            try:
                store = self.locator.store(entry.id, self.COMPONENT,
                                           Path(entry.project.locator))
            except ValueError as error:
                # Not provisioned, declared wrongly, or any other reason its
                # store cannot open (Design 1.3's third case).
                raise registry.unavailable(self.project_id, entry.id, self.COMPONENT,
                                           store_message=str(error)) from None
            if store.root.is_dir():
                found.append((entry.id, store))
        return found

    def own_paths(self) -> list[str]:
        """The id-paths of this project's own objects (TCW-112 choice 1), in
        name order. Reads no other project."""
        return [p for p in object_paths(self.root, self.COMPONENT)
                if self._entry_readable(self.root / p)]

    def has_own(self, id_path: str) -> bool:
        """Whether this project has an object of its own at `id_path`, every
        folder spelled exactly as given (TCW-111 Design 2.5). Reads no other
        project and no state file's contents."""
        try:
            id_path = _safe_store_id(id_path, "id-path")
        except UsageError:
            return False
        d = self.root / id_path
        # The cheap stat first, so a miss pays no `resolve()`; containment
        # second; the spelling, read from the listings, third.
        return d.is_dir() and self._entry_readable(d) \
            and is_object(self.root, self.COMPONENT, id_path)

    def _declared_description(self, d: Path) -> str | None:
        """The object folder `d`'s declared description (Design 2.3): its
        `description.md`, possibly empty, or None when it has none."""
        desc = d / "description.md"
        if desc.is_file() and self._within_store(desc):
            return desc.read_text(encoding="utf-8")
        return None

    def _declarations(self) -> dict[str, "Declaration | None"]:
        """This project's own declarations, by id-path (Design 2.2, 2.3):
        each state file without `tcw-version`, and the declared description.
        None for an object whose state file's version cannot be read, which
        is recorded in `unreadable` (TCW-111 Design 1.5): the object exists,
        and its contents are not read. Reads no other project."""
        if self._decl_cache is None:
            found: dict[str, Declaration | None] = {}
            for id_path in self.own_paths():
                d = self.root / id_path
                try:
                    meta = self._state(d)
                except StateFileProblem as problem:
                    self.unreadable[problem.path] = problem.problem
                    found[id_path] = None
                    continue
                found[id_path] = Declaration(meta, self._declared_description(d))
            self._decl_cache = found
        return self._decl_cache

    def _declaration_at(self, id_path: str) -> tuple[bool, "Declaration | None"]:
        """Whether this project has an object of its own at `id_path`, and its
        declaration (None when its version cannot be read, recorded as in
        `_declarations`), reading that one object only, unless every
        declaration is already read. So one object's read is not stopped by
        a sibling whose file is malformed."""
        if self._decl_cache is not None:
            return id_path in self._decl_cache, self._decl_cache.get(id_path)
        if not self.has_own(id_path):
            return False, None
        d = self.root / id_path
        try:
            meta = self._state(d)
        except StateFileProblem as problem:
            self.unreadable[problem.path] = problem.problem
            return True, None
        return True, Declaration(meta, self._declared_description(d))

    def _own_declaration(self, id_path: str) -> "Declaration | None":
        """One own object's declaration, read alone. Raises `StateFileProblem`
        for a version this TCW cannot read."""
        d = self.root / id_path
        return Declaration(self._state(d), self._declared_description(d))

    def _view(self) -> "_View":
        """This project's view of its axis, built once (Design 1.4). Raises
        `InheritedUnavailable` when it cannot be built (Design 1.3)."""
        if self._view_cache is None:
            self._view_cache = _View(self, self._source_stores())
        return self._view_cache

    def _combined(self, id_path: str) -> "Combined | None":
        """The combined object at `id_path` in the view, or None. Raises the
        version problem of a chain member whose object cannot be read
        (Design 1.3)."""
        view = self._view()
        found = view.combined(id_path)
        if found is not None and found.unreadable is not None:
            raise view.unreadable_problem(id_path, found.unreadable)
        return found

    def get_view(self, id_path: str):
        """The object at `id_path` in this project's view (Design 3.1 form
        d), named by its chain's first member, or None."""
        if id_path_refused(id_path):
            return None
        found = self._combined(id_path)
        return None if found is None else self._record(id_path, found, self._view().stores)

    def get_local(self, id_path: str):
        """This project's own object at `id_path` as this project sees it,
        combined over its sources (Design 3.1, second row), or None when it
        has no object of its own there."""
        if not self.has_own(id_path):
            return None
        return self.get_view(id_path)

    def declaration(self, id_path: str):
        """This project's own object at `id_path` read from its own
        declaration alone, marked `partial` (Design 3.4), or None. Reads no
        other project."""
        if not self.has_own(id_path):
            return None
        alone = combine([(self.project_id, self._own_declaration(id_path))],
                        lambda a, b: False, axis=self.COMPONENT)
        return self._record(id_path, alone, {self.project_id: self}, partial=True)

    def chain(self, id_path: str) -> list[FullId]:
        """Design 2.1's chain at `id_path`, nearest first, as full
        identifiers; empty when nothing has an object there."""
        if id_path_refused(id_path):
            return []
        found = self._combined(id_path)
        return [] if found is None else \
            [FullId(pid, self.COMPONENT, id_path) for pid in found.chain]

    def inherited_at(self, id_path: str) -> FullId | None:
        """Design 2.7: the full identifier of the inherited object at
        `id_path`, the first member of the path's chain that is not this
        project, computed over its sources without its own object; or None."""
        if id_path_refused(id_path):
            return None
        view = self._view()
        found = view.combined(id_path, without=self.project_id)
        if found is None:
            return None
        if found.unreadable is not None:
            raise view.unreadable_problem(id_path, found.unreadable)
        return FullId(found.owner, self.COMPONENT, id_path)

    def view_warnings(self, id_paths=None) -> list[str]:
        """Design 2.5's warnings for `id_paths`, or for the whole view, ordered
        by id-path, then by the unused project's place in the load order."""
        view = self._view()
        out = []
        for id_path in sorted(view.paths() if id_paths is None else set(id_paths)):
            found = view.combined(id_path)
            for unused in (found.unused if found is not None else ()):
                if unused.warned:
                    out.append(clash_warning(self.COMPONENT, id_path, unused.project,
                                             unused.winner, self.project_id))
        return out

    def _listing(self, local_only: bool) -> list:
        """The view's objects, each id-path once, or with `local_only` the
        ones this project owns (Design 3.2). An id-path whose chain holds an
        object that cannot be read is left out and recorded (Design 1.3);
        with `local_only`, this project's own object there is given as its
        own declaration, marked partial."""
        view = self._view()
        self._view_unreadable = {}
        decls = self._declarations()
        if local_only:
            paths = [p for p in decls if decls[p] is not None]
        else:
            paths = view.paths()
        out = []
        for id_path in paths:
            found = view.combined(id_path)
            if found.unreadable is not None:
                problem = view.unreadable_problem(id_path, found.unreadable)
                self._view_unreadable[problem.path] = problem.problem
                if local_only:
                    out.append(self.declaration(id_path))
                continue
            out.append(self._record(id_path, found, view.stores))
        return out

    def own_declarations(self) -> list:
        """Each of this project's own objects read from its own declaration
        alone, marked partial (Design 3.4): what `list` under `--scope own`
        shows when the view cannot be built. Objects whose state file cannot
        be read are left out and recorded, as a listing leaves them."""
        decls = self._declarations()
        return [self.declaration(p) for p in decls if decls[p] is not None]

    def own_or_partial(self, id_path: str):
        """This project's own object at `id_path` as it sees it, or, when the
        view cannot be built, its own declaration alone, with `view_error`
        set (Design 3.4). None when it has no object there."""
        if not self.has_own(id_path):
            return None
        try:
            return self.get_local(id_path)
        except InheritedUnavailable as error:
            self.view_error = error
            return self.declaration(id_path)

    def _target_parts(self, target) -> tuple["FullId | None", str]:
        """`(full identifier or None, id-path)` for a target given as a full
        identifier, or text sorted as command input is (TCW-110 Design 3.1)."""
        if isinstance(target, str):
            found = sort_input(target, self.COMPONENT)
            if found.form == "d":
                return None, found.id_path
            target = found.full_id
        return target, target.id_path

    def _found(self, target: "FullId | str"):
        """The object an operation naming one existing object reads: a full
        identifier names its owner's own object as its owner sees it (Design
        3.1), and an id-path the object in this project's view."""
        full_id, id_path = self._target_parts(target)
        if full_id is None:
            return self.get_view(id_path)
        return self._as_seen_here(self._owner_store(full_id.project).get_local(id_path))

    def _as_seen_here(self, obj):
        """`obj`, read from its owner's store, with `origin` said from this
        store's side: "local" only when this project owns it."""
        if obj is None or obj.origin != "local" or obj.owner == self.project_id:
            return obj
        return dataclasses.replace(obj, origin=obj.owner)

    def _owner_store(self, project_id: str) -> "FsTreeStore":
        """The store of this axis of project `project_id`: this one for its
        own project, else the owner's, found through the command's
        `Locator`."""
        if project_id == self.project_id:
            return self
        locator = self.locator
        return locator.owner_store(project_id, self.COMPONENT, locator.root)

    def _no_such(self, target) -> str:
        noun = "term" if self.COMPONENT == "taxonomy" else "capability"
        return f"no such {noun}: {target}"

    def move(self, id_path: str, new_id_path: str, before_folder, *,
             report=None) -> list[tuple[FullId, FullId]]:
        """Design 8: `before_folder`, then one move of the object's folder,
        which carries every nested folder; the missing organising folders
        above the new place are made first, and removed again if the move
        fails."""
        from tcw.object_folders import move_object_folder, objects_below
        report = report or (lambda line: None)
        moved = [id_path, *objects_below(self.root, self.COMPONENT, id_path)]
        pairs = [(FullId(self.project_id, self.COMPONENT, p),
                  FullId(self.project_id, self.COMPONENT, new_id_path + p[len(id_path):]))
                 for p in moved]
        before_folder()
        old_path, new_path = self.root / id_path, self.root / new_id_path
        try:
            created = move_object_folder(self.root, id_path, new_id_path)
        except OSError as error:
            raise BackendError(f"could not move {_shown(old_path)} to "
                               f"{_shown(new_path)}: {error}") from None
        for rel in created:
            report(f"created {_shown(self.root / rel)}/")
        report(f"moved {_shown(old_path)} to {_shown(new_path)}")
        return pairs

    def removal_target(self, target: "FullId | str") -> FullId:
        """The full identifier of this project's own object that `rm` removes
        for `target` (TCW-112 choice 9). Another project's full identifier
        is refused before anything is read; this project's own one where it
        has no object, and an id-path nothing has an object at, are not
        found; an id-path the view shows as another project's is refused. An
        id-path this project has no object at when the view cannot be built
        is not found, since `rm` only removes this project's own objects
        (Design 4.4)."""
        from tcw.ownership import check_owned
        full_id, id_path = self._target_parts(target)
        if full_id is not None:
            # Another project's object is refused before anything is read,
            # by the one ownership check (TCW-114 Design 1.1, 1.3).
            check_owned(full_id, self._active_root)
        if self.has_own(id_path):
            return FullId(self.project_id, self.COMPONENT, id_path)
        if full_id is not None:
            raise NotFound(self._no_such(target))
        try:
            hit = self.get_view(id_path)
        except InheritedUnavailable:
            hit = None
        if hit is None:
            raise NotFound(self._no_such(target))
        # The view shows another project's object here: refused, since this
        # project has none of its own at the path to remove.
        check_owned(hit.full_id, self._active_root)
        raise NotFound(self._no_such(target))

    def _chain_texts(self, store: "FsTreeStore", id_path: str) -> list[str]:
        """Every chain member's state file and description at `id_path`, as
        `store` sees the path: what a revision token covers, so an edit to
        any member makes a held token stale."""
        view = store._view()
        found = store._combined(id_path)
        texts: list[str] = []
        for pid in (found.chain if found is not None else ()):
            member = view.stores[pid]
            texts += member._entry_texts(member.root / id_path)
        return texts

    def _write_meta(self, d: Path, meta: dict, *,
                    removed: tuple[Path, ...] = ()) -> None:
        """Write an entry's state file alone, rolling back what this call
        created.

        Owns the `mkdir` so it can prove whether the directory is its own: a
        write making a *fresh* override is the path where a refused write
        would otherwise leave an empty folder behind, and an update of an
        existing object is the path where removing the folder would take
        files this call never wrote.
        """
        owned = _mkdir_owned(d)
        self._write_files(
            [(d / self.STATE_FILE, state_text(d / self.STATE_FILE, meta))],
            owned_dir=d if owned else None, removed=removed)

    def _object_modified(self, d: Path, fields: dict) -> str:
        """When an object folder's files last changed."""
        return _modified_timestamp([d / self.STATE_FILE, d / "description.md"])

    def _load_entry(self, d: Path) -> tuple[dict, str, list[str]]:
        """Read a folder entry → (meta mapping, description text, attachment names).

        Attachments are the files under the folder's `resources/`
        (`_resource_files`), as paths relative to the folder.
        """
        # Containment per resource, not just per folder. A folder can be
        # legitimately inside the store while a file in it is a symlink pointing
        # out, and the folder guards upstream cannot see that. A resource that
        # escapes reads as *absent* — the same fail-closed shape `get_local`
        # already uses for the folder. An empty meta is what makes the entry stop
        # resolving: `_is_capability` and the `overrides` test both read falsey,
        # and a taxonomy entry with no kind is not a term.
        meta = self._state(d)
        desc = d / "description.md"
        description = (desc.read_text(encoding="utf-8")
                       if desc.exists() and self._within_store(desc) else "")
        return meta, description, self._resource_files(d)

    def _write_entry(self, d: Path, meta: dict, description: str) -> None:
        """Create/overwrite a folder entry's meta + description, atomically, staged.

        Rollback is `_write_files`'s: a failed write undoes this call's work.
        What it removes depends on who made the directory — the whole folder
        when this call did, only the files it created when the entry already
        existed. Same applies to `_write_meta`.
        """
        # `_mkdir_owned` rather than `exist_ok=True` + a prior `d.exists()`:
        # exactly one process's `mkdir` succeeds, so this is an ownership proof
        # with no check-then-act window — retiring the TOCTOU the old `existed`
        # probe carried, where a second writer creating the entry between our
        # check and our failure would have had its directory removed.
        owned = _mkdir_owned(d)
        self._write_files(
            [(d / self.STATE_FILE, state_text(d / self.STATE_FILE, meta)),
             (d / "description.md", description)],
            owned_dir=d if owned else None)


class _View:
    """One project's view of one axis (TCW-112 Design 2): its sources in
    load order, ending with the project, and each id-path combined by
    `combine` on first use from the members' own declarations there. Every
    member's declarations are read only when every id-path is asked for."""

    def __init__(self, store: "FsTreeStore", sources: list):
        self.store = store
        self.members = [*sources, (store.project_id, store)]
        self.stores = dict(self.members)
        self.order = [pid for pid, _ in self.members]
        self._combined: dict = {}
        self._passed_to: dict[str, set[str]] = {}

    def paths(self) -> list[str]:
        """Every id-path any member has an object at, in name order."""
        return sorted({p for _, st in self.members for p in st._declarations()})

    def passes(self, a: str, b: str) -> bool:
        """Whether project `a` passes the axis to project `b` (TCW-112 choice
        3): `a` is one of `b`'s sources and not `b`."""
        if b == self.store.project_id:
            return a != b and a in self.stores
        if b not in self._passed_to:
            member = self.stores[b]
            self._passed_to[b] = {entry.id for entry in member._source_entries()} - {b}
        return a in self._passed_to[b]

    def combined(self, id_path: str, *, without: str | None = None) -> Combined | None:
        """The object at `id_path` combined over the members that declare it,
        leaving out `without`'s declaration, or None."""
        key = (id_path, without)
        if key not in self._combined:
            declarers, unreadable = [], set()
            for pid in self.order:
                if pid == without:
                    continue
                present, declaration = self.stores[pid]._declaration_at(id_path)
                if not present:
                    continue
                if declaration is None:
                    unreadable.add(pid)
                    declaration = Declaration({})
                declarers.append((pid, declaration))
            self._combined[key] = combine(declarers, self.passes,
                                          axis=self.store.COMPONENT,
                                          unreadable=frozenset(unreadable))
        return self._combined[key]

    def unreadable_problem(self, id_path: str, project_id: str) -> StateFileProblem:
        """The version problem of `project_id`'s object at `id_path`."""
        member = self.stores[project_id]
        path = member.root / id_path / member.STATE_FILE
        return StateFileProblem(path, member.unreadable.get(path, "cannot be read"))


#: Design 6.4's message for a TCW 3.x override pointer.
_OVERRIDES_REMOVED = ("'overrides' was removed in TCW 4.0: an override is an object at "
                      "the same path as the object it overrides; run 'tcw migrate' in "
                      "this project, or move this folder to that path and delete the key")


def _not_inherited(full_id: FullId, project_id: str, active_root: Path) -> None:
    """Design 4.2's refusal of another project's object outside the chain,
    by the one ownership check, with Design 4.2's reason (TCW-114 Design
    1.3)."""
    from tcw.ownership import check_owned
    check_owned(full_id, active_root, reason=f", and '{project_id}' does not "
                                             f"inherit it, so it cannot be "
                                             f"overridden here")


def _incomplete(full_id: FullId, declaration: Declaration, axis: str) -> str | None:
    """Design 6.1's error for an object that overrides nothing and lacks a
    part of a complete one, naming each part, or None."""
    missing = ["description.md" if part == "description" else part
               for part in missing_parts(declaration, axis)]
    if not missing:
        return None
    named = missing[0] if len(missing) == 1 else \
        f"{', '.join(missing[:-1])} or {missing[-1]}"
    return (f"{full_id} is incomplete: it overrides nothing, and has no {named}; if it "
            f"overrode an object that moved or was removed, complete it or remove it")


def _view_or_error(store: FsTreeStore) -> tuple["_View | None", "InheritedUnavailable | None"]:
    """The store's view, or None and why it could not be built: what
    `check` runs on (TCW-112 Design 6.5)."""
    try:
        return store._view(), None
    except InheritedUnavailable as error:
        return None, error


def _selected(store: FsTreeStore, identifier: str, view):
    """`(id-path, object, own)` for a check scoped to `identifier`: the
    project's own object read alone when it has one (a version this TCW
    cannot read raises `StateFileProblem`), else the view's, which needs the
    view."""
    if store.has_own(identifier):
        store._own_declaration(identifier)
        return identifier, True, True
    if view is None:
        raise store.view_error
    return identifier, store.get_view(identifier), False


def _combined_or_problem(store: FsTreeStore, view, id_path: str,
                         problems: list[Finding]) -> Combined | None:
    """The combined object at one of the store's own id-paths, for `check`;
    None when the view could not be built, or when a member of the path's
    chain cannot be read, which adds Design 1.3's `unresolved` finding (the
    project's own unreadable object is reported at its file instead)."""
    if view is None:
        return None
    found = view.combined(id_path)
    if found is None or found.unreadable is None:
        return found
    if found.unreadable != store.project_id:
        problem = view.unreadable_problem(id_path, found.unreadable)
        problems.append(store._store_finding(
            f"could not check {store.COMPONENT} {id_path}: {problem}", "unresolved"))
    return None


# ── FsTaxonomyStore ─────────────────────────────────────────────────────────

TAXONOMY_KINDS = {"Vocabulary", "Feature"}


def _normalize_taxonomy_kind(kind: str | None) -> str:
    if not kind:
        return "Vocabulary"
    by_lower = {k.lower(): k for k in TAXONOMY_KINDS}
    return by_lower.get(str(kind).lower(), str(kind))


class _DanglingRef(UsageError):
    """A reference value given to a write names nothing."""


class _RefInputProblem(UsageError):
    """One reference value a capability write cannot store, worded as
    `check` words it; collected, never raised out of the store."""


def _stored_parent(value, namespace: str) -> "FullId | str | None":
    """A state file's `parent` (TCW-111 Design 3.1): its full identifier, the
    text as written when it is none, which `check` reports, or None."""
    if value is None:
        return None
    try:
        return parse_stored(value, namespace)
    except IdError:
        return str(value)


def _ref_finding(label: str, ref, outcome) -> "tuple[str, str] | None":
    """`(level, message)` for a stored reference that was not found, worded
    as `check` reports it, or None when it was."""
    from tcw.locate import ERROR, MISSING, UNRESOLVED
    lead = f"{label} " if label else ""
    if outcome.kind == MISSING:
        return "error", f"dangling {lead}ref '{ref}'"
    if outcome.kind == UNRESOLVED:
        return "unresolved", f"{lead}ref '{ref}' could not be checked: {outcome.message}"
    if outcome.kind == ERROR:
        if outcome.message.startswith(repr(str(ref))):
            return "error", f"{lead}{outcome.message}"      # its form, naming it
        return "error", f"{lead}ref '{ref}' cannot be looked up: {outcome.message}"
    return None


def _wrong_kind_ref(ref: str, kind: str) -> str:
    """The one wording for "this vocabulary ref points at the wrong kind"."""
    return f"vocabulary ref '{ref}' points to {kind}, expected Vocabulary"


class FsTaxonomyStore(FsTreeStore, TaxonomyStore):
    """`TaxonomyStore` over nested dirs under `docs/taxonomy/` (Phase 2 B.3).

    A term's slug is its directory path under the taxonomy root. What the
    project inherits comes from its parent links, each id-path's term
    combined over its sources (TCW-112 Design 1, 2).
    """
    COMPONENT = "taxonomy"
    LEGACY_CONFIG_NAME = "config.yaml"
    STATE_FILE = STATE_FILES["taxonomy"]

    # -- reads --

    def _record(self, slug: str, found: Combined, stores: dict, *,
                partial: bool = False) -> Term:
        """The term `found` combines at `slug`, read from the members'
        folders in `stores` (Design 2.2-2.4)."""
        fields = found.fields
        folders = [stores[pid].root / slug for pid in found.chain]
        # A term's attachments are its nearest member's that holds any
        # (Design 2.3): the list is replaced whole.
        attachments: list[str] = []
        for pid, d in zip(found.chain, folders):
            attachments = stores[pid]._resource_files(d)
            if attachments:
                break
        return Term(
            slug=slug,
            name=fields.get("name") or slug.rsplit("/", 1)[-1].replace("-", " ").title(),
            description=found.description or "",
            kind=_normalize_taxonomy_kind(fields.get("kind")),
            relates_to=list(fields.get("relatesTo") or []),
            vocabulary=list(fields.get("vocabulary") or []),
            attachments=attachments,
            origin="local" if found.owner == self.project_id else found.owner,
            modified=max((self._object_modified(d, {}) for d in folders), default=""),
            owner=found.owner,
            parent=_stored_parent(fields.get("parent"), "taxonomy"),
            overrides=None if partial or found.overrides is None
            else FullId(found.overrides, "taxonomy", slug),
            partial=partial,
        )

    def _local_slugs(self) -> list[str]:
        # The walk is the one listing of a store's objects (TCW-111 Design
        # 2.5): a folder with no state file is never a term. `list` must not
        # advertise what `show`/`rm` refuse, so a state file reached through
        # a symbolic link out of the store is left out too; the walk never
        # enters a symlinked folder, but the file itself can be one.
        return [p for p in object_paths(self.root, "taxonomy")
                if self._entry_readable(self.root / p) and self._listable(self.root / p)]

    def list_all(self, local_only: bool = False) -> list[Term]:
        return self._listing(local_only)

    def search(self, query: str) -> list[Term]:
        return [t for t in self.list_all() if text_matches(t.name, t.description, query)]

    # -- writes --

    def add(self, name: str, slug: str | None = None, parent: str | None = None,
            description: str = "", kind: str | None = None,
            vocabulary: list[str] | None = None) -> Term:
        leaf = _safe_store_id(slug or slugify(name), "slug")
        # After `_safe_store_id`, so a slug that would leave the store is still
        # "invalid slug"; nesting is `parent`'s job, so a `/` is refused here.
        if slug and not is_slug(leaf):
            raise NotASlug(f"{slug!r} is not a slug: use lowercase letters, "
                           f"digits and single hyphens")
        # The parent is any term TCW can find (TCW-111 Design 3.3): the
        # folder goes inside it when it is this store's own, else at the root,
        # and `parent:` is written either way. Not found is exit 4.
        parent_term = self.find_parent(parent) if parent else None
        inside = (parent_term.slug if parent_term is not None
                  and parent_term.owner == self.project_id else None)
        if parent_term is not None and inside is None:
            # A parent this project only sees through its view: when the path
            # inside it is inherited, the new term is that path's override,
            # and the folders between are made as organising folders (TCW-112
            # Design 4.1).
            nested = f"{parent_term.slug}/{leaf}"
            if self.get_view(parent_term.slug) is not None \
                    and self.get_view(parent_term.slug).full_id == parent_term.full_id \
                    and self.inherited_at(nested) is not None:
                inside = parent_term.slug
        full = f"{inside}/{leaf}" if inside else leaf
        _check_id_path(full, "slug")
        _check_reserved(full, "taxonomy", "slug")
        _check_length(self.project_id, "taxonomy", full)
        given_kind = None if kind is None else _normalize_taxonomy_kind(kind)
        if given_kind is not None and given_kind not in TAXONOMY_KINDS:
            raise UsageError(f"invalid taxonomy kind '{given_kind}' "
                             f"(choose: {', '.join(sorted(TAXONOMY_KINDS))})")
        d = self.root / full
        # Before `d.exists()` and before the first mkdir: one guard covers a
        # symlinked `--parent` and a symlinked leaf alike, and it keeps the
        # fail-closed contract below (a rejected write leaves no partial folder).
        if not self._within_store(d):
            raise UsageError(f"parent term does not exist: {parent or full}")
        if d.exists() or d.is_symlink():   # a dangling/looping link reads absent
            raise Refused(f"term already exists: {full}")
        inherited = self.inherited_at(full)
        if inherited is not None:
            return self._add_override(full, inherited, name, parent_term, description,
                                      given_kind, vocabulary)
        kind = given_kind or "Vocabulary"
        # Fail closed on refs *before* the first mkdir: a rejected write must
        # leave no partial folder behind. The same rules `check` applies, so a
        # term that `add` accepted never fails the very next `check`.
        if kind == "Feature" and not vocabulary:
            raise UsageError("Feature requires at least one vocabulary ref")
        meta = {"name": name, "kind": kind, "relatesTo": []}
        if parent_term is not None:
            meta["parent"] = str(parent_term.full_id)
        if vocabulary:
            meta["vocabulary"] = [self._resolve_vocab_ref(r) for r in vocabulary]
        self._write_entry(d, meta, description)
        return self.get_local(full)

    def _add_override(self, full: str, inherited: FullId, name: str, parent_term,
                      description: str, kind: str | None,
                      vocabulary: list[str] | None) -> Term:
        """`add` at a path this project inherits (TCW-112 Design 4.1): a term
        holding only what differs from the inherited one as this project sees
        it, and never `relatesTo`, which would clear the inherited list."""
        base = self.get_view(full)
        meta: dict = {}
        if name != base.name:
            meta["name"] = name
        if kind is not None and kind != base.kind:
            meta["kind"] = kind
        if vocabulary:
            meta["vocabulary"] = [self._resolve_vocab_ref(r) for r in vocabulary]
        if parent_term is not None and str(parent_term.full_id) != str(base.parent):
            meta["parent"] = str(parent_term.full_id)
        has_text = bool(description.strip())
        if not meta and not has_text:
            raise Refused(
                f"cannot add '{full}': '{self.project_id}' already inherits {inherited} "
                f"there, and nothing given differs from it; give a description on "
                f"standard input, --vocab, or a different name or kind")
        # The combined term's checks run before anything is written.
        if meta.get("kind", base.kind) == "Feature" \
                and not meta.get("vocabulary", base.vocabulary):
            raise UsageError("Feature requires at least one vocabulary ref")
        d = self.root / full
        if has_text:
            self._write_entry(d, meta, description)
        else:
            self._write_meta(d, meta)
        return self.get_local(full)

    def remove(self, ref: "FullId | str") -> None:
        target = self.removal_target(ref)
        slug = target.id_path
        d = self.root / slug
        # Refused, never cascaded, and decided from the disk (TCW-73 Design
        # 8.2): a nested object is a folder under this one holding a state
        # file of any store, or a 3.x file (TCW-111 Design 2.5). Everything
        # else in the folder — attachments, files an operating system writes
        # on its own, files git has never seen — goes with it. The search is
        # the folder's own, not the walk's, which skips hidden folders and
        # `resources/` that the removal deletes all the same.
        _blocked_removal(d, self.root, "taxonomy", slug)
        referrers = self._referrers(d) + self._capability_referrers(d, slug)
        if referrers:
            raise Refused(f"cannot remove '{slug}': still referenced by "
                             f"{', '.join(referrers)} (repoint or clear those first)")
        self._rm(d)

    def _capability_referrers(self, target: Path, slug: str) -> list[str]:
        """`capability <path> (Subject|Feature)` for every capability of this
        project whose own declaration names the term folder `target` or a
        folder inside it — what `tcw validate` would report dangling once it
        is gone (TCW-112 Design 7.3). An override is one of the project's own
        capabilities, and only what it declares is read.

        The project's capabilities store is found by the normal resolution. None
        here: nothing to ask. One that cannot be opened or read refuses the
        removal, because whether it names the term cannot then be known.
        """
        try:
            caps = FsCapabilitiesStore.open(
                self.project_root, locator=self.locator if self._as_other else None)
            if not caps.root.is_dir():
                return []
            declared = [(path, decl.fields) for path, decl in caps._declarations().items()
                        if decl is not None]
        except (ValueError, TcwError, yaml.YAMLError) as e:
            raise Refused(f"cannot remove '{slug}': the capabilities that might "
                             f"name it cannot be read: {e}") from None
        out = []
        for path, fields in declared:
            named = set()
            for field, ref in FsCapabilitiesStore._term_refs(fields):
                hit = self._local_ref(ref)
                if hit is not None and _in_folder(self.root / hit, target, self.root):
                    named.add(field)
            out += [f"capability {path} ({field})"
                    for field in ref_names("capability", namespace="taxonomy")
                    if field in named]
        return out

    def _referrers(self, target: Path) -> list[str]:
        """`<term> (<field>)` for every other term of this project whose own
        declaration's `relatesTo` or `vocabulary` names the term folder
        `target` or a folder inside it — exactly the refs `check` would report
        dangling once it is gone. Compared by folder identity, not spelling,
        so `admin/permission` never matches a top-level `permission`."""
        out = []
        for slug, decl in self._declarations().items():
            if decl is None or _in_folder(self.root / slug, target, self.root):
                continue
            fields = decl.fields
            # `vocabulary` only on a Feature, the one kind `check` reads it on;
            # an override that declares no kind may be one.
            declared_kind = fields.get("kind")
            vocabulary = fields.get("vocabulary") or [] \
                if declared_kind is None or \
                _normalize_taxonomy_kind(declared_kind) == "Feature" else []
            for field, refs in ((name, vocabulary if name == "vocabulary"
                                 else fields.get(name) or [])
                                for name in ref_names("term", parent=False)):
                for ref in refs:
                    hit = self._local_ref(ref)
                    if hit is not None and _in_folder(self.root / hit, target, self.root):
                        out.append(f"{slug} ({field})")
                        break
        return out

    # -- validation --

    def _ref_problem(self, ref, label: str, expect_vocabulary: bool = False
                     ) -> "tuple[Term | None, tuple[str, str] | None]":
        """Resolve one stored taxonomy ref (TCW-110 Design 5.2): `(term,
        problem)`, `problem` None when it names an entry (and, with
        `expect_vocabulary`, a Vocabulary one), else `(level, message)` as
        `check` reports it. The term is None when it exists but cannot be
        read as its owner sees it here, and its kind is then not checked."""
        from tcw.locate import FOUND
        outcome = self._stored_ref(ref, "taxonomy")
        if outcome.kind != FOUND:
            return None, _ref_finding(label, ref, outcome)
        term = outcome.value
        if expect_vocabulary and term is not None and term.kind != "Vocabulary":
            return term, ("error", _wrong_kind_ref(ref, term.kind))
        return term, None

    def _require_ref(self, ref, label: str, expect_vocabulary: bool = False) -> str:
        """A reference value given to a write (`add`, `update_term`), in any
        input form, as the full identifier it stores — or a usage error."""
        term = self._input_ref(ref, label)
        if expect_vocabulary and term.kind != "Vocabulary":
            raise UsageError(_wrong_kind_ref(ref, term.kind))
        return str(term.full_id)

    def _resolve_vocab_ref(self, ref: str) -> str:
        """A `--vocab` ref as it will be stored, its full identifier — or a
        usage error.

        A ref that names an entry as command input does is stored as that
        entry's full identifier. One that does not is retried as a *leaf
        slug* against the local tree, and the entry it matched is what gets
        stored. The asymmetry is deliberate: a leaf slug is an input
        convenience at the write boundary, not a stored identity, so no read
        path widens (`tcw taxonomy show zeta` still fails) while a stored ref
        always resolves for `check`. Local terms only.
        """
        try:
            return self._require_ref(ref, "vocabulary", expect_vocabulary=True)
        except _DanglingRef:
            matches = [s for s in self._local_slugs() if s.rsplit("/", 1)[-1] == ref]
            if len(matches) > 1:
                raise UsageError(f"vocabulary ref '{ref}' is ambiguous: "
                                 f"{', '.join(matches)}") from None
            if not matches:
                raise
            return self._require_ref(matches[0], "vocabulary", expect_vocabulary=True)

    def check(self, identifier: str | None = None) -> list[Finding]:
        problems: list[Finding] = []
        # A full listing first, so what is reported about state files that
        # cannot be read never depends on what was called before.
        self.unreadable.clear()
        self._forget()
        if identifier is None:
            # About the store, not any one term — left out of a scoped check,
            # which is how `tcw serve` validates the object it just wrote.
            problems += self._legacy_config_problems()
        view, self.view_error = _view_or_error(self)
        # Every own declaration only for the whole store: a scoped check
        # reads its one object, so a malformed sibling never stops it.
        decls = self._declarations() if identifier is None else {}
        if identifier is not None:
            try:
                slug, selected, own = _selected(self, identifier, view)
            except StateFileProblem as problem:
                return [Finding("error", self._where(problem.path), problem.problem)]
            if selected is None:
                return [Finding("error", self._where(self.root),
                                f"no such term: {identifier}")]
            slugs = [slug] if own else []
            problems += self._shape_findings(slug) if own else []
            if not own:
                problems += self._term_findings(selected, None)
        else:
            slugs = [p for p in decls if decls[p] is not None]
            problems += self._unreadable_findings()
            problems += self._shape_findings()
        records = []
        declared_parents = {}
        for slug in slugs:
            decl = decls.get(slug) if identifier is None else self._own_declaration(slug)
            found = _combined_or_problem(self, view, slug, problems)
            term = self._record(slug, found, view.stores) if found is not None \
                else self.declaration(slug)
            records.append(term)
            declared_parents[slug] = _stored_parent(decl.fields.get("parent"), "taxonomy")
            where = self._where(slug)
            state = self._where(self.root / slug / self.STATE_FILE)
            if (problem := _bad_name(slug)):
                problems.append(Finding("error", where, problem))
            if (problem := id_problem(decl.fields, slug)):
                problems.append(Finding("error", state, problem))
            if "overrides" in decl.fields:
                problems.append(Finding("error", state, _OVERRIDES_REMOVED))
            if found is not None and len(found.chain) == 1:
                if (problem := _incomplete(term.full_id, decl, "taxonomy")):
                    problems.append(Finding("error", state, problem))
            problems += self._term_findings(term if found is not None else None, decl)
        problems += self._parent_findings(
            records, None if identifier is None else slugs[0] if slugs else None,
            declared=declared_parents)
        if identifier is None and view is not None:
            problems += [self._store_finding(w, "warning") for w in self.view_warnings()]
        return problems

    def _term_findings(self, term: "Term | None", decl: "Declaration | None") -> list[Finding]:
        """The checks of one term (TCW-112 Design 6.2): its kind and a
        Feature's vocabulary on the term as the project sees it, when that
        could be read; the references only its own declaration sets."""
        problems: list[Finding] = []
        slug = term.slug if term is not None else None
        fields = decl.fields if decl is not None else None

        def found(where_slug: str, message: str) -> None:
            problems.append(Finding("error", self._where(where_slug), message))

        def report(where_slug: str, problem) -> None:
            if problem:
                problems.append(Finding(problem[0], self._where(where_slug), problem[1]))
        if term is not None:
            if term.kind not in TAXONOMY_KINDS:
                found(slug, f"unknown kind '{term.kind}'")
            if term.kind == "Feature" and not term.vocabulary:
                found(slug, "Feature requires at least one vocabulary ref")
        if fields is None:
            # An inherited term selected by a scoped check: its references
            # are its owner's to check.
            return problems
        where_slug = slug or ""
        for ref in fields.get("relatesTo") or []:
            report(where_slug, self._ref_problem(ref, "relatesTo")[1])
        kind = term.kind if term is not None else \
            _normalize_taxonomy_kind(fields.get("kind"))
        if term is None and kind not in TAXONOMY_KINDS and fields.get("kind") is not None:
            found(where_slug, f"unknown kind '{kind}'")
        if kind == "Feature":
            for ref in fields.get("vocabulary") or []:
                report(where_slug, self._ref_problem(ref, "vocabulary",
                                                     expect_vocabulary=True)[1])
        return problems

    def _validation_resources(self, identifier: str) -> list[Path]:
        """Filesystem resources bounded to one taxonomy object: every chain
        member's files at its id-path."""
        try:
            identifier = _safe_store_id(identifier, "taxonomy target")
        except UsageError:
            return []
        try:
            view = self._view()
            found = view.combined(identifier)
            members = [view.stores[pid] for pid in found.chain] if found else []
        except (InheritedUnavailable, StateFileProblem, yaml.YAMLError):
            # Its files are still this object's to scan, a malformed one
            # above all: the scan is what reports it.
            members = [self] if self.has_own(identifier) else []
        # Asked of each *owning* store: an inherited term's files are bounded
        # by its own root, not this one.
        return [path for owner in members
                for path in (owner.root / identifier / self.STATE_FILE,
                             owner.root / identifier / "description.md")
                if path.is_file() and owner._within_store(path)]

    # -- revision-bearing detail + update --

    def get_term_detail(self, ref: "FullId | str") -> "TermDetail" | None:
        full_id, slug = self._target_parts(ref)
        store = self if full_id is None else self._owner_store(full_id.project)
        term = self._found(ref)
        if term is None:
            return None
        return TermDetail(term=term,
                          core_revision=_revision_multi(*self._chain_texts(store, slug)))

    def update_term(self, ref: "FullId | str", *,
                    name=_UNSET, description=_UNSET, relates_to=_UNSET,
                    vocabulary=_UNSET, kind=_UNSET,
                    core_revision: str | None = None) -> "TermDetail":
        # The project's own term only, an override included (TCW-112 choice 6).
        term = self._found(ref)
        if term is None:
            raise NotFound(f"no such term: {ref}")
        if term.owner != self.project_id:
            raise Refused(f"cannot update inherited term '{term.full_id}' "
                             f"(edit it at its source)")
        d = self.root / term.slug

        # Validate provided fields against the editable set
        provided = {}
        for key, val in [("name", name), ("description", description),
                         ("relates_to", relates_to), ("vocabulary", vocabulary),
                         ("kind", kind)]:
            if val is not _UNSET:
                if key not in TAXONOMY_EDITABLE_FIELDS:
                    raise UsageError(f"field '{key}' is not editable")
                provided[key] = val

        # Stale revision check
        if core_revision is not None:
            detail = self.get_term_detail(ref)
            if detail and detail.core_revision != core_revision:
                raise StaleRevision(
                    f"stale revision for term '{ref}' "
                    f"(expected {core_revision}, got {detail.core_revision})")

        # Read the project's own declaration
        meta = self._state(d)
        declared = self._declared_description(d)
        desc_text = declared or ""

        # Apply changes
        if "name" in provided:
            meta["name"] = provided["name"] if provided["name"] is not None else ""
        if "description" in provided:
            desc_text = provided["description"] if provided["description"] is not None else ""
        # A reference given here, in any input form, is stored as its full
        # identifier (TCW-110 Design 5.3); one this edit does not give is left
        # as it is, and `check` reports it if it names nothing.
        if "relates_to" in provided:
            meta["relatesTo"] = [self._require_ref(r, "relatesTo")
                                 for r in provided["relates_to"] or []]
        if "vocabulary" in provided:
            meta["vocabulary"] = [self._require_ref(r, "vocabulary", expect_vocabulary=True)
                                  for r in provided["vocabulary"] or []]
        if "kind" in provided:
            new_kind = _normalize_taxonomy_kind(provided["kind"])
            if provided["kind"] is not None and new_kind not in TAXONOMY_KINDS:
                raise UsageError(f"invalid taxonomy kind '{new_kind}' "
                                 f"(choose: {', '.join(sorted(TAXONOMY_KINDS))})")
            meta["kind"] = new_kind if provided["kind"] is not None else "Vocabulary"

        # A Feature names at least one Vocabulary entry. Checked on the term as
        # the project will see it, its own new declaration combined over its
        # sources (TCW-112 choice 6); when this edit keeps the vocabulary, the
        # kept values are checked as stored.
        combined = self._view().combined(term.slug, without=self.project_id)
        inherited = combined.fields if combined is not None else {}
        merged = {**inherited, **{k: v for k, v in meta.items() if v is not None}}
        for k, v in meta.items():
            if v is None:
                merged.pop(k, None)
        if _normalize_taxonomy_kind(merged.get("kind")) == "Feature":
            vocs = merged.get("vocabulary") or []
            if not vocs:
                raise UsageError("Feature requires at least one vocabulary ref")
            if "vocabulary" not in provided:
                for r in vocs:
                    problem = self._ref_problem(r, "vocabulary", expect_vocabulary=True)[1]
                    if problem:
                        raise UsageError(problem[1])

        # Write atomically; an override that never declared a description
        # gains one only when this edit gives it.
        if declared is None and "description" not in provided:
            self._write_meta(d, meta)
        else:
            self._write_entry(d, meta, desc_text)

        # Return fresh detail
        return _require_detail(self.get_term_detail(ref), "term", ref)


# ── FsCapabilitiesStore ──────────────────────────────────────────────────────

def _cap_ref_rows():
    """The capability fields naming another capability, `parent` aside
    (TCW-110 Design 5.1), read from the one table of reference fields
    (TCW-114 Design 6.1) when they are needed, so a row added there is
    checked here."""
    return ref_rows("capability", namespace="capabilities", parent=False)
# `_stored_forms`' answer when the project has no taxonomy store to read.
_NO_TAXONOMY = object()

# Meta keys that are structural (not part of the locked CAP_FIELDS vocabulary).
# `id` and `overrides` are TCW 3.x keys that `check` reports (TCW-112 Design
# 5.3, 6.4); kept here so that neither is ever read as a field.
_CAP_STRUCTURAL = {"id", "name", "overrides", "prependedDocs", "appendedDocs", "parent"}


def heading_slug(text: str) -> str:
    """GitHub-flavored heading anchor: lowercased, punctuation stripped, spaces→'-'.

    Still used by the serve viewer for anchors; no longer part of capability
    identity (capabilities are path-addressed folders).
    """
    s = re.sub(r"[^\w\s-]", "", text.strip().lower())
    return re.sub(r"\s+", "-", s)


def _as_list(v) -> list[str]:
    """Normalize a scalar / list / comma-string meta value to a list of strings."""
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [s.strip() for s in str(v).split(",") if s.strip()]


class FsCapabilitiesStore(FsTreeStore, CapabilitiesStore):
    """`CapabilitiesStore` over folder-per-capability entries under
    `docs/capabilities/`, inherited and combined as the taxonomy is (TCW-112
    Design 1, 2).

    A capability is a folder with `tcw-capability.yaml` (`name` + the locked
    metadata vocabulary) and `description.md` (the body). A directory is a
    capability iff it holds that state file; dirs without one are pure grouping
    parents. Its path is its only identity (TCW-112 Design 5). Mirrors
    `FsTaxonomyStore` on the shared tree-store core.
    """
    COMPONENT = "capabilities"
    LEGACY_CONFIG_NAME = ".config.yaml"
    STATE_FILE = STATE_FILES["capabilities"]

    # -- resolution --

    def _is_capability(self, d: Path) -> bool:
        """Whether the folder `d` is an object of this store, by the walk's
        rule (TCW-111 Design 2.5)."""
        try:
            rel = d.relative_to(self.root).as_posix()
        except ValueError:
            return False
        return is_object(self.root, "capabilities", rel)

    def _object_dirs(self) -> list[str]:
        """The id-path of every object the walk finds, minus those whose state
        file is reached through a symbolic link out of the store or whose
        version cannot be read."""
        return [p for p in object_paths(self.root, "capabilities")
                if self._entry_readable(self.root / p) and self._listable(self.root / p)]

    def _compose_body(self, path: str, found: Combined, stores: dict) -> str:
        """The combined body (TCW-112 Design 2.3): the attached documents of
        `prependedDocs`, the description, then those of `appendedDocs`, each
        list's entries read from the `resources/` of the member that declared
        the list."""
        parts = []

        def documents(key: str) -> list[str]:
            pid = found.declared_by.get(key)
            if pid is None:
                return []
            owner = stores[pid]
            d = owner.root / path
            # `_in_resources` on each document: these are read by name from
            # the state file, so they never pass through a listing. Only a
            # document in that member's own `resources/` is read (TCW-111
            # Design 2.2); `check` reports one listed anywhere else.
            return [(d / fn).read_text(encoding="utf-8").strip()
                    for fn in _as_list(found.fields.get(key))
                    if owner._in_resources(d, fn) and (d / fn).is_file()]
        parts += documents("prependedDocs")
        if found.description and found.description.strip():
            parts.append(found.description.strip())
        parts += documents("appendedDocs")
        return "\n\n".join(parts)

    def _object_modified(self, d: Path, fields: dict) -> str:
        return _modified_timestamp(_capability_resources(d, fields))

    def _record(self, path: str, found: Combined, stores: dict, *,
                partial: bool = False) -> Capability:
        """The capability `found` combines at `path` (Design 2.2-2.4)."""
        fields = {k: v for k, v in found.fields.items() if k not in _CAP_STRUCTURAL}
        if "Subject" in fields:
            fields["Subject"] = _as_list(fields["Subject"])
        modified = []
        for pid in found.chain:
            member = stores[pid]
            declaration = member._declarations().get(path)
            modified.append(member._object_modified(
                member.root / path, declaration.fields if declaration else {}))
        return Capability(
            path=path,
            name=found.fields.get("name") or path.rsplit("/", 1)[-1].replace("-", " ").title(),
            fields=fields,
            body=self._compose_body(path, found, stores),
            origin="local" if found.owner == self.project_id else found.owner,
            modified=max(modified, default=""),
            owner=found.owner,
            parent=_stored_parent(found.fields.get("parent"), "capabilities"),
            overrides=None if partial or found.overrides is None
            else FullId(found.overrides, "capabilities", path),
            partial=partial,
        )

    def list_all(self, status=None, namespace=None, local_only=False) -> list[Capability]:
        out = []
        for c in self._listing(local_only):
            if status and c.status != status:
                continue
            if namespace and c.path.split("/")[0] != namespace:
                continue
            out.append(c)
        return out

    def unreviewed_inherited(self) -> list[Capability]:
        """Inherited capabilities never ruled on here (TCW-112 Design 7.2):
        the view's capabilities this project has no object of its own at,
        and its own overrides whose own declaration sets no `Status`."""
        decls = self._declarations()
        out = []
        for cap in self.list_all():
            if cap.owner != self.project_id:
                out.append(cap)
            elif cap.overrides is not None and decls.get(cap.path) is not None \
                    and "Status" not in decls[cap.path].fields:
                out.append(cap)
        return out

    def search(self, query: str) -> list[Capability]:
        return [c for c in self.list_all() if text_matches(c.name, c.body, query)]

    # -- writes --

    def override_target(self, target: "FullId | str") -> FullId:
        """The full identifier of this project's own capability that `set`
        and `reset` write for `target` (TCW-112 choice 9), deciding in this
        order: this project's own full identifier, where it has an object;
        another project that is not one of its sources, refused before
        anything is read; an id-path this project has an object at, read
        from nothing else; otherwise the view, in which another project's
        full identifier must be a member of the id-path's chain."""
        full_id, path = self._target_parts(target)
        own = FullId(self.project_id, "capabilities", path)
        if full_id is not None and full_id.project == self.project_id:
            if self.has_own(path):
                return own
            raise NotFound(self._no_such(target))
        if full_id is not None:
            if full_id.project not in self._source_ids():
                _not_inherited(full_id, self.project_id, self._active_root)
        elif self.has_own(path):
            return own
        chain = self.chain(path)
        if full_id is not None:
            if full_id not in chain:
                _not_inherited(full_id, self.project_id, self._active_root)
            return own
        if not chain:
            raise NotFound(self._no_such(target))
        return own

    def add(self, identifier, name=None, status="Missing", body="",
            fields=None, parent=None) -> Capability:
        path = _safe_store_id(identifier, "path")
        _check_id_path(path, "path")
        _check_reserved(path, "capabilities", "path")
        _check_length(self.project_id, "capabilities", path)
        # Any capability TCW can find; the folder is made where `identifier`
        # says, whatever the parent (TCW-111 Design 3.3).
        parent_id = str(self.find_parent(parent).full_id) if parent else None
        if status not in CAP_STATUSES:
            raise UsageError(f"invalid Status '{status}' "
                             f"(choose: {', '.join(sorted(CAP_STATUSES))})")
        d = self.root / path
        if not self._within_store(d):
            raise NotFound(f"no such capability: {path}")
        if d.exists() or d.is_symlink():   # a dangling/looping link reads absent
            raise Refused(f"capability already exists: {path}")
        # `add` writes a complete object, so at an inherited path it would be
        # a full copy, which nothing reports once the original moves (TCW-112
        # Design 4.1): `set` writes only what it is given.
        inherited = self.inherited_at(path)
        if inherited is not None:
            raise Refused(f"cannot add '{path}': '{self.project_id}' already inherits "
                          f"{inherited} there; to change it, override it with tcw "
                          f"capabilities set {path} --field <name>=<value>")
        # After the cheap string and stat refusals, because this one may open a
        # taxonomy store — and before `_write_entry`, which is the point: a create
        # carrying a field the store would reject must leave nothing behind.
        norm = self._validate_fields(fields or {})
        display = name or path.rsplit("/", 1)[-1].replace("-", " ").title()
        meta = {"name": display, "Status": status}
        if parent_id is not None:
            meta["parent"] = parent_id
        # Field values win over the `status` parameter — what create-then-set
        # did. A None clears, rather than being skipped: there *is* something to
        # clear, the Status seeded a line above. A new capability overrides
        # nothing, so the key is dropped rather than written as null.
        for k, v in norm.items():
            if v is None:
                meta.pop(k, None)
            else:
                meta[k] = v
        self._write_entry(d, meta, body)
        return self.get_local(path)

    def remove(self, identifier: "FullId | str") -> None:
        target = self.removal_target(identifier)
        d = self.root / target.id_path
        # Refused, never cascaded: `_rm` deletes the whole folder.
        _blocked_removal(d, self.root, "capabilities", target.id_path)
        referrers = self._referrers(d)
        if referrers:
            raise Refused(f"cannot remove '{target.id_path}': still referenced by "
                             f"{', '.join(referrers)} (repoint or clear those fields first)")
        self._rm(d)

    def _nested_entries(self, d: Path) -> list[str]:
        """Every folder below `d` holding a state file of any store or a 3.x
        one, relative to the store: `removal_blockers`, asked of the folder
        itself rather than `_object_dirs`, which skips dot-directories,
        `resources/` and unreadable entries that `git rm -rf` would delete all
        the same."""
        return [where for where, _ in removal_blockers(d, self.root)]

    def _referrers(self, target: Path) -> list[str]:
        """`<folder> (<field>)` for every other capability of this project
        whose own reference fields name the capability folder `target`.

        Each field is read as `check` reads it (`_ref_problems`,
        `_check_globals`): a full identifier of this project's own capability
        (TCW-110 Design 5.1), compared by folder identity. A value in any
        other form names nothing here, and `check` reports it.
        """
        def tokens(field: str, raw) -> list[str]:
            row = ref_field("capability", field)
            if not row.many:
                return [str(raw)]
            ns = row.group
            toks = raw if isinstance(raw, list) else str(raw).split(",")
            refs = [str(s).strip().lstrip("!") for s in toks if str(s).strip()]
            return [r for r in refs
                    if (hit := self._local_ref(r)) is not None
                    and hit.startswith(f"{ns}/")]

        def same(a: Path) -> bool:
            return _same_folder(a, target)

        out = []
        for p in self._object_dirs():
            folder = self.root / p
            if same(folder):
                continue
            meta = self._state(folder)
            for field in (row.name for row in _cap_ref_rows()):
                if field not in meta or meta[field] is None:
                    continue
                for ref in tokens(field, meta[field]):
                    hit = self._local_ref(ref)
                    if hit is not None and same(self.root / hit):
                        out.append(f"{p} ({field})")
                        break
        return out

    def _naming(self, full_id: FullId) -> list[str]:
        """`<full id> (<field>)` for every other own object of this project
        whose own declaration names `full_id` by its full identifier: in a
        capability's reference fields or `parent` (TCW-112 Design 4.3)."""
        named = str(full_id)
        out = []
        for path, decl in self._declarations().items():
            if decl is None or path == full_id.id_path:
                continue
            for field in ref_names("capability", namespace="capabilities"):
                raw = decl.fields.get(field)
                if raw is None:
                    continue
                toks = raw if isinstance(raw, list) else str(raw).split(",")
                if any(str(t).strip().lstrip("!") == named for t in toks):
                    out.append(f"{FullId(self.project_id, self.COMPONENT, path)} "
                               f"({field})")
        return out

    def reset(self, identifier: "FullId | str") -> None:
        target = self.override_target(identifier)
        path = target.id_path
        inherited = self.inherited_at(path)
        # A capability that overrides nothing is not an override — `remove`
        # deletes it.
        if self.has_own(path) and inherited is None:
            raise Refused(f"'{identifier}' is a local capability, not an override "
                             f"(use `tcw capabilities rm` to delete it)")
        if not self.has_own(path):
            raise Refused(f"no local override at '{identifier}' to reset "
                             f"(it inherits '{inherited}' verbatim)")
        d = self.root / path
        # Refused, as `remove` refuses, when anything is nested under the
        # override: `_rm` would delete it with the folder.
        nested = self._nested_entries(d)
        if nested:
            raise Refused(f"cannot reset '{identifier}': nested under its override: "
                          f"{', '.join(nested)} (delete a local capability with "
                          f"`tcw capabilities rm` and drop an override with "
                          f"`tcw capabilities reset` first)")
        # The override's full identifier stops existing once it is removed.
        naming = self._naming(target)
        if naming:
            raise Refused(f"cannot reset '{identifier}': {target} is still named by "
                          f"{', '.join(naming)}; repoint each at {inherited} first")
        self._rm(d)

    def _validate_fields(self, fields: dict) -> dict:
        out = {}
        for k, v in fields.items():
            if k not in CAP_FIELDS:
                raise UsageError(f"unknown field '{k}' (not in the locked vocabulary)")
            if v is None:
                out[k] = None                            # clear sentinel
                continue
            if k == "Status" and v not in CAP_STATUSES:
                raise UsageError(f"invalid Status '{v}' "
                                 f"(choose: {', '.join(sorted(CAP_STATUSES))})")
            out[k] = _as_list(v) if k == "Subject" else v
        # Every reference supplied, in any input form, becomes the full
        # identifier it names (TCW-110 Design 5.3) before it is checked or
        # stored; one that names nothing is refused here.
        out = self._stored_forms(out)
        # Fail closed on refs, in the one seam both `set` and `update_capability`
        # call before touching disk — so the CLI, `tcw serve`'s PATCH and any
        # future caller inherit it rather than each remembering to check.
        #
        # `out`, not `fields`: Subject must be resolved after `_as_list`, so
        # `Subject=a,b` is two refs. `v is not None`: None is the documented
        # clear sentinel, and passing it through would make `_check_globals`
        # stringify it into a bogus problem about a field just cleared. Only the
        # refs this write *supplies*, never the merged entry, or a capability with
        # one bad ref could not be repaired by the very command that repairs it.
        supplied = {k: v for k, v in out.items() if v is not None}
        # A taxonomy store is opened only when a field needing one was supplied:
        # the other four resolve against `self`, and a status-only repair should
        # not start failing because the project's taxonomy config is malformed.
        needs_taxonomy = bool(supplied.get("Subject")) or bool(supplied.get("Feature"))
        problems = [message for level, message in self._ref_problems(
            supplied, self._taxonomy() if needs_taxonomy else None) if level == "error"]
        if problems:
            # All of them, joined — `check` reports every problem, and a write
            # that reported one at a time would cost a round trip per bad ref.
            # No message contains "no such", so `_map_store_error` keeps these
            # at 422 rather than 404.
            raise UsageError("; ".join(problems))
        return out

    def _stored_forms(self, fields: dict) -> dict:
        """`fields` with each reference value given (Subject, Feature,
        Superseded by, Blocked by, Roles, When), in any input form of TCW-110
        Design 3.1, replaced by the full identifier it names, `!` kept outside
        it and a comma list kept a comma list. A value naming nothing is
        refused, every problem worded as `check` words it and all of them
        joined, so one write reports them all."""
        out, problems = dict(fields), []
        taxonomy = None
        for key, value in fields.items():
            if value is None or key not in ref_names("capability", parent=False):
                continue
            if key in ("Subject", "Feature") and taxonomy is None:
                taxonomy = self._taxonomy() or _NO_TAXONOMY
            single = not ref_field("capability", key).many
            tokens = [str(value).strip()] if single else [
                str(t).strip() for t in (value if isinstance(value, list)
                                         else str(value).split(",")) if str(t).strip()]
            stored = []
            for token in tokens:
                negated = ref_field("capability", key).negatable and token.startswith("!")
                text = token[1:] if negated else token
                try:
                    full_id = self._ref_input(key, text, token, taxonomy)
                except _RefInputProblem as problem:
                    problems.append(str(problem))
                    continue
                stored.append(("!" if negated else "") + str(full_id))
            if single:
                out[key] = stored[0] if stored else value
            else:
                out[key] = stored if isinstance(value, list) or key == "Subject" \
                    else ", ".join(stored)
        if problems:
            raise UsageError("; ".join(problems))
        return out

    def _ref_input(self, key: str, text: str, token: str, taxonomy) -> FullId:
        """The full identifier one reference value given to a write names;
        `token` is the value as given, a `!` included."""
        namespace = "taxonomy" if key in ("Subject", "Feature") else "capabilities"
        noun = "ref" if namespace == "taxonomy" else "identifier"
        try:
            found = sort_input(text, namespace)
        except IdError as error:
            raise _RefInputProblem(f"{key} → {error}") from None
        if key in ("Roles", "When"):
            folder = "roles" if key == "Roles" else "conditions"
            id_path = found.full_id.id_path if found.form == "a" else found.id_path
            if not id_path.startswith(f"{folder}/"):
                raise _RefInputProblem(f"{key} '{token}' must be a {folder}/ slug")
        if namespace == "taxonomy" and taxonomy is _NO_TAXONOMY:
            # No taxonomy store to read: an id-path is this project's own,
            # stored unchecked, as it always was.
            return found.full_id if found.form == "a" else \
                FullId(self.project_id, "taxonomy", found.id_path)
        store = taxonomy if namespace == "taxonomy" else self
        try:
            return store._input_ref(text, key).full_id
        except _DanglingRef:
            raise _RefInputProblem(f"{key} → dangling {noun} '{text}'") from None
        except UsageError as error:
            if "is ambiguous" in str(error):
                raise _RefInputProblem(f"{key} → ambiguous {noun} '{text}'") from None
            raise _RefInputProblem(f"{key} → {error}") from None

    def _write_target(self, target: FullId) -> tuple[Path, dict]:
        """`(folder, state)` for a write to this project's own capability at
        `target`'s id-path (TCW-112 Design 4.2): its own object in place, or
        a new state file at the same id-path, holding nothing yet, written
        into an organising folder already there. Another store would record
        the same declaration at the same path its own way."""
        d = self.root / target.id_path
        if self.has_own(target.id_path):
            return d, self._state(d)
        # The one write not downstream of a guarded lookup: a local symlink
        # shadowing a segment of the path would have it create the folder
        # and its state file outside the store.
        if not self._within_store(d):
            raise NotFound(f"no such capability: {target.id_path}")
        return d, {}

    @staticmethod
    def _merge_meta(meta: dict, norm: dict) -> dict:
        """Merge validated fields into an own object's state. A None writes
        an explicit null on every own object (TCW-112 Design 4.2): over an
        inherited value it removes it, and over none it means what an absent
        key means, so `set` needs no view to know which it is."""
        meta.update(norm)
        return meta

    def _reread(self, path: str) -> Capability:
        """The capability at `path` as the project sees it after a write, or
        its own declaration when the view cannot be built (Design 3.4)."""
        try:
            return self.get_view(path)
        except InheritedUnavailable as error:
            self.view_error = error
            return self.declaration(path)
        except StateFileProblem:
            # A source's object at this path cannot be read (Design 1.3):
            # the write is this project's own and stands (AC 39).
            return self.declaration(path)

    def set(self, identifier: "FullId | str", fields: dict,
            parent: str | None = None) -> Capability:
        norm = self._validate_fields(fields)           # validate before touching disk
        target = self.override_target(identifier)
        if parent is not None:
            # A parent is a field like any other (TCW-112 Design 2.2), so an
            # override may set it; `''` clears it, as a cleared field does.
            norm["parent"] = str(self.find_parent(parent).full_id) \
                if parent.strip() else None
        d, meta = self._write_target(target)
        # `_write_meta` owns the mkdir and the rollback: a fresh override's
        # folder is made here, and a refused write must not leave an empty
        # one behind.
        self._write_meta(d, self._merge_meta(meta, norm))
        return self._reread(target.id_path)

    # -- validation --

    def _taxonomy(self) -> "FsTaxonomyStore | None":
        """The sibling taxonomy store for this project, or None if it has none.

        The FS adapter's answer to "where does this store's taxonomy live";
        another adapter answers it from its own connection, so nothing about
        this belongs on the abstract interface. Putting it on the store rather
        than in the call is what makes it impossible to forget: `set`,
        `update_capability` and `check` all reach the same handle.
        """
        # A taxonomy that is present and cannot open raises: that is a broken
        # configuration, not "this project has no taxonomy".
        return (FsTaxonomyStore.open(
                    self.project_root, locator=self.locator if self._as_other else None)
                if tree_store_present(self.project_root, "taxonomy") else None)

    def check(self, taxonomy=None, identifier: str | None = None) -> list[Finding]:
        # `is not None`, not `or`: an explicitly injected store must win even
        # when it is falsey. Without the fallback, `check()` called bare skips
        # Subject/Feature entirely, so the write path and `check` could disagree
        # about *whether* a ref is checked even once they agree about what a
        # problem is.
        problems: list[Finding] = []
        unchecked = ""
        # A full listing first, as `FsTaxonomyStore.check` does.
        self.unreadable.clear()
        self._forget()
        if taxonomy is None:
            try:
                taxonomy = self._taxonomy()
            except ValueError as e:
                # A taxonomy that is configured and will not open — declared and
                # not yet provisioned, say — costs the Subject/Feature checks, not
                # every other problem this ledger has. Said once, and only if a
                # capability checked here names a Subject or Feature: otherwise
                # nothing went unchecked, and every save would carry the line.
                unchecked = f"Subject and Feature not checked: {e}"
        if identifier is None:
            problems += self._legacy_config_problems()     # see FsTaxonomyStore.check
        view, self.view_error = _view_or_error(self)
        # Every own declaration only for the whole store: a scoped check
        # reads its one object, so a malformed sibling never stops it.
        decls = self._declarations() if identifier is None else {}
        if identifier is not None:
            try:
                path, selected, own = _selected(self, identifier, view)
            except StateFileProblem as problem:
                return [Finding("error", self._where(problem.path), problem.problem)]
            if selected is None:
                return [Finding("error", self._where(self.root),
                                f"no such capability: {identifier}")]
            paths = [path] if own else []
            if own:
                problems += self._shape_findings(path)
            else:
                # An inherited capability: what the project sees is checked;
                # its references are its owner's to check.
                problems += self._field_findings(path, selected.fields, combined=True)
        else:
            paths = [p for p in decls if decls[p] is not None]
            problems += self._unreadable_findings()
            problems += self._shape_findings()
        records = []
        declared_parents = {}
        for path in paths:
            decl = decls.get(path) if identifier is None else self._own_declaration(path)
            found = _combined_or_problem(self, view, path, problems)
            cap = self._record(path, found, view.stores) if found is not None \
                else self.declaration(path)
            records.append(cap)
            declared_parents[path] = _stored_parent(decl.fields.get("parent"),
                                                    "capabilities")
            where = self._where(path)
            state = self._where(self.root / path / self.STATE_FILE)

            def error(message: str, at: str = where) -> None:
                problems.append(Finding("error", at, message))
            if (bad := _bad_name(path)):
                error(bad)
            if (problem := id_problem(decl.fields, path)):
                error(problem, state)
            if "overrides" in decl.fields:
                error(_OVERRIDES_REMOVED, state)
            if found is not None and len(found.chain) == 1:
                if (problem := _incomplete(cap.full_id, decl, "capabilities")):
                    error(problem, state)
            # The fields as the project sees them when that could be read;
            # otherwise only the values its own file holds (Design 6.5).
            own_fields = {k: v for k, v in decl.fields.items()
                          if k not in _CAP_STRUCTURAL}
            problems += self._field_findings(
                path, cap.fields if found is not None else own_fields,
                combined=found is not None)
            # The references this project's own declaration sets (Design 6.2).
            declared = {k: v for k, v in own_fields.items() if v is not None}
            if "Subject" in declared:
                declared["Subject"] = _as_list(declared["Subject"])
            for level, problem in self._ref_problems(declared, taxonomy):
                problems.append(Finding(level, where, problem))
            if unchecked and (declared.get("Subject") or declared.get("Feature")):
                error(unchecked)
                unchecked = ""
            d = self.root / path
            listed = _as_list(decl.fields.get("prependedDocs")) + \
                _as_list(decl.fields.get("appendedDocs"))
            for fn in listed:
                if not self._in_resources(d, str(fn)):
                    error(f"'{fn}' is not in {RESOURCES}/")
                elif not (d / fn).is_file():
                    error(f"missing attachment '{fn}'")
            # A loose document the lists do not name is the shape check's row
            # a, which reports any loose file, `.md` or not.
        problems += self._parent_findings(
            records, None if identifier is None else paths[0] if paths else None,
            declared=declared_parents)
        if identifier is None and view is not None:
            problems += [self._store_finding(w, "warning") for w in self.view_warnings()]
        return problems

    def _field_findings(self, path: str, f: dict, *, combined: bool) -> list[Finding]:
        """The checks of a capability's fields (TCW-112 Design 6.2): unknown
        and retired fields and invalid values, and, on the fields as the
        project sees them (`combined`), the fields one value requires. Each
        is at the state file, which holds the fields (AC 16)."""
        where = self._where(self.root / path / self.STATE_FILE)
        out: list[Finding] = []

        def found(message: str) -> None:
            out.append(Finding("error", where, message))
        for key in f:
            if key in RETIRED_CAP_FIELDS:
                found(f"field '{key}' was retired in TCW 3.0 — see "
                      f"{MIGRATION_GUIDE}")
            elif key not in CAP_FIELDS:
                found(f"unknown field '{key}'")
        status = f.get("Status")
        # `null` only clears a value, so it is never an invalid one.
        if status is not None and status not in CAP_STATUSES:
            found(f"invalid Status '{status}'")
        if f.get("Priority") is not None and f["Priority"] not in CAP_PRIORITIES:
            found(f"invalid Priority '{f['Priority']}'")
        if f.get("Lifecycle") is not None and f["Lifecycle"] not in CAP_LIFECYCLES:
            found(f"invalid Lifecycle '{f['Lifecycle']}'")
        if combined:
            if status == "Partial" and "Gaps" not in f:
                found("Partial requires Gaps")
            if status == "Blocked" and "Blocked by" not in f:
                found("Blocked requires Blocked by")
        return out

    def _validation_resources(self, identifier: str) -> list[Path]:
        """Filesystem resources bounded to one capability object: every chain
        member's state file, description and listed attachments at its
        id-path."""
        try:
            identifier = _safe_store_id(identifier, "capability target")
        except UsageError:
            return []
        try:
            view = self._view()
            found = view.combined(identifier)
            members = [view.stores[pid] for pid in found.chain] if found else []
        except (InheritedUnavailable, StateFileProblem, yaml.YAMLError):
            # Its files are still this object's to scan, a malformed one
            # above all: the scan is what reports it.
            members = [self] if self.has_own(identifier) else []
        out = []
        for owner in members:
            folder = owner.root / identifier
            try:
                meta = owner._state(folder)
            except (yaml.YAMLError, StateFileProblem):
                meta = {}
            names = [self.STATE_FILE, "description.md",
                     *_as_list(meta.get("prependedDocs")),
                     *_as_list(meta.get("appendedDocs"))]
            # `validate()` parses and reads whatever comes back, so a listed
            # attachment that is a symlink out of the store would be read
            # there. Asked of the *owning* store, because an inherited folder
            # is bounded by its own root, not this one.
            out += [folder / name for name in names
                    if (folder / name).is_file() and owner._within_store(folder / name)]
        return out

    def _ref_problems(self, f: dict, taxonomy) -> list[tuple[str, str]]:
        """Every cross-object ref problem in `f`, as `(level, message)` worded
        exactly as `check` reports it, minus the `<path>: ` location prefix.

        The single renderer: `check` prefixes these, the write path raises
        the errors. Two callers cannot disagree about what a problem *is*
        because there is only one place that says it.
        """
        out = []
        for key in (row.name for row in _cap_ref_rows() if not row.many):
            if key in f and (e := self._ref_error(str(f[key]))):
                out.append((e[0], f"{key} → {e[1]}"))
        return (out + self._check_globals(f)
                + self._check_subject(f, taxonomy)
                + self._check_feature(f, taxonomy))

    def _ref_error(self, identifier: str) -> "tuple[str, str] | None":
        from tcw.locate import FOUND, MISSING
        outcome = self._stored_ref(identifier, "capabilities")
        if outcome.kind == FOUND:
            return None
        if outcome.kind == MISSING:
            return "error", f"dangling identifier '{identifier}'"
        return _ref_finding("", identifier, outcome)

    def _check_globals(self, f) -> list[tuple[str, str]]:
        out = []
        for ns, field in ((row.group, row.name) for row in _cap_ref_rows() if row.group):
            raw = f.get(field, "")
            toks = raw if isinstance(raw, list) else str(raw).split(",")
            for tok in (str(s).strip() for s in toks if str(s).strip()):
                ref = tok.lstrip("!")
                try:
                    id_path = parse_stored(ref, "capabilities").id_path
                except IdError:
                    id_path = None      # reported by `_ref_error` below
                if id_path is not None and not id_path.startswith(f"{ns}/"):
                    out.append(("error", f"{field} '{tok}' must be a {ns}/ slug"))
                elif (e := self._ref_error(ref)):
                    out.append((e[0], f"{field} → {e[1]}"))
        return out

    @staticmethod
    def _term_refs(f) -> list[tuple[str, str]]:
        """`(field, ref)` for every taxonomy reference a capability makes — the
        one definition of which references count, read by `check` and by the
        taxonomy's refusal to remove a term a capability names.

        `str(...)`, as the other four ref fields already do: a ref resolver
        takes a string, and a non-string here used to escape as AttributeError
        out of `taxonomy.get` rather than as a refusal the caller can read."""
        refs = []
        for row in ref_rows("capability", namespace="taxonomy"):
            if row.many:
                refs += [(row.name, str(s)) for s in _as_list(f.get(row.name))]
            elif f.get(row.name):
                refs.append((row.name, str(f[row.name])))
        return refs

    def _term_problem(self, ref: str, taxonomy) -> "tuple[Term | None, tuple | None]":
        from tcw.locate import FOUND, MISSING
        outcome = self._stored_ref(ref, "taxonomy", store=taxonomy)
        if outcome.kind == FOUND:
            return outcome.value, None
        if outcome.kind == MISSING:
            return None, ("error", f"dangling ref '{ref}'")
        return None, _ref_finding("", ref, outcome)

    def _check_subject(self, f, taxonomy) -> list[tuple[str, str]]:
        subjects = [ref for field, ref in self._term_refs(f) if field == "Subject"]
        if not subjects or taxonomy is None:
            return []
        out = []
        for subj in subjects:
            _, problem = self._term_problem(subj, taxonomy)
            if problem:
                out.append((problem[0], f"Subject → {problem[1]}"))
        return out

    def _check_feature(self, f, taxonomy) -> list[tuple[str, str]]:
        feature = next((ref for field, ref in self._term_refs(f)
                        if field == "Feature"), None)
        if not feature or taxonomy is None:
            return []
        target, problem = self._term_problem(feature, taxonomy)
        if problem:
            return [(problem[0], f"Feature → {problem[1]}")]
        if target is not None and target.kind != "Feature":
            return [("error", f"Feature → ref '{feature}' points to "
                              f"{target.kind}, expected Feature")]
        return []

    # -- revision-bearing detail + update --

    def get_capability_detail(self, identifier: "FullId | str") -> "CapabilityDetail" | None:
        full_id, path = self._target_parts(identifier)
        store = self if full_id is None else self._owner_store(full_id.project)
        cap = self._found(identifier)
        if cap is None:
            return None
        owner = store if cap.owner == store.project_id else store._view().stores[cap.owner]
        declared = owner._declared_description(owner.root / path)
        # Every chain member's files are part of what the caller sees, so they
        # are part of the revision — else two edits to the same override hash
        # identically and a stale write sails through.
        return CapabilityDetail(
            capability=cap,
            core_revision=_revision_multi(*self._chain_texts(store, path)),
            declared_description=None if declared is None else declared.strip())

    def update_capability(self, identifier: "FullId | str", *, body=_UNSET, fields=_UNSET,
                          core_revision: str | None = None) -> "CapabilityDetail":
        norm = self._validate_fields(fields) \
            if fields is not _UNSET and fields is not None else {}

        if core_revision is not None:
            detail = self.get_capability_detail(identifier)
            if detail and detail.core_revision != core_revision:
                raise StaleRevision(f"stale revision for capability '{identifier}'")

        target = self.override_target(identifier)
        d, meta = self._write_target(target)
        meta = self._merge_meta(meta, norm)
        # No mkdir and no outer guard here any more: `_write_meta` and
        # `_write_entry` each own their directory and roll back what they
        # created. A body given is the declared description, written as it is,
        # an empty one included: it adds no text, so the body shown falls back
        # to the next member's description (TCW-112 Design 2.3, choice 5).
        # With no body given, an object with no description file gains none.
        if body is not _UNSET:
            self._write_entry(d, meta, body if body is not None else "")
        else:
            self._write_meta(d, meta)
        return _require_detail(self.get_capability_detail(target),
                               "capability", identifier)


# ── provisioning (FS adapter: a declared store is a git checkout) ────────────
#
# Everything below realizes `StoreProvisioner` for the filesystem. Clones, refs
# and cache directories are named *here and nowhere else* — a store-interface
# signature that mentioned one would put the seam in the wrong layer.


def _git_subcommand(argv: list[str]) -> str:
    """The verb in a git argv, for an error message.

    `argv[1]` is not it. Every call here is built as
    `["git", "-C", <path>, <verb>, …]`, so naming `argv[1]` reported "git -C
    failed" for every failure the adapter has ever produced.
    """
    tokens = iter(argv[1:] if argv and argv[0] == "git" else argv)
    for token in tokens:
        if token == "-C":
            next(tokens, None)                 # skip the path it takes
            continue
        if not token.startswith("-"):
            return token
    return "command"


def _git_reason(done) -> str:
    """The line of git's output worth showing.

    Git puts the diagnosis first and the boilerplate last — an unreachable remote
    ends with "and the repository exists.", which is what taking the *last* line
    used to report. Prefer the first line git itself marked as the failure.
    """
    lines = [line.strip()
             for line in (done.stderr or done.stdout or "").strip().splitlines()
             if line.strip()]
    for line in lines:
        if line.startswith(("fatal:", "error:")):
            return line
    return lines[0] if lines else ""


def _normalize_remote(url: str) -> str:
    """A remote URL reduced to the differences that matter for identity here:
    surrounding whitespace, a trailing slash, and a `.git` suffix. Nothing more —
    see `_require_declared_checkout` for why this stays deliberately literal."""
    cleaned = (url or "").strip().rstrip("/")
    return cleaned[:-4] if cleaned.endswith(".git") else cleaned


def _is_store_layout(root: Path, component: str) -> bool:
    """Whether `root` holds `component`'s store, as far as the filesystem can say.

    The answer has two strengths, because the components differ in what they can
    honestly claim.

    A **work** store names nothing either (TCW-70 Design 3.5): it is present
    when its directory is, the same answer `WorkLocation.open` gives, so a
    provisioned store and an opened one agree.

    A **tree** store — taxonomy, capabilities — names nothing. `init` scaffolds
    it as a bare directory (see `init`'s plan loop), it holds no config file of its
    own at all, and the
    only file reliably left behind is a `.gitkeep`, which is git's answer to
    empty directories and means nothing here. So "the directory is there" is the strongest honest answer, and it is
    shared by the work store: a declared tree store that clones
    into an empty directory reads as usable, because an empty taxonomy is a real
    state and nothing distinguishes the two. What this still refuses — a
    `repository.path` naming nothing at all — is what keeps "a failure leaves
    nothing behind" true for every component.
    """
    return root.is_dir()


def _registry_checkout_root(
    project_root: Path, declaration: "RepositoryDeclaration"
) -> Path | None:
    """Where the declared store sits inside a project this machine already has.

    The join the ladder's rung 1.5 needs: ask the project registry which project
    is a checkout of the declared repository, then descend to the store's path
    within it. None when the registry cannot answer, which sends the ladder on
    to the provisioned copy.

    **Every failure here is "no answer", never an error.** This rung is a
    fallback reached only after a configured path has already failed, and a
    graph problem must not turn a working provisioned store into a refusal. So
    the registry is opened without `require_valid()` — the shape `run_provision`
    already uses for the same reason — and anything raised is swallowed.
    """
    try:
        found = FsProjectRegistry.open(project_root).checkout_of(declaration.url)
    except Exception:
        return None
    if found is None:
        return None
    return (found / declaration.path) if declaration.path else found


class LocationProjectAbsent(StoreLocationUnusable):
    """A store location is a folder address naming a project that is not on
    this machine (TCW-110 Design 7.2): the location is unusable, so a declared
    `repository` still answers; with none the command stops with exit 5."""

    def __init__(self, unreachable: Unreachable):
        super().__init__(str(unreachable))
        self.unreachable = unreachable


def store_location(project_root: Path, component: str, configured: str | None, *,
                   locator=None, chain: tuple = ()) -> Path:
    """The folder a configured `<component>.path` names, written in the
    configuration of the project at `project_root` (TCW-110 Design 7.5): the
    one function every reader calls.

    `None` is the default `docs/<component>`. A plain path is relative to the
    project, re-anchored in a linked worktree (`anchor_configured_path`). A
    folder address is resolved by Design 7.2 through `locator`, the command's
    one `Locator` (the active project's when None): `tcw://<id>.path/<rest>`
    is that project's root joined with `<rest>`, and
    `tcw://<id>.<namespace>.path/<rest>` that project's own location for
    `<namespace>`, resolved from its own configuration by this same function,
    joined with `<rest>`. `chain` is the (project, namespace) pairs already
    followed; reaching one again is a loop (Design 7.3).

    Raises `StoreDeclarationError` for an address that is malformed, names an
    object, or loops; `LocationProjectAbsent` for a project not on this
    machine; and `ProjectGraphError` (an unknown ID included) as the lookup
    does."""
    if configured is None:
        return project_root / "docs" / component
    if not has_scheme(configured):
        value = Path(configured).expanduser()
        if value.is_absolute():            # names a place, not an offset
            return value
        return anchor_configured_path(project_root, value) / value
    key = f"{component}.path"
    try:
        found = parse_address(configured)
    except IdError as error:
        raise StoreDeclarationError(f"{key}: {error}") from None
    if not isinstance(found, FolderAddress):
        raise StoreDeclarationError(
            f"{key}: {configured} names an object, not a folder; a store location "
            f"is a folder address, tcw://<project>[.<namespace>].path/<folder>")
    if not chain:
        own = load_config(project_root / SENTINEL)
        chain = ((own.get("id") if isinstance(own, dict) else None, component),)
    from tcw.locate import Locator, resolve_folder_address
    if locator is None:
        locator = Locator.of(project_root)
    try:
        return resolve_folder_address(found, locator, Path(project_root), chain=chain)
    except Unreachable as error:
        raise LocationProjectAbsent(error) from None


def _same_root(a: Path, b: Path) -> bool:
    """Whether two project roots are one folder, compared by identity."""
    return _below(Path(a).resolve(), Path(b).resolve()) == Path(".")


def resolve_store(store_cls, project_root: Path, active_root: Path | None = None):
    """This project's store for `store_cls`'s component, in one ordered ladder.

    1. the local store (`<component>.path`, else `docs/<component>`) when it is
       usable;
    1.5. else inside a project the registry has already located here, when one
       is a checkout of the declared repository, matched against the manifest
       entries that place it (TCW-107 Design 6.4) — local before remote. Numbered as
       a half because it was added after the others and renumbering them would
       silently rewrite what every message and comment elsewhere calls "rule 2";
    2. else the declared home repository's provisioned location, if usable;
    3. else `StoreNotProvisioned`, when a home repository is declared;
    4. else exactly what the component did before a declaration existed — the
       same checks, in the same order, with the same messages.

    **A declaration is a fallback, never an override.** Rule 1 runs first so a
    checkout that already has the store keeps using it and nothing about that
    machine changes; the declaration answers only for a machine that does not
    have it. Rules 3 and 4 are the same failure told two ways: with a
    declaration it is actionable, so it says what to run.

    **Only `StoreLocationUnusable` falls through.** Rules 1 and 2 mean "try here,
    and if there is no store here try the next place" — which is a statement
    about the *location*, not about every way opening can fail. A store that is
    present and raises while opening has to surface, or the ladder answers a
    config error with `tcw project provision`.

    One function for every component, because the ladder is the contract and
    three copies of a contract drift. The two things that genuinely differ are
    hooks on the store class: `_local_root`, which knows the component's default
    location and how a relative path re-anchors, and `_open_at`, which decides
    what "usable" means and builds the store. `COMPONENT` names the config
    section.
    """
    project_root = project_root.resolve()
    config_path = project_root / SENTINEL
    config = load_config(config_path)
    component = store_cls.COMPONENT
    section = config.get(component) or {} if isinstance(config, dict) else {}
    if not isinstance(section, dict):
        section = {}
    configured = section.get("path")
    if configured is not None and (not isinstance(configured, str) or not configured.strip()):
        raise ValueError(
            f"{config_path}: {component}.path must be a non-empty path string")
    declaration, declaration_problems = parse_repository_declaration(
        section.get("repository"), f"{component}.repository")
    locator = None
    if isinstance(configured, str) and has_scheme(configured):
        # The command's one `Locator` (TCW-110 Design 6.1): the active
        # project's, for a store opened on its behalf.
        from tcw.locate import Locator
        locator = Locator.of(active_root or project_root)
    try:
        raw_root = store_cls._local_root(project_root, configured, locator=locator)
    except LocationProjectAbsent as absent:
        if declaration is None:
            raise absent.unreachable from None
        # Unusable here, so the declaration answers (rules 1.5 to 3).
        raw_root = None
    except StoreDeclarationError as wrong:
        raise StoreDeclarationError(f"{config_path}: {wrong}") from None

    # Whether a candidate location has to prove it holds a store. It does once
    # anything points at it — a configured path, or a declaration that gives the
    # ladder somewhere else to fall to. It does not for a component's bare
    # default with nothing configured: that is rule 4, and for the tree stores
    # "return `docs/<component>` whether or not it exists" is the behaviour that
    # predates this ladder and must survive it.
    #
    # `declaration_problems` counts too, and that is not an edge case. A
    # malformed declaration parses to `(None, problems)`, so the ladder sees no
    # declaration and takes rule 4 — and a tree store's rule 4 validates nothing
    # and therefore cannot fail, which dropped the problems on a path that never
    # raised. The user got "no tcw taxonomy project here" for a typo in the block
    # right in front of them. A candidate allowed to mask a configuration error
    # has to be a real store, not a directory that might not exist.
    must_exist = (configured is not None or declaration is not None
                  or bool(declaration_problems))

    if declaration is None:                                     # rule 4
        try:
            return store_cls._open_at(
                raw_root, project_root, config_path,
                external=configured is not None, must_exist=must_exist,
                active_root=active_root)
        except ValueError:
            # A valid local store keeps reads working even when an unused
            # declaration is malformed. When no local store can open, however,
            # the declaration is the actionable config error and must not be
            # hidden behind the dead local path.
            if declaration_problems:
                raise StoreDeclarationError(
                    f"{config_path}: {'; '.join(declaration_problems)}") from None
            raise

    local_failure = None
    try:                                                        # rule 1
        if raw_root is None:
            raise StoreLocationUnusable("")
        return store_cls._open_at(
            raw_root, project_root, config_path,
            external=configured is not None, must_exist=must_exist,
            active_root=active_root)
    except StoreLocationUnusable as unusable:
        # Only this. A store that is *there* and fails to open — a removed key
        # in its project's file, say — is a real error, and swallowing it here
        # reported "not provisioned; run `tcw project provision`", which then succeeded
        # and left the store exactly as unopenable.
        #
        # The reason is carried rather than discarded, but **only when the
        # configured path is actually there**. A path that does not exist,
        # beside a declaration, is the ordinary case the declaration exists for
        # — reporting it would make every provisioned project noisy. A path that
        # exists and holds no store is a second configuration problem, and it
        # used to vanish behind rule 3's message entirely.
        #
        # Presence is tested here rather than read out of the message: `_open_at`
        # raises the same "is not a directory" for an absent path and for one
        # that is a file, so the message cannot tell them apart.
        local_failure = str(unusable) if raw_root is not None and raw_root.exists() \
            else None
        prefix = f"{config_path}: "
        if local_failure and local_failure.startswith(prefix):
            local_failure = local_failure[len(prefix):]
    local = _registry_checkout_root(project_root, declaration)
    if local is not None:
        try:                                                    # rule 1.5
            # No `declaration=`, and that omission is the whole of "must not
            # publish". This store is on the user's own disk and they push it
            # themselves — the same reasoning rule 1 relies on. `publishes`
            # consults nothing else.
            return store_cls._open_at(
                local, project_root, config_path,
                external=True, must_exist=True, active_root=active_root)
        except StoreLocationUnusable:
            # The project is here but holds no store at the declared path.
            # A location that did not work out, so the ladder carries on —
            # the same rule rules 1 and 2 follow.
            pass
    try:                                                        # rule 2
        # The declaration travels with the store *only* here. Rules 1 and 1.5
        # above resolved without it, so a store built there carries None.
        return store_cls._open_at(
            provisioned_store_root(project_root, declaration), project_root, config_path,
            external=True, must_exist=True, declaration=declaration,
            active_root=active_root)
    except StoreLocationUnusable:
        pass                                                    # same rule
    # The command that fetches *this* store: run in its own project, which
    # is not the active one when an inheriting project reads it (TCW-115
    # Design 7.2). `active_root` is given only for another project's store.
    command = f"tcw project provision --component {component}"
    if active_root is not None and not _same_root(active_root, project_root):
        command = (f"tcw -C {shlex.quote(str(project_root))} project provision "
                   f"--component {component}")
    raise StoreNotProvisioned(                                  # rule 3
        f"{config_path}: the {component} store is declared in "
        f"{declaration.url} but has not been provisioned here; "
        f"run `{command}` to obtain it"
        + (f" — and the configured {local_failure}" if local_failure else ""))


def declared_repository(
    project_root: Path, component: str
) -> tuple["RepositoryDeclaration | None", list[str]]:
    """A component's declared home repository, read straight from the config.

    Deliberately not a store method: the whole point is to answer for a component
    whose store cannot be opened, which is exactly when a store method would be
    unavailable. Component-generic from the start — it reads `<component>.repository`
    for any component, so extending provisioning past `work` adds a caller, not a
    reader.
    """
    try:
        config = load_config(project_root / SENTINEL)
    except ValueError:
        return None, []          # a config too broken to read declares nothing
    section = config.get(component) if isinstance(config, dict) else None
    if not isinstance(section, dict):
        return None, []
    return parse_repository_declaration(section.get("repository"),
                                        f"{component}.repository")


class FsStoreProvisioner(StoreProvisioner):
    """A declared store, realized as a git checkout.

    Obtains into a temporary directory beside the target and renames it into
    place, so a failed or interrupted fetch is never visible as a store. That is
    what makes "leaves nothing behind" true rather than aspirational.
    A project is fetched by `fetch_project`, below, not by this class.
    """

    def __init__(self, project_root: Path, component: str,
                 declaration: RepositoryDeclaration | None):
        self.project_root = project_root.resolve()
        self.component = component
        self.declaration = declaration

    # -- StoreProvisioner --

    def describe(self) -> str:
        if self.declaration is None:
            return f"{self.component}: no home repository declared"
        d = self.declaration
        at = f" at {d.ref}" if d.ref else ""
        within = f", store at {d.path}" if d.path else ""
        return (f"{self.component}: {d.url}{at}{within} → "
                f"{provisioned_store_root(self.project_root, d)}")

    def is_available(self) -> bool:
        if self.declaration is None:
            return False
        target = provisioned_store_root(self.project_root, self.declaration)
        checkout = checkout_root(self.project_root, self.declaration)
        # A directory is not enough: the store needs a checkout of its own.
        # Check the filesystem marker rather than invoking Git: an
        # already-available second run is deliberately a zero-subprocess no-op.
        return (_is_store_layout(target, self.component)
                and (checkout / ".git").exists())

    def ensure_available(self, *, dry_run: bool = False) -> ProvisionResult:
        if self.declaration is None:
            return ProvisionResult(action="undeclared", available=False,
                                   detail=f"{self.component}: nothing declared")
        target = provisioned_store_root(self.project_root, self.declaration)
        checkout = checkout_root(self.project_root, self.declaration)

        if self.is_available():
            return ProvisionResult(action="available", available=True,
                                   location=str(target),
                                   detail=f"{self.component}: already available")
        if checkout.exists():
            # Something is at the checkout and it is not a usable store. It is
            # never fetched into or replaced (TCW-73 Design 8.4): say which of
            # the two is wrong, contacting nothing.
            self._require_declared_checkout(checkout)
            self._require_store_layout(target)
            raise ValueError(f"{self.component}.repository: {checkout} is not a "
                             f"usable store; move it aside and run `tcw project provision` "
                             f"again")
        if dry_run:
            # Short on purpose: the caller prints `describe()` immediately above,
            # and repeating it here read as "work: would obtain work: …".
            return ProvisionResult(action="planned", available=False,
                                   location=str(target),
                                   detail=f"{self.component}: would obtain into {target}")
        self._obtain(checkout)
        return ProvisionResult(action="obtained", available=True, location=str(target),
                               detail=f"{self.component}: obtained at {target}")

    def _require_store_layout(self, root: Path) -> None:
        """Refuse a repository that carries no store where the declaration says.

        Two shapes of refusal, because the two predicates fail differently: a
        tree store can only be absent, while a work store can also be present
        and incomplete, and naming the folders it lacks is what makes that
        message worth reading.
        """
        if _is_store_layout(root, self.component):
            return
        where = self.declaration.path or "."
        prefix = (f"{self.component}.repository: {self.declaration.url} has no "
                  f"{self.component} store at '{where}'")
        raise ValueError(f"{prefix}: no such directory in the repository")

    # -- git plumbing (adapter-private; nothing above this class names it) --

    def _obtain(self, checkout: Path) -> None:
        """Clone beside the target, then rename in. The rename is what makes a
        failure leave nothing behind — a half-clone is never at the real path.

        **Everything that can refuse runs before the rename**, the store-layout
        check included. Validating after publishing left a cloned repository at
        the target whenever it carried no store at the declared path: the command
        reported a failure and the directory stayed, and a re-run then found a
        checkout that was never usable.
        """
        checkout.parent.mkdir(parents=True, exist_ok=True)
        staging = checkout.parent / f".{checkout.name}.tcw-{uuid.uuid4().hex[:8]}"
        try:
            # `--` before the URL and after the `ref`, so neither is read as an
            # option, and a `ref` naming no branch, tag or commit fails rather
            # than being read as a file (TCW-115 Design 7.2).
            self._run(["git", "clone", "--quiet", "--", self.declaration.url,
                       str(staging)])
            if self.declaration.ref:
                self._run(["git", "-C", str(staging), "checkout", "--quiet",
                           self.declaration.ref, "--"])
            self._require_store_layout(
                (staging / self.declaration.path) if self.declaration.path else staging)
            staging.rename(checkout)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise

    def _require_declared_checkout(self, checkout: Path) -> None:
        """Refuse a working copy that is not the declared repository's.

        A declared `checkout` is an arbitrary user-chosen directory, so it can
        hold anything at all; saying it is the declared store when it is not
        would be the one thing `tcw project provision` must never do.

        Comparison is on the URL as spelled, normalized only for a trailing
        slash and a `.git` suffix. Deliberately not smarter: treating `ssh` and
        `https` spellings of one host as equal means deciding two URLs are the
        same repository, which this cannot know. The error says so, because the
        fix in that case is to point `checkout` somewhere else.
        """
        probe = _git(["git", "-C", str(checkout), "rev-parse", "--git-dir"],
                     capture_output=True, text=True)
        if probe.returncode != 0:
            raise ValueError(
                f"{self.component}.repository: {checkout} already exists and is not a "
                f"git repository; move it aside or point `checkout` elsewhere")
        origin = _git(["git", "-C", str(checkout), "remote", "get-url", "origin"],
                      capture_output=True, text=True)
        found = origin.stdout.strip() if origin.returncode == 0 else ""
        if _normalize_remote(found) != _normalize_remote(self.declaration.url):
            raise ValueError(
                f"{self.component}.repository: {checkout} is a checkout of "
                f"{found or '(no origin)'}, not the declared "
                f"{self.declaration.url}; nothing was contacted. Point `checkout` at a "
                f"different directory, or spell the declared url the way that "
                f"checkout's origin does")

    def _run(self, argv: list[str]) -> None:
        """Every git call goes through `_git`, so stdin stays closed, and with
        `_no_prompt_env`, so a remote demanding credentials, a passphrase or a
        host-key confirmation fails instead of asking on the terminal, which
        git and ssh open themselves whatever stdin is."""
        done = _git(argv, capture_output=True, text=True, env=_no_prompt_env())
        if done.returncode != 0:
            raise ValueError(
                f"{self.component}.repository: git {_git_subcommand(argv)} failed: "
                f"{_git_reason(done) or f'exit {done.returncode}'}")


# ── fetching a project that is not on this machine (TCW-115 Design 7.9, 7.10) ──

class FetchRefused(TcwError):
    """A project `tcw project provision` did not fetch, and why: one line,
    starting with the project's ID."""


#: How many staging names are tried before a project is refused (Design 7.9).
STAGING_TRIES = 5


def _same_file(a: os.stat_result, b: os.stat_result) -> bool:
    return (a.st_dev, a.st_ino) == (b.st_dev, b.st_ino)


def _inside(path: Path, top: Path) -> bool:
    """Whether `path`, every link followed, is `top` or below it."""
    return _below(Path(os.path.realpath(path)), Path(os.path.realpath(top))) is not None


def _empty_or_absent(target: Path) -> bool:
    """Whether `target` is absent, or a real folder (not a link) with no
    entries; the name itself is never followed."""
    try:
        found = os.lstat(target)
    except FileNotFoundError:
        return True
    import stat as kinds
    if not kinds.S_ISDIR(found.st_mode):
        return False
    with os.scandir(target) as entries:
        return next(entries, None) is None


def _clone_problem(clone: Path, url: str, project_id: str, subfolder: str | None,
                   kept: dict, group: frozenset, target: Path) -> str | None:
    """What makes the staging clone not the project its entry names (Design
    7.9), or None. Every path read is first checked to lie inside the clone,
    so a committed link never leads these checks to a file elsewhere."""
    where = subfolder or "."
    reads = [Path(subfolder)] if subfolder else []
    at = Path(subfolder) if subfolder else Path()
    reads += [at / TCW_FOLDER, at / SENTINEL]
    if subfolder:
        reads += [Path(TCW_FOLDER), Path(SENTINEL)]
    for relative in reads:
        if os.path.lexists(clone / relative) and not _inside(clone / relative, clone):
            return (f"{project_id}: {url} has a link at '{relative.as_posix()}' that "
                    f"leads outside the clone")
    config = clone / at / SENTINEL
    if not config.is_file():
        if (clone / at / LEGACY_SENTINEL).is_file():
            return f"{project_id}: {url}: {legacy_message(clone / at)}"
        return f"{project_id}: {url} has no TCW project at '{where}'"
    try:
        mapping = yaml.safe_load(config.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
        return f"{project_id}: {url}: {where}/{SENTINEL} cannot be read: {error}"
    problem = version_problem(mapping)
    if problem:
        return f"{project_id}: {url}: {where}/{SENTINEL} {problem}"
    declared = mapping.get("id") if isinstance(mapping, dict) else None
    if declared != project_id:
        return f"{project_id}: {url} holds project '{declared}' at '{where}', not '{project_id}'"
    if subfolder and (clone / SENTINEL).is_file():
        try:
            top = yaml.safe_load((clone / SENTINEL).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
            top = None
        other = top.get("id") if isinstance(top, dict) else None
        if isinstance(other, str) and other not in group and other in kept \
                and _below(Path(os.path.realpath(target)),
                           Path(os.path.realpath(kept[other]))) != Path("."):
            return (f"{project_id}: the clone of {url} holds project '{other}' at its "
                    f"top, but '{other}' is already at {kept[other]}; placing the clone "
                    f"at {target} would give '{other}' a second folder")
    return None


def fetch_project(url: str, branch: str | None, target: Path, *, project_id: str,
                  subfolder: str | None = None, trusted: bool = True,
                  bound: Path | None = None, kept: dict | None = None,
                  group: frozenset = frozenset(), recheck=None, written: str | None = None,
                  file=None, warn=print) -> None:
    """Clone `url` (at `branch`) into `target`, the resolved repository folder
    of project `project_id`'s deciding entry, or raise `FetchRefused` having
    left nothing behind (TCW-115 Design 7.9, 7.10; plan choice 9).

    The clone is made in `<target's parent>/.tcw-staging-<hex>/<name>`, checked,
    and renamed into place within the parent folder held open since it was
    checked, so the folder written is the folder checked. `trusted` entries
    may have their missing parent folders made; a bounded entry's parent must
    be `bound`. `kept` maps the IDs this run keeps answers for to their
    folders, and `group` holds the projects this one clone is made for.
    `recheck()` resolves the entry's path again just before the move;
    `written` is that path as the manifest `file` gives it, for messages."""
    target = Path(target)
    parent = target.parent
    made: list[Path] = []
    fetched = False
    parent_fd = None
    staging = None
    try:
        if trusted and not parent.exists():
            missing = []
            for folder in (parent, *parent.parents):
                if os.path.lexists(folder):
                    break
                missing.append(folder)
            for folder in reversed(missing):
                try:
                    os.mkdir(folder)
                except OSError as error:
                    raise FetchRefused(f"{project_id}: could not make {folder}: "
                                       f"{error.strerror or error}") from None
                made.append(folder)
            if _below(Path(os.path.realpath(parent)), parent) != Path("."):
                raise FetchRefused(f"{project_id}: {parent} led elsewhere once it was made; "
                                   f"nothing was fetched for it")
        try:
            parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
        except OSError as error:
            raise FetchRefused(f"{project_id}: cannot open {parent}: "
                               f"{error.strerror or error}") from None
        held = os.fstat(parent_fd)
        if bound is not None and not _same_file(held, os.stat(bound)):
            raise FetchRefused(f"{project_id}: {parent} is no longer the folder directly "
                               f"inside {bound}; nothing was fetched for it")
        for _ in range(STAGING_TRIES):
            name = f".tcw-staging-{secrets.token_hex(4)}"
            try:
                os.mkdir(name, dir_fd=parent_fd)
            except FileExistsError:
                continue
            staging = name
            break
        else:
            raise FetchRefused(f"{project_id}: could not make a staging folder in {parent}: "
                               f"five names in a row were already taken")
        clone = parent / staging / target.name
        argv = ["git", "clone", "--quiet", *(["--branch", branch] if branch else []),
                "--", url, str(clone)]
        done = _git(argv, capture_output=True, text=True, env=_no_prompt_env())
        if done.returncode != 0:
            raise FetchRefused(f"{project_id}: git clone of {url} failed: "
                               f"{_git_reason(done) or f'exit {done.returncode}'}")
        problem = _clone_problem(clone, url, project_id, subfolder, kept or {}, group,
                                 target)
        if problem is not None:
            raise FetchRefused(problem)
        if recheck is not None:
            again = recheck()
            if _below(Path(os.path.realpath(again)), target) != Path("."):
                raise FetchRefused(f"{project_id}: {written or target} led to {target} when this round "
                                   f"was checked, and now leads to {again}; nothing was "
                                   f"fetched for it")
        if not _same_file(os.stat(parent), held) or not _empty_or_absent(target):
            raise FetchRefused(f"{project_id}: {target} is not empty; move it aside, or "
                               f"correct the manifest entry in {file}")
        try:
            os.rename(f"{staging}/{target.name}", target.name,
                      src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        except OSError as error:
            raise FetchRefused(f"{project_id}: could not move the clone into {target}: "
                               f"{error.strerror or error}") from None
        fetched = True
    finally:
        if staging is not None:
            try:
                if _same_file(os.stat(parent), os.fstat(parent_fd)):
                    shutil.rmtree(parent / staging)
            except OSError as error:
                warn(f"could not remove the staging folder {parent / staging}: "
                     f"{error.strerror or error}; remove it by hand")
        if parent_fd is not None:
            os.close(parent_fd)
        if not fetched:
            for folder in reversed(made):
                try:
                    os.rmdir(folder)
                except OSError:
                    break
