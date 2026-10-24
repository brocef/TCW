"""A project's configuration, read in layers (TCW-72).

Configuration is read from four layers, lowest first:

  built-in → tcw-config.yaml → the user-wide file → tcw-config.local.yaml

`built-in` is TCW's own defaults; `tcw-config.yaml` is the team's file; the
two above it are a person's own, are never tracked, and may set only the keys
in `PERSONAL_KEYS`. A higher layer wins. `load_config` is the one function
that reads all four, checks them, merges them and parses the result; every
command that acts on a project's configuration goes through it.

Mappings merge key by key. A stage's `prompt`, `pre` and `post` lists and
each procedure's list are "chain lists": a layer that sets one replaces what
the layers below resolved, unless the list holds one `inherit: true` entry,
which stands for that resolved list at its position. Every value and every
list entry remembers the layer it came from (its `Origin`), so a problem can
name the file to fix and `tcw config show --origin` can say where each value
came from.

It sits at the top of the package, beside `tcw/errors.py`, because all three
axes read configuration.
"""

from __future__ import annotations

import copy
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import yaml

from tcw.store.yaml_source import UniqueKeyLoader, load as _load_named_yaml

from tcw.project_files import (LOCAL_CONFIG_NAME, LOCAL_SENTINEL as LOCAL_FILE, SENTINEL,
                               SKIP_VARIABLE, key_problems, personal_files_skipped,
                               root_of, version_problem, without_version)

#: The key paths a personal file may set; `*` stands for exactly one key.
#: Anything not listed is shared, including any key TCW adds later unless it
#: is added here. `user.name` may be set only in a personal file. `children`
#: is not here: it may be added to in the project's own personal file but not
#: in the user-wide one, which applies to every project (TCW-108 Design 2.2),
#: so it is in `LOCAL_ONLY_KEYS` instead.
PERSONAL_KEYS = (
    "user.name",
    "work.stages.*.prompt",
    "work.stages.*.post",
    "work.procedures.*",
    "work.jira.credentials.email-env",
    "work.jira.credentials.token-env",
)

#: The top-level keys the project's personal file `.tcw/tcw-config.local.yaml`
#: may add to and the user-wide file may not (TCW-108 Design 2.2). The
#: personal list is added after the committed one (Design 2.1).
LOCAL_ONLY_KEYS = ("children",)

#: The keys that cross a parent link passing `config` (TCW-109 Design 1.1):
#: `work.tags`, and `work.jira` with every key under it. Everything else is
#: each project's own, `work.backend` included. The list grows only in a
#: release, and its order is the order `tcw config show` names an undecided
#: key in (Design 7.1).
INHERITED_KEYS = ("work.tags", "work.jira")

LAYERS = ("built-in", "project", "user", "local", "environment")
PERSONAL_LAYERS = ("user", "local", "environment")

_PATTERNS = tuple(tuple(path.split(".")) for path in PERSONAL_KEYS)
_CREDENTIALS = ("work", "jira", "credentials")

KeyPath = tuple  # of str keys and int list indexes


@dataclass(frozen=True)
class Origin:
    """The layer a value came from, and the file that layer was read from
    (none for `built-in` and `environment`); for `environment`, the
    variable's name. `project` is the ID of the project that declared the
    value, and `position` that project's place in the fold (TCW-109 Design
    2.6), so a value one project passes to another still names its file."""

    layer: str
    file: Path | None = None
    # The project root a personal file is read for, when that is not the root
    # of the folder holding it: a linked worktree borrowing its main checkout's
    # file (TCW-107 Design 4.2); for a variable, the root of the project it
    # names (TCW-109 Design 4.8).
    root: Path | None = field(default=None, compare=False)
    variable: str | None = None
    project: str | None = field(default=None, compare=False)
    position: int = field(default=0, compare=False)

    @property
    def folder(self) -> Path | None:
        """The folder a `file:` binding is read from and `TCW_CONFIG_DIR`
        names: the declaring file's folder, except that a file in a project's
        `.tcw/` folder is read as though it sat at the project root (TCW-106
        Design 1.4), and a borrowed personal file as though it sat in the
        worktree that borrowed it."""
        if self.root is not None:
            return self.root
        if self.file is None:
            return None
        if self.layer in ("project", "local"):
            return root_of(self.file)
        return self.file.parent

    @property
    def personal(self) -> bool:
        return self.layer in PERSONAL_LAYERS

    @property
    def rank(self) -> tuple[int, int]:
        """A later project in the fold outranks an earlier one; within one
        project, a higher layer a lower one."""
        return (self.position, LAYERS.index(self.layer))

    def __str__(self) -> str:
        if self.variable is not None:
            return f"{self.layer}: {self.variable}"
        if self.file is None or self.layer == "project":
            return self.layer
        return f"{self.layer}: {self.file}"


BUILT_IN = Origin("built-in", position=-1)


def dotted(key_path: KeyPath) -> str:
    """A key path as people write it: `work.stages.spec.prompt[2]`."""
    out = ""
    for part in key_path:
        if isinstance(part, int):
            out += f"[{part}]"
        else:
            out += ("." if out else "") + str(part)
    return out


def shown_in(path: Path, root: Path | None) -> str:
    """`path` relative to `root` when it is inside it, else absolute."""
    if root is not None:
        for base in (root, root.resolve()):
            try:
                return str(path.relative_to(base))
            except ValueError:
                continue
    return str(path)


@dataclass(frozen=True)
class Problem:
    """One configuration problem, naming the file and key it is about. `file`
    is None for a problem with no file, such as a bad `TCW_NO_PERSONAL_CONFIG`
    value or a built-in value."""

    file: Path | None
    key_path: KeyPath
    message: str
    root: Path | None = field(default=None, compare=False)

    @property
    def where(self) -> str:
        return shown_in(self.file, self.root) if self.file is not None else ""

    @property
    def detail(self) -> str:
        """The message with its key path in front, as `validate` prints it
        after the file."""
        return (f"{dotted(self.key_path)}: {self.message}" if self.key_path
                else self.message)

    def __str__(self) -> str:
        return f"{self.where}: {self.detail}" if self.file is not None else self.detail


@dataclass(frozen=True)
class Setting:
    """A personal value that was read but not applied, and why; `variable` is
    the override variable's name when it came from one."""

    file: Path | None
    key_path: KeyPath
    value: Any
    reason: str
    variable: str | None = None


@dataclass
class Config:
    root: Path
    values: dict
    origins: dict
    work: Any  # tcw.work.config.WorkConfig
    jira: Any = None  # the parsed `work.jira` in Jira mode
    problems: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    refused: list = field(default_factory=list)
    #: Each chain list's key path, with the origin of every layer that set it.
    written: dict = field(default_factory=dict)
    #: True when `tcw-config.yaml` itself could not be read, so nothing above
    #: it could be merged.
    unreadable: bool = False
    #: Each inherited key that cannot be used, by its dotted name (TCW-109
    #: Design 3.4): a `Withheld` carrying the error a reader of it gets.
    withheld: dict = field(default_factory=dict)
    #: The IDs of the configuration sources folded, in order, gaps included
    #: and this project last.
    sources: tuple = ()
    #: The problems in values other projects pass that still reach this
    #: project (Design 1.6), each naming its file by its whole path: `tcw
    #: validate` warns about them; a reader of the key stops on them.
    inherited_problems: list = field(default_factory=list)
    #: Values an ancestor's `tcw-config.local.yaml` may not set, never merged:
    #: `tcw validate` warns about them at that file (Design 1.6).
    inherited_refusals: list = field(default_factory=list)
    #: The sources not here, or whose parents could not be read, that left a
    #: key undecided (Design 3.6), in load order.
    gaps_withholding: tuple = ()
    #: Why the configuration sources could not be had, when they could not
    #: (plan choice 11): the message `tcw work list` stops with.
    order_error: str | None = None

    def require(self, key: str) -> None:
        """Raise the error of `key` (`work.tags`, `work.jira`) when it is
        withheld; return when it can be used."""
        held = self.withheld.get(key)
        if held is not None:
            raise held.error()

    @property
    def user_name(self) -> str | None:
        user = self.values.get("user")
        name = user.get("name") if isinstance(user, dict) else None
        return name if isinstance(name, str) and _good_name(name) else None

    def personal_files(self, key_path: KeyPath) -> list[Path]:
        """The personal files that set the chain list at `key_path`."""
        return [o.file for o in self.written.get(tuple(key_path), ())
                if o.personal and o.file is not None]

    def personal_variables(self, key_path: KeyPath) -> list[str]:
        """The override variables that set the chain list at `key_path`."""
        return [o.variable for o in self.written.get(tuple(key_path), ())
                if o.variable is not None]


class Withheld:
    """A configuration value that cannot be used (TCW-109 Design 3.4): an
    inherited key a missing parent may have set, or one whose inherited value
    has a problem. Holding it, passing it along and printing it are fine;
    using it raises the error it carries, a new one at each use: iterating
    it, `in`, `len`, a truth test, or reading an attribute. So `config.tags
    or ()` is not a safe test for it; `isinstance(value, Withheld)` is."""

    __slots__ = ("_make",)

    def __init__(self, make):
        self._make = make

    def error(self) -> Exception:
        return self._make()

    def _raise(self):
        raise self._make()

    def __iter__(self):
        self._raise()

    def __contains__(self, item):
        self._raise()

    def __len__(self):
        self._raise()

    def __bool__(self):
        self._raise()

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        self._raise()

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self

    def __repr__(self) -> str:
        return "Withheld(...)"


def user_config_path() -> Path | None:
    """The user-wide file: `$XDG_CONFIG_HOME/tcw/config.yaml` when that
    variable is an absolute path, else `~/.config/tcw/config.yaml`, or None
    when there is no home folder. A relative `XDG_CONFIG_HOME` is ignored, as
    the XDG base directory specification says."""
    xdg = os.environ.get("XDG_CONFIG_HOME", "")
    if xdg and os.path.isabs(xdg):
        return Path(xdg) / "tcw" / "config.yaml"
    try:
        home = Path.home()
    except (RuntimeError, KeyError, OSError):
        return None
    return home / ".config" / "tcw" / "config.yaml"


def user_config_label() -> str:
    """The user-wide file as a message names it."""
    path = user_config_path()
    return str(path) if path is not None else "~/.config/tcw/config.yaml"


def built_in_values() -> dict:
    """TCW's own defaults: the `built-in` layer. A stage whose table row has a
    prompt and every procedure get one built-in entry, `{builtin: true}`,
    which stands for TCW's packaged text. Empty lists are not written."""
    from tcw.store.base import PROCEDURE_IDS
    from tcw.work.config import DEFAULT_BACKEND, HookLimits
    from tcw.work.model import STAGES
    limits = HookLimits()
    return {"work": {
        "backend": DEFAULT_BACKEND,
        "hooks": {"timeout": limits.timeout, "output-cap": limits.output_cap},
        "stages": {s.name: {"prompt": [{"builtin": True}]} for s in STAGES if s.prompt},
        "procedures": {name: [{"builtin": True}] for name in PROCEDURE_IDS},
    }}


# ---------------------------------------------------------------------------
# Reading one file


def _read(path: Path, required: bool, root: Path) -> tuple[dict | None, list[Problem]]:
    """One file as a mapping, `{}` when it is absent and not required or
    empty, or None with a problem when it cannot be used at all."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        if required:
            return None, [Problem(path, (), "not found", root)]
        return {}, []
    except OSError as error:
        return None, [Problem(path, (), f"cannot be read: {error.strerror or error}",
                              root)]
    except UnicodeDecodeError as error:
        bad = error.object[error.start:error.start + 1].hex()
        return None, [Problem(path, (), f"is not valid UTF-8 text (byte 0x{bad} at "
                                        f"position {error.start})", root)]
    try:
        data = _load_named_yaml(text, path, UniqueKeyLoader)
    except yaml.YAMLError as error:
        one_line = " ".join(str(error).split())
        return None, [Problem(path, (), f"is not valid YAML: {one_line}", root)]
    if data is None:
        return {}, []
    if not isinstance(data, dict):
        return None, [Problem(path, (), f"must be a mapping, not a "
                                        f"{type(data).__name__}", root)]
    return data, []


def read_project_file(project_root: Path) -> tuple[dict | None, list[Problem]]:
    """The single read of one `.tcw/tcw-config.yaml`, refusing a duplicate key
    and a version this TCW cannot read, and nothing else: no layers, no
    allowlist, no parsing of `work:`. For readers that look only at the shared
    graph keys and must still answer for a graph that cannot be fully loaded."""
    root = Path(project_root)
    path = root / SENTINEL
    data, problems = _read(path, True, root)
    if data is not None:
        version = version_problem(data)
        if version:
            return None, [*problems, Problem(path, (), version, root)]
        data = without_version(data)
    return data, problems


def _file_problems(path: Path, data: dict, root: Path | None, *,
                   versioned: bool) -> tuple[dict | None, list[Problem]]:
    """The version (for a `tcw-*.yaml` file) and naming checks on one file read
    as `data` (TCW-106 Design 3.4 and 5), and the mapping to merge: without its
    `tcw-version`, or None when the version means it cannot be read."""
    if versioned:
        version = version_problem(data)
        if version:
            # No key path: the message names `tcw-version` itself, with the
            # file as its subject (Design 3.4's shapes). A file this TCW cannot
            # read is not checked against this version's naming rule: its keys
            # may follow an older or newer one, and the version is the problem.
            return None, [Problem(path, (), version, root)]
        data = without_version(data)
    return data, [Problem(path, tuple(key_path), message, root)
                  for key_path, message in key_problems(data)]


# ---------------------------------------------------------------------------
# Checks on one file, before it is merged


def _is_chain(key_path: KeyPath) -> bool:
    """A stage's `prompt`, `pre` or `post` list, or a procedure's list."""
    p = key_path
    return ((len(p) == 4 and p[:2] == ("work", "stages")
             and p[3] in ("prompt", "pre", "post"))
            or (len(p) == 3 and p[:2] == ("work", "procedures")))


def _takes_inherit(key_path: KeyPath) -> bool:
    """A list that takes an `inherit: true` entry: a chain list, or
    `work.tags`, where it stands for the tags merged before it, which
    includes what the project's parents pass (TCW-109 Design 2.4)."""
    return _is_chain(key_path) or tuple(key_path) == ("work", "tags")


def _inherited_key(key_path: KeyPath) -> bool:
    """A key of `INHERITED_KEYS`, or one under it."""
    return tuple(key_path[:2]) in (("work", "tags"), ("work", "jira"))


def _lists(mapping: dict, path: KeyPath = ()) -> Iterator[tuple[KeyPath, list]]:
    """Every list reachable through mappings, with its key path."""
    for key, value in mapping.items():
        here = (*path, key)
        if isinstance(value, dict):
            yield from _lists(value, here)
        elif isinstance(value, list):
            yield here, value


#: The three store locations' keys (TCW-110 Design 7.1).
STORE_COMPONENTS = ("taxonomy", "capabilities", "work")


def store_location_problem(key: str | None, value: Any, address: bool = True) -> str | None:
    """Design 7.1: why a store location in the shared file cannot be used, or
    None. An absolute path or one starting with `~` names a folder on one
    machine in a file every machine reads. `key` starts the message; None
    leaves it out, for a problem whose line already names the key. `address`
    False leaves out the tcw:// form, for `tcw init`, which refuses it."""
    if not isinstance(value, str) or value.startswith("tcw://"):
        return None
    if value.startswith("~") or Path(value).is_absolute():
        offer = (", or a tcw:// .path address such as tcw://<project>.path/<folder>"
                 if address else "")
        return (f"{key + ' ' if key else ''}must be a path relative to the project"
                f"{offer}; a folder that sits elsewhere on this machine is placed by "
                f"an entry in .tcw/tcw-manifest.local.yaml")
    return None


def _store_location_problems(mapping: dict, origin: Origin, root: Path) -> list[Problem]:
    problems = []
    for component in STORE_COMPONENTS:
        section = mapping.get(component)
        if not isinstance(section, dict):
            continue
        message = store_location_problem(None, section.get("path"))
        if message:
            problems.append(Problem(origin.file, (component, "path"), message, root))
    return problems


def _list_problems(mapping: dict, origin: Origin, root: Path) -> list[Problem]:
    """`builtin:` written in a file, the `inherit` entry's rules, and an entry
    repeated within one chain list (Design 3.4, 3.6, 3.8)."""
    from tcw.store.base import MIGRATION_GUIDE
    problems = []

    def add(path: KeyPath, message: str) -> None:
        problems.append(Problem(origin.file, path, message, root))

    for path, entries in _lists(mapping):
        if path == ("parents",):
            # A parent's `inherit` names the axes it passes; the registry
            # checks that list (TCW-108 Design 1).
            continue
        chain = _is_chain(path)
        takes = _takes_inherit(path)
        inherits = 0
        seen: list = []
        for i, entry in enumerate(entries):
            here = (*path, i)
            if isinstance(entry, dict) and "builtin" in entry:
                add(here, f"'builtin' is not written in a file; write "
                          f"'inherit: true' to include the list the layer below "
                          f"resolved (in .tcw/tcw-config.yaml, TCW's own text). See "
                          f"{MIGRATION_GUIDE}")
                continue
            if isinstance(entry, dict) and "inherit" in entry:
                if not takes:
                    add(here, "'inherit' is allowed only in work.tags, a stage's "
                              "prompt, pre or post list, or a procedure's list")
                elif entry["inherit"] is not True:
                    add(here, "'inherit' takes only the value true; to replace "
                              "the list below, leave the entry out")
                elif len(entry) > 1:
                    add(here, "an 'inherit' entry stands alone; 'when' and other "
                              "keys are not allowed beside it")
                else:
                    inherits += 1
                    if inherits == 2:
                        add(here, "a list may hold one 'inherit' entry")
                continue
            if chain:
                if entry in seen:
                    add(here, f"repeats entry {seen.index(entry)} of this list")
                else:
                    seen.append(entry)
    return problems


def _good_name(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def _matches(path: KeyPath, pattern: tuple) -> bool:
    return len(path) == len(pattern) and all(
        want == "*" or want == got for want, got in zip(pattern, path))


def _leads_to_allowed(path: KeyPath) -> bool:
    return any(len(pattern) > len(path) and _matches(path, pattern[:len(path)])
               for pattern in _PATTERNS)


def _allowed(mapping: dict, origin: Origin, root: Path | None, refused: list,
             path: KeyPath = (), *, variable: str | None = None
             ) -> tuple[dict, list[Problem]]:
    """The part of a personal file the allowlist lets it set, and a problem
    for everything else (Design 4.4, 4.5, 3.10). A refused value is recorded in
    `refused` and not merged. With `variable`, the same walk speaks for an
    override variable of that name (TCW-109 Design 4.5): each problem has no
    file, and its message starts with the name and its key."""
    problems: list[Problem] = []
    kept: dict = {}

    def problem(here: KeyPath, message: str) -> None:
        if variable is None:
            problems.append(Problem(origin.file, here, message, root))
        else:
            problems.append(Problem(None, (), f"{variable}: {dotted(here)}: {message}",
                                    root))

    def shared(here: KeyPath, value: Any, message: str) -> None:
        if variable is not None:
            problems.append(Problem(None, (), f"{variable}: {dotted(here)} is a shared "
                                              f"key; an environment variable cannot "
                                              f"set it", root))
        else:
            problems.append(Problem(origin.file, here, message, root))
        refused.append(Setting(origin.file, here, value, "shared key", variable))

    null = ("null has no meaning in an environment variable; unset it instead"
            if variable is not None
            else "null has no meaning in a personal file; remove the key instead")
    for key, value in mapping.items():
        here = (*path, key)
        if not path and key in LOCAL_ONLY_KEYS:
            if variable is not None or origin.layer != "local":
                shared(here, value, f"{key} may be listed only in this project's own "
                       f"files, .tcw/tcw-config.yaml or .tcw/tcw-config.local.yaml; the "
                       f"user-wide file applies to every project")
            elif value is None:
                problem(here, null)
            else:
                kept[key] = value
            continue
        if value is None and (any(_matches(here, p) for p in _PATTERNS)
                              or _leads_to_allowed(here) or _inherited_key(here)):
            # At an inherited key `null` removes a parent's value in the shared
            # file (TCW-109 Design 2.5); a personal layer cannot do that.
            problem(here, null)
        elif any(_matches(here, pattern) for pattern in _PATTERNS):
            if here == ("user", "name") and not _good_name(value):
                problem(here, "must be a name: a non-blank string with no space at "
                              "either end, matched exactly")
                continue
            kept[key] = value
        elif _leads_to_allowed(here):
            if not isinstance(value, dict):
                problem(here, "must be a mapping")
                continue
            inner, found = _allowed(value, origin, root, refused, here,
                                    variable=variable)
            problems += found
            if inner:
                kept[key] = inner
        else:
            message = ("'user' takes only 'name'" if here[0] == "user" else
                       "a shared key; a personal file cannot set it")
            # Each value named by its whole key path, as it was written.
            for leaf, leaf_value in _leaves(here, value):
                shared(leaf, leaf_value, message)
    return kept, problems


def _leaves(path: KeyPath, value: Any) -> Iterator[tuple[KeyPath, Any]]:
    """Every value under `path` that is not a non-empty mapping."""
    if isinstance(value, dict) and value:
        for key, inner in value.items():
            yield from _leaves((*path, key), inner)
    else:
        yield path, value


def _without_credentials(mapping: dict, origin: Origin,
                         skipped: list) -> dict:
    """A personal file's Jira credential names, set aside in a project that is
    not in Jira mode (Design 4.6)."""
    work = mapping.get("work")
    jira = work.get("jira") if isinstance(work, dict) else None
    credentials = jira.get("credentials") if isinstance(jira, dict) else None
    if not isinstance(credentials, dict):
        return mapping
    for key, value in credentials.items():
        skipped.append(Setting(origin.file, (*_CREDENTIALS, key), value,
                               "Jira credential names apply only in a Jira-mode "
                               "project", origin.variable))
    mapping = copy.deepcopy(mapping)
    del mapping["work"]["jira"]["credentials"]
    if not mapping["work"]["jira"]:
        del mapping["work"]["jira"]
    if not mapping["work"]:
        del mapping["work"]
    return mapping


# ---------------------------------------------------------------------------
# Merging


def _clear(origins: dict, path: KeyPath) -> None:
    for key in [k for k in origins if k[:len(path)] == path]:
        del origins[key]


def _stamp(origins: dict, path: KeyPath, value: Any, origin: Origin) -> None:
    """Record `origin` for every scalar, list and list entry at or under
    `path`. A mapping is recorded through its contents, and an empty one,
    which has none, at its own key."""
    if isinstance(value, dict):
        if not value and path:
            origins[path] = origin
        for key, inner in value.items():
            _stamp(origins, (*path, key), inner, origin)
        return
    origins[path] = origin
    if isinstance(value, list):
        for i in range(len(value)):
            origins[(*path, i)] = origin


def _chain(below: Any, below_origins: list, value: list,
           origin: Origin) -> tuple[list, list]:
    """A chain list as a layer sets it: its own entries, with the list the
    layer below resolved in place of its `inherit` entry."""
    if not isinstance(below, list):
        below, below_origins = [], []
    out: list = []
    origins: list = []
    inherited = False
    for entry in value:
        if isinstance(entry, dict) and "inherit" in entry:
            if entry.get("inherit") is True and not inherited:
                out += copy.deepcopy(below)
                origins += below_origins
                inherited = True
            continue
        out.append(copy.deepcopy(entry))
        origins.append(origin)
    return out, origins


def _merge(values: dict, origins: dict, written: dict, layer: dict,
           origin: Origin, path: KeyPath = ()) -> None:
    for key, value in layer.items():
        here = (*path, key)
        lower = values.get(key)
        if here == ("children",) and origin.layer == "local" and isinstance(value, list):
            # The personal children follow the committed ones, each once,
            # each entry keeping the file it came from (TCW-108 Design 2.1).
            below = lower if isinstance(lower, list) else []
            added = [entry for entry in value if entry not in below]
            values[key] = [*below, *added]
            for i in range(len(below), len(below) + len(added)):
                origins[(*here, i)] = origin
            if not below:
                origins[here] = origin
        elif _takes_inherit(here) and isinstance(value, list):
            below = lower if isinstance(lower, list) else []
            below_origins = [origins.get((*here, i), origin) for i in range(len(below))]
            entries, entry_origins = _chain(below, below_origins, value, origin)
            _clear(origins, here)
            values[key] = entries
            origins[here] = origin
            for i, entry_origin in enumerate(entry_origins):
                origins[(*here, i)] = entry_origin
            if _is_chain(here):
                written.setdefault(here, []).append(origin)
        elif value is None and origin.layer == "project" and _inherited_key(here):
            # `null` removes an inherited value: the key has none from any
            # project before this one, nor a built-in one (TCW-109 Design 2.5).
            _clear(origins, here)
            values.pop(key, None)
        elif isinstance(value, dict) and isinstance(lower, dict):
            if value:
                # An empty mapping below no longer speaks for this key.
                origins.pop(here, None)
            elif not lower:
                # Both layers write an empty mapping: the higher one speaks.
                origins[here] = origin
            _merge(lower, origins, written, value, origin, here)
        elif value is None and origin.layer == "project" and isinstance(lower, dict):
            # `work:` with nothing under it means "no settings", which is
            # the defaults, not "none of TCW's own text" (plan choice 6).
            continue
        elif isinstance(value, dict):
            # A mapping no lower layer holds is merged into an empty one, so
            # a chain list inside it still has its `inherit` entry resolved
            # (to nothing, Design 3.2) and is recorded as written.
            _clear(origins, here)
            values[key] = {}
            _merge(values[key], origins, written, value, origin, here)
            if not value:
                origins[here] = origin
        else:
            _clear(origins, here)
            values[key] = copy.deepcopy(value)
            _stamp(origins, here, value, origin)
            if _is_chain(here):
                written.setdefault(here, []).append(origin)


# ---------------------------------------------------------------------------
# After merging


def _confinement(values: dict, origins: dict, root: Path) -> list[Problem]:
    """A `file:` binding that leaves its declaring file's folder (Design 6.1),
    symlinks followed. Whether the file exists is checked when the prompt is
    composed."""
    problems = []
    for path, entries in _lists(values):
        if not _is_chain(path):
            continue
        for i, entry in enumerate(entries):
            if not isinstance(entry, dict) or not isinstance(entry.get("file"), str):
                continue
            origin = origins.get((*path, i))
            if origin is None or origin.folder is None:
                continue
            folder = origin.folder.resolve()
            target = (folder / entry["file"].strip()).resolve()
            if target != folder and folder not in target.parents:
                if origin.variable is not None:
                    # A variable's binding is read from the root of the
                    # project it names (TCW-109 Design 4.8).
                    problems.append(Problem(
                        None, (), f"{origin.variable}: {dotted((*path, i))}: file "
                                  f"'{entry['file']}' resolves outside {origin.folder}, "
                                  f"the root of the project it names", root))
                    continue
                problems.append(Problem(
                    origin.file, (*path, i),
                    f"file '{entry['file']}' resolves outside {origin.folder}, the "
                    f"folder of the file that declares it", root))
    return problems


def _origin_for(key_path: KeyPath, origins: dict, project: Origin) -> Origin:
    """Which layer a parser problem is blamed on (Design 5.2): the key path's
    own origin; else its longest prefix that has one; else, for a mapping,
    the highest layer that wrote anything under it; else `tcw-config.yaml`."""
    path = tuple(key_path)
    for end in range(len(path), 0, -1):
        if path[:end] in origins:
            return origins[path[:end]]
    under = [o for k, o in origins.items()
             if k[:len(path)] == path and o.layer != "built-in"]
    if under:
        return max(under, key=lambda o: o.rank)
    return project


def load_config(project_root: Path, *, personal: bool = True,
                registry=None) -> Config:
    """The effective configuration of the project at `project_root`, folded
    over its configuration sources (TCW-109 Design 2.1): the built-in values,
    then for each source, farthest first and this project last, its shared
    file and, when personal files apply, the user-wide file and its
    `tcw-config.local.yaml`. From a source other than this project only the
    inherited keys are taken (`INHERITED_KEYS`). Never raises for a problem in
    the configuration; every problem of this project's own is in `problems`.
    A key it inherits that cannot be used, because a source is not here or
    passes a value with a problem, is in `withheld` (Design 3.4, 1.6).

    `personal=False` is how a project is read for itself rather than as the
    project a command acts on (a descendant, the project of an item named by
    its full identifier, a delegation target): its own sources' shared files,
    with no personal file, since personal files apply only to the project a
    command acts on. `registry` is the command's, through which the sources
    are found (Design 5.2); it is required when such a project declares
    `parents:`, and `TypeError` is raised without it. For the project a
    command acts on, one is opened at `project_root` when none is passed, and
    only when the project declares `parents:`.
    """
    from tcw.work.config import parse_work_config
    root = Path(project_root).absolute()
    # The acting project's files are named relative to it; another project's
    # by their whole path, so a message says which project to fix.
    shown = root if personal else None
    values = built_in_values()
    origins: dict = {}
    _stamp(origins, (), values, BUILT_IN)
    written: dict = {}
    for path, _ in _lists(values):
        if _is_chain(path):
            written[path] = [BUILT_IN]
    config = Config(root, values, origins, None, written=written)

    shared = root / SENTINEL
    raw, problems = _read(shared, True, shown)
    config.problems += problems
    if raw is not None:
        raw, problems = _file_problems(shared, raw, shown, versioned=True)
        config.problems += problems
    if raw is None:
        config.unreadable = True
        config.work, _ = parse_work_config(values.get("work"), origins)
        return config
    own_id = raw.get("id") if isinstance(raw.get("id"), str) else None
    work = raw.get("work")
    # The project's mode is its own (Design 1.2): it decides whether a
    # parent's `work.jira` is taken (1.5) and whether credential names are
    # set aside.
    jira_mode = isinstance(work, dict) and work.get("backend") == "jira"
    if "parents" in raw:
        if registry is None and not personal:
            raise TypeError("load_config(personal=False) needs the command's registry "
                            "for a project that declares parents:")
        entries, opened, own_id, config.order_error = _sources(
            raw, root, personal, registry, own_id)
    else:
        entries, opened = None, None
    if entries is None:
        entries = [_SELF]
    config.sources = tuple(own_id if e is _SELF else e.id for e in entries)
    here = len(entries) - 1

    config.problems += _list_problems(raw, Origin("project", shared), shown)
    config.problems += _store_location_problems(raw, Origin("project", shared), shown)
    if "user" in raw:
        config.problems.append(Problem(
            shared, ("user",),
            f"'user' is personal; set it in {user_config_label()} or "
            f"{LOCAL_FILE}", shown))
        raw = {k: v for k, v in raw.items() if k != "user"}

    # The user-wide file is read and checked once, as this project's own
    # layer, and applied again at each source, cut to the inherited keys,
    # with no second check (Design 1.6, 2.1).
    layers = _personal_layers(root, config.problems) if personal else []
    user = next((o for o in layers if o.layer == "user"), None)
    user_kept, user_problems = ({}, [])
    if user is not None:
        user_kept, user_problems = _user_layer(user, root, config, jira_mode)

    # A variable's problem is the active project's, reported once; a project
    # read for itself takes only the variables that passed (Design 4.4,
    # plan choice 13).
    overrides, override_problems = _command_overrides()
    if personal:
        config.problems += override_problems

    fold = _Fold(values, origins, written, jira_mode)
    for position, entry in enumerate(entries):
        if position == here:
            project = Origin("project", shared, project=own_id, position=position)
            fold.merge(raw, project)
            for origin in layers:
                origin = Origin(origin.layer, origin.file, root=origin.root,
                                project=own_id, position=position)
                if origin.layer == "user":
                    config.problems += user_problems
                    mapping = user_kept
                else:
                    mapping = _personal_layer(origin, root, config, jira_mode)
                if mapping:
                    fold.merge(mapping, origin)
            for override in overrides.get(own_id, ()):
                origin = Origin("environment", variable=override.name, project=own_id,
                                position=position, root=root)
                mapping = override.mapping
                if not jira_mode:
                    mapping = _without_credentials(mapping, origin, config.skipped)
                if mapping:
                    fold.merge(mapping, origin)
        elif entry.state == "here":
            fold.ancestor(entry, position, user if user_kept else None, user_kept,
                          layers, config)
            q_root = Path(entry.project.locator)
            for override in overrides.get(entry.id, ()):
                part = _inherited_part(override.mapping, jira_mode)
                if part:
                    fold.merge(part, Origin("environment", variable=override.name,
                                            project=entry.id, position=position,
                                            root=q_root))
        else:
            fold.gaps.append((position, entry))

    config.problems += _confinement(values, origins, shown)
    work, parsed = parse_work_config(values.get("work"), origins)
    config.work = work
    if work.backend == "jira":
        from tcw.work.jira.config import parse_jira_config
        config.jira, jira_problems = parse_jira_config(work.jira)
        parsed = [*parsed, *jira_problems]
    project = Origin("project", shared, project=own_id, position=here)
    undecided = fold.undecided(here, config.order_error is not None)
    for problem in parsed:
        key_path = tuple(problem.key_path)
        if any(key_path[:len(u)] == u for u in undecided):
            # No check of a value that is not known runs (Design 3.2).
            continue
        origin = _origin_for(key_path, origins, project)
        if origin.project not in (None, own_id) and origin.layer != "user":
            fold.broke(key_path, origin, Problem(origin.file, key_path, problem.message))
            continue
        config.problems.append(Problem(origin.file, key_path, problem.message, shown))
    _withhold(config, fold, undecided, opened, own_id)
    return config


#: The project being folded, in a fold with no other source.
_SELF = object()


def _sources(raw: dict, root: Path, personal: bool, registry, own_id):
    """This project's configuration sources (Design 1.3), as
    `(entries, registry, id, order_error)`. `entries` is None when the order
    cannot be had (plan choice 11): this project's own `parents:` is refused,
    its ancestors form a loop, the registry raises, or it lists this project
    as unreadable. `order_error` is then the text `tcw work list` stops with
    in the same project: the registry's graph problems as `require_valid`
    joins them, else the error raised, else the loop."""
    from tcw.errors import InheritedUnavailable, TcwError
    from tcw.store.base import find_loop, loop_message
    from tcw.store.links import parse_parents
    from tcw.store.project import FsProjectRegistry
    links, _ = parse_parents(raw.get("parents"), str(root / SENTINEL))
    opened = registry
    caught = None
    try:
        if opened is None:
            opened = FsProjectRegistry.open(root)
        if personal:
            own_id = opened.current.id
        if links is not None:
            # A loop through the ancestors, looked for whether or not the
            # order computation would raise for it.
            seen: dict = {}
            pending = [own_id]
            entries = (opened.source_entries("config") if personal else
                       opened.source_entries("config", own_id, root=root))
            while pending:
                pid = pending.pop()
                if pid in seen:
                    continue
                seen[pid] = opened.parents(pid)
                pending += [link.id for link in seen[pid]]
            loop = find_loop(seen, [own_id])
            if loop is not None:
                caught = loop_message(loop)
            elif entries and entries[-1].state != "here":
                caught = opened.link_problem(entries[-1].id) or "its parents could not be read"
            else:
                return entries, opened, own_id, None
    except InheritedUnavailable:
        raise
    except (ValueError, TcwError) as error:
        caught = str(error)
    text = None
    if personal and opened is not None:
        try:
            opened.require_valid()
        except ValueError as error:
            text = str(error)
    if text is None and caught is None and links is None:
        # A refused `parents:` the registry did not record (a project read
        # for itself): its own reading of the key.
        _, found = parse_parents(raw.get("parents"), str(root / SENTINEL))
        caught = "; ".join(f"{root / SENTINEL}: {key}: {message}" for key, message in found)
    return None, opened, own_id, text or caught or "its parents could not be read"


def _user_layer(user: Origin, root: Path, config: Config, jira_mode: bool):
    """The user-wide file, read and checked once: what it may set, and its
    problems, which are this project's own."""
    problems: list = []
    mapping, found = _read(user.file, False, root)
    problems += found
    if mapping is not None and user.file.exists():
        mapping, found = _file_problems(user.file, mapping, root, versioned=False)
        problems += found
    if not mapping:
        return {}, problems
    mapping, found = _allowed(mapping, user, root, config.refused)
    problems += found
    problems += _list_problems(mapping, user, root)
    if not jira_mode:
        mapping = _without_credentials(mapping, user, config.skipped)
    return mapping, problems


def _personal_layer(origin: Origin, root: Path, config: Config, jira_mode: bool) -> dict:
    """This project's own `tcw-config.local.yaml`, checked as today."""
    mapping, problems = _read(origin.file, False, root)
    config.problems += problems
    if mapping is not None and origin.file.exists():
        mapping, problems = _file_problems(origin.file, mapping, root, versioned=True)
        config.problems += problems
    if not mapping:
        return {}
    mapping, problems = _allowed(mapping, origin, root, config.refused)
    config.problems += problems
    config.problems += _list_problems(mapping, origin, root)
    if not jira_mode:
        mapping = _without_credentials(mapping, origin, config.skipped)
    return mapping


def _inherited_part(mapping: Any, jira_mode: bool) -> dict:
    """What a layer of another project passes (Design 1.1, 1.5): its
    `work.tags`, and its `work.jira` when the project folded is in Jira mode."""
    work = mapping.get("work") if isinstance(mapping, dict) else None
    if not isinstance(work, dict):
        return {}
    keys = ("tags", "jira") if jira_mode else ("tags",)
    part = {key: copy.deepcopy(work[key]) for key in keys if key in work}
    return {"work": part} if part else {}


def _replacements(mapping: dict) -> list[KeyPath]:
    """The keys of Design 1.1 a layer replaces whole (Design 3.1): a value
    that is not a mapping, other than a list holding an `inherit: true`
    entry; or `null`."""
    work = mapping.get("work") if isinstance(mapping, dict) else None
    if not isinstance(work, dict):
        return []
    found: list[KeyPath] = []
    if "tags" in work:
        tags = work["tags"]
        if not (isinstance(tags, list) and any(
                isinstance(e, dict) and e.get("inherit") is True for e in tags)):
            found.append(("work", "tags"))

    def walk(value: Any, path: KeyPath) -> None:
        if isinstance(value, dict):
            for key, inner in value.items():
                walk(inner, (*path, key))
        else:
            found.append(path)
    if "jira" in work:
        walk(work["jira"], ("work", "jira"))
    return found


def _broken_key(key_path: KeyPath) -> KeyPath:
    """Where a problem marks an inherited value broken: the longest start of
    its key path that is a key TCW knows under `work.tags` or `work.jira`."""
    from tcw.config_keys import known_keys
    table = known_keys()
    path = tuple(key_path)
    for end in range(len(path), 1, -1):
        if path[:end] in table and _inherited_key(path[:end]):
            return path[:end]
    return ("work", "jira") if path[:2] == ("work", "jira") else ("work", "tags")


class _Fold:
    """The merge of the sources, with what Design 3.1 and 1.6 need from it:
    each key a layer replaces whole, with its rank; each gap, with its
    position; and each problem in another project's inherited value."""

    def __init__(self, values: dict, origins: dict, written: dict, jira_mode: bool):
        self.values, self.origins, self.written = values, origins, written
        self.jira_mode = jira_mode
        self.replaced: list[tuple[tuple, KeyPath]] = []
        self.gaps: list[tuple[int, Any]] = []
        self.broken: list[tuple[KeyPath, tuple, Problem]] = []

    def merge(self, mapping: dict, origin: Origin) -> None:
        for path in _replacements(mapping):
            self.replaced.append((origin.rank, path))
        _merge(self.values, self.origins, self.written, mapping, origin)

    def broke(self, key_path: KeyPath, origin: Origin, problem: Problem) -> None:
        self.broken.append((_broken_key(key_path), origin.rank, problem))

    def ancestor(self, entry, position: int, user: Origin | None, user_kept: dict,
                 layers: list, config: Config) -> None:
        """One source other than the project folded: its shared file, then
        the user-wide file and its local file, each cut to what it passes and
        checked as the project's own are (Design 1.6)."""
        from tcw.project_files import key_problems
        from tcw.store.project import personal_file
        q_root = Path(entry.project.locator)
        shared = Origin("project", q_root / SENTINEL, project=entry.id,
                        position=position)
        mapping, problems = _read(shared.file, True, None)
        if mapping is not None:
            version = version_problem(mapping)
            if version:
                mapping, problems = None, [Problem(shared.file, (), version)]
            else:
                mapping = without_version(mapping)
        if mapping is None:
            for problem in problems:
                for key in (("work", "tags"), ("work", "jira")):
                    self.broken.append((key, shared.rank, problem))
            return
        self._layer(_inherited_part(mapping, self.jira_mode), shared, key_problems)
        if not layers:
            return
        if user is not None and user_kept:
            part = _inherited_part(user_kept, self.jira_mode)
            if part:
                self.merge(part, Origin("user", user.file, project=entry.id,
                                        position=position))
        local_file = personal_file(q_root, LOCAL_CONFIG_NAME)
        local = Origin("local", local_file, project=entry.id, position=position,
                       root=q_root if local_file != q_root / LOCAL_FILE else None)
        mapping, problems = _read(local.file, False, None)
        if mapping is not None and local.file.exists():
            mapping, problems = _file_problems(local.file, mapping, None, versioned=True)
            mapping = mapping if mapping is None else _inherited_part(mapping,
                                                                      self.jira_mode)
            problems = [p for p in problems if _inherited_key(p.key_path)] \
                if mapping is not None else problems
        for problem in problems:
            if mapping is None or not problem.key_path:
                if self.jira_mode:
                    self.broken.append((("work", "jira"), local.rank, problem))
            else:
                self.broken.append((_broken_key(problem.key_path), local.rank, problem))
        if not mapping:
            return
        refused: list = []
        mapping, problems = _allowed(mapping, local, None, refused)
        # A refused value is never merged, so it breaks nothing; `tcw
        # validate` warns about it at that file (Design 1.6).
        config.inherited_refusals += problems
        self._layer(mapping, local, None)

    def _layer(self, mapping: dict, origin: Origin, key_problems) -> None:
        if not mapping:
            return
        problems = []
        if key_problems is not None:
            problems += [Problem(origin.file, tuple(path), message)
                         for path, message in key_problems(mapping)]
        problems += [Problem(p.file, p.key_path, p.message)
                     for p in _list_problems(mapping, origin, None)]
        for problem in problems:
            self.broken.append((_broken_key(problem.key_path), origin.rank, problem))
        self.merge(mapping, origin)

    def _decided_after(self, path: KeyPath, rank: tuple) -> bool:
        return any(r > rank and path[:len(p)] == p for r, p in self.replaced)

    def undecided(self, here: int, no_order: bool) -> set:
        """Every key of Design 1.1 that no layer after the last gap replaces
        whole, or, when the order could not be had, that this project's own
        layers do not (plan choices 4, 11)."""
        from tcw.config_keys import jira_keys
        if not self.gaps and not no_order:
            return set()
        last = (here - 1, len(LAYERS)) if no_order else (max(p for p, _ in self.gaps),
                                                          len(LAYERS))
        candidates = [("work", "tags")]
        if self.jira_mode:
            candidates += list(jira_keys())
        return {path for path in candidates if not self._decided_after(path, last)}

    def gap_for(self, path: KeyPath):
        """The gap Design 3.3 names for `path`: the first after the last layer
        that replaced it whole, or the first."""
        ranks = [r for r, p in self.replaced if path[:len(p)] == p]
        after = max(ranks) if ranks else (-2, 0)
        return next(((pos, e) for pos, e in self.gaps if (pos, len(LAYERS)) > after),
                    self.gaps[0])

    def standing(self) -> dict:
        """The broken marks no later layer replaced, by inherited key."""
        out: dict = {}
        for path, rank, problem in self.broken:
            if self._decided_after(path, rank):
                continue
            key = "work.tags" if path[:2] == ("work", "tags") else "work.jira"
            if key == "work.jira" and not self.jira_mode:
                continue
            out.setdefault(key, []).append(problem)
        return out


def _withhold(config: Config, fold: _Fold, undecided: set, registry, own_id) -> None:
    """Set `Config.withheld` (Design 3.4): an undecided key with Design 3.3's
    error, or, when the order could not be had, the graph problem's; a broken
    key, not also undecided, with its problems (Design 1.6)."""
    import dataclasses

    from tcw.errors import BackendError, ConfigError
    for key in INHERITED_KEYS:
        path = tuple(key.split("."))
        under = sorted((u for u in undecided if u[:len(path)] == path), key=len)
        if under:
            if config.order_error is not None:
                text = config.order_error
                config.withheld[key] = Withheld(lambda text=text: BackendError(text))
                continue
            found = [fold.gap_for(u) for u in under]
            position, gap = min(found, key=lambda pair: pair[0])
            for gap_position, gap_entry in fold.gaps:
                if gap_position >= position and gap_entry.id not in config.gaps_withholding:
                    config.gaps_withholding += (gap_entry.id,)
            config.withheld[key] = Withheld(
                lambda gap=gap, key=key: registry.unavailable(
                    own_id, gap.id, "config", subject=f"configuration ({key})",
                    missing=gap.state == "missing"))
    broken = fold.standing()
    for key, problems in broken.items():
        config.inherited_problems += problems
        if key not in config.withheld:
            config.withheld[key] = Withheld(lambda problems=problems: ConfigError(problems))
    if "work.tags" in config.withheld:
        config.work = dataclasses.replace(config.work, tags=config.withheld["work.tags"])
    if "work.jira" in config.withheld and config.work.backend == "jira":
        config.jira = config.withheld["work.jira"]


# ---------------------------------------------------------------------------
# Once per command

#: The acting project's configuration, kept while one command runs so it is
#: read and checked once (Design 2.3). None outside a command: a library
#: caller, such as a test, always reads the files afresh.
_EFFECTIVE: dict | None = None
#: The override variables, read and checked once while a command runs
#: (TCW-109 plan choice 9), so each problem is reported once.
_OVERRIDES: tuple | None = None


def _command_overrides() -> tuple[dict, list]:
    """The override variables of this process (TCW-109 Design 4): those that
    passed every check, by the project they name, and the problems of the
    others. None of either when `TCW_NO_PERSONAL_CONFIG` is set to anything
    (Design 5.3): they are then neither read nor checked."""
    global _OVERRIDES
    if personal_files_skipped():
        return {}, []
    if _EFFECTIVE is None:
        from tcw.config_keys import read_overrides
        return read_overrides(os.environ)
    if _OVERRIDES is None:
        from tcw.config_keys import read_overrides
        _OVERRIDES = read_overrides(os.environ)
    return _OVERRIDES


def begin_command() -> None:
    """Start one command: the configuration, and the project registry
    (TCW-107 Design 2.13), are each read once until `end_command`. The
    registry is dropped after the command writes a configuration or a
    manifest; this configuration cache is still not, as in 3.x."""
    global _EFFECTIVE, _OVERRIDES
    _EFFECTIVE = {}
    _OVERRIDES = None
    from tcw.store import project
    project.begin_command()


def end_command() -> None:
    global _EFFECTIVE, _OVERRIDES
    _EFFECTIVE = None
    _OVERRIDES = None
    from tcw.store import project
    project.end_command()


def effective(project_root: Path, registry=None) -> Config:
    """The configuration of the project a command acts on, personal layers
    included, read once per command. `registry`, the project's own, is used
    by the call that reads it."""
    if _EFFECTIVE is None:
        return load_config(project_root, registry=registry)
    key = Path(project_root).resolve()
    if key not in _EFFECTIVE:
        _EFFECTIVE[key] = load_config(project_root, registry=registry)
    return _EFFECTIVE[key]


def _personal_layers(root: Path, problems: list) -> list[Origin]:
    """The personal layers to read, or none when `TCW_NO_PERSONAL_CONFIG=1`.
    Any value but `1` or empty is a problem, so `=true` cannot silently do
    nothing; the files are then not read."""
    if personal_files_skipped():
        flag = os.environ.get(SKIP_VARIABLE, "")
        if flag != "1":
            problems.append(Problem(None, (), f"{SKIP_VARIABLE} must be 1, to skip "
                                              f"personal configuration, or unset; got "
                                              f"{flag!r}", root))
        return []
    layers = []
    user = user_config_path()
    if user is not None:
        layers.append(Origin("user", user))
    # `.tcw/tcw-config.local.yaml`, or a linked worktree's main checkout's
    # when the worktree has none of its own (TCW-107 Design 4.2).
    from tcw.store.project import personal_file
    local = personal_file(root, LOCAL_CONFIG_NAME)
    layers.append(Origin("local", local,
                         root=Path(root) if local != Path(root) / LOCAL_FILE else None))
    return layers
