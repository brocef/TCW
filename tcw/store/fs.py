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

import hashlib
import os
import re
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

from tcw.errors import (BackendError, NotFound, Refused, StateFileProblem, TcwError,
                        Unreachable, UsageError)
from tcw.findings import Finding
from tcw.ids import (SCHEME, FolderAddress, FullId, IdError, MalformedId, id_path_problem,
                     parse_address, parse_stored, sort_input)
from tcw.object_folders import (STATE_FILES, exact_child, exact_path, id_problem, read_state,
                                state_text)
from tcw.output import shown as _shown
from tcw.store.yaml_source import UniqueKeyLoader, load as _load_named_yaml
from tcw.store.base import (
    CAP_FIELDS, CAP_LIFECYCLES, MIGRATION_GUIDE, CAP_PRIORITIES, CAP_STATUSES,
    RETIRED_CAP_FIELDS, RETIRED_PROJECTS_KEY, retired_key_problem,
    TAXONOMY_EDITABLE_FIELDS, _UNSET, AmbiguousRef, Capability, CapabilitiesStore,
    CapabilityDetail, NotASlug, is_slug, slugify, StaleRevision,
    parse_repository_declaration, ProvisionResult, RepositoryDeclaration,
    StoreDeclarationError, StoreLocationUnusable, StoreNotProvisioned,
    StoreProvisioner, TaxonomyStore, Term, TermDetail,
)
from tcw.store import config_edit
from tcw.store.checkouts import (
    checkout_root, provisioned_root as provisioned_store_root,
)
from tcw.project_files import (CONFIG_NAME, LOCAL_CONFIG_NAME, LOCAL_MANIFEST,
                               LOCAL_MANIFEST_NAME, LOCAL_SENTINEL, MANIFEST_NAME,
                               SENTINEL, TCW_FOLDER, V3, V4,
                               find_marker, legacy_message, version_problem,
                               without_version)
from tcw.store.project import (FsProjectRegistry, _below, forget_registries,
                               validate_project_id, worktree_anchors)

# Component trees `tcw init` scaffolds. `work` gets a status-folder skeleton;
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
    def open(cls, project_root: Path) -> "WorkLocation":
        return resolve_store(cls, Path(project_root))

    @classmethod
    def _local_root(cls, project_root: Path, configured: str | None, *,
                    locator=None) -> Path:
        return store_location(project_root, cls.COMPONENT, configured, locator=locator)

    @classmethod
    def _open_at(cls, raw_root: Path, project_root: Path, config_path: Path, *,
                 external: bool, must_exist: bool = True, declaration=None,
                 _walk=None) -> "WorkLocation":
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
#: The lines `tcw init` writes in `.tcw/.gitignore` for the two personal
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


def find_component_project(component: str, start: Path | None = None) -> Path | None:
    """The project owning `component`'s store, or None. A project is the nearest
    ancestor marked by a `tcw-config.yaml` sentinel (FS-adapter-local). Returns
    the project iff it has that component, preserving the prior contract.

    "Has that component" is asked of the *resolved* store, never of a literal
    `docs/<component>` folder. The two answers differ in exactly the case this
    feature exists for: a checkout that cloned only the code repository has no
    `docs/taxonomy/`, because the taxonomy is in the other repository — so
    looking for the folder answered None before the resolution ladder could read
    the declaration, and the project's own config went unread.
    """
    nr = find_project_root(start)
    if nr is None:
        return None
    FsProjectRegistry.open(nr).require_valid()
    try:
        store = STORE_CLASSES[component].open(nr)
    except (StoreNotProvisioned, StoreDeclarationError):
        # Not "no project here" — the project is right in front of us and says where
        # its store comes from. Flattening this to None is what made `tcw work
        # list` answer a declared-but-absent store with "run `tcw init`", which
        # would scaffold a second, empty store beside the real one.
        #
        # A *malformed* declaration is the same project with the same hazard, only
        # the actionable message is "fix this line" rather than "run this
        # command", so it travels the same way.
        raise
    except StoreLocationUnusable:
        # The one failure that means "there is no store at this location" — the
        # ladder's own definition (see `resolve_store`). Anything else, a broken
        # `extends` or a malformed `<component>.path`, is a project that is here and
        # wrong, and "run `tcw init`" is the wrong advice for it.
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
    see", which `tcw validate` uses: `extends` alone is not a location, and a
    project that only inherits a taxonomy should not have its capability checks
    fail on that inheritance. It resolves no location: presence is read from
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
    # `tcw init work --work-path`) that predates the mapping.
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
    # `tcw init`" advice for a configured-but-absent store never came true.
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
            # advice: "run `tcw provision`" after it succeeded sends the user in
            # a circle.
            others = [o for o in components if o != c]
            rest = (f" To scaffold the rest, name them: `tcw init {' '.join(others)}`."
                    if others else "")
            try:
                resolve_store(STORE_CLASSES[c], root)
            except ValueError:
                raise ValueError(
                    f"{root / SENTINEL}: {c} declares a repository; run `tcw provision` "
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


def _extends_ids(config: dict, label: str) -> list[str]:
    """The declared `extends` list, or a `ValueError` naming what is wrong.

    `label` is how a refusal addresses the declaration. It is the key path —
    `<path>/tcw-config.yaml: taxonomy.extends` — not just the file, because one
    project config can hold both `taxonomy.extends` and `capabilities.extends` and
    naming only the file leaves the reader to guess which one is meant.

    All four refusals carry it, including the project-id one: `validate_project_id`
    raises a perfectly good message about the id and knows nothing about where
    the id was read from, which sent people hunting for a key nothing named.
    """
    value = config.get("extends") or []
    if isinstance(value, dict):
        raise ValueError(
            f"{label}: legacy extends map is unsupported; replace it with "
            "a list of registered project IDs"
        )
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        raise ValueError(f"{label}: extends must be a list of project IDs")
    ids = []
    for v in value:
        try:
            ids.append(validate_project_id(v))
        except ValueError as error:
            raise ValueError(f"{label}: {error}") from None
    if len(ids) != len(set(ids)):
        raise ValueError(f"{label}: extends contains duplicate project IDs")
    return ids


class _FederationWalk:
    """State threaded down an `extends` walk.

    Two things with different lifetimes, which is why they cannot be one set.
    `seen` is the projects on *this* path, copied at every descent, and is what
    detects a cycle: a project is a back edge only relative to the route that
    reached it. `built` is shared by the whole walk and is what stops a diamond
    from rebuilding the same subtree once per route — `seen` alone terminated a
    cycle and memoised nothing, so a graph where two extended projects reach a
    common ancestor cost 2^depth store constructions.

    **Only a subtree that truncated nothing is cached.** A store built with a
    cycle truncated in it is correct for the path that built it and wrong for any
    other, since a back edge is a property of the route. A cycle-free subtree is
    path-independent, so it can be reused anywhere — and that is the common case,
    which is the one the cost was in.
    """

    __slots__ = ("seen", "built", "active_root")

    def __init__(self, seen: "frozenset[Path]" = frozenset(),
                 built: "dict | None" = None, active_root: Path | None = None):
        self.seen = seen
        self.built = {} if built is None else built
        # The root of the project the command acts on, whose `Locator` every
        # store opened on this walk uses (TCW-110 Design 6.1): None until a
        # store sets it, so the first store's own project is the active one.
        self.active_root = active_root

    def descend(self, project_root: Path) -> "_FederationWalk":
        """The walk as seen one project further down. Shares `built`."""
        return _FederationWalk(self.seen | {project_root}, self.built, self.active_root)


class _FederationCycles:
    """Mixin for the two tree stores: the cycles anywhere below this one.

    A cycle is recorded by the store that closes it — the deepest one built —
    so a caller checking the store at the top of the chain finds nothing on
    itself. Gathering the whole tree is what makes `check()` report a cycle
    from wherever it is run.
    """

    def _federation_cycles(self) -> list[str]:
        cached = getattr(self, "_cycles_cache", None)
        if cached is not None:
            return cached
        found: list[str] = list(getattr(self, "extends_cycles", []))
        for store in getattr(self, "extends", {}).values():
            for project_id in store._federation_cycles():
                if project_id not in found:
                    found.append(project_id)
        # Memoised because the `extends` tree is fixed once construction
        # returns, and because the walk asks this of every store it builds to
        # decide whether the subtree may be cached — recomputing it there would
        # trade one quadratic for another.
        self._cycles_cache = found
        return found


class _NotInherited(ValueError):
    """Design 3.6's refusal of an `extends` ID the project does not inherit
    that axis from."""


def _extends_target(registry, axis: str, owner_root: Path, owner_id: str,
                    extends_id: str) -> "Project":
    """The project an `extends` ID of the project at `owner_root` names,
    held to the parent links until TCW-112 (Design 3.6, 6.3): it must pass
    `axis` to that project. A passing project not available here raises
    `InheritedUnavailable` (exit 7), as does any ID while some passing
    project is not available, since what lies above is then unknown; any
    other ID raises `_NotInherited`. `registry` is the command's one, and the
    load order is the store's own project's, which may lie outside the
    active project's family (Design 3.6's "whose links decide")."""
    active = owner_id in ("", registry.current.id) and \
        _same_folder_or_equal(owner_root, registry.project_root)
    order = registry.load_order() if active else \
        registry.load_order(owner_id, root=owner_root)
    owner = order.ids[-1]
    passes = registry.passing_in(order, axis) - {owner}
    absent = {*order.missing, *order.unreadable}
    if extends_id in passes:
        if extends_id in absent:
            raise registry.inherited_unavailable(order, axis, extends_id)
        return registry.order_project(extends_id)
    blocked = next((pid for pid in order.ids if pid in passes and pid in absent), None)
    if blocked is not None:
        raise registry.inherited_unavailable(order, axis, blocked)
    raise _NotInherited(
        f"'{extends_id}' is in {axis}.extends, but '{owner}' does not inherit its "
        f"{axis} from it: name it under 'parents:' with an 'inherit' that includes "
        f"{axis}")


def _same_folder_or_equal(a: Path, b: Path) -> bool:
    try:
        return Path(a).resolve() == Path(b).resolve()
    except OSError:
        return False


def _extended_component_stores(
    project_root: Path, config: dict, label: str, component: str,
    walk: "_FederationWalk | None" = None, owner_id: str = "",
) -> "tuple[dict[str, object], list[str]]":
    """Each extended project's component store, by project id, and the ids whose
    edge closed a cycle.

    `walk` carries the state of the whole `extends` walk — see
    `_FederationWalk`. Its `seen` half is the *projects* already on this path,
    and it is checked before the store is opened, which it has to be: resolving a
    sibling's store now opens it, and opening a tree store resolves its own
    `extends`, so a cycle would recur infinitely instead of being reported.
    Project identity is known before any store is touched, which is what makes
    the guard possible at all — and a cycle in `extends` is a cycle among
    projects, so this is also the
    honest place to detect one.
    """
    from tcw.locate import Locator
    ids = _extends_ids(config, label)
    active_root = (walk.active_root if walk is not None and walk.active_root is not None
                   else project_root)
    registry = Locator.of(active_root).registry if ids else None
    if registry is not None:
        registry.require_valid()
    walk = (walk or _FederationWalk()).descend(project_root.resolve())
    stores: dict[str, object] = {}
    cyclic: list[str] = []
    for project_id in ids:
        # Identity first: extending yourself is wrong whatever the store does,
        # and asking the store about it would make a config error depend on
        # whether a tree happens to be provisioned.
        if owner_id and project_id == owner_id:
            raise ValueError(f"a {component} store cannot extend itself")
        try:
            project = _extends_target(registry, component, project_root, owner_id,
                                      project_id)
        except _NotInherited as refused:
            # `label` already ends in `<component>.extends`.
            raise ValueError(f"{label}: {refused}") from None
        if Path(project.locator).resolve() == project_root.resolve():
            raise ValueError(f"a {component} store cannot extend itself")
        if Path(project.locator).resolve() in walk.seen:
            # The back edge of a federation cycle. Truncated here so the walk
            # terminates, and *named*, because a truncated tree cannot show a
            # cycle to anyone looking at it afterwards — which is why `check()`
            # used to report nothing at all.
            cyclic.append(project_id)
            continue
        # The extended project's *configured* store, not `docs/<component>` under
        # its root. Composing that path skipped the whole resolution ladder, so a
        # sibling that had moved its tree with `<component>.path` could not be
        # extended from, and one whose tree was declared but unprovisioned read
        # as having no tree at all — the confusion the ladder exists to end.
        # Failures are re-worded for a reader standing in a *different* project than
        # the one that failed.
        cache_key = (component, Path(project.locator).resolve())
        if (cached := walk.built.get(cache_key)) is not None:
            # Built already, somewhere else on this walk, with nothing truncated
            # in it — see `_FederationWalk`. This is what makes a diamond cost
            # one construction of the shared subtree instead of one per route.
            stores[project_id] = cached
            continue
        try:
            # The store itself, not its root. Rebuilding it from the root is
            # what broke the hop past a moved tree — `FsTreeStore` falls back to
            # `root.parent.parent` for `project_root`, correct only for the
            # `docs/<component>` shape this resolution exists to stop assuming.
            store = STORE_CLASSES[component].open(
                Path(project.locator), _walk=walk)
        except StoreNotProvisioned as error:
            raise ValueError(f"project '{project_id}': {error}") from None
        except StoreDeclarationError as error:
            raise ValueError(f"project '{project_id}': {error}") from None
        except ValueError as error:
            # The sibling's own error, quoted. Rewriting every `ValueError` as
            # "has no <component> component" sent readers to create a store that
            # already existed — a legacy `extends` map, a failed `require_valid`
            # and a self-extend all arrived here wearing that message.
            raise ValueError(f"project '{project_id}': {error}") from None
        # Rule 4 of the ladder validates nothing for a bare default, so a project
        # with no tree at all resolves to a path that is simply not there. That
        # is the honest answer for the project's *own* store and the wrong one to
        # federate from.
        if not store.root.is_dir():
            raise ValueError(f"project '{project_id}' has no {component} component")
        if not store._federation_cycles():
            walk.built[cache_key] = store
        stores[project_id] = store
    return stores, cyclic


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
    #: The filename this component once kept its own `extends` in, before it
    #: moved to the project's `tcw-config.yaml`. Nothing reads or writes the file
    #: any more. The name survives on the class for two reasons: `_entry_reserved`
    #: keeps it out of a folder's attachments (see the comment there), and
    #: `_legacy_config_problems` reports a copy left at the store root.
    LEGACY_CONFIG_NAME: str | None = None
    #: The file whose presence makes a folder one of this store's objects
    #: (TCW-111 Design 1.1).
    STATE_FILE: str

    def __init__(self, root: Path, *, project_root: Path | None = None,
                 store_git_root: Path | None = None):
        self.root = root                       # docs/<component>/, or wherever configured
        # Two roots, because they answer different questions and diverge the
        # moment a store leaves its project's repository — the same split the
        # work store has carried since `work.path` existed.
        #
        # `project_root` is the *project*: whose config this is, and what federation
        # resolves `extends` against. `store_git_root` is the repository a write
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
        # opened for another, as an inherited store or an owner's store read
        # by `Locator.read` is (see `_walk_for`).
        self._active_root = self.project_root

    def _walk_for(self, walk: "_FederationWalk | None") -> "_FederationWalk":
        """The walk this store resolves its `extends` on, carrying the active
        project's root, which this store adopts."""
        if walk is not None and walk.active_root is not None:
            self._active_root = walk.active_root
            return walk
        return _FederationWalk(*((walk.seen, walk.built) if walk else ()),
                               active_root=self._active_root)

    @property
    def locator(self):
        """The command's one `Locator`, for the active project (TCW-110
        Design 6.1): a reference read here, or a location written in this
        project's file, is looked up on that project's registry."""
        from tcw.locate import Locator
        return Locator.of(self._active_root)

    def owner_of(self, origin: str) -> str:
        """The ID of the project that holds an entry resolved through
        `origin`: this store's own project for `"local"`, else the `extends`
        ID it came through."""
        return self.project_id if origin == "local" else origin

    def _stored_ref(self, value, namespace: str, store=None):
        """What a reference stored in this project's records names (TCW-110
        Design 5.2, 6): a `tcw.locate.Outcome`. `store` is the store of
        `namespace` already open for this project (this one for its own
        namespace), read directly for its own and its inherited entries;
        every other owner is read through the command's `Locator`. A value
        in a 3.x form or none at all is an `error` outcome naming why."""
        from tcw.locate import ERROR, FOUND, MISSING, Outcome
        try:
            full_id = parse_stored(value, namespace)
        except IdError as error:
            return Outcome(ERROR, message=str(error))
        if store is None and namespace == self.COMPONENT:
            store = self
        if store is not None:
            if full_id.project == store.project_id:
                hit = store.get_local(full_id.id_path)
                return Outcome(FOUND, hit) if hit else Outcome(MISSING)
            if full_id.project in store._inherited():
                hit = store.get_inherited(full_id.project, full_id.id_path)
                return Outcome(FOUND, hit) if hit else Outcome(MISSING)
        try:
            return self.locator.read(full_id, named_by=self.project_root)
        except (ValueError, OSError, TcwError) as error:
            return Outcome(ERROR, message=str(error))

    def _local_ref(self, value) -> "Term | Capability | None":
        """This store's own entry that a stored reference of its namespace
        names, or None for any other value: what a removal compares against,
        never looking another project up."""
        try:
            full_id = parse_stored(value, self.COMPONENT)
        except IdError:
            return None
        return self.get_local(full_id.id_path) if full_id.project == self.project_id \
            else None

    def _input_ref(self, text, label: str):
        """The entry a reference value given to a write names, read as command
        input is (TCW-110 Design 3.1), for the full identifier the write
        stores (Design 5.3). A value naming nothing is a usage error."""
        from tcw.locate import find_tree
        try:
            return find_tree(self, str(text))
        except AmbiguousRef:            # before NotFound, its base class
            raise UsageError(f"{label} ref '{text}' is ambiguous") from None
        except NotFound:
            raise _DanglingRef(f"{label} ref '{text}' does not resolve") from None

    @classmethod
    def open(cls, project_root: Path, _walk: "_FederationWalk | None" = None,
             locator=None):
        """Resolve this project's store for this component. The ladder is
        `resolve_store`, shared with the work store.

        `locator` is the command's `Locator` when the store opened is not the
        active project's own (TCW-110 Design 6.1): the store then looks
        projects up on that one registry. None means it is the active one.

        `_walk` is private and carries the federation walk's state: the projects
        already on this path, so `extends` can resolve a sibling's store without
        a cycle becoming infinite recursion, and the stores already built
        anywhere on the walk, so a shared subtree is built once. Callers outside
        federation never pass it.
        """
        if locator is not None and (_walk is None or _walk.active_root is None):
            _walk = _FederationWalk(*((_walk.seen, _walk.built) if _walk else ()),
                                    active_root=locator.root)
        return resolve_store(cls, project_root, _walk=_walk)

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
                 _walk: "_FederationWalk | None" = None):
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
        # The project stays the project — federation resolves `extends` against it —
        # while writes follow the store into whatever repository holds it.
        return cls(root, _walk=_walk, project_root=project_root,
                   store_git_root=owner)

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
        `unreadable` instead (Design 1.5)."""
        try:
            self._state(d)
        except StateFileProblem as problem:
            self.unreadable[problem.path] = problem.problem
            return False
        return True

    def unreadable_files(self) -> dict[Path, str]:
        """`unreadable`, with that of every store this one inherits from:
        what a `list` of the whole view left out."""
        found = dict(self.unreadable)
        for store in self._inherited().values():
            found.update(store.unreadable)
        return found

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
    # On `FsTreeStore` rather than on one component, because all three now write
    # it: `work.tags`, `taxonomy.extends` and `capabilities.extends`. It is the
    # project's file, not any store's, and the two roots vary independently.

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

    def _persist_extends(self, extends: list[str]) -> None:
        """Write this component's `extends` to the project config, and keep the
        in-memory copy in step.

        The in-memory update is why this is not just `_write_project_config`: a
        second add/rm in the same process reads `self.config`, and term
        *resolution* (`self.extends`) stays load-time only — reopen to use it.
        An empty list removes the key rather than writing `extends: []`, which
        is what the per-store file did.

        The in-memory copy changes only once the write has succeeded, so a
        refused write leaves this store agreeing with the file.
        """
        config = self._config()
        section = config.get(self.COMPONENT)
        if section is not None and not isinstance(section, dict):
            # Reading normalizes this to "no configuration" (`_component_config`,
            # matching `resolve_store`), and writing could do the same — but
            # reading discards nothing, while writing would replace whatever the
            # user typed with a mapping of our own. `taxonomy: docs/taxonomy` is
            # someone reaching for `taxonomy: {path: docs/taxonomy}`, and telling
            # them so costs less than silently deleting it.
            raise Refused(
                f"{self._config_path()}: {self.COMPONENT} must be a mapping, "
                f"found {type(section).__name__}")
        # `Remove` drops a section that is left holding nothing, so removing the
        # last `extends` from a project that configured nothing else leaves the
        # config as it was rather than growing an empty `taxonomy: {}`.
        self._write_project_config([
            config_edit.SetList(self.COMPONENT, "extends", tuple(extends)) if extends
            else config_edit.Remove(self.COMPONENT, "extends")])
        if extends:
            self.config["extends"] = extends
        else:
            self.config.pop("extends", None)

    def _extends_label(self) -> str:
        """What a refusal about `extends` calls the thing it is refusing.

        The key path, not just the file: one `tcw-config.yaml` can hold both
        `taxonomy.extends` and `capabilities.extends`, and a message naming only
        the file leaves the reader to guess which one is wrong.
        """
        return f"{self._config_path()}: {self.COMPONENT}.extends"

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

    def _rm(self, path: Path) -> None:
        """Delete a folder entry from disk, whatever git knows of it, recording
        one `removed` line per file it held."""
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

    def _entry_reserved(self) -> set[str]:
        """Filenames in an entry folder that are not attachments.

        **Kept per-store after `extends` moved to the project config.** Each store
        still reserves the file it used to write — taxonomy `config.yaml`,
        capabilities `.config.yaml` — so a folder holding a leftover copy lists
        the same attachments it listed before.

        Only taxonomy can actually observe this: `_term` carries the list onto
        `Term.attachments`, while `_capability` discards it and composes bodies
        from `prependedDocs`/`appendedDocs` read by name out of the state file. So
        the capabilities half is inert, and is kept anyway — the two stores
        reading alike costs one string and removes the question. See
        `test_the_capabilities_store_has_no_attachment_surface_to_regress`,
        which fails if `Capability` ever grows an attachments field and makes
        this reasoning stale.
        """
        names = {self.STATE_FILE, "description.md"}
        if self.LEGACY_CONFIG_NAME:
            names.add(self.LEGACY_CONFIG_NAME)
        return names

    def _where(self, path: Path | str) -> str:
        """A finding's `where`: `path`, or an entry's slug joined onto the store
        root, relative to the project root when it is inside it."""
        path = self.root / path if isinstance(path, str) else path
        try:
            return str(path.relative_to(self.project_root))
        except ValueError:
            return str(path)

    def _store_finding(self, message: str) -> Finding:
        """A problem with the store's federation, which `tcw-config.yaml`
        configures."""
        return Finding("error", self._where(self._config_path()), message)

    def _legacy_config_problems(self) -> list[Finding]:
        """The pre-2.5.0 config file at this store's root, reported, or `[]`.

        An upgraded project that never moved its `extends` out of this file
        silently lost every inherited entry, and nothing said why. So a copy at
        the store root is a problem whatever it holds — even one that only
        repeats `<component>.extends` misleads the next reader into thinking it
        is read. Existence only: the file is never opened, so a corrupt copy
        cannot make `check` raise, and it is never rewritten or deleted.

        Only the root: a file of the same name inside a folder entry is an
        ordinary file of that entry.
        """
        if not self.LEGACY_CONFIG_NAME:
            return []
        path = self.root / self.LEGACY_CONFIG_NAME
        if not path.is_file():
            return []
        return [Finding("error", self._where(path),
                        f"no longer read since TCW 2.5.0 — move any needed "
                        f"extends into {self._extends_label()}, then delete the "
                        f"file; if already migrated, just delete it")]

    def _load_entry(self, d: Path) -> tuple[dict, str, list[str]]:
        """Read a folder entry → (meta mapping, description text, attachment names).

        Attachments are the folder's non-reserved, non-dot files (bounded set).
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
        reserved = self._entry_reserved()
        attachments = sorted(
            f.name for f in d.iterdir()
            if f.is_file() and f.name not in reserved and not f.name.startswith(".")
            and self._within_store(f))
        return meta, description, attachments

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


class FsTaxonomyStore(FsTreeStore, _FederationCycles, TaxonomyStore):
    """`TaxonomyStore` over nested dirs under `docs/taxonomy/` (Phase 2 B.3).

    A term's slug is its directory path under the taxonomy root. `extends`
    aliases (local-path repo roots) are realized as nested stores.
    """
    COMPONENT = "taxonomy"
    LEGACY_CONFIG_NAME = "config.yaml"
    STATE_FILE = STATE_FILES["taxonomy"]

    def __init__(self, root: Path, *,
                 _walk: "_FederationWalk | None" = None,
                 project_root: Path | None = None, store_git_root: Path | None = None):
        super().__init__(root, project_root=project_root, store_git_root=store_git_root)
        self.extends: dict[str, "FsTaxonomyStore"] = {}
        # Reused, never rebuilt: the resolution below already constructed each
        # store with the right project root and the right walk state. There is no
        # second filter on the results — the `_seen` set that used to be one was
        # dead once recursion moved into `_extended_component_stores`, since the
        # only case it could refuse is a self-extend the identity check there
        # already refuses by project id.
        self.extends, self.extends_cycles = _extended_component_stores(
            self.project_root, self.config, self._extends_label(), "taxonomy",
            walk=self._walk_for(_walk), owner_id=self.project_id,
        )

    # -- reads --

    def _term(self, slug: str, origin: str = "local") -> Term:
        d = self.root / slug
        meta, description, attachments = self._load_entry(d)
        return Term(
            slug=slug,
            name=meta.get("name") or slug.rsplit("/", 1)[-1].replace("-", " ").title(),
            description=description,
            kind=_normalize_taxonomy_kind(meta.get("kind")),
            relates_to=list(meta.get("relatesTo") or []),
            vocabulary=list(meta.get("vocabulary") or []),
            attachments=attachments,
            origin=origin,
            modified=_modified_timestamp(
                [d / self.STATE_FILE, d / "description.md"]
            ),
            owner=self.owner_of(origin),
        )

    def get_local(self, slug: str) -> Term | None:
        """This store's own project's entry at the id-path `slug`, every
        folder spelled exactly as given, or None."""
        # A ref is joined onto the store root, so it is bounded input like any
        # other store id: one that escapes (`../capabilities/thing`) resolves to
        # nothing rather than raising — `get()` is documented to return None for
        # a ref that resolves to nothing, and `check()` catches only AmbiguousRef,
        # so a raise here would crash `check` on a taxonomy that already holds one.
        try:
            slug = _safe_store_id(slug, "term ref")
        except UsageError:
            return None
        d = self.root / slug
        # Order matters: the cheap stat first, so a miss pays no `resolve()`;
        # containment second; the spelling, read from the listings, third;
        # the read (`_term`) only after all three.
        return self._term(slug) if d.is_dir() and self._entry_readable(d) \
            and exact_path(self.root, slug) is True else None

    def _local_slugs(self) -> list[str]:
        # `list` must not advertise what `show`/`rm` refuse. Note `rglob` does
        # not descend into a symlinked directory, so only the final component
        # can be one — but that is the case this filter is for.
        return sorted(
            str(p.relative_to(self.root)) for p in self.root.rglob("*")
            if p.is_dir() and self._entry_readable(p) and self._listable(p))

    def _inherited_stores(self) -> dict[str, "FsTaxonomyStore"]:
        """Every inherited taxonomy keyed by its owning project ID.

        ``self.extends`` remains the direct declarations used by writes and cycle
        checks.  Reads flatten their nested stores so a source keeps the same
        canonical namespace regardless of the route that reaches it.
        """
        stores: dict[str, FsTaxonomyStore] = {}
        for project_id, store in self.extends.items():
            stores.setdefault(project_id, store)
            for inherited_id, inherited_store in store._inherited_stores().items():
                stores.setdefault(inherited_id, inherited_store)
        return stores

    def list_all(self, local_only: bool = False) -> list[Term]:
        terms = [self._term(s) for s in self._local_slugs()]
        if not local_only:
            for project_id, store in self._inherited_stores().items():
                terms += [
                    self._term_via(store, slug, project_id)
                    for slug in store._local_slugs()
                ]
        return terms

    @staticmethod
    def _term_via(store: "FsTaxonomyStore", slug: str, alias: str) -> Term:
        return store._term(slug, origin=alias)


    def get_view(self, slug: str) -> Term | None:
        """An id-path read as the active project sees it (TCW-110 Design 3.1
        form d): the local entry first, else the one inherited entry at that
        path. `AmbiguousRef` when two inherited projects both hold it."""
        ref = slug
        inherited_stores = self._inherited_stores()
        local = self.get_local(ref)                    # bare-wins-local (B.6.2)
        if local is not None:
            return local
        matches = [
            (project_id, term)
            for project_id, store in inherited_stores.items()
            if (term := store.get_local(ref)) is not None
        ]
        if len(matches) == 1:
            project_id = matches[0][0]
            return self._term_via(inherited_stores[project_id], ref, project_id)
        if len(matches) > 1:
            raise AmbiguousRef(ref, "taxonomy")
        return None

    def get_inherited(self, alias: str, slug: str) -> Term | None:
        """The entry at id-path `slug` in project `alias`, one this store
        inherits from, as this project sees it, or None."""
        st = self._inherited_stores().get(alias)
        return self._term_via(st, slug, alias) if st and st.get_local(slug) else None

    def _inherited(self) -> dict[str, "FsTaxonomyStore"]:
        """The projects whose entries this store reads as its own, by ID."""
        return self._inherited_stores()

    def _found(self, target: "FullId | str") -> Term | None:
        """The entry an operation naming one existing object acts on: a full
        identifier of this project's own entry or of one it inherits, or text
        sorted as command input is (TCW-110 Design 3.1), an id-path read by
        `get_view`. Another project's entry is not this store's to act on."""
        if isinstance(target, str):
            found = sort_input(target, "taxonomy")
            if found.form == "d":
                return self.get_view(found.id_path)
            target = found.full_id
        if target.project == self.project_id:
            return self.get_local(target.id_path)
        return self.get_inherited(target.project, target.id_path)

    def search(self, query: str) -> list[Term]:
        q = query.lower()
        return [t for t in self.list_all()
                if q in t.name.lower() or q in t.description.lower()]

    # -- writes --

    def add(self, name: str, slug: str | None = None, parent: str | None = None,
            description: str = "", kind: str = "Vocabulary",
            vocabulary: list[str] | None = None) -> Term:
        leaf = _safe_store_id(slug or slugify(name), "slug")
        # After `_safe_store_id`, so a slug that would leave the store is still
        # "invalid slug"; nesting is `parent`'s job, so a `/` is refused here.
        if slug and not is_slug(leaf):
            raise NotASlug(f"{slug!r} is not a slug: use lowercase letters, "
                           f"digits and single hyphens")
        if parent:
            parent = _safe_store_id(parent, "parent")
            _check_id_path(parent.strip("/"), "parent")
        full = f"{parent.strip('/')}/{leaf}" if parent else leaf
        _check_id_path(full, "slug")
        if parent and not (self.root / parent).is_dir():
            raise UsageError(f"parent term does not exist: {parent}")
        kind = _normalize_taxonomy_kind(kind)
        if kind not in TAXONOMY_KINDS:
            raise UsageError(f"invalid taxonomy kind '{kind}' "
                             f"(choose: {', '.join(sorted(TAXONOMY_KINDS))})")
        d = self.root / full
        # Before `d.exists()` and before the first mkdir: one guard covers a
        # symlinked `--parent` and a symlinked leaf alike, and it keeps the
        # fail-closed contract below (a rejected write leaves no partial folder).
        if not self._within_store(d):
            raise UsageError(f"parent term does not exist: {parent or full}")
        if d.exists() or d.is_symlink():   # a dangling/looping link reads absent
            raise Refused(f"term already exists: {full}")
        # Fail closed on refs *before* the first mkdir: a rejected write must
        # leave no partial folder behind. The same rules `check` applies, so a
        # term that `add` accepted never fails the very next `check`.
        if kind == "Feature" and not vocabulary:
            raise UsageError("Feature requires at least one vocabulary ref")
        meta = {"name": name, "kind": kind, "relatesTo": []}
        if vocabulary:
            meta["vocabulary"] = [self._resolve_vocab_ref(r) for r in vocabulary]
        self._write_entry(d, meta, description)
        return self._term(full)

    def remove(self, ref: "FullId | str") -> None:
        term = self._found(ref)
        # The exact listed spelling only, as `FsCapabilitiesStore.remove`: on a
        # case-insensitive disk `ADMIN` resolves to the `admin` folder but echoes
        # the spelling back as the slug, and git would not find that path.
        if term is not None and term.origin == "local" and term.slug not in self._local_slugs():
            term = None
        if term is None:
            raise NotFound(f"no such term: {ref}")
        if term.origin != "local":
            raise Refused(f"cannot remove inherited term '{term.full_id}' "
                             f"(edit it at its source)")
        d = self.root / term.slug
        # Refused, never cascaded, and decided from the disk (TCW-73 Design
        # 8.2): a nested term is a folder under this one holding a state file.
        # Everything else in the folder — attachments, files an operating
        # system writes on its own, files git has never seen — goes with it.
        # A sub-folder without a state file still lists as a term, so the
        # reference checks below cover it too: a term or capability naming
        # `invoice/sub` refuses the removal of `invoice` exactly as one naming
        # `invoice` does, and nothing is left pointing at a deleted folder.
        nested = sorted({str(m.parent.relative_to(self.root))
                         for m in d.rglob(self.STATE_FILE) if m.parent != d})
        if nested:
            raise Refused(f"cannot remove '{term.slug}': nested under it: "
                          f"{', '.join(nested)} (remove those first)")
        referrers = self._referrers(d) + self._capability_referrers(d, term.slug)
        if referrers:
            raise Refused(f"cannot remove '{term.slug}': still referenced by "
                             f"{', '.join(referrers)} (repoint or clear those first)")
        self._rm(d)

    def _capability_referrers(self, target: Path, slug: str) -> list[str]:
        """`capability <path> (Subject|Feature)` for every local capability whose
        reference resolves to the term folder `target` or a folder inside it —
        what `tcw validate` would report dangling once it is gone.

        The project's capabilities store is found by the normal resolution. None
        here: nothing to ask. One that cannot be opened or read refuses the
        removal, because whether it names the term cannot then be known.
        """
        try:
            caps = FsCapabilitiesStore.open(
                self.project_root, _walk=_FederationWalk(active_root=self._active_root))
            if not caps.root.is_dir():
                return []
            local = caps.list_all(local_only=True)
            # An override's references become the composed capability's own, so
            # a term one names is as named as one a local capability names.
            overrides = caps._override_fields()
        except (ValueError, TcwError, yaml.YAMLError) as e:
            raise Refused(f"cannot remove '{slug}': the capabilities that might "
                             f"name it cannot be read: {e}") from None
        referrers = ([(f"capability {cap.path}", cap.fields) for cap in local]
                     + [(f"capability override {path}", fields)
                        for path, fields in overrides])
        out = []
        for label, fields in referrers:
            named = set()
            for field, ref in FsCapabilitiesStore._term_refs(fields):
                hit = self._local_ref(ref)
                if (hit is not None and hit.origin == "local"
                        and _in_folder(self.root / hit.slug, target, self.root)):
                    named.add(field)
            out += [f"{label} ({field})"
                    for field in ("Subject", "Feature") if field in named]
        return out

    def _referrers(self, target: Path) -> list[str]:
        """`<term> (<field>)` for every other local term whose `relatesTo` or
        `vocabulary` resolves to the local term folder `target` or a folder
        inside it — exactly the refs `check` would report dangling once it is
        gone. Compared by folder
        identity, not spelling, so `admin/permission` never matches a top-level
        `permission`."""
        out = []
        for term in self.list_all(local_only=True):
            if _in_folder(self.root / term.slug, target, self.root):
                continue
            # `vocabulary` only on a Feature, the one kind `check` reads it on.
            vocabulary = term.vocabulary if term.kind == "Feature" else []
            for field, refs in (("relatesTo", term.relates_to),
                                ("vocabulary", vocabulary)):
                for ref in refs:
                    hit = self._local_ref(ref)
                    if (hit is not None and hit.origin == "local"
                            and _in_folder(self.root / hit.slug, target, self.root)):
                        out.append(f"{term.slug} ({field})")
                        break
        return out

    def extends_add(self, project_id: str) -> None:
        try:
            project_id = validate_project_id(project_id)
        except ValueError as e:
            raise UsageError(str(e)) from None             # a malformed name (Design 4)
        extends = _extends_ids(self.config, self._extends_label())
        if project_id in extends:
            raise Refused(f"extends project already exists: {project_id}")
        if project_id == self.project_id:
            raise Refused("a taxonomy cannot extend itself")
        registry = self.locator.registry.require_valid()
        try:
            # Design 3.6: an ancestor passing taxonomy; exit 7 when what lies
            # above is not known, and nothing written.
            project = _extends_target(registry, "taxonomy", self.project_root,
                                      self.project_id, project_id)
        except _NotInherited as refused:
            raise UsageError(str(refused)) from None
        if not (Path(project.locator) / "docs" / "taxonomy").is_dir():
            raise UsageError(f"project '{project_id}' has no docs/taxonomy/")
        extends.append(project_id)
        self._persist_extends(extends)

    def extends_remove(self, project_id: str) -> None:
        extends = _extends_ids(self.config, self._extends_label())
        if project_id not in extends:
            raise NotFound(f"no such extends project: {project_id}")
        extends.remove(project_id)
        self._persist_extends(extends)

    # -- validation --

    def _ref_problem(self, ref, label: str, expect_vocabulary: bool = False
                     ) -> "tuple[Term | None, tuple[str, str] | None]":
        """Resolve one stored taxonomy ref (TCW-110 Design 5.2): `(term,
        problem)`, `problem` None when it names an entry (and, with
        `expect_vocabulary`, a Vocabulary one), else `(level, message)` as
        `check` reports it."""
        from tcw.locate import FOUND
        outcome = self._stored_ref(ref, "taxonomy")
        if outcome.kind != FOUND:
            return None, _ref_finding(label, ref, outcome)
        term = outcome.value
        if expect_vocabulary and term.kind != "Vocabulary":
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
        top_level = {s.split("/")[0] for s in self._local_slugs()}
        for project_id in self._federation_cycles():
            problems.append(self._store_finding(
                f"extends '{project_id}': cycle in taxonomy federation"))
        for project_id in self._inherited_stores():
            if project_id in top_level:
                problems.append(self._store_finding(
                    f"project ID '{project_id}' collides with local top-level term"))
        if identifier is None:
            # About the store, not any one term — left out of a scoped check,
            # which is how `tcw serve` validates the object it just wrote.
            problems += self._legacy_config_problems()

        if identifier is not None:
            try:
                selected = self.get_view(identifier)
            except StateFileProblem as problem:
                return [Finding("error", self._where(problem.path), problem.problem)]
            if selected is None:
                return [Finding("error", self._where(self.root),
                                f"no such term: {identifier}")]
            terms = [selected]
        else:
            terms = self.list_all(local_only=True)
            problems += self._unreadable_findings()
        for term in terms:
            def found(message: str) -> None:
                problems.append(Finding("error", self._where(term.slug), message))
            if (problem := _bad_name(term.slug)):
                found(problem)
            if term.origin == "local" and (problem := id_problem(
                    self._state(self.root / term.slug), term.slug)):
                problems.append(Finding("error", self._where(
                    self.root / term.slug / self.STATE_FILE), problem))
            if term.kind not in TAXONOMY_KINDS:
                found(f"unknown kind '{term.kind}'")
            def report(problem) -> None:
                if problem:
                    problems.append(Finding(problem[0], self._where(term.slug), problem[1]))
            for ref in term.relates_to:
                report(self._ref_problem(ref, "relatesTo")[1])
            if term.kind == "Feature":
                if not term.vocabulary:
                    found("Feature requires at least one vocabulary ref")
                for ref in term.vocabulary:
                    report(self._ref_problem(ref, "vocabulary", expect_vocabulary=True)[1])
        return problems

    def _validation_resources(self, identifier: str) -> list[Path]:
        """Filesystem resources bounded to one taxonomy object."""
        try:
            identifier = _safe_store_id(identifier, "taxonomy target")
        except UsageError:
            return []
        local_folder = self.root / identifier
        if local_folder.is_dir() and self._within_store(local_folder):
            owner, folder = self, local_folder
        else:
            term = self.get_view(identifier)
            if term is None:
                return []
            owner = (
                self if term.origin == "local"
                else self._inherited_stores()[term.origin]
            )
            folder = owner.root / term.slug
        # Asked of the *owning* store: an inherited term's files are bounded by
        # its own root, not this one.
        return [path for path in (folder / self.STATE_FILE, folder / "description.md")
                if path.is_file() and owner._within_store(path)]

    # -- revision-bearing detail + update --

    def get_term_detail(self, ref: "FullId | str") -> "TermDetail" | None:
        term = self._found(ref)
        if term is None:
            return None
        # Inherited terms' files live under the source store's root, not ours.
        owner = (
            self if term.origin == "local"
            else self._inherited_stores()[term.origin]
        )
        d = owner.root / term.slug
        meta_text, desc_text = owner._entry_texts(d)
        return TermDetail(term=term, core_revision=_revision_multi(meta_text, desc_text))

    def update_term(self, ref: "FullId | str", *,
                    name=_UNSET, description=_UNSET, relates_to=_UNSET,
                    vocabulary=_UNSET, kind=_UNSET,
                    core_revision: str | None = None) -> "TermDetail":
        # Resolve the term (must be local)
        term = self._found(ref)
        if term is None:
            raise NotFound(f"no such term: {ref}")
        if term.origin != "local":
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

        # Read current state
        meta, desc_text = self._state(d), ""
        if (d / "description.md").is_file() and self._within_store(d / "description.md"):
            desc_text = (d / "description.md").read_text(encoding="utf-8")

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

        # A Feature names at least one Vocabulary entry; when this edit makes
        # the entry a Feature and keeps its vocabulary, the kept values are
        # checked as stored.
        if meta.get("kind", "Vocabulary") == "Feature":
            vocs = meta.get("vocabulary", [])
            if not vocs:
                raise UsageError("Feature requires at least one vocabulary ref")
            if "vocabulary" not in provided:
                for r in vocs:
                    problem = self._ref_problem(r, "vocabulary", expect_vocabulary=True)[1]
                    if problem:
                        raise UsageError(problem[1])

        # Write atomically
        self._write_entry(d, meta, desc_text)

        # Return fresh detail
        return _require_detail(self.get_term_detail(ref), "term", ref)


# ── FsCapabilitiesStore ──────────────────────────────────────────────────────

# The capability fields that hold references (TCW-110 Design 5.1).
_REF_FIELDS = ("Subject", "Feature", "Superseded by", "Blocked by", "Roles", "When")
# `_stored_forms`' answer when the project has no taxonomy store to read.
_NO_TAXONOMY = object()

# Meta keys that are structural (not part of the locked CAP_FIELDS vocabulary).
_CAP_STRUCTURAL = {"id", "name", "overrides", "prependedDocs", "appendedDocs"}


def heading_slug(text: str) -> str:
    """GitHub-flavored heading anchor: lowercased, punctuation stripped, spaces→'-'.

    Still used by the serve viewer for anchors; no longer part of capability
    identity (capabilities are path-addressed folders).
    """
    s = re.sub(r"[^\w\s-]", "", text.strip().lower())
    return re.sub(r"\s+", "-", s)


def _mint_cap_id() -> str:
    """A fresh opaque, immutable capability id (`cap-` + 6 hex). Not path-derived."""
    return "cap-" + uuid.uuid4().hex[:6]


def _as_list(v) -> list[str]:
    """Normalize a scalar / list / comma-string meta value to a list of strings."""
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [s.strip() for s in str(v).split(",") if s.strip()]


class FsCapabilitiesStore(FsTreeStore, _FederationCycles, CapabilitiesStore):
    """`CapabilitiesStore` over folder-per-capability entries under
    `docs/capabilities/`, optionally federated via `extends`.

    A capability is a folder with `tcw-capability.yaml` (`id` + `name` + the locked
    metadata vocabulary) and `description.md` (the body). A directory is a
    capability iff it holds that state file; dirs without one are pure grouping
    parents. Mirrors `FsTaxonomyStore` on the shared tree-store core.
    """
    COMPONENT = "capabilities"
    LEGACY_CONFIG_NAME = ".config.yaml"
    STATE_FILE = STATE_FILES["capabilities"]

    def __init__(self, root: Path, *,
                 _walk: "_FederationWalk | None" = None,
                 project_root: Path | None = None, store_git_root: Path | None = None):
        super().__init__(root, project_root=project_root, store_git_root=store_git_root)
        self.extends: dict[str, "FsCapabilitiesStore"] = {}
        # Reused, never rebuilt: the resolution below already constructed each
        # store with the right project root and the right walk state. There is no
        # second filter on the results — the `_seen` set that used to be one was
        # dead once recursion moved into `_extended_component_stores`, since the
        # only case it could refuse is a self-extend the identity check there
        # already refuses by project id.
        self.extends, self.extends_cycles = _extended_component_stores(
            self.project_root, self.config, self._extends_label(), "capabilities",
            walk=self._walk_for(_walk), owner_id=self.project_id,
        )

    # -- resolution --

    def _is_capability(self, d: Path) -> bool:
        return (d / self.STATE_FILE).is_file()

    def _all_meta_dirs(self) -> list[str]:
        """Every folder holding a state file (capabilities + overrides), minus
        dot-dirs and those whose state file's version cannot be read."""
        out = []
        for p in sorted(self.root.rglob("*")):
            if not p.is_dir():
                continue
            rel = p.relative_to(self.root)
            if any(part.startswith(".") for part in rel.parts):
                continue
            if not self._entry_readable(p):
                continue                      # before the _is_capability stat
            if self._is_capability(p) and self._listable(p):
                out.append(str(rel))
        return out

    def _local_paths(self) -> list[str]:
        """Standalone local capabilities — state-file folders WITHOUT an `overrides`
        pointer (those are deltas, not caps; see `_override_index`)."""
        return [p for p in self._all_meta_dirs()
                if not self._state(self.root / p).get("overrides")]

    def _override_fields(self) -> list[tuple[str, dict]]:
        """`(path, fields)` for every local override: the fields it sets on the
        capability it overrides — its meta minus the structural keys and minus
        `null`, which clears an inherited field and so references nothing.

        The one definition of an override's references, read by `check` and by
        the taxonomy's refusal to remove a term something still names; an
        override's `Subject` becomes the composed capability's (`_apply_override`),
        so leaving it out of either lets a reference dangle unreported."""
        out = []
        for p in self._all_meta_dirs():
            meta = self._state(self.root / p)
            if meta.get("overrides"):
                out.append((p, self._set_fields(meta)))
        return out

    @staticmethod
    def _set_fields(meta: dict) -> dict:
        """The fields an override's meta sets (see `_override_fields`)."""
        return {k: v for k, v in meta.items()
                if k not in _CAP_STRUCTURAL and v is not None}

    def _override_index(self) -> dict[str, tuple[Path, dict]]:
        """`overrides` target string → (override folder, override meta)."""
        idx: dict[str, tuple[Path, dict]] = {}
        for p in self._all_meta_dirs():
            meta = self._state(self.root / p)
            target = meta.get("overrides")
            if target:
                idx[str(target)] = (self.root / p, meta)
        return idx

    def _compose_body(self, d: Path, meta: dict, raw_desc: str) -> str:
        """Effective body = prependedDocs + description + appendedDocs (bounded lists)."""
        parts = []
        # `_within_store` on each attachment: these are read by name from meta,
        # so they never pass through `_load_entry`'s filtered name list.
        for fn in _as_list(meta.get("prependedDocs")):
            f = d / fn
            if f.is_file() and self._within_store(f):
                parts.append(f.read_text(encoding="utf-8").strip())
        if raw_desc.strip():
            parts.append(raw_desc.strip())
        for fn in _as_list(meta.get("appendedDocs")):
            f = d / fn
            if f.is_file() and self._within_store(f):
                parts.append(f.read_text(encoding="utf-8").strip())
        return "\n\n".join(parts)

    def _capability(self, path: str, origin: str = "local") -> Capability:
        d = self.root / path
        meta, description, _attachments = self._load_entry(d)
        fields = {k: v for k, v in meta.items() if k not in _CAP_STRUCTURAL}
        if "Subject" in fields:
            fields["Subject"] = _as_list(fields["Subject"])
        return Capability(
            path=path,
            name=meta.get("name") or path.rsplit("/", 1)[-1].replace("-", " ").title(),
            id=str(meta.get("id") or ""),
            fields=fields,
            body=self._compose_body(d, meta, description),
            origin=origin,
            modified=_modified_timestamp(_capability_resources(d, meta)),
            owner=self.owner_of(origin),
        )

    def _apply_override(self, base: Capability, alias: str,
                        ov_index: dict[str, tuple[Path, dict]]) -> Capability:
        """Merge a local override (if any) onto an inherited capability `base`.

        Override matches by upstream id (bare `<id>` or `<alias>/<id>`). Fields
        partial-merge (YAML null clears); body = child.prepend + (child
        description.md if present else upstream raw description.md) + child.append.
        """
        ov = ov_index.get(base.id) or ov_index.get(f"{alias}/{base.id}")
        if ov is None:
            return base                                   # inherited verbatim
        d, meta = ov
        merged = dict(base.fields)
        for k, v in meta.items():
            if k in _CAP_STRUCTURAL:
                continue
            if v is None:
                merged.pop(k, None)                       # null clears inherited field
            else:
                merged[k] = _as_list(v) if k == "Subject" else v
        up_store = self.extends[alias]
        up_desc = up_store.root / base.path / "description.md"
        upstream_raw = (up_desc.read_text(encoding="utf-8")
                        if up_desc.exists() and up_store._within_store(up_desc) else "")
        child_desc = d / "description.md"
        child_raw = (child_desc.read_text(encoding="utf-8")
                     if child_desc.exists() and self._within_store(child_desc) else "")
        mid = child_raw if child_raw.strip() else upstream_raw
        return Capability(
            path=base.path,
            name=meta.get("name") or base.name,
            id=base.id,
            fields=merged,
            body=self._compose_body(d, meta, mid),
            origin=alias,
            owner=self.owner_of(alias),
            modified=max(
                filter(
                    None,
                    [
                        base.modified,
                        _modified_timestamp(_capability_resources(d, meta)),
                    ],
                ),
                default="",
            ),
        )

    def get_local(self, path: str) -> Capability | None:
        """This store's own project's capability at the id-path `path`, every
        folder spelled exactly as given, or None."""
        d = self.root / path
        # Reordered rather than extended: the old one-expression form called
        # `load_yaml` inside the condition, so a containment test appended to
        # the end would parse a state file outside the store before rejecting it.
        # The stat stays first so a miss pays no `resolve()`.
        if not (path and self._is_capability(d) and self._entry_readable(d)
                and exact_path(self.root, path) is True):
            return None
        return None if self._state(d).get("overrides") else self._capability(path)

    def get_by_id(self, cap_id: str) -> Capability | None:
        """Resolve an opaque id to its local capability (keyed lookup)."""
        for p in self._local_paths():
            c = self._capability(p)
            if c.id and c.id == cap_id:
                return c
        return None

    def list_all(self, status=None, namespace=None, local_only=False) -> list[Capability]:
        caps = [self._capability(p) for p in self._local_paths()]
        if not local_only:
            ov_index = self._override_index()
            for alias, st in self.extends.items():
                caps += [self._apply_override(st._capability(p, origin=alias), alias, ov_index)
                         for p in st._local_paths()]
        out = []
        for c in caps:
            if status and c.status != status:
                continue
            if namespace and c.path.split("/")[0] != namespace:
                continue
            out.append(c)
        return out


    def get_view(self, path: str) -> Capability | None:
        """An id-path read as the active project sees it (TCW-110 Design 3.1
        form d): the local capability first, else the one inherited at that
        path, its local override applied. `AmbiguousRef` when two extended
        projects both hold it."""
        identifier = path
        local = self.get_local(identifier)               # bare-wins-local
        if local is not None:
            return local
        matches = [(a, c) for a, st in self.extends.items()
                   if (c := st.get_local(identifier)) is not None]
        if len(matches) == 1:
            a = matches[0][0]
            return self._apply_override(self.extends[a]._capability(identifier, origin=a),
                                        a, self._override_index())
        if len(matches) > 1:
            raise AmbiguousRef(identifier, "capabilities")
        return None

    def get_inherited(self, alias: str, path: str) -> Capability | None:
        """The capability at id-path `path` in project `alias`, one this store
        extends, as this project sees it (its local override applied), or
        None."""
        st = self.extends.get(alias)
        if not (st and st.get_local(path)):
            return None
        return self._apply_override(st._capability(path, origin=alias),
                                    alias, self._override_index())

    def _inherited(self) -> dict[str, "FsCapabilitiesStore"]:
        """The projects whose capabilities this store reads as its own, by ID."""
        return self.extends

    def _found(self, target: "FullId | str") -> Capability | None:
        """The capability an operation naming one existing object acts on: a
        full identifier of this project's own capability or of one it
        extends, or text sorted as command input is (TCW-110 Design 3.1), an
        id-path read by `get_view`."""
        if isinstance(target, str):
            found = sort_input(target, "capabilities")
            if found.form == "d":
                return self.get_view(found.id_path)
            target = found.full_id
        if target.project == self.project_id:
            return self.get_local(target.id_path)
        return self.get_inherited(target.project, target.id_path)

    def _status_is_local(self, cap: Capability) -> bool:
        """True iff `cap`'s Status is a local decision, not an inherited default.
        A local capability always is; an inherited one only if a local override
        matches its upstream id (exactly as `_apply_override` keys) AND that
        override sets `Status` (an override editing only a body/field re-inherits
        the master's Status — `tcw/store/fs.py` `_apply_override`)."""
        if cap.origin == "local":
            return True
        ov = self._override_index()
        hit = ov.get(cap.id) or ov.get(f"{cap.origin}/{cap.id}")
        return hit is not None and "Status" in hit[1]

    def unreviewed_inherited(self) -> list[Capability]:
        return [c for c in self.list_all()
                if c.origin != "local" and not self._status_is_local(c)]

    def search(self, query: str) -> list[Capability]:
        q = query.lower()
        return [c for c in self.list_all()
                if q in c.name.lower() or q in c.body.lower()]

    # -- writes --

    def add(self, identifier, name=None, status="Missing", body="",
            fields=None) -> Capability:
        path = _safe_store_id(identifier, "path")
        _check_id_path(path, "path")
        if status not in CAP_STATUSES:
            raise UsageError(f"invalid Status '{status}' "
                             f"(choose: {', '.join(sorted(CAP_STATUSES))})")
        d = self.root / path
        if not self._within_store(d):
            raise NotFound(f"no such capability: {path}")
        if d.exists() or d.is_symlink():   # a dangling/looping link reads absent
            raise Refused(f"capability already exists: {path}")
        # After the cheap string and stat refusals, because this one may open a
        # taxonomy store — and before `_write_entry`, which is the point: a create
        # carrying a field the store would reject must leave nothing behind.
        norm = self._validate_fields(fields or {})
        display = name or path.rsplit("/", 1)[-1].replace("-", " ").title()
        meta = {"id": _mint_cap_id(), "name": display, "Status": status}
        # Field values win over the `status` parameter — what create-then-set
        # did. A None clears, rather than being skipped: there *is* something to
        # clear, the Status seeded a line above, and `_merge_meta` pops the key
        # on a local entry. Skipping it would keep a Status the caller asked to
        # remove, which create-then-set did not.
        for k, v in norm.items():
            if v is None:
                meta.pop(k, None)
            else:
                meta[k] = v
        self._write_entry(d, meta, body)
        return self._capability(path)

    def remove(self, identifier: "FullId | str") -> None:
        cap = self._found(identifier)
        # The exact listed spelling only. `get` resolves `routes/`, `./routes`,
        # or `Routes` on a case-insensitive disk, to the `routes` folder but
        # echoes the spelling back as the path, so everything below that works
        # from the path would be working from the wrong one.
        if cap is not None and cap.origin == "local" and cap.path not in self._local_paths():
            cap = None
        if cap is None:
            raise NotFound(f"no such capability: {identifier}")
        if cap.origin != "local":
            raise Refused(f"cannot remove inherited capability '{cap.full_id}' "
                             f"(edit it at its source; to drop a local override use "
                             f"`tcw capabilities reset`)")
        d = self.root / cap.path
        # Refused, never cascaded: `_rm` deletes the whole folder.
        nested = self._nested_entries(d)
        if nested:
            raise Refused(f"cannot remove '{cap.path}': nested under it: "
                             f"{', '.join(nested)} (remove those first)")
        referrers = self._referrers(d)
        if referrers:
            raise Refused(f"cannot remove '{cap.path}': still referenced by "
                             f"{', '.join(referrers)} (repoint or clear those fields first)")
        self._rm(d)

    def _nested_entries(self, d: Path) -> list[str]:
        """Every folder below `d` holding a state file, relative to the store.
        Asked of the folder itself rather than `_all_meta_dirs`, which skips
        dot-directories and unreadable entries that `git rm -rf` would delete
        all the same."""
        return sorted(str(m.parent.relative_to(self.root))
                      for m in d.rglob(self.STATE_FILE) if m.parent != d)

    def _referrers(self, target: Path) -> list[str]:
        """`<folder> (<field>)` for every other local capability or override whose
        reference fields resolve to the local capability folder `target`.

        Each field is read as `check` reads it (`_ref_problems`,
        `_check_globals`): a full identifier of this project's own capability
        (TCW-110 Design 5.1), compared by folder identity. A value in any
        other form names nothing here, and `check` reports it.
        """
        def tokens(field: str, raw) -> list[str]:
            if field in ("Superseded by", "Blocked by"):
                return [str(raw)]
            ns = "roles" if field == "Roles" else "conditions"
            toks = raw if isinstance(raw, list) else str(raw).split(",")
            refs = [str(s).strip().lstrip("!") for s in toks if str(s).strip()]
            return [r for r in refs
                    if (hit := self._local_ref(r)) is not None
                    and hit.path.startswith(f"{ns}/")]

        def same(a: Path) -> bool:
            return _same_folder(a, target)

        out = []
        for p in self._all_meta_dirs():
            folder = self.root / p
            if same(folder):
                continue
            meta = self._state(folder)
            for field in ("Superseded by", "Blocked by", "Roles", "When"):
                if field not in meta:
                    continue
                for ref in tokens(field, meta[field]):
                    hit = self._local_ref(ref)
                    if hit is not None and hit.origin == "local" and same(self.root / hit.path):
                        out.append(f"{p} ({field})")
                        break
        return out

    def reset(self, identifier: "FullId | str") -> None:
        cap = self._found(identifier)                  # federated; may raise AmbiguousRef
        if cap is None:
            raise NotFound(f"no such capability: {identifier}")
        # A standalone local capability is not an override — `remove` deletes it.
        if cap.origin == "local":
            raise Refused(f"'{identifier}' is a local capability, not an override "
                             f"(use `tcw capabilities rm` to delete it)")
        # Find the override by the same upstream-id keys `_write_target` writes,
        # so we drop whatever folder `set` materialized (bare or alias-qualified).
        ov_index = self._override_index()
        ov = ov_index.get(cap.id) or ov_index.get(f"{cap.origin}/{cap.id}")
        if ov is None:
            raise Refused(f"no local override at '{identifier}' to reset "
                             f"(it inherits '{cap.full_id}' verbatim)")
        # Refused, as `remove` refuses, when anything is nested under the
        # override: `_rm` would delete it with the folder. A nested folder may
        # itself be an override, which only `reset` drops.
        nested = self._nested_entries(ov[0])
        if nested:
            raise Refused(f"cannot reset '{identifier}': nested under its override: "
                          f"{', '.join(nested)} (delete a local capability with "
                          f"`tcw capabilities rm` and drop an override with "
                          f"`tcw capabilities reset` first)")
        self._rm(ov[0])                                # remove only the local override folder

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
            if value is None or key not in _REF_FIELDS:
                continue
            if key in ("Subject", "Feature") and taxonomy is None:
                taxonomy = self._taxonomy() or _NO_TAXONOMY
            single = key in ("Superseded by", "Blocked by", "Feature")
            tokens = [str(value).strip()] if single else [
                str(t).strip() for t in (value if isinstance(value, list)
                                         else str(value).split(",")) if str(t).strip()]
            stored = []
            for token in tokens:
                negated = key in ("Roles", "When") and token.startswith("!")
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

    def _write_meta(self, d: Path, meta: dict, *,
                    removed: tuple[Path, ...] = ()) -> None:
        """Write an entry's meta, rolling back what this call created.

        Owns the `mkdir` so it can prove whether the directory is its own:
        `set` materializing a *fresh* override is the path where a refused write
        would otherwise leave an empty folder behind, and an update of an
        existing capability is the path where removing the folder would take
        files this call never wrote.
        """
        owned = _mkdir_owned(d)
        self._write_files(
            [(d / self.STATE_FILE, state_text(d / self.STATE_FILE, meta))],
            owned_dir=d if owned else None, removed=removed)

    def _write_target(self, identifier: "FullId | str") -> tuple[Path, dict, bool]:
        """Resolve a write to `(folder, meta, is_override)`.

        A local capability writes to its own folder. An *inherited* one writes to
        a local override — the existing one for its upstream id if there is any
        (wherever the author put it), else a fresh delta mirroring the upstream
        path. Materializing the override here is what lets `set` accept every path
        `show` accepts; the placement is an FS detail (another store would record
        the same delta keyed by the upstream id its own way).
        """
        cap = self._found(identifier)                  # federated; may raise AmbiguousRef
        if cap is None:
            raise NotFound(f"no such capability: {identifier}")
        if cap.origin == "local":
            d = self.root / cap.path
            return d, self._state(d), False
        ov_index = self._override_index()
        ov = ov_index.get(cap.id) or ov_index.get(f"{cap.origin}/{cap.id}")
        if ov is not None:
            return ov[0], ov[1], True                  # update in place
        d = self.root / cap.path                       # mirror the upstream path
        if self._is_capability(d):
            # Taken — by a local capability, or by another alias's override of
            # the same path. Qualify by origin rather than refusing: `show`
            # accepts this ref, so `set` has to as well.
            d = self.root / cap.origin / cap.path
        if self._is_capability(d):
            raise Refused(
                f"cannot override '{cap.full_id}': both '{cap.path}' and "
                f"'{cap.origin}/{cap.path}' are already taken")
        # The mirror is the one write not downstream of a guarded lookup: a local
        # symlink shadowing the first segment of the upstream path would have it
        # create the folder and its state file outside the store.
        if not self._within_store(d):
            raise NotFound(f"no such capability: {identifier}")
        return d, {"overrides": f"{cap.origin}/{cap.id}"}, True

    def _merge_meta(self, meta: dict, norm: dict, is_override: bool) -> dict:
        """Merge validated fields into an entry's meta.

        On an override a None writes an explicit YAML null — `_apply_override`
        reads that as *clear the inherited field*, where popping the key would
        mean *re-inherit it*. On a local entry None pops, as it always has.
        """
        for k, v in norm.items():
            if v is None and not is_override:
                meta.pop(k, None)
            else:
                meta[k] = v
        return meta

    def set(self, identifier: "FullId | str", fields: dict) -> Capability:
        norm = self._validate_fields(fields)           # validate before touching disk
        d, meta, is_override = self._write_target(identifier)
        # `_write_meta` owns the mkdir and the rollback: `_write_target` can
        # materialize a fresh override directory, and a refused write must not
        # leave an empty one behind.
        self._write_meta(d, self._merge_meta(meta, norm, is_override))
        return self._found(identifier)                 # the composed (post-merge) entry

    # -- federation config --

    def extends_add(self, project_id: str) -> None:
        try:
            project_id = validate_project_id(project_id)
        except ValueError as e:
            raise UsageError(str(e)) from None             # a malformed name (Design 4)
        extends = _extends_ids(self.config, self._extends_label())
        if project_id in extends:
            raise Refused(f"extends project already exists: {project_id}")
        if project_id == self.project_id:
            raise Refused("a capabilities store cannot extend itself")
        registry = self.locator.registry.require_valid()
        try:
            # Design 3.6: an ancestor passing capabilities; exit 7 when what lies
            # above is not known, and nothing written.
            project = _extends_target(registry, "capabilities", self.project_root,
                                      self.project_id, project_id)
        except _NotInherited as refused:
            raise UsageError(str(refused)) from None
        if not (Path(project.locator) / "docs" / "capabilities").is_dir():
            raise UsageError(f"project '{project_id}' has no docs/capabilities/")
        extends.append(project_id)
        self._persist_extends(extends)

    def extends_remove(self, project_id: str) -> None:
        extends = _extends_ids(self.config, self._extends_label())
        if project_id not in extends:
            raise NotFound(f"no such extends project: {project_id}")
        extends.remove(project_id)
        self._persist_extends(extends)

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
                    self.project_root, _walk=_FederationWalk(active_root=self._active_root))
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
        top_level = {s.split("/")[0] for s in self._local_paths()}
        for project_id in self._federation_cycles():
            problems.append(self._store_finding(
                f"extends '{project_id}': cycle in capability federation"))
        for project_id in self.extends:
            if project_id in top_level:
                problems.append(self._store_finding(
                    f"project ID '{project_id}' collides with local top-level capability"))
        if identifier is None:
            problems += self._legacy_config_problems()     # see FsTaxonomyStore.check

        try:
            selected = self.get_view(identifier) if identifier is not None else None
        except StateFileProblem as problem:
            return [Finding("error", self._where(problem.path), problem.problem)]
        if identifier is not None and selected is None:
            return [Finding("error", self._where(self.root),
                            f"no such capability: {identifier}")]
        if selected is not None:
            seen_ids: dict[str, str] = {}
            for path in self._local_paths():
                if path == selected.path:
                    continue
                try:
                    candidate_id = str(self._state(self.root / path).get("id") or "")
                except (yaml.YAMLError, StateFileProblem):
                    continue
                if candidate_id:
                    seen_ids[candidate_id] = path
            caps = [selected]
        else:
            seen_ids = {}
            caps = self.list_all(local_only=True)
            problems += self._unreadable_findings()
        for cap in caps:
            where = self._where(cap.path)

            def found(message: str) -> None:
                problems.append(Finding("error", where, message))
            if (bad := _bad_name(cap.path)):
                found(bad)
            f = cap.fields
            if not cap.id:
                found("missing id")
            elif cap.id in seen_ids:
                found(f"duplicate id '{cap.id}' (also {seen_ids[cap.id]})")
            else:
                seen_ids[cap.id] = cap.path
            for key in f:
                if key in RETIRED_CAP_FIELDS:
                    found(f"field '{key}' was retired in TCW 3.0 — see "
                          f"{MIGRATION_GUIDE}")
                elif key not in CAP_FIELDS:
                    found(f"unknown field '{key}'")
            status = f.get("Status")
            if status is None:
                found("missing Status")
            elif status not in CAP_STATUSES:
                found(f"invalid Status '{status}'")
            if "Priority" in f and f["Priority"] not in CAP_PRIORITIES:
                found(f"invalid Priority '{f['Priority']}'")
            if "Lifecycle" in f and f["Lifecycle"] not in CAP_LIFECYCLES:
                found(f"invalid Lifecycle '{f['Lifecycle']}'")
            if status == "Partial" and "Gaps" not in f:
                found("Partial requires Gaps")
            if status == "Blocked" and "Blocked by" not in f:
                found("Blocked requires Blocked by")
            for level, problem in self._ref_problems(f, taxonomy):
                problems.append(Finding(level, where, problem))
            if unchecked and (f.get("Subject") or f.get("Feature")):
                found(unchecked)
                unchecked = ""

        # Override + attachment validation (every meta dir, incl. override folders).
        meta_dirs = self._all_meta_dirs()
        if selected is not None:
            meta_dirs = [selected.path]
        for p in meta_dirs:
            d = self.root / p
            # `is_dir` because an inherited capability's path is upstream's, and
            # a local folder of that name exists only when its override sits there.
            if not d.is_dir() or not self._entry_readable(d):
                continue          # `selected` bypasses the _all_meta_dirs filter
            meta = self._state(d)

            def found(message: str) -> None:
                problems.append(Finding("error", self._where(p), message))
            listed = _as_list(meta.get("prependedDocs")) + _as_list(meta.get("appendedDocs"))
            for fn in listed:
                if not (d / fn).is_file():
                    found(f"missing attachment '{fn}'")
            for f in d.iterdir():
                if (f.is_file() and f.suffix == ".md" and f.name != "description.md"
                        and f.name not in listed):
                    found(f"unlisted extra doc '{f.name}'")
            target = meta.get("overrides")
            if target and (e := self._override_problem(str(target))):
                found(e)
            if target and selected is None:
                # The references it sets, checked as a local capability's are:
                # they become the composed capability's own. A selected
                # capability's composed fields, override included, were checked
                # above; checking them here too reported each problem twice.
                fields = self._set_fields(meta)
                for level, problem in self._ref_problems(fields, taxonomy):
                    problems.append(Finding(level, self._where(p), problem))
                if unchecked and (fields.get("Subject") or fields.get("Feature")):
                    found(unchecked)
                    unchecked = ""
        return problems

    def _validation_resources(self, identifier: str) -> list[Path]:
        """Filesystem resources bounded to one capability object."""
        try:
            identifier = _safe_store_id(identifier, "capability target")
        except UsageError:
            return []
        local_folder = self.root / identifier
        if (local_folder / self.STATE_FILE).is_file() and self._entry_readable(local_folder):
            owner, folder = self, local_folder
        else:
            cap = self.get_view(identifier)
            if cap is None:
                return []
            owner = self if cap.origin == "local" else self.extends[cap.origin]
            folder = owner.root / cap.path
        try:
            meta = owner._state(folder)
        except (yaml.YAMLError, StateFileProblem):
            meta = {}
        names = [self.STATE_FILE, "description.md", *_as_list(meta.get("prependedDocs")),
                 *_as_list(meta.get("appendedDocs"))]
        # `validate()` parses and reads whatever comes back, so a listed
        # attachment that is a symlink out of the store would be read there —
        # the folder guard above cannot see it. Asked of the *owning* store,
        # because an inherited folder is bounded by its own root, not this one.
        return [folder / name for name in names
                if (folder / name).is_file() and owner._within_store(folder / name)]

    def _override_problem(self, target: str) -> str | None:
        """Validate an `overrides: <target>` pointer (dangling / ambiguous / local)."""
        if "/" in target:                                 # alias-qualified <alias>/<id>
            alias, _, cid = target.partition("/")
            st = self.extends.get(alias)
            if st is None:
                # On the store being checked, an alias missing here is always
                # one `<component>.extends` does not declare: a declared alias
                # that cannot be resolved fails the open, and a cycle's back
                # edge is recorded on the deepest store, never this one.
                return (f"overrides → unknown alias '{alias}' "
                        f"(not declared in {self._extends_label()})")
            return None if st.get_by_id(cid) else f"overrides → dangling id '{target}'"
        if self.get_by_id(target):
            return f"overrides → '{target}' targets a local capability (must be inherited)"
        hits = [a for a, st in self.extends.items() if st.get_by_id(target)]
        if not hits:
            return f"overrides → dangling id '{target}'"
        if len(hits) > 1:
            return f"overrides → ambiguous id '{target}' (in {', '.join(hits)})"
        return None

    def _ref_problems(self, f: dict, taxonomy) -> list[tuple[str, str]]:
        """Every cross-object ref problem in `f`, as `(level, message)` worded
        exactly as `check` reports it, minus the `<path>: ` location prefix.

        The single renderer: `check` prefixes these, the write path raises
        the errors. Two callers cannot disagree about what a problem *is*
        because there is only one place that says it.
        """
        out = []
        for key in ("Superseded by", "Blocked by"):
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
        for ns, field in (("roles", "Roles"), ("conditions", "When")):
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
        refs = [("Subject", str(s)) for s in _as_list(f.get("Subject"))]
        if f.get("Feature"):
            refs.append(("Feature", str(f["Feature"])))
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
        if target.kind != "Feature":
            return [("error", f"Feature → ref '{feature}' points to "
                              f"{target.kind}, expected Feature")]
        return []

    # -- revision-bearing detail + update --

    def get_capability_detail(self, identifier: "FullId | str") -> "CapabilityDetail" | None:
        cap = self._found(identifier)
        if cap is None:
            return None
        owner = self if cap.origin == "local" else self.extends[cap.origin]
        texts = self._entry_texts(owner.root / cap.path)
        if cap.origin != "local":
            # The local override's files are part of what the caller sees, so
            # they are part of the revision — else two edits to the same
            # override hash identically and a stale write sails through.
            ov_index = self._override_index()
            ov = ov_index.get(cap.id) or ov_index.get(f"{cap.origin}/{cap.id}")
            texts += self._entry_texts(ov[0]) if ov else ["", ""]
        return CapabilityDetail(capability=cap, core_revision=_revision_multi(*texts))

    def update_capability(self, identifier: "FullId | str", *, body=_UNSET, fields=_UNSET,
                          core_revision: str | None = None) -> "CapabilityDetail":
        norm = self._validate_fields(fields) \
            if fields is not _UNSET and fields is not None else {}

        if core_revision is not None:
            detail = self.get_capability_detail(identifier)
            if detail and detail.core_revision != core_revision:
                raise StaleRevision(f"stale revision for capability '{identifier}'")

        d, meta, is_override = self._write_target(identifier)
        desc = d / "description.md"
        desc_text = desc.read_text(encoding="utf-8") if desc.exists() else ""
        if body is not _UNSET:
            desc_text = body if body is not None else ""
        meta = self._merge_meta(meta, norm, is_override)

        # No mkdir and no outer guard here any more: `_write_meta` and
        # `_write_entry` each own their directory and roll back what they
        # created. Doing it here as well would double-delete — and, worse, the
        # old guard had to key on the state file being absent precisely because it
        # wrapped a callee that stages internally.
        if is_override and not desc_text.strip():
            # An override's description.md is a *body delta*, and an empty one
            # means "no delta" — `_apply_override` falls back to the upstream
            # body (which is what makes append-only overrides work). So clearing
            # an override's body drops the delta and re-inherits, rather than
            # leaving an empty file that silently means the same thing.
            had_body = desc.exists() or desc.is_symlink()
            desc.unlink(missing_ok=True)
            self._write_meta(d, meta, removed=(desc,) if had_body else ())
        elif body is _UNSET and not desc.exists():
            self._write_meta(d, meta)          # pure delta — no empty body file
        else:
            self._write_entry(d, meta, desc_text)
        return _require_detail(self.get_capability_detail(identifier),
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


# What a *project* is, for the provisioner: a directory carrying a sentinel. Not a
# component, and deliberately not spelled as one anywhere it could be mistaken
# for a store — `PROVISION_COMPONENTS` never contains it.
PROJECT_TARGET = "project"


def _is_store_layout(root: Path, component: str) -> bool:
    """Whether `root` holds `component`'s store, as far as the filesystem can say.

    The answer has two strengths, because the components differ in what they can
    honestly claim.

    A **work** store names nothing either (TCW-70 Design 3.5): it is present
    when its directory is, the same answer `WorkLocation.open` gives, so a
    provisioned store and an opened one agree.

    A **tree** store — taxonomy, capabilities — names nothing. `init` scaffolds
    it as a bare directory (see `init`'s plan loop), it holds no config file of its
    own at all now that `extends` lives in the project's `tcw-config.yaml`, and the
    only file reliably left behind is a `.gitkeep`, which is git's answer to
    empty directories and means nothing here. So "the directory is there" is the strongest honest answer, and it is
    shared by the work store: a declared tree store that clones
    into an empty directory reads as usable, because an empty taxonomy is a real
    state and nothing distinguishes the two. What this still refuses — a
    `repository.path` naming nothing at all — is what keeps "a failure leaves
    nothing behind" true for every component.

    `component` is required rather than defaulted: a caller that forgets it
    should not silently get a store's answer for a project.
    """
    if not root.is_dir():
        return False
    if component == PROJECT_TARGET:
        # A project names one file and it is the same file everywhere, which is
        # exactly how much a project can honestly claim.
        return (root / SENTINEL).is_file()
    return True


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
    if not configured.startswith(SCHEME):
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
    if locator is None:
        from tcw.locate import Locator
        locator = Locator.of(project_root)
    try:
        root = locator.owner_root(found.project, Path(project_root))
    except Unreachable as error:
        raise LocationProjectAbsent(error) from None
    if found.namespace is None:
        return root.joinpath(*found.parts)
    pair = (found.project, found.namespace)
    if pair in chain:
        followed = " -> ".join(f"{p} {n}" for p, n in (*chain, pair))
        raise StoreDeclarationError(
            f"{chain[0][1]}.path: store locations loop: {followed}")
    named = load_config(root / SENTINEL)
    section = named.get(found.namespace) if isinstance(named, dict) else None
    inner = section.get("path") if isinstance(section, dict) else None
    if inner is not None and not isinstance(inner, str):
        raise StoreDeclarationError(
            f"{root / SENTINEL}: {found.namespace}.path must be a non-empty path string")
    base = store_location(root, found.namespace, inner, locator=locator,
                          chain=(*chain, pair))
    return base.joinpath(*found.parts)


def resolve_store(store_cls, project_root: Path, _walk=None):
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
    config error with `tcw provision`.

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
    if isinstance(configured, str) and configured.startswith(SCHEME):
        # The command's one `Locator` (TCW-110 Design 6.1): the active
        # project's, which the walk carries for a store opened on its behalf.
        from tcw.locate import Locator
        active = _walk.active_root if _walk is not None and _walk.active_root \
            else project_root
        locator = Locator.of(active)
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
                _walk=_walk)
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
            _walk=_walk)
    except StoreLocationUnusable as unusable:
        # Only this. A store that is *there* and fails to open — a federation
        # error, a malformed `extends` — is a real error, and swallowing it here
        # reported "not provisioned; run `tcw provision`", which then succeeded
        # and left the store exactly as unopenable. `_extended_component_stores`
        # raises for many more reasons than it used to, so the hole widened.
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
                external=True, must_exist=True, _walk=_walk)
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
            _walk=_walk)
    except StoreLocationUnusable:
        pass                                                    # same rule
    raise StoreNotProvisioned(                                  # rule 3
        f"{config_path}: the {component} store is declared in "
        f"{declaration.url} but has not been provisioned here; "
        f"run `tcw provision` to obtain it"
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

    Its branches for `PROJECT_TARGET` are unused since `tcw provision` stopped
    fetching connected projects (TCW-107 Design 6.3); they are kept for
    `tcw project provision` (TCW-115), which fetches a project into its
    deciding manifest entry's folder and reuses this clone code.
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
        thing = "project" if self.component == PROJECT_TARGET else "store"
        within = f", {thing} at {d.path}" if d.path else ""
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
                             f"usable store; move it aside and run `tcw provision` "
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
        if self.component == PROJECT_TARGET:
            raise ValueError(
                f"projects: {self.declaration.url} has no TCW project at "
                f"'{where}': no {SENTINEL} there")
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
            self._run(["git", "clone", "--quiet", self.declaration.url, str(staging)])
            if self.declaration.ref:
                self._run(["git", "-C", str(staging), "checkout", "--quiet",
                           self.declaration.ref])
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
        would be the one thing `tcw provision` must never do.

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
