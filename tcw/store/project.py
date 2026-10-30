"""Filesystem implementation of the storage-neutral project registry."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterator

import yaml

from tcw.findings import Finding
from tcw.store.base import (
    LoadOrder, ParentLink, Project, ProjectOverride, ProjectRegistry,
    UnreachableProject, find_loop, load_order_of, loop_message, retired_key_problem,
)
from tcw.errors import ProjectGraphError, Unreachable, UnknownProject
from tcw.project_files import (LEGACY_PROJECT, LEGACY_SENTINEL, LOCAL_CONFIG_NAME,
                               LOCAL_MANIFEST,
                               LOCAL_MANIFEST_NAME, MANIFEST, PROJECT_ID_PATTERN,
                               SENTINEL, TCW_FOLDER,
                               personal_files_skipped, root_of,
                               validate_project_id, version_problem)
from tcw.store.manifest import ManifestEntry, parse_manifest
from tcw.store.checkouts import normalized_url
from tcw.store.links import parse_children, parse_parents
from tcw.store.yaml_source import UniqueKeyLoader as _UniqueKeyLoader, load as _load_named_yaml

def override_variable(project_id: str) -> str:
    """The environment variable that says where `project_id` lives on this machine.

    The id, uppercased, with `-` as `_`: `app-repo` →
    `TCW_PROJECT_APP_REPO`. **Project ids, not repository names** — the two are
    routinely different, and a workspace where they are crossed is what this
    mapping is most often got wrong against.

    Injective, and only because `PROJECT_ID_PATTERN` admits neither an
    underscore nor an uppercase letter: with either allowed, `a_b` or `A-b` would
    claim the same variable as `a-b`. `test_invalid_or_reserved_project_ids`
    holds that guarantee, so this function may not be given a laxer id.

    The variable supplies a fact about this machine that no shared
    configuration can carry, and is read as one step of an ordered fallback.
    """
    return "TCW_PROJECT_" + project_id.upper().replace("-", "_")


# The cache lives as long as the process: one command for the CLI, but a whole
# server run under `tcw serve`. A graph walk re-probes the same handful of
# directories, so an unbounded module-level dict is the right cache here —
# don't "fix" it into an LRU. The price is that a directory added or removed as
# a linked worktree while a server runs is seen only after a restart.
_ANCHOR_CACHE: dict[Path, tuple[Path, Path] | None] = {}
_REPOSITORY_CACHE: dict[Path, tuple[Path, tuple[str, ...],
                                  tuple[tuple[str, str], ...]] | None] = {}


#: The registry opened for each project root while a command runs; None
#: outside a command, so a library caller and a test always read afresh.
_OPEN: "dict[Path, FsProjectRegistry] | None" = None


def begin_command() -> None:
    global _OPEN
    _OPEN = {}


def end_command() -> None:
    global _OPEN
    _OPEN = None


def forget_registries() -> None:
    """Drop the registries this command has opened, after it wrote a
    `tcw-config.yaml` or a manifest, so the next `open` reads the files as
    they are now. It cannot refresh a registry a caller already holds in a
    variable: such a caller opens the registry again after writing."""
    if _OPEN is not None:
        _OPEN.clear()


def worktree_anchors(directory: Path) -> tuple[Path, Path] | None:
    """`(current worktree top, main worktree root)` when `directory` sits inside a
    *linked* git worktree, else None — None for git absent, not a repository, the
    primary checkout, a bare main repo, or any git failure. Never raises.

    Lives here rather than beside `git_root` in `fs.py`: `fs.py` imports this
    module, so the reverse import would be circular. It is a filesystem-adapter
    private detail — `ProjectRegistry` exposes no path-resolution operation.
    """
    key = directory.resolve()
    if key not in _ANCHOR_CACHE:
        _ANCHOR_CACHE[key] = _probe_worktree(key)
    return _ANCHOR_CACHE[key]


def personal_file(root: Path, name: str,
                  anchors: "tuple[Path, Path] | None | bool" = True) -> Path:
    """Where to read the personal file `name` (`tcw-config.local.yaml` or
    `tcw-manifest.local.yaml`) of the project at `root` (TCW-107 Design 4.2):
    its own `.tcw/<name>` when that is a file; otherwise, when `root` lies
    inside a linked git worktree, the same file below the main checkout when
    that one is a file; otherwise its own. A file is personal by its name: git
    is asked only where the worktree is, never whether the file is tracked.

    `anchors` is the worktree's `(top, main)` when the caller already holds
    them (None for none), or True to probe `root`."""
    own = Path(root) / TCW_FOLDER / name
    if own.is_file():
        return own
    if anchors is True:
        anchors = worktree_anchors(Path(root))
    if not anchors:
        return own
    top, main = anchors
    inside = _below(Path(root).resolve(), top)
    if inside is None:
        return own
    borrowed = main / inside / TCW_FOLDER / name
    return borrowed if borrowed.is_file() else own


def _is_file(path: Path) -> bool:
    """`path.is_file()`, answering False for a path that cannot be looked at.
    Python 3.11 raises PermissionError for a path inside a folder that cannot
    be searched, where 3.12 and later answer False; this answers as they do."""
    try:
        return path.is_file()
    except OSError:
        return False


def _below(path: Path, root: Path) -> Path | None:
    """The part of `path` below `root` when `path` is `root` or inside it, else
    None — deciding "inside" by folder identity, not by text.

    `Path.resolve()` keeps the spelling it was given, so on a disk that ignores
    letter case `.../APP/pkg` and git's `.../app/pkg` are one folder that text
    comparison calls two. The text answer is tried first; failing it, each of
    `path` and its parents is compared with `root` by device and inode, as
    `_canonical` compares the graph's keys. A folder that cannot be read is
    skipped, and a filesystem reporting no inode numbers keeps the text answer.
    """
    if path.is_relative_to(root):
        return path.relative_to(root)
    try:
        found = root.stat()
    except OSError:
        return None
    if not found.st_ino:
        return None
    for ancestor in (path, *path.parents):
        try:
            here = ancestor.stat()
        except OSError:
            continue
        if (here.st_dev, here.st_ino) == (found.st_dev, found.st_ino):
            return path.relative_to(ancestor)
    return None


def _config_file(path: Path) -> Path:
    """A `.tcw/tcw-config.yaml` path with its project root resolved and the file
    itself not followed. A symlinked config belongs to the project it sits in:
    that folder is the project, and its relative locators are read from there —
    resolving the file took them from wherever the link pointed."""
    return root_of(path).resolve() / SENTINEL


#: The variables that tell git which repository to act on, or where to look
#: for one (TCW-115 Design 7.8, "Git answers about the folder named"): every
#: name `git rev-parse --local-env-vars` prints at git 2.54 but the three
#: configuration variables, and the two that change where git searches. A git
#: hook runs with `GIT_DIR` and often `GIT_WORK_TREE` and `GIT_INDEX_FILE` set,
#: and with them `git -C <folder>` answers about the hook's repository.
GIT_LOCATION_VARIABLES = (
    "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_IMPLICIT_WORK_TREE", "GIT_GRAFT_FILE", "GIT_NO_REPLACE_OBJECTS",
    "GIT_REPLACE_REF_BASE", "GIT_PREFIX", "GIT_SHALLOW_FILE",
    "GIT_CEILING_DIRECTORIES", "GIT_DISCOVERY_ACROSS_FILESYSTEM")


def git_environment(base: "dict[str, str] | None" = None) -> dict[str, str]:
    """`base` (this process's environment by default) without
    `GIT_LOCATION_VARIABLES`, for every git call TCW makes: no TCW command
    means a git call to act on any repository but the folder it names. The
    configuration variables are kept, since a person's `git -c` settings
    are theirs."""
    env = dict(os.environ if base is None else base)
    for name in GIT_LOCATION_VARIABLES:
        env.pop(name, None)
    return env


def _git_lines(directory: Path, *args: str) -> list[str] | None:
    """`git -C directory <args>`'s output lines, or None on any failure."""
    try:
        return subprocess.run(
            ["git", "-C", str(directory), *args],
            capture_output=True, text=True, check=True, env=git_environment(),
            stdin=subprocess.DEVNULL,      # reads no input; see tcw/store/fs.py::_git
            # splitlines(), NOT split(): git emits one path per line, and a repo
            # path containing a space (`~/My Drive`, `~/Google Drive`) would split
            # into more than two tokens and silently disable worktree resolution.
        ).stdout.splitlines()
    except (subprocess.CalledProcessError, OSError):   # OSError covers git absent
        return None


def _probe_worktree(directory: Path) -> tuple[Path, Path] | None:
    out = _git_lines(directory, "rev-parse", "--path-format=absolute",
                     "--show-toplevel", "--git-common-dir")
    if not out or len(out) != 2:
        return None
    top, common = Path(out[0]).resolve(), Path(out[1]).resolve()
    if common.name == ".git":
        main = common.parent
    else:
        # A repository that is itself a submodule keeps its git dir at
        # `<outer>/.git/modules/<name>`, and records its checkout as
        # `core.worktree`, relative to that dir. A *bare* repo records none and
        # is not a worktree at all, so it gives no anchors.
        worktree = _git_lines(common, "--git-dir", str(common), "config", "--get",
                              "core.worktree")
        if not worktree:
            return None
        main = (common / worktree[0]).resolve()
    if main != top:
        return top, main
    # Not a linked worktree of its own repository. A submodule checked out in a
    # superproject's linked worktree is its own repository, checked out right
    # there; the worktree that matters is the superproject's.
    outer = _git_lines(directory, "rev-parse", "--show-superproject-working-tree")
    return worktree_anchors(Path(outer[0])) if outer else None


def _declares_a_project(config: Path) -> bool:
    """Whether the folder of the config path `config` declares a project of
    any version: its `.tcw/tcw-config.yaml`, or a 3.x root
    `tcw-config.yaml`. A path leaving a linked worktree that lands on a 3.x
    copy in a checkout of another repository is read as written, and a path
    into the main checkout whose counterpart in the worktree is a 3.x copy
    is read in the worktree (`_worktree_copy`), as for a 4.0 copy: the copy
    on the worktree's side is the one reported as 3.x, never the main
    checkout's on another branch (TCW-118, evaluation of candidate 6)."""
    return config.is_file() or (root_of(config) / LEGACY_SENTINEL).is_file()


def read_as_written(target: Path, anchors: tuple[Path, Path],
                    url: str | None = None) -> bool:
    """Whether a relative path that leads out of the linked worktree whose
    `(top, main)` are `anchors` is read where it lands, as written, rather
    than beside the main checkout: `target`, the folder it names, is there
    and inside a git checkout, main or linked, of a repository other than
    this worktree's own, and, when the path's declaration names a
    repository `url`, one of that checkout's remotes names it
    (`_names_repository`). This is what reads a copy made of linked
    worktrees, one inside another, in the copy, while a worktree made away
    from the folders its paths lead to (GitHub #26, #39) still reads them
    beside its main checkout."""
    found = _other_checkout(target, anchors)
    if found is None:
        return False
    return url is None or _names_repository(url, found)


def passed_over(target: Path, anchors: tuple[Path, Path], url: str | None) -> bool:
    """Whether `target`, where such a path lands, is a folder in a checkout
    of another repository that is read beside the main checkout only
    because none of that checkout's remotes names the repository `url` the
    path's declaration names: a checkout with no remote, or one whose
    remote is written in a form not recognised, which the person is told
    about (`passed_over_message`)."""
    if url is None:
        return False
    found = _other_checkout(target, anchors)
    return found is not None and not _names_repository(url, found)


def passed_over_message(key: str, landing: Path, instead: Path, url: str) -> str:
    """What `tcw migrate` and `tcw validate` say of a store path `key` that
    `passed_over` the folder `landing` and is read at `instead`."""
    return (f"{key} leads to {landing}, but no remote of the checkout there names "
            f"the repository the store declares, {url}, so the store is read beside "
            f"the main checkout, at {instead}; if the store at {landing} is the one "
            f"meant, add that repository's remote to its checkout, or correct the "
            f"remote's URL")


def _other_checkout(target: Path, anchors: tuple[Path, Path]):
    """`_repository_of(target)` when `target` is a folder in a checkout of a
    repository other than the worktree's own, else None."""
    if not target.is_dir():
        return None
    found, own = _repository_of(target), _repository_of(anchors[0])
    if found is None or own is None or found[0] == own[0]:
        return None
    return found


def _names_repository(url: str, found) -> bool:
    """Whether one of the remotes of the checkout `found` describes
    (`_repository_of`) names the repository `url`. Two URLs name one
    repository when their normalized forms are equal, before or after the
    `url.<base>.insteadOf` rules of the checkout's git config and of the
    user's own git config files rewrite either; or when one of them names
    its host by an SSH alias that the user's SSH configuration maps to a
    real host (`_alias_of`), and their last two path parts, the
    owner and the repository's name, are equal, ignoring case. A checkout
    with no remote names nothing."""
    rules = (*found[2], *_insteadof_rules_of_user())
    wanted = _forms(url.split("#", 1)[0], rules)
    return any(_same(a, b) for remote in found[1] for b in _forms(remote, rules)
               for a in wanted)


def _forms(url: str, rules) -> set[str]:
    """`url` normalized, as written and as git's longest matching insteadOf
    rule rewrites it."""
    prefixes = [(prefix, base) for prefix, base in rules if url.startswith(prefix)]
    forms = {normalized_url(url)}
    if prefixes:
        prefix, base = max(prefixes, key=lambda rule: len(rule[0]))
        forms.add(normalized_url(base + url[len(prefix):]))
    return forms


def _same(a: str, b: str) -> bool:
    """Two normalized URLs name one repository (`_names_repository`)."""
    if a == b:
        return True
    (host_a, _, path_a), (host_b, _, path_b) = a.partition("/"), b.partition("/")
    owner_a, owner_b = path_a.lower().split("/")[-2:], path_b.lower().split("/")[-2:]
    return (len(owner_a) == 2 and owner_a == owner_b and bool(host_a) and bool(host_b)
            and (_alias_of(host_a, host_b) or _alias_of(host_b, host_a)))


def _alias_of(alias: str, host: str) -> bool:
    """Whether `alias` reads as an SSH alias for `host` (`_names_repository`):
    a name with no dot, such as `github-work`, or `host` with a part added
    after a `-` or before a `.`, such as `github.com-work` or
    `work.github.com`, the forms used to keep one SSH key per account."""
    alias, host = alias.lower(), host.lower()
    part = r"[a-z0-9_-]+"
    return bool(re.fullmatch(r"[a-z0-9][a-z0-9_-]*", alias)
                or re.fullmatch(re.escape(host) + "-" + part, alias)
                or re.fullmatch(rf"{part}(\.{part})*\." + re.escape(host), alias))


def search_rounds(named_by: Path, anchors: tuple[Path, Path] | None
                  ) -> list[tuple[Path, Path, list[Path]]]:
    """The rounds of the search for a related project no manifest entry
    places, named by the project at `named_by`, whose active project's
    linked worktree is `anchors` (None outside one): each round's folder
    whose other folders are next to the project, the project's own folder
    there, and the folders enclosing it, tested in that order (Design 2.4,
    2.5). There is one round but in the case below.

    Inside the active project's linked worktree (Design 4.3), what lies
    outside the repository is read from the main checkout: when `named_by`
    is the worktree's top folder, the folders next to it are those next to
    the main checkout; the enclosing folders are the worktree's own up to
    its top, then those enclosing the main checkout, whose own root is not
    tested again.

    A worktree whose folder lies inside another repository's checkout
    (`read_as_written`) is searched from where it is. When that checkout is
    itself a linked worktree and the worktree's own main checkout lies
    inside that checkout's main checkout, the worktree is part of a copy
    made of linked worktrees, one inside another, and that is the only
    round: the main checkout's neighbours are the projects it was copied
    from, which the copy must not read or write. Otherwise a second round,
    from the main checkout as above, follows when the first finds nothing:
    a workspace repository's `.worktrees/` folder, in its main checkout or
    in one of its linked worktrees, or a home folder kept in git, holds a
    worktree whose sibling projects are beside the main checkout only."""
    as_written = (named_by.parent, named_by, list(named_by.parents))
    if anchors is None or _below(named_by, anchors[0]) is None:
        return [as_written]
    top, main = anchors
    holder, own = (main.parent, main) if named_by == top else (named_by.parent, named_by)
    enclosing = [p for p in named_by.parents if _below(p, top) is not None]
    enclosing += list(main.parents)
    from_main = (holder, own, enclosing)
    if not read_as_written(top.parent, anchors):
        return [from_main]
    holding = worktree_anchors(top.parent)
    if holding is not None and _below(main, holding[1]) is not None:
        return [as_written]
    return [as_written, from_main]


def _repository_of(folder: Path):
    """The git common dir of the checkout `folder` is in, its remotes' URLs,
    and the `url.<base>.insteadOf` rules of its config, as (prefix, base);
    None outside one. Cached as `worktree_anchors` is. Only `git rev-parse`
    runs, as for every read of where a project is: the remotes and rules are
    read from the common dir's `config` file, which every checkout of the
    repository shares."""
    key = folder.resolve()
    if key not in _REPOSITORY_CACHE:
        found = _git_lines(key, "rev-parse", "--path-format=absolute", "--git-common-dir")
        common = Path(found[0]).resolve() if found else None
        entries = [] if common is None else _config_entries(common / "config")
        _REPOSITORY_CACHE[key] = None if common is None else (
            common, tuple(_remote_urls(entries)), tuple(_insteadof_rules(entries)))
    return _REPOSITORY_CACHE[key]


def _insteadof_rules_of_user() -> list[tuple[str, str]]:
    """The `url.<base>.insteadOf` rules of the user's own git config files,
    `$XDG_CONFIG_HOME/git/config` (`~/.config/git/config` when it is not set)
    and `~/.gitconfig`, read as the files are, with no `git config` call."""
    xdg = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    files = (Path(xdg) / "git" / "config", Path.home() / ".gitconfig")
    return [rule for file in files for rule in _insteadof_rules(_config_entries(file))]


def _config_entries(config: Path) -> list[tuple[str, str, str, str]]:
    """Each `key = value` of a git config file, as (section, subsection,
    key, value), the section and key lowercased; [] when it cannot be read.
    A value's quotes and a comment after it are dropped; an include is not
    followed."""
    try:
        text = config.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    header = re.compile(r'\[\s*([^\s\]"]+)\s*(?:"((?:[^"\\]|\\.)*)")?\s*\]')
    entries, section, subsection = [], "", ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            match = header.match(stripped)
            section, subsection = ((match.group(1).lower(), match.group(2) or "")
                                   if match else ("", ""))
        elif "=" in stripped and not stripped.startswith(("#", ";")):
            key, _, value = stripped.partition("=")
            value = value.strip()
            if value.startswith('"'):
                value = value[1:].partition('"')[0]
            else:
                value = re.split(r"\s[#;]", value, maxsplit=1)[0].strip()
            entries.append((section, subsection, key.strip().lower(), value))
    return entries


def _remote_urls(entries) -> list[str]:
    """Each `url` of a `[remote "<name>"]` section."""
    return [value for section, _, key, value in entries
            if section == "remote" and key == "url"]


def _insteadof_rules(entries) -> list[tuple[str, str]]:
    """Each `insteadOf` of a `[url "<base>"]` section, as (prefix, base)."""
    return [(value, base) for section, base, key, value in entries
            if section == "url" and key == "insteadof" and value]


# ---------------------------------------------------------------------------
# Finding a project's folder from its ID (TCW-107 Design 2)


def _read_text(path: Path) -> str:
    """A file's text. Every file the registry reads is read here, so a test
    can count the reads (TCW-107 AC 24, AC 27)."""
    return Path(path).read_text(encoding="utf-8")


def _list_folder(path: Path) -> list[tuple[str, bool]]:
    """Each entry in a folder, by name, and whether it is a folder. Every
    folder the registry lists is listed here, for the same reason. Raises the
    `OSError` listing it raised."""
    result = []
    with os.scandir(path) as entries:
        for entry in entries:
            try:
                is_dir = entry.is_dir()
            except OSError:
                is_dir = False
            result.append((entry.name, is_dir))
    return sorted(result)


#: The folders macOS asks a person's permission to read, directly in the home
#: folder. The search never tests one next to a project (see `_protected`).
_PROTECTED_NAMES = ("Desktop", "Documents", "Downloads")
_ON_MACOS = sys.platform == "darwin"


def _holds_only_git(path: str) -> str:
    """The words for an entry folder holding nothing but `.git`: what a
    clone or a submodule update leaves when it stopped before checking out a
    file. The fetching command refuses such a folder (TCW-115), so the person
    is told to deal with it first."""
    return f"{path} holds only .git; finish or remove it with git"


@dataclass(frozen=True)
class _Probe:
    """What a folder's two files say (Design 2.6): `none` (neither file),
    `project` (a 4.0 project declaring `id`), `version` (a 4.0 file whose
    version this TCW cannot read; `id` when it declares one), `legacy` (a 3.x
    root file; `id` when it declares one) or `unreadable`."""

    kind: str
    id: str | None = None
    detail: str = ""


@dataclass(frozen=True)
class _Answer:
    """One answer to "where is `X`, asked by `P`" (Design 2.11 b).

    `folder` is the project's root when found, and `by` the rule that found
    it: `manifest` (with the deciding `entry`), `variable` or `search`.
    Otherwise `problem` is the graph problem, rendered as recorded, or the
    project is not here: `named` says whether anything the walk consulted
    names the ID, and `message` is Design 6.2's text."""

    folder: Path | None = None
    by: str | None = None
    entry: ManifestEntry | None = None
    entry_folder: Path | None = None
    problem: str | None = None
    named: bool = False
    message: str = ""
    remedy: str = ""
    # A folder that holds the project's shared file but cannot be read
    # (TCW-109 Design 1.6), and the problem not yet recorded: in an ancestor,
    # or a project read only for a lookup, it is a gap rather than a graph
    # problem, so the problem is recorded only where it stays one.
    unreadable: Path | None = None
    deferred: tuple | None = None
    # The root of the project whose `.tcw/` holds the deciding entry's
    # manifest; for a personal file a linked worktree borrows, the worktree
    # (TCW-115 Design 8.1).
    owner: Path | None = None
    # The entry's folder, when it holds files and no project (Design 2.3,
    # row b): a graph problem, except to the command that would fetch the
    # project there, which refuses that project alone (TCW-115 Design 7.6).
    occupied: Path | None = None


class GraphProblems(ValueError):
    """`require_valid`'s refusal: the problems as one message, and `files`,
    the file each is about in the same order, so a caller can say whose
    files they are without reading the message (TCW-115 Design 7.11)."""

    def __init__(self, message: str, files: list[Path]):
        super().__init__(message)
        self.files = files


@dataclass(frozen=True)
class Placement:
    """Where the lookup placed project `id`, and why (TCW-115 Design 8.1): the
    answer to "where is `id`, asked by `asked_by`" with its deciding manifest
    entry made readable. `folder` is the project's root when it is here;
    `entry` the deciding entry (None when the search or `TCW_PROJECT_<ID>`
    decided, or nothing did), `owner` the root of the project whose `.tcw/`
    holds that entry's manifest, `entry_folder` the entry's `path` resolved
    and `repository_folder` that with `subfolder` removed (TCW-107 Design
    1.6). `repository_path` is the same folder before any link is followed:
    the entry's path as written, joined to the folder it is read from.

    Deployment layer: a store that is not a folder of files has no manifest."""

    id: str
    asked_by: Path
    folder: Path | None = None
    entry: ManifestEntry | None = None
    owner: Path | None = None
    entry_folder: Path | None = None
    repository_folder: Path | None = None
    repository_path: Path | None = None


def _without_subfolder(path: Path, subfolder: str | None) -> Path:
    """`path` with the last folders `subfolder` names removed."""
    if subfolder is None:
        return path
    return path.parents[len(Path(subfolder).parts) - 1]


def _not_here_message(project_id: str, remedy: str) -> str:
    """TCW-107 Design 6.2's sentence: its lead, then `remedy`."""
    return f"project '{project_id}' is not on this machine: {remedy}"


def _search(registry: "FsProjectRegistry", project_id: str,
            named_by: Path) -> tuple[list[Path], list[tuple[Path, str]]]:
    """Design 2.4-2.8: the folders next to `named_by` and enclosing it that
    declare `project_id`, and the problems of candidates that are
    `project_id` but cannot be read as 4.0. Every match is collected; the
    registry decides. Never reads below a folder it tests (Design 2.6). The
    folders are tested in the rounds `_search_candidates` gives, and a round
    is tried only when the ones before it found neither a match nor a
    problem.

    A module-level function, so a test run can replace it with one that finds
    nothing, and so show that each test's projects are placed by its
    manifests rather than found by accident."""
    matches: list[Path] = []
    problems: list[tuple[Path, str]] = []
    tested: set[Path] = set()
    for candidates in registry._search_candidates(named_by):
        if matches or problems:
            break
        for folder in candidates:
            if folder in tested:
                continue
            tested.add(folder)
            probe = registry._probe(folder)
            if probe.id != project_id:
                continue
            if probe.kind == "project":
                matches.append(folder)
            elif probe.kind == "version":
                problems.append((folder / SENTINEL, probe.detail))
            elif probe.kind == "legacy":
                problems.append((folder, f"is {LEGACY_PROJECT}"))
    return matches, problems


@dataclass(frozen=True)
class _Config:
    """One project's configuration as the walk read it (TCW-108 Design 1, 2).

    `links` is its `parents:`, in order, or None when they could not be read,
    `link_problem` then saying why (Design 6.6). `children` is its committed
    `children:`, the entries that are valid IDs; for an ancestor or a project
    read only for a lookup, it is read only as a list of names (Design 2.5)."""

    project: Project
    path: Path
    links: list[ParentLink] | None
    link_problem: str | None
    children: list[str]
    raw: dict[str, Any]


def _same_repository(marker: Path, main: Path) -> bool:
    """Whether a directory holding `marker` (its `.git`) is still the repository
    whose main worktree is `main`: no marker, or a submodule of it — a `.git`
    file whose `gitdir:` lies inside `main/.git`, which is the commit this
    branch pins. A `.git` directory, or a file pointing anywhere else, is a
    separate repository nested here."""
    if not marker.exists():
        return True
    if not marker.is_file():
        return False
    try:
        first = marker.read_text(encoding="utf-8").splitlines()[0]
    except (OSError, UnicodeDecodeError, IndexError):
        return False
    if not first.startswith("gitdir:"):
        return False
    gitdir = (marker.parent / first[len("gitdir:"):].strip()).resolve()
    return gitdir.is_relative_to((main / ".git").resolve())


class FsProjectRegistry(ProjectRegistry):
    """The family of the project at `project_root`, found by following its
    parent links up and its listed children down (TCW-108 Design 3)."""

    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()
        # The family (Design 3.3): the active project, its ancestors and its
        # descendants, by configuration path and by ID, in the order read.
        self._cache: dict[Path, _Config] = {}
        self._by_id: dict[str, _Config] = {}
        # Projects read only to answer a lookup or a load order (Design 3.4,
        # 4.6), never part of the family: `get`, `ancestors`, `descendants`
        # and `projects` do not read these.
        self._outside: dict[Path, _Config] = {}
        self._outside_by_id: dict[str, _Config] = {}
        # Every project read, family or not, by ID in the order read (the
        # order Design 4.7 names a loop's first member by); the role each
        # configuration was read in; the configurations whose parents have
        # been walked up; and, for each one, the configuration whose link
        # first reached it.
        self._read_order: list[str] = []
        self._roles: dict[Path, str] = {}
        self._walked: set[Path] = set()
        # The active project's children listed only in its personal file
        # (Design 2.1).
        self._personal_children: set[str] = set()
        self._reached_from: dict[Path, Path] = {}
        # The same problems twice, in step: rendered for the refusals that
        # raise them, and as findings for `check()` (TCW-73 Design 6.3).
        self._problems: list[str] = []
        # The file each rendered problem is about, for `GraphProblems.files`.
        self._problem_files: dict[str, Path] = {}
        # The problems that are an entry's folder holding files and no
        # project (`_Answer.occupied`), as recorded.
        self._occupied_problems: set[str] = set()
        self._findings: list[Finding] = []
        self._unreachable: list[UnreachableProject] = []
        self._warnings: list[str] = []
        self._warning_findings: list[Finding] = []
        # Rule 0's answer per project id, memoised, so the disk is probed once
        # and `_overrides` holds one record per variable.
        self._override_cache: dict[str, Path | None] = {}
        self._overrides: list[ProjectOverride] = []
        # Ids whose override was present and wrong. They are not "not obtained
        # yet", so they must not also be reported as unreachable — that would
        # answer a refusal with `run tcw project provision`, which is advice that
        # contradicts it.
        self._override_refused: set[str] = set()
        self._loaded = False
        # The first spelling met of each project folder, by the folder's identity: on
        # a case-insensitive disk `Root` and `ROOT` are one folder, and keying the
        # graph by path text loaded it twice.
        self._spellings: dict[tuple[int, int], Path] = {}
        self._current_path = self.project_root / SENTINEL
        # Probed once per registry, not once per locator (~8 ms a call).
        self._anchors = worktree_anchors(self.project_root)
        # The lookup's reads, each made at most once (TCW-107 Design 2.13): a
        # file's text or the error reading it, a folder's listing or the error
        # listing it, what a folder's two files say, and each project root's
        # manifests (None when one has a problem, which makes it unusable).
        self._texts: dict[Path, str | Exception] = {}
        self._listings: dict[Path, list[tuple[str, bool]] | OSError] = {}
        self._probes: dict[Path, _Probe] = {}
        self._manifests: dict[Path, list[tuple[Any, Path, dict]] | None] = {}
        self._manifest_problem: dict[Path, str] = {}
        # One answer per question, "where is `X`, asked by `P`", keyed by the
        # ID and `P`'s root (Design 2.11 b), and the answer that placed each
        # configuration in the graph, for `found`.
        self._answers: dict[tuple[str, Path], _Answer] = {}
        self._placed: dict[Path, _Answer] = {}
        # The folders `project_folder` returned, by ID.
        self._found: dict[str, Path] = {}

    @classmethod
    def open(cls, project_root: Path) -> "FsProjectRegistry":
        """The registry of the project at `project_root`, its graph loaded.
        While a command runs, the same registry for the same root, so the
        graph, every lookup's answer and every folder the search reads are
        read once (TCW-107 Design 2.13); outside a command, a new one."""
        if _OPEN is None:
            registry = cls(project_root)
            registry._load_graph()
            return registry
        key = Path(project_root).resolve()
        if key not in _OPEN:
            registry = cls(project_root)
            registry._load_graph()
            # Kept only once the load has finished, so a load that raised is
            # never handed out half-built.
            _OPEN[key] = registry
        return _OPEN[key]

    @property
    def current(self) -> Project:
        cfg = self._cache.get(self._canonical(self._current_path))
        if cfg is None:
            raise ValueError(self._problems[0] if self._problems else "invalid project registry")
        return cfg.project

    def get(self, project_id: str) -> Project | None:
        cfg = self._by_id.get(project_id)
        return cfg.project if cfg else None

    def parents(self, project_id: str | None = None) -> list[ParentLink]:
        """The project's declared parent links, in order; empty for one whose
        links could not be read and for one not on this machine. Answers for
        any project this registry has read, a descendant's other parents
        included (Design 4.6)."""
        cfg = self._any_config(project_id)
        return list(cfg.links or []) if cfg else []

    def link_state(self, project_id: str) -> str:
        cfg = self._any_config(project_id)
        if cfg is None:
            return "missing"
        return "unreadable" if cfg.link_problem is not None else "here"

    def children(self, project_id: str | None = None) -> list[Project]:
        return [self._by_id[child_id].project
                for child_id in self.declared_child_ids(project_id)
                if child_id in self._by_id]

    def declared_child_ids(self, project_id: str | None = None) -> list[str]:
        cfg = self._any_config(project_id)
        return list(cfg.children) if cfg else []

    def personal_child_ids(self) -> set[str]:
        """The active project's children listed only in its personal file
        (Design 2.1), for the listing's `personal` flag."""
        self._load_graph()
        return set(self._personal_children)

    def load_order(self, project_id: str | None = None, *,
                   root: Path | None = None) -> LoadOrder:
        """Design 4, for the active project, any project of the family, or
        any other project the lookup can locate (Design 4.6). A project not
        in the family is found at `root` when the caller holds its store,
        else at the folder this command returned for it, else by the lookup
        from the active project; its ancestors are read for this question
        only and never join the family. A loop met here, after the walk, is
        a `ProjectGraphError`, also added to `check()`."""
        self._load_graph()
        if project_id is not None:
            self._walk_for(project_id, root)
        try:
            return super().load_order(project_id)
        except ProjectGraphError as error:
            cfg = self._any_config(project_id)
            path = cfg.path if cfg else self._current_path
            self._problem(path, str(error))
            raise ProjectGraphError(f"{path}: {error}") from None

    def ancestors(self, project_id: str | None = None) -> list[Project]:
        """The load order without the project, the projects on this machine,
        farthest first."""
        ids = self.load_order(project_id).ids[:-1]
        return [cfg.project for cfg in (self._any_config(pid) for pid in ids)
                if cfg is not None]

    def order_project(self, project_id: str) -> Project:
        cfg = self._any_config(project_id)
        if cfg is None:
            raise KeyError(project_id)
        return cfg.project

    def absent_note(self, project_id: str) -> str:
        """TCW-107 Design 6.2's sentence for the project, after its colon:
        where the deciding entry places it, and how to fetch it when the entry
        gives a repository, or that no entry places it."""
        self._load_graph()
        record = next((u for u in self._unreachable if u.id == project_id), None)
        if record is not None and record.remedy:
            return record.remedy
        return f"no manifest lists it; add it to {MANIFEST} or {LOCAL_MANIFEST}"

    def link_problem(self, project_id: str) -> str | None:
        cfg = self._any_config(project_id)
        return cfg.link_problem if cfg is not None else None

    def descendants(self, project_id: str | None = None) -> list[Project]:
        """The family's projects below this one, breadth first through each
        project's listed children (Design 3.1)."""
        cfg = self._config_for(project_id)
        if cfg is None:
            return []
        result: list[Project] = []
        seen = {cfg.project.id}
        queue = [cfg]
        while queue:
            for child_id in queue.pop(0).children:
                child = self._by_id.get(child_id)
                if child is None or child_id in seen:
                    continue
                seen.add(child_id)
                result.append(child.project)
                queue.append(child)
        return result

    def projects(self) -> list[Project]:
        """The family, in the order the walk read it; never a sibling."""
        self._load_graph()
        return [cfg.project for cfg in self._by_id.values()]

    def checkout_of(self, url: str) -> Path | None:
        """Where a project this graph holds is a checkout of `url`, or None.

        **Filesystem-adapter private, deliberately not on `ProjectRegistry`.**
        The question itself is storage-neutral — a tracker-backed registry could
        answer "which of your projects comes from this source" perfectly well —
        but answering it here means comparing a manifest entry's repository and
        returning a `Project.locator`, and both are things nothing above the
        adapter may read. The one caller is `resolve_store` in
        `fs.py`, which is the same adapter reading its own values.

        Asks the *found* project rather than the entry that names its
        repository. That is the entire point: an entry says where a project
        comes from, and only the lookup knows where it is here,
        `TCW_PROJECT_<ID>` included.

        A project's repository is written in the manifest entries that place
        it (TCW-107 Design 6.4), read in a fixed order so the answer does not
        depend on which lookups the command made first: `_manifest_order`'s.
        For the first entry whose repository is `url` and whose project this
        command has found, the repository's folder is the found folder with the
        entry's `subfolder` removed. An entry whose project is not found, or
        whose found folder does not end with its `subfolder`, gives no answer:
        it names a repository but no location here, and sending the store
        ladder to a path that is not there is worse than sending it nowhere.
        """
        self._load_graph()
        wanted = normalized_url(url)
        if not wanted:
            return None
        for root in self._manifest_order():
            for _file, _base, entries in self._manifests_of(root) or []:
                for entry in entries.values():
                    if entry.url is None or normalized_url(entry.url) != wanted:
                        continue
                    folder = self._known_folder(entry.id)
                    if folder is None:
                        continue
                    folder = Path(folder).resolve()
                    if entry.subfolder is None:
                        return folder
                    tail = Path(entry.subfolder).parts
                    if folder.parts[-len(tail):] == tail:
                        return folder.parents[len(tail) - 1]
        return None

    def _manifest_order(self) -> list[Path]:
        """The roots whose manifests `checkout_of` reads, in the order the
        lookup reads them from the active project (Design 3.4): its own, its
        ancestors' in the reverse of its load order, then its descendants'
        nearest first."""
        order, _ = self._family(self.project_root, "")
        return order

    def check(self) -> list[Finding]:
        return list(self._findings)

    def warnings(self) -> list[str]:
        return list(self._warnings)

    def warning_findings(self) -> list[Finding]:
        """The same warnings as findings, the file each concerns as `where`."""
        return list(self._warning_findings)

    def overrides(self) -> list[ProjectOverride]:
        """The `TCW_PROJECT_*` locators that took effect in this graph.

        Discovered by walking, so the graph is loaded first: an override is in
        force only where some config actually declares that project, and one
        naming a project nothing connects to is never consulted. Listing it
        would claim the graph depends on something it does not.

        Includes an override that resolved to the *wrong* project. The id mismatch
        is reported separately, and a reader who sees only that message is
        looking at a path written in no config they can find.
        """
        self._load_graph()
        return list(self._overrides)

    def unreachable(self) -> list[UnreachableProject]:
        """Declared projects this checkout does not have.

        Filtered by what the graph ended up holding, not by what each locator
        did. Every connection is declared twice — once by each side — and in a
        multi-repository workspace the two sides are written against different
        machines, so a locator failing to resolve is routine and says nothing on
        its own. Only the project being absent from the graph does.

        Filtered here rather than at the point of record so the walk order cannot
        matter: an edge may be recorded before the route that resolves the same
        project is followed.
        """
        return [entry for entry in self._unreachable if entry.id not in self._by_id]

    def require_valid(self, *, fetching: bool = False) -> "FsProjectRegistry":
        """Raise `GraphProblems` naming every graph problem. `fetching` leaves
        out an entry's folder that holds files and no project: `tcw project
        provision` refuses that one project as occupied and goes on with the
        others (TCW-115 Design 7.6)."""
        problems = [p for p in self._problems
                    if not (fetching and p in self._occupied_problems)]
        if problems:
            raise GraphProblems("; ".join(problems),
                                [self._problem_files[p] for p in problems
                                 if p in self._problem_files])
        return self

    def occupied_ids(self) -> list[str]:
        """The IDs whose deciding entry places them at a folder that holds
        files and no project, in the order they were looked up."""
        found: list[str] = []
        for (project_id, _), answer in list(self._answers.items()):
            if answer.occupied is not None and project_id not in found:
                found.append(project_id)
        return found

    def config(self, project_id: str | None = None) -> dict[str, Any]:
        cfg = self._config_for(project_id)
        return dict(cfg.raw) if cfg else {}

    def _config_for(self, project_id: str | None) -> _Config | None:
        if project_id is None:
            return self._cache.get(self._canonical(self._current_path))
        return self._by_id.get(project_id)

    def _any_config(self, project_id: str | None) -> _Config | None:
        """A configuration this registry has read, in the family or not."""
        self._load_graph()
        if project_id is None:
            return self._config_for(None)
        return self._by_id.get(project_id) or self._outside_by_id.get(project_id)

    def _load_graph(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        cfg = self._visit(self._current_path, None, None, "active")
        if cfg is None:
            return
        # Read whether or not anything is looked up, so their problems are
        # reported (Design 1.8); a missing file costs one failed read.
        self._manifests_of(self.project_root)
        self._walk_up(cfg, "ancestor")
        self._walk_down(cfg)
        self._validate_name_back()
        self._validate_loops()
        self._recheck_search_answers()
        self._reconcile_overrides()

    def _walk_up(self, cfg: _Config, role: str) -> None:
        """Design 3.1, up: each parent in listing order, and that parent's
        own parents before the next one. Nothing above a project whose links
        could not be read is looked up (Design 6.6)."""
        if cfg.path in self._walked:
            return
        self._walked.add(cfg.path)
        for link in cfg.links or []:
            parent = self._follow(cfg, link.id, role)
            if parent is not None:
                self._walk_up(parent, role)

    def _walk_down(self, start: _Config) -> None:
        """Design 3.1, down: the active project's listed children, then
        theirs, breadth first. An ancestor's children are never followed, so
        a sibling is never reached, nor a descendant's other parents."""
        queue, seen = [start], {start.path}
        while queue:
            cfg = queue.pop(0)
            for child_id in cfg.children:
                child = self._follow(cfg, child_id, "descendant")
                if child is not None and self._roles.get(child.path) == "descendant" \
                        and child.path not in seen:
                    seen.add(child.path)
                    queue.append(child)

    def _walk_for(self, project_id: str, root: Path | None) -> None:
        """Read `project_id` and its ancestors for a question about it
        (Design 4.6): a descendant's other parents, or a project outside the
        family and the projects above it, none of them joining the family."""
        cfg = self._by_id.get(project_id) or self._outside_by_id.get(project_id)
        if cfg is None:
            folder = root
            if folder is None:
                folder = self._found.get(project_id)
            if folder is None:
                folder = self.project_folder(project_id, self.project_root)
            cfg = self._config_at(Path(folder))
            if cfg is None or cfg.project.id != project_id:
                raise UnknownProject(f"no project with ID '{project_id}' is known or "
                                     f"found near this one; check the spelling")
        role = "ancestor" if self._roles.get(cfg.path) in ("active", "ancestor") \
            else "outside"
        self._walk_up(cfg, role)

    def _follow(self, cfg: _Config, target_id: str, role: str) -> _Config | None:
        """One link of `cfg`'s, resolved by the lookup and read in `role`; a
        project not on this machine is recorded as not here, and a problem is
        already recorded. A project linking to itself is itself (a loop)."""
        if target_id == cfg.project.id:
            return cfg
        answer = self._locate(target_id, root_of(cfg.path))
        if answer.unreadable is not None and role in ("ancestor", "outside"):
            return self._visit(self._canonical(answer.unreadable / SENTINEL), target_id,
                               cfg.path, role)
        if answer.problem is not None:
            self._settle(answer)
            return None
        if answer.folder is None:
            self._unreachable_edge(
                cfg.path, target_id, answer.entry_folder, message=answer.message,
                remedy=answer.remedy,
                decided_by=answer.entry.file if answer.entry else None,
                repository=answer.entry.repository if answer.entry else None)
            return None
        target = self._canonical(answer.folder / SENTINEL)
        self._placed.setdefault(target, answer)
        return self._visit(target, target_id, cfg.path, role)

    def _visit(self, config_path: Path, declared_id: str | None,
               declared_in: Path | None, role: str) -> _Config | None:
        """Read one configuration in its role in the walk (`active`,
        `ancestor`, `descendant`, or `outside` for one read only for a lookup
        or a load order), once; a project reached twice is read once."""
        config_path = self._canonical(config_path)
        known = self._cache.get(config_path) or self._outside.get(config_path)
        if known is not None:
            if declared_id and known.project.id != declared_id:
                self._problem(
                    config_path,
                    f"registered key '{declared_id}' does not match target id "
                    f"'{known.project.id}'")
            return known
        if role == "outside":
            # Its file's own problems are that project's to report, in a
            # command run there; its links' are Design 6.6's.
            marks = (len(self._problems), len(self._findings))
            cfg = self._read_config(config_path, declared_id, declared_in, role)
            del self._problems[marks[0]:]
            del self._findings[marks[1]:]
        else:
            cfg = self._read_config(config_path, declared_id, declared_in, role)
        if cfg is None:
            return None
        cache, by_id = ((self._outside, self._outside_by_id) if role == "outside"
                        else (self._cache, self._by_id))
        cache[config_path] = cfg
        self._roles[config_path] = role
        if declared_in is not None:
            self._reached_from.setdefault(config_path, self._canonical(declared_in))
        previous = self._by_id.get(cfg.project.id) or self._outside_by_id.get(
            cfg.project.id)
        if previous and previous.path != config_path:
            self._problem(
                config_path,
                f"duplicate project id '{cfg.project.id}' also used by {previous.path}")
        else:
            by_id[cfg.project.id] = cfg
            self._read_order.append(cfg.project.id)
        return cfg

    def _read_config(self, path: Path, declared_id: str | None,
                     declared_in: Path | None, role: str) -> _Config | None:
        if not _is_file(path) and _is_file(root_of(path) / LEGACY_SENTINEL):
            # A 3.x project: present, and in a format this TCW does not read
            # (TCW-106 Design 4.2). Not "this machine does not have it". A
            # TCW_PROJECT_<ID> that named it has already said so, naming itself.
            if not any(o.locator == root_of(path) and o.problem
                       for o in self._overrides):
                self._problem(root_of(path), f"is {LEGACY_PROJECT}")
            return None
        if not _is_file(path):
            # Not a defect. A locator is a fact about one machine — the same
            # thing `work.path` is — so a target that is not here means this
            # checkout does not have that project, not that the declaration
            # is wrong. Failing closed here refused every command in exactly
            # the checkouts that have only some of a graph's repositories.
            # Everything else below stays an error: those targets are present
            # and wrong, which is what fail-closed was written for.
            if declared_id is None and declared_in is None:
                # The project the command was run in, not a target it declared.
                # The fail-open below is argued for *targets* — "this checkout
                # does not have that project" — and says nothing about a
                # directory that is not a project at all. Recording nothing for it
                # made `require_valid()` accept any directory on the disk, and
                # every helper built on it answer "no parent, no children,
                # valid".
                self._problem(path, f"no {SENTINEL} here")
                return None
            self._unreachable_edge(declared_in or path, declared_id, root_of(path))
            return None
        def unreadable(message: str) -> _Config | None:
            """A shared file that cannot be read at all. In an ancestor, or a
            project read only for a lookup, its parents and settings are
            unknown: it is placed as a project with no parents and its links
            as unreadable (TCW-109 Design 1.6, adding to TCW-108 Design 6.6).
            Anywhere else it is a graph problem, as is a file of any role
            that does not say which project it is."""
            if role in ("ancestor", "outside") and declared_id:
                return _Config(project=Project(declared_id, root_of(path)), path=path,
                               links=None, link_problem=f"{path}: {message}",
                               children=[], raw={})
            self._problem(path, message)
            return None

        text = self._text(path)
        if isinstance(text, UnicodeDecodeError):
            return unreadable(_not_utf8(text))
        try:
            if isinstance(text, Exception):
                raise text
            raw = _load_named_yaml(text, path, _UniqueKeyLoader) or {}
        except (OSError, yaml.YAMLError) as error:
            return unreadable(f"invalid YAML: {error}")
        if not isinstance(raw, dict):
            return unreadable("config must be a mapping")
        version = version_problem(raw)
        if version:
            # Read by every reader of a `tcw-*.yaml` file (TCW-106 Design 3.4a).
            return unreadable(version)
        project_id = raw.get("id")
        if not isinstance(project_id, str) or not project_id.strip():
            self._problem(
                path,
                "missing project id; migrate with `tcw project new --id <project-id>`",
            )
            return None
        try:
            project_id = validate_project_id(project_id)
        except ValueError as error:
            self._problem(path, str(error))
            return None
        if declared_id and declared_id != project_id:
            self._problem(
                path,
                f"registered key '{declared_id}' does not match target id '{project_id}'",
            )
        links, link_problem, children = self._read_links(path, raw, project_id, role)
        return _Config(project=Project(project_id, root_of(path)), path=path,
                       links=links, link_problem=link_problem, children=children,
                       raw=raw)

    def _read_links(self, path: Path, raw: dict, project_id: str,
                    role: str) -> tuple[list[ParentLink] | None, str | None, list[str]]:
        """`parents:` and `children:` (Design 1, 2), and whose problems they
        are (Design 1.3, 6.6). In the active project every problem is a graph
        problem. In another project a `parents:` problem leaves its links
        unknown instead; a descendant's `children:` problems, "named both as a
        parent and as a child" among them, stay graph problems, and an
        ancestor's `children:` is read only as names.

        A `projects:` or `connected-projects` key (Design 3.5) is a graph
        problem in the active project and in a descendant; in any other
        project it leaves the links unknown, as a broken `parents:` does."""
        retired = retired_key_problem(raw)
        if retired is not None:
            if role in ("active", "descendant"):
                self._problem(path, retired)
            return None, f"{path}: {retired}", []
        links, found = parse_parents(raw.get("parents"), str(path))
        link_problems = [f"{key}: {message}" for key, message in found]
        children, found = parse_children(raw.get("children"), str(path),
                                         own_id=project_id)
        child_problems = [f"{key}: {message}" for key, message in found]
        parent_ids = {link.id for link in links or []}
        listed = raw.get("children")
        child_problems += [
            f"children[{listed.index(child_id)}]: '{child_id}' is named both as "
            f"a parent and as a child" for child_id in children
            if child_id in parent_ids]
        if role in ("active", "descendant"):
            for problem in child_problems:
                self._problem(path, problem)
        if role == "active" and not personal_files_skipped():
            children = [*children, *self._personal_children_of(
                root_of(path), project_id, children, parent_ids)]
        if not link_problems:
            return links or [], None, children
        if role == "active":
            for problem in link_problems:
                self._problem(path, problem)
        return None, f"{path}: {link_problems[0]}", children

    def _personal_children_of(self, root: Path, project_id: str, committed: list[str],
                              parent_ids: set[str]) -> list[str]:
        """The children the active project's personal file adds after its
        committed ones (Design 2.1-2.3), its problems recorded against that
        file as graph problems. No other project's personal file is read
        (Design 2.4). A file that cannot be read or parsed adds nothing here:
        the configuration reader reports it."""
        path = personal_file(root, LOCAL_CONFIG_NAME, self._anchors)
        text = self._text(path)
        if isinstance(text, Exception):
            return []
        try:
            raw = _load_named_yaml(text, path, _UniqueKeyLoader)
        except yaml.YAMLError:
            return []
        if not isinstance(raw, dict) or raw.get("children") is None:
            return []
        listed = raw["children"]
        found, problems = parse_children(listed, str(path), own_id=project_id)
        for key, message in problems:
            self._problem(path, f"{key}: {message}")
        for child_id in found:
            if child_id in parent_ids:
                self._problem(path, f"children[{listed.index(child_id)}]: '{child_id}' "
                                    f"is named both as a parent and as a child")
        added = [child_id for child_id in found
                 if child_id not in committed and child_id not in parent_ids]
        self._personal_children.update(added)
        return added

    def _override_path(self, project_id: str) -> Path | None:
        """Rule 0: where `TCW_PROJECT_<ID>` says this project is, or None.

        None means the ladder carries on — either no variable, or one naming a
        path this machine does not have. A `Path` means it answered, and the
        caller must not consult a lower rung.

        **Absent is not wrong.** A variable pointing at a directory that is not
        here means this machine does not have that project, which is the same
        thing an unresolvable locator means, and `_read_config` has drawn that
        distinction for every locator since fail-closed refused every checkout
        holding part of a graph. It is what lets one set of variables be
        configured once for an environment — a cloud session's base directory,
        say — and used by sessions that attach different subsets of the
        repositories, with neither needing to know which case it is in.

        **Present and wrong is wrong.** A directory that is here and is not a
        project is a mistake with no benign reading, and it is refused rather than
        skipped. Skipping it is the fail-open shape that produces "my override
        does nothing" with nothing at all to read.

        A relative value resolves against the *process's working directory*, not
        the declaring config — the one path in this module that does. A locator
        is written in a file, so it means "relative to that file"; a variable is
        written in a shell, so it means what the shell means.
        """
        if project_id not in self._override_cache:
            self._override_cache[project_id] = self._resolve_override(project_id)
        return self._override_cache[project_id]

    def _resolve_override(self, project_id: str) -> Path | None:
        name = override_variable(project_id)
        value = (os.environ.get(name) or "").strip()
        if not value:
            # An exported-but-empty variable names no path. Reading it as one
            # yields the working directory, which nobody means by `FOO=`.
            return None
        root = Path(value).expanduser()
        if not root.is_absolute():
            root = Path.cwd() / root
        root = root.resolve()
        if not root.is_dir():
            return None
        config_path = root / SENTINEL
        if not config_path.is_file():
            problem = (f"{name} names {LEGACY_PROJECT}"
                       if (root / LEGACY_SENTINEL).is_file()
                       else f"{name} names a directory with no {SENTINEL}")
            self._problem(root, problem)
            self._override_refused.add(project_id)
            # Recorded as an override too, not only as a problem. It stopped the
            # ladder, so it is in force; a caller asking "which overrides are
            # acting on this graph" must not be told none.
            self._overrides.append(ProjectOverride(id=project_id, source=name,
                                                   locator=root,
                                                   problem=f"{root}: {problem}"))
            return config_path
        # Recorded before the id is known to be right. An override that landed
        # on the wrong project still explains a path the reader will otherwise find
        # in no config, and `_read_config` reports the mismatch itself, naming
        # both ids — parsing the config here to say it again would print two
        # messages for one cause.
        self._overrides.append(ProjectOverride(id=project_id, source=name,
                                               locator=root))
        return config_path

    def _locator_path(self, source_config: Path, locator: str,
                      url: str | None = None) -> Path:
        """The config file a locator written in `source_config` names; `url`,
        the repository its entry names, if any."""
        target = Path(locator)
        source_dir = root_of(source_config).resolve()
        resolved = _config_file(
            (target if target.is_absolute() else source_dir / target) / SENTINEL)
        if self._anchors is None:
            return resolved
        top, main = self._anchors
        # Rule 1 — re-anchor only on escape, and only a *relative* locator: an
        # absolute one names a place, not an offset from the config. A target
        # that stays inside the worktree is a sibling project on the same branch and
        # belongs to the worktree (this is what keeps multi-project-in-one-repo
        # working). Only a target that leaves the checkout was authored against
        # the primary checkout's position on disk, so resolve it against the
        # source directory's counterpart under the main worktree root instead
        # — unless, read as written, it lands on a project in a checkout of the
        # repository its entry names (`read_as_written`).
        inside = _below(source_dir, top)
        if (
            not target.is_absolute()
            and inside is not None
            and _below(root_of(resolved), top) is None
            and not (_declares_a_project(resolved)
                     and read_as_written(root_of(resolved), self._anchors, url))
        ):
            counterpart = main / inside
            resolved = _config_file(counterpart / target / SENTINEL)
        return self._worktree_copy(resolved)

    def _worktree_copy(self, resolved: Path) -> Path:
        """Rule 2 — a config path under the main worktree, as this worktree's copy.

        Projects outside this worktree point back into its repository as the *main*
        worktree spells it — the current project, and every sibling in the same
        repository — so the graph would load each twice under one ID and fail
        reciprocity. A path under the main worktree whose counterpart under this
        worktree holds a config, in this same repository, is the same project on the
        checked-out branch, so it resolves there (GitHub #39). Anything else keeps
        its path, so an ID repeated across *different* repositories is still a
        duplicate — including a repository nested inside this one, which the
        branch does not hold even when a copy sits at the same place. A path
        already inside this worktree is left alone: TCW's own worktrees live under
        the primary checkout (`.worktrees/<slug>`), where every worktree path is
        also "under main". Applied to every way a project is declared — a locator,
        absolute or relative, and a `repository:` checkout."""
        if self._anchors is None:
            return resolved
        top, main = self._anchors
        under_main = _below(resolved, main)
        if under_main is None or _below(resolved, top) is not None:
            return resolved
        copy = top / under_main
        if not _declares_a_project(copy):        # a 3.x copy here is the branch's
            return resolved
        between = root_of(copy)
        while between != top and between.is_relative_to(top):
            if not _same_repository(between / ".git", main):
                return resolved                  # another repository's project
            between = between.parent
        return _config_file(copy)

    def _canonical(self, config_path: Path) -> Path:
        """`config_path` (see `_config_file`) under the first spelling seen of its
        folder; as given when the folder cannot be read."""
        config_path = _config_file(config_path)
        root = root_of(config_path)
        try:
            found = root.stat()
        except OSError:
            return config_path
        if not found.st_ino:
            return config_path    # a filesystem with no inode numbers: text only
        folder = self._spellings.setdefault((found.st_dev, found.st_ino), root)
        return folder / SENTINEL

    def _validate_name_back(self) -> None:
        """Design 2.5: each child listed by the active project or by a
        descendant, when it is here and its links could be read, names the
        lister among its parents. A problem against the lister's file."""
        for path, cfg in list(self._cache.items()):
            if self._roles.get(path) not in ("active", "descendant"):
                continue
            for child_id in cfg.children:
                child = self._cache.get(self._edge_target(path, child_id))
                if child is None or child.links is None:
                    continue
                if cfg.project.id not in {link.id for link in child.links}:
                    self._problem(
                        path,
                        f"'{child_id}' is listed as a child of '{cfg.project.id}' but "
                        f"does not name '{cfg.project.id}' among its parents")

    def _validate_loops(self) -> None:
        """Design 4.7: a loop through the parent links of every project read,
        against the configuration of its member read first."""
        loop = find_loop(self._known_links(), self._read_order)
        if loop is not None:
            self._problem(self._any_config(loop[0]).path, loop_message(loop))

    def _known_links(self) -> dict[str, list[ParentLink]]:
        """Each project's links, for every project read whose links could be
        read, in the order read."""
        found = {}
        for project_id in self._read_order:
            cfg = self._by_id.get(project_id) or self._outside_by_id.get(project_id)
            if cfg is not None and cfg.links is not None:
                found[project_id] = cfg.links
        return found

    def _recheck_search_answers(self) -> None:
        """Design 3.4, "a search answer and a manifest that disagree", within
        one command: each folder the search gave is checked against the first
        manifest entry for that ID that its lookup would now consult, other
        than the asking project's own."""
        for (project_id, asker), answer in list(self._answers.items()):
            if answer.by != "search":
                continue
            roots, _ = self._family(asker, project_id)
            entry = self._entry_from_others(project_id, roots)
            if entry is None:
                continue
            decided = self._entry_answer(*entry, record=False)
            self._search_conflict(project_id, asker, decided, [answer.folder])

    def _entry_from_others(self, project_id: str,
                           roots: list[Path]) -> tuple[ManifestEntry, Path] | None:
        """The first entry for `project_id` in the manifests of `roots` after
        the first (the asking project's own), with the root its path is read
        from."""
        for root in roots[1:]:
            for _, base, entries in self._manifests_of(root) or []:
                if project_id in entries:
                    return entries[project_id], base
        return None

    def _search_conflict(self, project_id: str, asker: Path, decided: _Answer,
                         matches: list[Path]) -> str | None:
        """The recorded problem when the search from `asker` finds
        `project_id` in another folder than the manifest entry that decided
        `decided` places it, or None (Design 3.4, decided 2026-10-23)."""
        placed = decided.folder or decided.entry_folder
        if decided.entry is None or placed is None:
            return None
        for match in matches:
            if self._identity(match) != self._identity(placed):
                return self._recorded(
                    decided.entry.file,
                    f"'{project_id}' is found at {match} by the search from {asker}, "
                    f"but {decided.entry.file} places it at {placed}; add an entry for "
                    f"'{project_id}' to {LOCAL_MANIFEST} in {asker}, which that lookup "
                    f"reads first, to say which folder it is")
        return None

    def _reconcile_overrides(self) -> None:
        """Fill in `problem` for every override that did not deliver its project.

        Run after the walk because one of the two failures cannot be seen before
        it. A directory holding no `tcw-config.yaml` is known the moment the
        override resolves; a directory holding the *wrong* project is known only
        once that project's config has been read, by the same mismatch check that
        catches a wrong declared locator.

        The test is deliberately the outcome rather than a list of failure
        modes: an override is satisfied when the graph ended up holding its
        project, under its id, at the place it pointed. Anything else failed,
        including a mode nobody has thought of yet.
        """
        for index, override in enumerate(self._overrides):
            if override.problem is not None:
                continue
            # Through `_canonical`, as the walk read it: the variable may spell
            # the folder in other letter case than the walk met it first.
            where = self._canonical(Path(override.locator) / SENTINEL)
            cfg = self._by_id.get(override.id)
            if cfg is not None and cfg.path == where:
                if (warning := self._other_branch_warning(override, where)):
                    self._overrides[index] = replace(override, warning=warning)
                continue
            # Not `cfg`: that is whatever answered for this id, which is not
            # necessarily what the override pointed at. Name the project actually
            # sitting at the overridden location, read from the walk's cache.
            at_location = self._cache.get(where)
            found = (f"which is '{at_location.project.id}', not '{override.id}'"
                     if at_location is not None
                     else f"which did not yield '{override.id}'")
            self._overrides[index] = replace(
                override,
                problem=f"{override.source} names {override.locator}, {found}",
            )

    def _other_branch_warning(self, override: ProjectOverride,
                              where: Path) -> str | None:
        """Why `override`, run from a linked worktree, reads its project from
        another branch: it names the primary checkout's copy while this
        worktree holds the same project. Kept as stated — it says exactly where
        the project is — but a variable set once for a machine lands here
        whenever a worktree is used, and the graph then mixes two branches."""
        copy = self._worktree_copy(where)
        if copy == where:
            return None
        try:
            held = yaml.safe_load(copy.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
            return None
        try:                                   # read as `_read_config` reads it
            held_id = validate_project_id(str(held.get("id") or "")) \
                if isinstance(held, dict) else None
        except ValueError:
            return None
        if held_id != override.id:
            return None
        return (f"{override.source} names {override.locator}, the primary "
                f"checkout's copy, while this worktree has its own at "
                f"{root_of(copy)}; '{override.id}' is read from another branch "
                f"than the rest of the graph")

    def _problem(self, path: Path, message: str) -> None:
        rendered = f"{path}: {message}"
        if rendered not in self._problems:
            self._problems.append(rendered)
            self._problem_files[rendered] = Path(path)
            self._findings.append(Finding("error", str(path), message))

    def _unreachable_edge(self, config_path: Path, project_id: str | None,
                          locator: Path | None, *,
                          message: str = "", decided_by: Any = None,
                          repository: str | None = None, remedy: str = "") -> None:
        """Record a declared project that is not here, rather than a problem.

        `project_id` is the key the declaring config used. It can be None only
        for the current project's own config, which is never an edge — the guard is
        here so a future caller cannot record a nameless entry that no message
        could ever render.
        """
        if not project_id:
            return
        if project_id in self._override_refused:
            # Told where it is, and it is not a project. That is a refusal, not a
            # thing to obtain, and `run tcw project provision` would contradict it.
            return
        if any(known.id == project_id for known in self._unreachable):
            # One record per project, the first in walk order, however many
            # links reach it (TCW-108 AC 20).
            return
        self._unreachable.append(UnreachableProject(
            id=project_id, locator=locator, declared_in=config_path, message=message,
            decided_by=decided_by, repository=repository, remedy=remedy))

    def unreachable_project(self, project_id: str) -> UnreachableProject | None:
        """The recorded entry for `project_id`, or None.

        The lookup every "declared but not here" message needs: a caller holding
        an id that `get()` answered None for asks this before deciding which
        message to print.
        """
        self._load_graph()
        # Through `unreachable()`, not the raw list: a project another route
        # resolved is not missing, and a message telling the user to obtain a
        # repository they already have is worse than no message.
        return next((u for u in self.unreachable() if u.id == project_id), None)

    # -----------------------------------------------------------------------
    # Finding a project's folder from its ID (TCW-107 Design 2)

    def project_folder(self, project_id: str, named_by: Path) -> Path:
        """The root folder of project `project_id`, asked by the project at
        `named_by`, the one whose configuration, manifest or record names the
        ID (Design 2.12). Any valid ID: it need not appear under `projects:`.

        `named_by` must be a folder this registry has found: the active
        project's root, a project in its graph, or a folder an earlier call
        returned; anything else is a `ValueError`. Raises `Unreachable` for a
        project something names that is not on this machine, `UnknownProject`
        for an ID nothing names or holds, and `ProjectGraphError` for a graph
        problem, which is also added to `check()`.

        A method, because its answer depends on the active project's worktree
        and on what this command has already found (Design 2.9, 2.11 b)."""
        self._load_graph()
        root = self._root_key(named_by)
        if root not in self._found_roots():
            raise ValueError(f"{named_by} is not a project this registry has found")
        # Not in the family: its ancestors are read for the lookup, all of
        # them, and its children are not followed (Design 3.4, the 2.12 bullet).
        cfg = self._config_at(root)
        if cfg is not None and cfg.project.id == project_id:
            return root
        answer = self._locate(project_id, root)
        if answer.problem is not None:
            self._settle(answer)
            raise ProjectGraphError(answer.problem)
        if answer.folder is None:
            if not answer.named:
                raise UnknownProject(f"no project with ID '{project_id}' is known or "
                                     f"found near this one; check the spelling")
            raise Unreachable(answer.message, project=project_id,
                              repository=answer.entry.repository if answer.entry
                              else None)
        problem = self._checked(project_id, answer)
        if problem is not None:
            raise ProjectGraphError(problem)
        self._found.setdefault(project_id, answer.folder)
        return answer.folder

    def found(self, project_id: str) -> dict | None:
        """How the lookup placed a project in the graph (Design 6.1): by a
        manifest, naming its file; by `TCW_PROJECT_<ID>`, naming it; or by the
        search. None for the current project and for one not here."""
        self._load_graph()
        cfg = self._by_id.get(project_id)
        if cfg is None or cfg.path == self._canonical(self._current_path):
            return None
        answer = self._placed.get(cfg.path)
        if answer is None:
            return None
        if answer.by == "manifest":
            return {"by": "manifest", "file": str(answer.entry.file)}
        if answer.by == "variable":
            return {"by": "variable", "name": override_variable(project_id)}
        return {"by": "search"}

    def placement(self, project_id: str, named_by: Path | None = None) -> Placement | None:
        """Where the lookup placed `project_id` and the manifest entry that
        decided it (TCW-115 Design 8.1). With `named_by`, looked up exactly as
        `project_folder` looks it up, raising `UnknownProject` and
        `ProjectGraphError` the same way; a project not on this machine is an
        answer with no `folder`, not an error. Without it, the first answer
        this registry recorded for the ID, reading nothing; None when it has
        none. Every folder in it is resolved but `repository_path`."""
        if named_by is not None:
            root = self._root_key(named_by)
            try:
                folder = self.project_folder(project_id, named_by)
            except Unreachable:
                folder = None
            answer = self._answers.get((project_id, root))
            if answer is None:                 # the asking project itself
                return Placement(id=project_id, asked_by=root, folder=folder)
            return self._placement(project_id, root, answer)
        for (answered_id, root), answer in self._answers.items():
            if answered_id == project_id:
                return self._placement(project_id, root, answer)
        return None

    def placements(self) -> list[Placement]:
        """Every answer this registry has recorded, in the order it recorded
        them, one per ID and asking project (TCW-115 Design 7.4: the answers a
        provisioning run keeps). Reads nothing."""
        return [self._placement(project_id, root, answer)
                for (project_id, root), answer in list(self._answers.items())]

    def entry_elsewhere(self, project_id: str, asked_by: Path) -> Placement | None:
        """The first entry for `project_id` in a manifest the lookup from
        `asked_by` reads after the asking project's own, as a placement, or
        None: what disagrees with a search answer (Design 3.4), which a
        provisioning run names when a fetch moved a project it kept (TCW-115
        Design 7.4). Records nothing."""
        roots, _ = self._family(asked_by, project_id)
        found = self._entry_from_others(project_id, roots)
        if found is None:
            return None
        entry, base = found
        answer = self._entry_answer(entry, base, record=False)
        return self._placement(project_id, asked_by,
                               _Answer(folder=answer.folder, entry=entry, owner=base))

    def _placement(self, project_id: str, asked_by: Path, answer: _Answer) -> Placement:
        entry = answer.entry
        folder = Path(os.path.realpath(answer.folder)) if answer.folder else None
        if entry is None or answer.owner is None:
            return Placement(id=project_id, asked_by=asked_by, folder=folder)
        written = Path(entry.path).expanduser()
        entry_folder = Path(os.path.realpath(
            root_of(self._locator_path(answer.owner / SENTINEL, str(written),
                                       entry.url))))
        return Placement(
            id=project_id, asked_by=asked_by, folder=folder, entry=entry,
            owner=Path(os.path.realpath(answer.owner)), entry_folder=entry_folder,
            repository_folder=_without_subfolder(entry_folder, entry.subfolder),
            repository_path=_without_subfolder(
                self._read_from(answer.owner, written, entry.url) / written,
                entry.subfolder))

    def _read_from(self, owner: Path, written: Path, url: str | None = None) -> Path:
        """The folder an entry's relative path is read from: its owner's root,
        or, in the active project's linked worktree, the owner's counterpart in
        the main checkout when the path leads outside the repository and is not
        read as written (TCW-107 Design 4.3, `_locator_path` rule 1). Nothing
        is resolved."""
        source = Path(owner)
        if written.is_absolute() or self._anchors is None:
            return source
        top, main = self._anchors
        inside = _below(source.resolve(), top)
        if inside is None:
            return source
        leads_to = _config_file(source.resolve() / written / SENTINEL)
        if _below(root_of(leads_to), top) is not None or (
                _declares_a_project(leads_to)
                and read_as_written(root_of(leads_to), self._anchors, url)):
            return source
        return main / inside

    def _found_roots(self) -> set[Path]:
        return {self.project_root, *(root_of(path) for path in self._cache),
                *(root_of(path) for path in self._outside), *self._found.values()}

    def _checked(self, project_id: str, answer: _Answer) -> str | None:
        """The problem, recorded, with a found folder: one that does not hold
        `project_id` (only a variable can place one there), or another folder
        than the one this command already holds for the ID (Design 2.9)."""
        probe = self._probe(answer.folder)
        if probe.kind != "project" or probe.id != project_id:
            return self._recorded(
                answer.folder / SENTINEL,
                f"{override_variable(project_id)} names {answer.folder}, which does "
                f"not declare '{project_id}'")
        known = self._known_folder(project_id)
        if known is not None and self._identity(known) != self._identity(answer.folder):
            return self._recorded(
                answer.folder / SENTINEL,
                f"duplicate project id '{project_id}' also used by {known / SENTINEL}")
        return None

    def _recorded(self, path: Path, message: str) -> str:
        self._problem(path, message)
        return f"{path}: {message}"

    def _settle(self, answer: _Answer) -> None:
        """Record an answer's deferred problem, where it is a graph problem."""
        if answer.deferred is not None:
            self._problem(*answer.deferred)

    def _edge_target(self, source_config: Path, target_id: str) -> Path | None:
        """Where an edge's configuration is: the answer the walk got (never
        looked up again, Design 2.11 b)."""
        answer = self._answers.get((target_id, self._root_key(root_of(source_config))))
        if answer is None or answer.folder is None:
            return None
        return self._canonical(answer.folder / SENTINEL)

    def _root_key(self, root: Path) -> Path:
        """A project root under the first spelling met of its folder."""
        return root_of(self._canonical(Path(root) / SENTINEL))

    def _identity(self, root: Path) -> Any:
        try:
            found = root.stat()
        except OSError:
            return root
        return (found.st_dev, found.st_ino) if found.st_ino else root

    def _known_folder(self, project_id: str) -> Path | None:
        """The folder this command has found for `project_id`, if any."""
        cfg = self._by_id.get(project_id) or self._outside_by_id.get(project_id)
        if cfg is not None:
            return root_of(cfg.path)
        return self._found.get(project_id)

    def _config_at(self, root: Path) -> _Config | None:
        """The configuration of the project at `root`: the family's, or one
        read for a lookup with its ancestors (Design 3.4, the 2.12 bullet),
        never joining the family. None when it cannot be read."""
        path = self._canonical(root / SENTINEL)
        known = self._cache.get(path) or self._outside.get(path)
        if known is not None:
            return known
        if not _is_file(path):
            return None
        cfg = self._visit(path, None, root, "outside")
        if cfg is not None:
            self._walk_up(cfg, "outside")
        return cfg

    def _text(self, path: Path) -> str | Exception:
        """A file's text, or the error reading it, read at most once."""
        path = Path(path)
        if path not in self._texts:
            try:
                self._texts[path] = _read_text(path)
            except (OSError, UnicodeDecodeError) as error:
                self._texts[path] = error
        return self._texts[path]

    def _listing(self, folder: Path) -> list[tuple[str, bool]] | OSError:
        if folder not in self._listings:
            try:
                self._listings[folder] = _list_folder(folder)
            except OSError as error:
                self._listings[folder] = error
        return self._listings[folder]

    def _probe(self, folder: Path) -> _Probe:
        """What `folder`'s `.tcw/tcw-config.yaml` and root `tcw-config.yaml`
        say, the only two files the search reads in a folder (Design 2.6)."""
        if folder in self._probes:
            return self._probes[folder]
        text = self._text(folder / SENTINEL)
        if isinstance(text, str):
            probe = self._probe_text(text, folder / SENTINEL, legacy=False)
        elif isinstance(text, (FileNotFoundError, NotADirectoryError)):
            legacy = self._text(folder / LEGACY_SENTINEL)
            if isinstance(legacy, str):
                probe = self._probe_text(legacy, folder / LEGACY_SENTINEL, legacy=True)
            elif isinstance(legacy, (FileNotFoundError, NotADirectoryError)):
                probe = _Probe("none")
            else:
                probe = _Probe("unreadable", detail=str(legacy))
        else:
            probe = _Probe("unreadable", detail=str(text))
        self._probes[folder] = probe
        return probe

    @staticmethod
    def _probe_text(text: str, path: Path, *, legacy: bool) -> _Probe:
        try:
            raw = _load_named_yaml(text, path, _UniqueKeyLoader)
        except yaml.YAMLError as error:
            return _Probe("unreadable", detail=f"invalid YAML: {error}")
        if not isinstance(raw, dict):
            return _Probe("unreadable", detail="config must be a mapping")
        try:
            project_id = validate_project_id(str(raw.get("id") or ""))
        except ValueError:
            project_id = None
        if legacy:
            return _Probe("legacy", project_id)
        version = version_problem(raw)
        if version is not None:
            return _Probe("version", project_id, version)
        if project_id is None:
            return _Probe("unreadable", detail="missing or invalid project id")
        return _Probe("project", project_id)

    def _manifests_of(self, root: Path, *,
                      record: bool = True) -> list[tuple[Any, Path, dict]] | None:
        """`root`'s manifests, each as `(file as TCW names it, the root its
        paths are read from, entries)`, the personal one first, unless
        personal files are skipped (Design 1.10). None when one has a problem:
        it is recorded against its file, and a lookup that would consult it
        fails (Design 1.8). Unless `record` is false: then the problem is
        neither recorded nor kept, for a manifest read only in passing."""
        root = self._root_key(root)
        if root in self._manifests:
            return self._manifests[root]
        found: list[tuple[Path, str]] = []
        files = [] if personal_files_skipped() else [
            (personal_file(root, LOCAL_MANIFEST_NAME, self._anchors), True)]
        files.append((root / MANIFEST, False))
        result: list[tuple[Any, Path, dict]] | None = []
        for path, personal in files:
            text = self._text(path)
            if isinstance(text, (FileNotFoundError, NotADirectoryError)):
                continue
            problems: list[str] = []
            if isinstance(text, UnicodeDecodeError):
                problems.append(_not_utf8(text))
            elif isinstance(text, Exception):
                problems.append(f"cannot be read: {text}")
            else:
                try:
                    mapping = _load_named_yaml(text, path, _UniqueKeyLoader)
                except yaml.YAMLError as error:
                    problems.append(f"invalid YAML: {error}")
                else:
                    entries, problems = parse_manifest(mapping, path, personal=personal)
                    if not problems and result is not None:
                        result.append((path, root, entries))
            found += [(path, problem) for problem in problems]
            if problems:
                result = None
        if found and not record:
            return None
        for path, problem in found:
            self._problem(path, problem)
            self._manifest_problem.setdefault(root, f"{path}: {problem}")
        self._manifests[root] = result
        return result

    def _family(self, named_by: Path, project_id: str) -> tuple[list[Path], set[str]]:
        """The roots whose manifests the lookup of `project_id` from
        `named_by` consults, in Design 3.4's order, and every ID their
        `parents:` and `children:` name.

        `named_by` first; then (b) its ancestors found so far, in the reverse
        of its load order over the projects read so far (the depth-first
        order when C3 finds none, with no warning); then (c) every project
        read so far from which a chain of parent links leads up to it, fewest
        links first and, at one distance, in the order read. A project whose
        folder is the one being looked up is skipped."""
        asker = self._known_config(named_by)
        order = [named_by]
        named = _named_ids(asker)
        if asker is None:
            return order, named
        seen = {self._identity(named_by)}
        links = self._known_links()
        try:
            above = load_order_of(asker.project.id, links).ids[:-1]
        except ValueError:                     # a loop, reported on its own
            above = _reached_up(asker.project.id, links)
        for member_id in [*reversed(above), *self._below(asker.project.id, links)]:
            cfg = self._by_id.get(member_id) or self._outside_by_id.get(member_id)
            if cfg is None or member_id == project_id:
                continue
            root = root_of(cfg.path)
            if self._identity(root) in seen:
                continue
            seen.add(self._identity(root))
            order.append(root)
            named.update(_named_ids(cfg))
        return order, named

    def _located_by(self, roots: list[Path]) -> Iterator[Path]:
        """Design "Locating a project", step 1, "then, going down, in the
        manifests of the children already found": after the manifests of
        `roots` (the asking project's family), the roots of the projects
        their entries place, then of those the next manifests place, breadth
        first and in the order the entries are written, each project once.
        So a child of a sibling, listed only in that sibling's manifest, is
        found. These manifests are read only when the family's manifests
        have no entry and the search finds no folder declaring the ID
        (`_answer`), so they never overrule either. A manifest read only
        here that has a problem, or an entry in one that names a wrong
        folder, is passed over and not recorded: it names nothing this
        lookup can use, and it is reported where it is part of the family."""
        seen = {self._identity(root) for root in roots}
        frontier = list(roots)
        while frontier:
            layer: list[Path] = []
            for root in frontier:
                for _, base, entries in self._manifests_of(root, record=False) or []:
                    for entry in entries.values():
                        folder = self._entry_answer(entry, base, record=False).folder
                        if folder is None or self._identity(folder) in seen:
                            continue
                        seen.add(self._identity(folder))
                        layer.append(folder)
                        yield folder
            frontier = layer

    def _known_config(self, root: Path) -> _Config | None:
        path = self._canonical(root / SENTINEL)
        return self._cache.get(path) or self._outside.get(path)

    def _below(self, project_id: str, links: dict) -> list[str]:
        """The projects read so far that reach `project_id` by parent links,
        nearest first, and at one distance in the order read."""
        place = {pid: index for index, pid in enumerate(self._read_order)}
        found: list[str] = []
        reached = {project_id}
        frontier = [project_id]
        while frontier:
            layer = sorted({pid for pid, own in links.items()
                            if pid not in reached
                            and any(link.id in frontier for link in own)},
                           key=lambda pid: place.get(pid, len(place)))
            reached.update(layer)
            found += layer
            frontier = layer
        return found

    def _locate(self, project_id: str, named_by: Path) -> _Answer:
        """Design 2.1-2.8, answered once per question for the whole command."""
        key = (project_id, self._root_key(named_by))
        if key not in self._answers:
            self._answers[key] = self._answer(project_id, key[1])
        return self._answers[key]

    def _answer(self, project_id: str, named_by: Path) -> _Answer:
        override = self._override_path(project_id)
        if override is not None:
            if project_id in self._override_refused:
                return _Answer(problem=next(o.problem for o in self._overrides
                                            if o.id == project_id and o.problem))
            return _Answer(folder=root_of(override), by="variable")
        roots, named = self._family(named_by, project_id)
        for index, root in enumerate(roots):
            manifests = self._manifests_of(root)
            if manifests is None:
                return _Answer(problem=self._manifest_problem[self._root_key(root)])
            for _, base, entries in manifests:
                if project_id in entries:
                    answer = replace(self._entry_answer(entries[project_id], base),
                                     owner=base)
                    if index == 0 or answer.problem is not None:
                        return answer
                    # Another project's manifest decided: the search from the
                    # asking project must not disagree (Design 3.4).
                    conflict = self._search_conflict(
                        project_id, named_by, answer, self._searched(project_id, named_by))
                    return answer if conflict is None else _Answer(
                        problem=conflict, named=True)
        matches, problems = _search(self, project_id, named_by)
        if not matches and not problems:
            # The manifests reached only in passing are read after the
            # search, and only when it finds no folder declaring the ID, not
            # even one it cannot read: they add a project the family's
            # manifests and the search cannot reach, and never overrule
            # either. An entry there that names a wrong folder is passed
            # over, unrecorded, as a problem in the whole manifest is, so a
            # stale entry in an unrelated project's manifest cannot stop this
            # one (TCW-118, combined review). The first entry that finds the
            # folder decides; failing that, the first that names a folder not
            # on this machine, which provisioning can fill.
            not_here = None
            for root in self._located_by(roots):
                for _, base, entries in self._manifests_of(root, record=False) or []:
                    if project_id not in entries:
                        continue
                    answer = replace(self._entry_answer(entries[project_id], base,
                                                        record=False), owner=base)
                    if answer.folder is not None:
                        return answer
                    if answer.problem is None and not_here is None:
                        not_here = answer
            if not_here is not None:
                return not_here
        if problems and not matches and all(path.name == Path(SENTINEL).name
                                            for path, _ in problems):
            # A version this TCW cannot read: a gap in an ancestor (TCW-109
            # Design 1.6), a graph problem elsewhere, so recorded when settled.
            path, message = problems[0]
            return _Answer(problem=f"{path}: {message}", named=True,
                           unreadable=root_of(path), deferred=(path, message))
        if problems:
            rendered = [self._recorded(path, message) for path, message in problems]
            return _Answer(problem=rendered[0], named=True)
        distinct: dict[Any, Path] = {}
        for match in matches:
            folder = root_of(self._worktree_copy(_config_file(match / SENTINEL)))
            distinct.setdefault(self._identity(folder), folder)
        if len(distinct) > 1:
            folders = " and ".join(str(f) for f in distinct.values())
            return _Answer(problem=self._recorded(
                named_by / SENTINEL,
                f"project '{project_id}' is declared by more than one folder near "
                f"this one: {folders}; add an entry for '{project_id}' to "
                f"{LOCAL_MANIFEST} (this machine) or {MANIFEST} (everyone)"))
        if distinct:
            return _Answer(folder=next(iter(distinct.values())), by="search")
        remedy = (f"no manifest lists it, and no folder next to {named_by} or "
                  f"enclosing it declares it; add it to {MANIFEST} or {LOCAL_MANIFEST}")
        return _Answer(named=project_id in named, remedy=remedy,
                       message=_not_here_message(project_id, remedy))

    def _searched(self, project_id: str, named_by: Path) -> list[Path]:
        """The distinct folders the search from `named_by` finds declaring
        `project_id`, its problems left to a lookup that the search decides."""
        matches, _ = _search(self, project_id, named_by)
        distinct: dict[Any, Path] = {}
        for match in matches:
            folder = root_of(self._worktree_copy(_config_file(match / SENTINEL)))
            distinct.setdefault(self._identity(folder), folder)
        return list(distinct.values())

    def _entry_answer(self, entry: ManifestEntry, base: Path, *,
                      record: bool = True) -> _Answer:
        """Design 2.3: the deciding entry decides, whatever is on disk. A
        problem is recorded unless `record` is false, when it is only
        returned, unrendered (for `manifest_findings`)."""
        named = f"entry for '{entry.id}' in {entry.file}"
        try:
            written = str(Path(entry.path).expanduser())
        except RuntimeError as error:       # `~name` naming no user
            return _Answer(entry=entry, problem=self._recorded(entry.file, f"{named}: {error}")
                           if record else f"{named}: {error}")
        folder = root_of(self._locator_path(base / SENTINEL, written, entry.url))
        probe = self._probe(folder)
        if probe.kind == "project" and probe.id == entry.id:
            return _Answer(folder=folder, by="manifest", entry=entry)
        if probe.kind == "project":
            wrong = f"places it at {folder}, which declares '{probe.id}', not '{entry.id}'"
        elif probe.kind == "version":
            wrong = f"places it at {folder}, whose {SENTINEL} {probe.detail}"
        elif probe.kind == "legacy":
            wrong = f"places it at {folder}, which is {LEGACY_PROJECT}"
        elif probe.kind == "unreadable":
            wrong = f"places it at {folder}, whose {SENTINEL} cannot be read: {probe.detail}"
        else:
            listing = self._listing(folder)
            if isinstance(listing, FileNotFoundError) or (
                    isinstance(listing, list) and [n for n, _ in listing] in ([], [".git"])):
                only_git = isinstance(listing, list) and bool(listing)
                remedy = self._not_here(entry, folder, only_git)
                return _Answer(entry=entry, entry_folder=folder, named=True,
                               remedy=remedy,
                               message=_not_here_message(entry.id, remedy))
            if isinstance(listing, OSError):
                wrong = (f"places it at {folder}, which cannot be listed, so whether "
                         f"it is empty is not known: {listing.strerror or listing}")
            else:
                wrong = (f"places it at {folder}, which is not a TCW project: it "
                         f"holds files and no {SENTINEL}")
                if not record:
                    return _Answer(entry=entry, problem=f"{named} {wrong}",
                                   occupied=folder)
                problem = self._recorded(entry.file, f"{named} {wrong}")
                self._occupied_problems.add(problem)
                return _Answer(entry=entry, problem=problem, occupied=folder)
        if probe.kind in ("version", "unreadable"):
            # A gap in an ancestor (TCW-109 Design 1.6), so recorded when
            # settled, where it is a graph problem.
            if not record:
                return _Answer(entry=entry, problem=f"{named} {wrong}", unreadable=folder)
            return _Answer(entry=entry, problem=f"{entry.file}: {named} {wrong}",
                           unreadable=folder, deferred=(entry.file, f"{named} {wrong}"))
        return _Answer(entry=entry, problem=self._recorded(entry.file, f"{named} {wrong}")
                       if record else f"{named} {wrong}")

    def manifest_files(self) -> set:
        """The active project's two manifests, as TCW names them: the personal
        one where `_manifests_of` reads it, which in a linked worktree with no
        personal manifest of its own is the main checkout's (Design 4.2)."""
        root = self._root_key(self.project_root)
        files = {root / MANIFEST}
        if not personal_files_skipped():
            files.add(personal_file(root, LOCAL_MANIFEST_NAME, self._anchors))
        return files

    def manifest_findings(self, inherited=()) -> list[Finding]:
        """`tcw validate`'s check of every entry in the active project's two
        manifests, whether or not `projects:` names the ID (Design 5.1): an
        entry whose folder is not here, or empty, is `unresolved`; one whose
        folder is wrong is an `error`, or a `warning` when the shared entry
        does not decide on this machine because the personal manifest or
        `TCW_PROJECT_<ID>` places the project. Either finding for such an
        entry names the override. A manifest with a format problem is
        already a graph problem, and gives nothing here."""
        self._load_graph()
        manifests = self._manifests_of(self.project_root) or []
        personal = {entry_id: file for file, _, entries in manifests
                    if file.name == LOCAL_MANIFEST_NAME for entry_id in entries}
        # What could not be checked for a project this entry places (Design
        # 6.5's last paragraph), added to its finding rather than given one
        # of its own.
        owned = self.manifest_files()
        unchecked = {record["id"]: record["message"]
                     for record in self._availability(inherited)
                     if record["decided_by"] in owned}
        findings: list[Finding] = []
        for file, base, entries in manifests:
            for entry in entries.values():
                answer = self._entry_answer(entry, base, record=False)
                if answer.folder is not None or self._placed_unreadable(entry.id, answer):
                    continue
                by = None
                if file.name != LOCAL_MANIFEST_NAME:
                    by = (str(personal[entry.id]) if entry.id in personal
                          else self._variable_places(entry.id))
                overridden = "" if by is None else f" (overridden on this machine by {by})"
                if answer.problem is None:
                    suffix = ""
                    if entry.id in unchecked and unchecked[entry.id].startswith(
                            answer.message):
                        suffix = unchecked.pop(entry.id)[len(answer.message):]
                    findings.append(Finding("unresolved", str(file),
                                            answer.message + suffix + overridden))
                else:
                    findings.append(Finding("error" if by is None else "warning",
                                            str(file), answer.problem + overridden))
        return findings

    def _placed_unreadable(self, project_id: str, answer: _Answer) -> bool:
        """Whether the graph holds `project_id` at the folder an entry places
        it in, as a project whose shared file cannot be read (TCW-109 Design
        1.6): that is a gap, reported once by `_availability`, not an error
        of the entry."""
        cfg = self._any_config(project_id)
        return (answer.unreadable is not None and cfg is not None
                and cfg.link_problem is not None and cfg.links is None
                and self._identity(root_of(cfg.path)) == self._identity(answer.unreadable))

    def _availability(self, inherited=()) -> list[dict]:
        """Design 6.5's rows (a), (b) and (d), one record per project of the
        family's load order or listed by a member of the family below it
        that is not on this machine or whose links could not be read: its
        ID, its `where` (the file naming it), its message, and the manifest
        whose entry decided where a missing one should be. `inherited` holds
        `(project ID, axis)` for each project at which a store check stopped
        (row c), added to that project's record, or giving it one."""
        self._load_graph()
        here = self.current.id
        try:
            order = self.load_order()
        except ProjectGraphError:
            return []
        records: dict[str, dict] = {}

        def note(project_id: str, where: Path, row: str, lister: str) -> None:
            cfg = self._any_config(project_id)
            if cfg is not None and cfg.link_problem is None:
                return
            if cfg is not None:
                text = (f"could not check what '{project_id}' passes down to "
                        f"'{here}': {cfg.link_problem}" if row == "a" else
                        f"could not check that '{project_id}' names '{lister}' as a "
                        f"parent: {cfg.link_problem}")
                records.setdefault(project_id, {"id": project_id, "where": where,
                                                "message": text, "decided_by": None})
                return
            absent = self.unreachable_project(project_id)
            if absent is None:
                return
            suffix = (f"; could not check what it passes down to '{here}' or the "
                      f"projects above it" if row == "a" else
                      f"; could not check that it names '{lister}' as a parent")
            record = records.setdefault(project_id, {
                "id": project_id, "where": Path(absent.declared_in),
                "message": absent.message or (
                    f"connected project '{project_id}' is declared but not reachable "
                    f"in this checkout ({absent.locator})"),
                "suffixes": [], "decided_by": absent.decided_by})
            if suffix not in record["suffixes"]:
                record["suffixes"].append(suffix)

        for project_id in order.ids[:-1]:
            if project_id in order.missing or project_id in order.unreadable:
                note(project_id, self._naming_file(project_id), "a", here)
        for member in [self.current, *self.descendants()]:
            cfg = self._by_id[member.id]
            for child_id in self.declared_child_ids(member.id):
                if child_id not in order.ids:
                    note(child_id, cfg.path, "b", member.id)
        for project_id, axis in inherited:
            if project_id not in records:
                note(project_id, self._naming_file(project_id), "a", here)
            record = records.get(project_id)
            if record is None:
                continue
            suffix = f"; could not check the {axis} inherited from it"
            if "suffixes" in record:          # not on this machine: (a), (b), then (c)
                if suffix not in record["suffixes"]:
                    record["suffixes"].append(suffix)
            elif not record["message"].endswith(suffix):   # unreadable: (d), then (c)
                record["message"] += suffix
        for record in records.values():
            record["message"] += "".join(record.pop("suffixes", []))
        return list(records.values())

    def _naming_file(self, project_id: str) -> Path:
        """The configuration whose link first named `project_id`."""
        absent = self.unreachable_project(project_id)
        if absent is not None:
            return Path(absent.declared_in)
        cfg = self._any_config(project_id)
        return self._reached_from.get(cfg.path, self._current_path) if cfg \
            else self._current_path

    def availability_findings(self, inherited=()) -> list[Finding]:
        """One `unresolved` finding per project Design 6.5 reports, except a
        missing one whose deciding entry is in the active project's own
        manifests: `manifest_findings` reports that one, with the same
        suffixes (TCW-107 Design 5.1)."""
        owned = self.manifest_files()
        return [Finding("unresolved", str(record["where"]), record["message"])
                for record in self._availability(inherited)
                if record["decided_by"] is None or record["decided_by"] not in owned]

    @staticmethod
    def _variable_places(project_id: str) -> str | None:
        """`TCW_PROJECT_<ID>`'s name when it names a folder on this machine,
        read without recording it as an override in force."""
        name = override_variable(project_id)
        value = (os.environ.get(name) or "").strip()
        if not value:
            return None
        try:
            return name if Path(value).expanduser().is_dir() else None
        except (RuntimeError, OSError):
            return None

    @staticmethod
    def _not_here(entry: ManifestEntry, folder: Path, only_git: bool) -> str:
        """Design 6.2's message, after its lead, for a project its deciding
        entry places in a folder that is not here, or empty, naming the folder
        the entry was resolved to, as the error lines for a wrong folder do
        (TCW-108 AC 36)."""
        message = f"{entry.file} places it at {folder}"
        if entry.repository is None:
            return message + (f"; {_holds_only_git(str(folder))}" if only_git else "")
        fetch = f"fetch it with 'tcw project provision {entry.id}'"
        if only_git:
            fetch = f"{_holds_only_git(str(folder))}, then {fetch}"
        return f"{message}, from {entry.repository}; {fetch}"

    def _search_candidates(self, named_by: Path) -> list:
        """The rounds of folders the search tests (`_search`), as
        `search_rounds` gives them for the active project's worktree."""
        return [self._candidates_from(*spec)
                for spec in search_rounds(named_by, self._anchors)]

    def _candidates_from(self, holder: Path, own: Path, enclosing: list[Path]):
        """Each folder in `holder` but `own`, then each of `enclosing`."""
        listing = self._listing(holder)
        if isinstance(listing, list):
            for name, is_dir in listing:
                folder = holder / name
                if (is_dir and name != TCW_FOLDER and folder != own
                        and not self._protected(folder)):
                    yield folder
        yield from enclosing

    @staticmethod
    def _protected(folder: Path) -> bool:
        """Whether `folder` is one macOS asks a person's permission to read:
        Desktop, Documents or Downloads, directly in the home folder. Never
        tested as a folder next to a project, so a project kept directly in
        the home folder does not make the search read inside one the person
        never passed through. The search still tests such a folder as one
        enclosing a project, which the person is already working inside."""
        if not _ON_MACOS or folder.name not in _PROTECTED_NAMES:
            return False
        try:
            home = Path.home().resolve()
        except (RuntimeError, KeyError, OSError):
            return False
        return folder.parent == home


def _named_ids(cfg: _Config | None) -> set[str]:
    """The IDs a configuration's `parents:` and `children:` name; an
    ancestor's `children:` counts, read as names (Design 3.4)."""
    if cfg is None:
        return set()
    return {*(link.id for link in cfg.links or []), *cfg.children}


def _reached_up(project_id: str, links: dict) -> tuple[str, ...]:
    """The projects above `project_id` by parent links, depth first in
    listing order, for a graph with a loop, where there is no load order."""
    placed: list[str] = []

    def climb(pid: str) -> None:
        for link in links.get(pid, ()):
            if link.id not in placed and link.id != project_id:
                placed.append(link.id)
                climb(link.id)

    climb(project_id)
    return tuple(reversed(placed))


def _not_utf8(error: UnicodeDecodeError) -> str:
    return (f"is not valid UTF-8 text (byte "
            f"0x{error.object[error.start:error.start + 1].hex()} "
            f"at position {error.start})")
