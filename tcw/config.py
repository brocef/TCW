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

from tcw.project_files import (LOCAL_SENTINEL as LOCAL_FILE, SENTINEL,
                               SKIP_VARIABLE, key_problems, personal_files_skipped,
                               root_of, version_problem, without_version)

#: The key paths a personal file may set; `*` stands for exactly one key.
#: Anything not listed is shared, including any key TCW adds later unless it
#: is added here. `user.name` may be set only in a personal file.
PERSONAL_KEYS = (
    "user.name",
    "work.stages.*.prompt",
    "work.stages.*.post",
    "work.procedures.*",
    "work.jira.credentials.email-env",
    "work.jira.credentials.token-env",
)

LAYERS = ("built-in", "project", "user", "local")
PERSONAL_LAYERS = ("user", "local")

_PATTERNS = tuple(tuple(path.split(".")) for path in PERSONAL_KEYS)
_CREDENTIALS = ("work", "jira", "credentials")

KeyPath = tuple  # of str keys and int list indexes


@dataclass(frozen=True)
class Origin:
    """The layer a value came from, and the file that layer was read from
    (none for `built-in`)."""

    layer: str
    file: Path | None = None

    @property
    def folder(self) -> Path | None:
        """The folder a `file:` binding is read from and `TCW_CONFIG_DIR`
        names: the declaring file's folder, except that a file in a project's
        `.tcw/` folder is read as though it sat at the project root (TCW-106
        Design 1.4)."""
        if self.file is None:
            return None
        if self.layer in ("project", "local"):
            return root_of(self.file)
        return self.file.parent

    @property
    def personal(self) -> bool:
        return self.layer in PERSONAL_LAYERS

    @property
    def rank(self) -> int:
        return LAYERS.index(self.layer)

    def __str__(self) -> str:
        if self.file is None or self.layer == "project":
            return self.layer
        return f"{self.layer}: {self.file}"


BUILT_IN = Origin("built-in")


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
    """A personal value that was read but not applied, and why."""

    file: Path | None
    key_path: KeyPath
    value: Any
    reason: str


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

    @property
    def user_name(self) -> str | None:
        user = self.values.get("user")
        name = user.get("name") if isinstance(user, dict) else None
        return name if isinstance(name, str) and _good_name(name) else None

    def personal_files(self, key_path: KeyPath) -> list[Path]:
        """The personal files that set the chain list at `key_path`."""
        return [o.file for o in self.written.get(tuple(key_path), ())
                if o.personal and o.file is not None]


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


def _lists(mapping: dict, path: KeyPath = ()) -> Iterator[tuple[KeyPath, list]]:
    """Every list reachable through mappings, with its key path."""
    for key, value in mapping.items():
        here = (*path, key)
        if isinstance(value, dict):
            yield from _lists(value, here)
        elif isinstance(value, list):
            yield here, value


def _list_problems(mapping: dict, origin: Origin, root: Path) -> list[Problem]:
    """`builtin:` written in a file, the `inherit` entry's rules, and an entry
    repeated within one chain list (Design 3.4, 3.6, 3.8)."""
    from tcw.store.base import MIGRATION_GUIDE
    problems = []

    def add(path: KeyPath, message: str) -> None:
        problems.append(Problem(origin.file, path, message, root))

    for path, entries in _lists(mapping):
        chain = _is_chain(path)
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
                if not chain:
                    add(here, "'inherit' is allowed only in a stage's prompt, pre "
                              "or post list or in a procedure's list")
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


def _allowed(mapping: dict, origin: Origin, root: Path, refused: list,
             path: KeyPath = ()) -> tuple[dict, list[Problem]]:
    """The part of a personal file the allowlist lets it set, and a problem
    for everything else (Design 4.4, 4.5, 3.10). A refused value is recorded in
    `refused` and not merged."""
    problems: list[Problem] = []
    kept: dict = {}
    for key, value in mapping.items():
        here = (*path, key)
        if value is None and (any(_matches(here, p) for p in _PATTERNS)
                              or _leads_to_allowed(here)):
            problems.append(Problem(origin.file, here, "null has no meaning in a "
                                    "personal file; remove the key instead", root))
        elif any(_matches(here, pattern) for pattern in _PATTERNS):
            if here == ("user", "name") and not _good_name(value):
                problems.append(Problem(origin.file, here, "must be a name: a "
                                        "non-blank string with no space at either "
                                        "end, matched exactly", root))
                continue
            kept[key] = value
        elif _leads_to_allowed(here):
            if not isinstance(value, dict):
                problems.append(Problem(origin.file, here, "must be a mapping",
                                        root))
                continue
            inner, found = _allowed(value, origin, root, refused, here)
            problems += found
            if inner:
                kept[key] = inner
        else:
            message = ("'user' takes only 'name'" if here[0] == "user" else
                       "a shared key; a personal file cannot set it")
            # Each value named by its whole key path, as it was written.
            for leaf, leaf_value in _leaves(here, value):
                problems.append(Problem(origin.file, leaf, message, root))
                refused.append(Setting(origin.file, leaf, leaf_value, "shared key"))
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
                               "project"))
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
        if _is_chain(here) and isinstance(value, list):
            below = lower if isinstance(lower, list) else []
            below_origins = [origins.get((*here, i), origin) for i in range(len(below))]
            entries, entry_origins = _chain(below, below_origins, value, origin)
            _clear(origins, here)
            values[key] = entries
            origins[here] = origin
            for i, entry_origin in enumerate(entry_origins):
                origins[(*here, i)] = entry_origin
            written.setdefault(here, []).append(origin)
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


def load_config(project_root: Path, *, personal: bool = True) -> Config:
    """The effective configuration of the project at `project_root`: its four
    layers read, checked, merged and parsed. Never raises for a problem in
    the configuration; every problem found is in `problems`.

    `personal=False` reads `built-in` and `tcw-config.yaml` only: how another
    project (an upstream, a delegation target, the project of an item named by
    its full slug) is read, since personal files apply only to the project a
    command acts on.
    """
    from tcw.work.config import parse_work_config
    root = Path(project_root).absolute()
    # The acting project's files are named relative to it; another project's
    # by their whole path, so a message says which project to fix.
    shown = root if personal else None
    project = Origin("project", root / SENTINEL)
    values = built_in_values()
    origins: dict = {}
    _stamp(origins, (), values, BUILT_IN)
    written: dict = {}
    for path, _ in _lists(values):
        if _is_chain(path):
            written[path] = [BUILT_IN]
    config = Config(root, values, origins, None, written=written)

    raw, problems = _read(project.file, True, shown)
    config.problems += problems
    if raw is not None:
        raw, problems = _file_problems(project.file, raw, shown, versioned=True)
        config.problems += problems
    if raw is None:
        config.unreadable = True
        config.work, _ = parse_work_config(values.get("work"), origins)
        return config
    config.problems += _list_problems(raw, project, shown)
    if "user" in raw:
        config.problems.append(Problem(
            project.file, ("user",),
            f"'user' is personal; set it in {user_config_label()} or "
            f"{LOCAL_FILE}", shown))
        raw = {k: v for k, v in raw.items() if k != "user"}
    _merge(values, origins, written, raw, project)

    for origin in _personal_layers(root, config.problems) if personal else ():
        mapping, problems = _read(origin.file, False, root)
        config.problems += problems
        if mapping is not None and origin.file.exists():
            mapping, problems = _file_problems(origin.file, mapping, root,
                                               versioned=origin.layer == "local")
            config.problems += problems
        if not mapping:
            continue
        mapping, problems = _allowed(mapping, origin, root, config.refused)
        config.problems += problems
        config.problems += _list_problems(mapping, origin, root)
        work = values.get("work")
        if not (isinstance(work, dict) and work.get("backend") == "jira"):
            mapping = _without_credentials(mapping, origin, config.skipped)
        _merge(values, origins, written, mapping, origin)

    config.problems += _confinement(values, origins, shown)
    work, parsed = parse_work_config(values.get("work"), origins)
    config.work = work
    if work.backend == "jira":
        from tcw.work.jira.config import parse_jira_config
        config.jira, jira_problems = parse_jira_config(work.jira)
        parsed = [*parsed, *jira_problems]
    for problem in parsed:
        origin = _origin_for(problem.key_path, origins, project)
        config.problems.append(Problem(origin.file, tuple(problem.key_path),
                                       problem.message, shown))
    return config


# ---------------------------------------------------------------------------
# Once per command

#: The acting project's configuration, kept while one command runs so it is
#: read and checked once (Design 2.3). None outside a command: a library
#: caller, such as a test, always reads the files afresh.
_EFFECTIVE: dict | None = None


def begin_command() -> None:
    """Start one command: the configuration, and the project registry
    (TCW-107 Design 2.13), are each read once until `end_command`. The
    registry is dropped after the command writes a configuration or a
    manifest; this configuration cache is still not, as in 3.x."""
    global _EFFECTIVE
    _EFFECTIVE = {}
    from tcw.store import project
    project.begin_command()


def end_command() -> None:
    global _EFFECTIVE
    _EFFECTIVE = None
    from tcw.store import project
    project.end_command()


def effective(project_root: Path) -> Config:
    """The configuration of the project a command acts on, personal layers
    included, read once per command."""
    if _EFFECTIVE is None:
        return load_config(project_root)
    key = Path(project_root).resolve()
    if key not in _EFFECTIVE:
        _EFFECTIVE[key] = load_config(project_root)
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
    layers.append(Origin("local", root / LOCAL_FILE))  # `.tcw/tcw-config.local.yaml`
    return layers
