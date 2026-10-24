"""The TCW 3.x readers `tcw migrate` needs, in one place (TCW-116 Design 8.2).

A conversion must read a file exactly as TCW 3.x read it (TCW-116 Problem 4),
so each reader here is copied from the released 3.x, tag `v3.0.2`, rather than
written again; each copy names the file and line it came from, carries a
`_3x` ending so no 4.0 name is defined twice, and is trimmed only of what
read TCW 4.0 files or opened a store (plan, Decided 2). Nothing but
`tcw migrate` imports this module, and TCW 4.0's own readers never read a
3.x form: they refuse it.

Two pieces of 4.0 code are used as they stand rather than copied, because
they answer as they did at the tag: the duplicate-key YAML loader
(`tcw/store/yaml_source.py`, unchanged since it) and the linked-worktree
probe (`worktree_anchors`, `_probe_worktree` and `_below` in
`tcw/store/project.py`, unchanged; the git call under them now runs with
TCW's non-interactive environment, which changes no answer).
"""

from __future__ import annotations

import copy
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NamedTuple
from urllib.parse import unquote

import yaml

from tcw.project_files import (CONFIG_NAME, LOCAL_CONFIG_NAME, SENTINEL, LOCAL_SENTINEL,
                               without_version)
from tcw.store.config_edit import read_text
from tcw.store.yaml_source import UniqueKeyLoader, load as _load_named_yaml

TAG = "v3.0.2"

#: A 3.x project's two files, at its root.
ROOT_CONFIG = CONFIG_NAME                  # tcw-config.yaml
ROOT_LOCAL = LOCAL_CONFIG_NAME             # tcw-config.local.yaml

#: The 3.x state files, by namespace.
STATE_3X = {"taxonomy": "meta.yaml", "capabilities": "meta.yaml", "work": "item.yaml"}

KeyPath = tuple


# ---------------------------------------------------------------------------
# One file, read as 3.x read it


@dataclass
class Layer3:
    """One configuration file as read for the plan: its text exactly as
    stored (`config_edit.read_text`, no line-ending translation), its
    mapping, and why it could not be read, if it could not."""

    label: str                       # "shared", "user" or "personal"
    path: Path
    text: str | None = None          # None: the file is absent
    data: dict | None = None         # None: absent, or unreadable
    problem: str | None = None       # the reason, for blocker B14

    @property
    def present(self) -> bool:
        return self.text is not None


def read_layer_3x(path: Path, label: str) -> Layer3:
    """`path` read as 3.x's `_read` reads one configuration file
    (`tcw/config.py:220-246` at v3.0.2): absent is `{}`'s absence, not a
    problem; a file that is not UTF-8, not YAML, holds a duplicate key, or is
    not a mapping is a problem; empty content is an empty mapping."""
    layer = Layer3(label, Path(path))
    try:
        layer.text = read_text(layer.path)
    except UnicodeDecodeError as error:
        bad = error.object[error.start:error.start + 1].hex()
        layer.text = ""
        layer.problem = (f"is not valid UTF-8 text (byte 0x{bad} at position "
                         f"{error.start})")
        return layer
    except OSError as error:
        layer.text = ""
        layer.problem = f"cannot be read: {error.strerror or error}"
        return layer
    if layer.text is None:
        return layer
    layer.data, layer.problem = parse_mapping_3x(layer.text, layer.path)
    return layer


def parse_mapping_3x(text: str, path: Path) -> tuple[dict | None, str | None]:
    """The YAML half of 3.x's `_read` (`tcw/config.py:236-246` at v3.0.2),
    over text: the mapping, or None and the problem."""
    try:
        data = _load_named_yaml(text, path, UniqueKeyLoader)
    except yaml.YAMLError as error:
        return None, f"is not valid YAML: {' '.join(str(error).split())}"
    if data is None:
        return {}, None
    if not isinstance(data, dict):
        return None, f"must be a mapping, not a {type(data).__name__}"
    return data, None


def user_config_path_3x() -> Path | None:
    """The user-wide file, `tcw/config.py:179-191` at v3.0.2:
    `$XDG_CONFIG_HOME/tcw/config.yaml` when that variable is an absolute
    path, else `~/.config/tcw/config.yaml`, or None with no home folder."""
    xdg = os.environ.get("XDG_CONFIG_HOME", "")
    if xdg and os.path.isabs(xdg):
        return Path(xdg) / "tcw" / "config.yaml"
    try:
        home = Path.home()
    except (RuntimeError, KeyError, OSError):
        return None
    return home / ".config" / "tcw" / "config.yaml"


#: `TCW_NO_PERSONAL_CONFIG` (`tcw/config.py:38` at v3.0.2).
SKIP_VARIABLE_3X = "TCW_NO_PERSONAL_CONFIG"


def personal_layers_read_3x() -> bool:
    """Whether 3.x reads the personal layers (`_personal_layers`,
    `tcw/config.py:638-647` at v3.0.2): not when `TCW_NO_PERSONAL_CONFIG`
    is `1`. Any other non-empty value is a problem there, and the files are
    then not read either."""
    return os.environ.get(SKIP_VARIABLE_3X, "") == ""


@dataclass
class Layers3:
    """A 3.x project's three configuration layers, each as read."""

    shared: Layer3
    user: Layer3 | None
    personal: Layer3

    @property
    def problems(self) -> list[Layer3]:
        return [layer for layer in (self.shared, self.user, self.personal)
                if layer is not None and layer.problem]

    def merged(self) -> dict:
        """The three layers merged as 3.x's `load_config` merges them
        (`tcw/config.py:541-600` at v3.0.2), before its parse: the shared
        file, then each personal layer through the allowlist, when personal
        layers are read. A layer that could not be read adds nothing."""
        values: dict = {}
        origins: dict = {}
        written: dict = {}
        if self.shared.data:
            shared = {k: v for k, v in self.shared.data.items() if k != "user"}
            merge_3x(values, origins, written, shared,
                     Origin3("project", self.shared.path))
        if personal_layers_read_3x():
            for layer, name in ((self.user, "user"), (self.personal, "local")):
                if layer is not None and layer.data:
                    merge_3x(values, origins, written, allowed_3x(layer.data),
                             Origin3(name, layer.path))
        return values


def read_3x_layers(root: Path) -> Layers3:
    """The root `tcw-config.yaml`, the user-wide file and the root
    `tcw-config.local.yaml` of the project at `root`, each read with 3.x's
    duplicate-key refusal (TCW-116 plan Step 2)."""
    user_path = user_config_path_3x()
    return Layers3(
        shared=read_layer_3x(Path(root) / ROOT_CONFIG, "shared"),
        user=read_layer_3x(user_path, "user") if user_path is not None else None,
        personal=read_layer_3x(Path(root) / ROOT_LOCAL, "personal"))


# ---------------------------------------------------------------------------
# 3.x's layering, copied from `tcw/config.py` at v3.0.2

#: `tcw/config.py:44-51` at v3.0.2: the key paths a personal file may set.
PERSONAL_KEYS_3X = (
    "user.name",
    "work.stages.*.prompt",
    "work.stages.*.post",
    "work.procedures.*",
    "work.jira.credentials.email-env",
    "work.jira.credentials.token-env",
)
_PATTERNS_3X = tuple(tuple(path.split(".")) for path in PERSONAL_KEYS_3X)


def _is_chain_3x(key_path: KeyPath) -> bool:
    """`_is_chain`, `tcw/config.py:262-267` at v3.0.2."""
    p = key_path
    return ((len(p) == 4 and p[:2] == ("work", "stages")
             and p[3] in ("prompt", "pre", "post"))
            or (len(p) == 3 and p[:2] == ("work", "procedures")))


def _matches_3x(path: KeyPath, pattern: tuple) -> bool:
    """`_matches`, `tcw/config.py:328-330` at v3.0.2."""
    return len(path) == len(pattern) and all(
        want == "*" or want == got for want, got in zip(pattern, path))


def _leads_to_allowed_3x(path: KeyPath) -> bool:
    """`_leads_to_allowed`, `tcw/config.py:333-335` at v3.0.2."""
    return any(len(pattern) > len(path) and _matches_3x(path, pattern[:len(path)])
               for pattern in _PATTERNS_3X)


def allowed_3x(mapping: dict, path: KeyPath = ()) -> dict:
    """The part of a personal file 3.x's allowlist lets it set: `_allowed`,
    `tcw/config.py:338-374` at v3.0.2, keeping what it keeps and dropping
    what it refuses. Its problems are not needed here: 3.x reported them,
    and migration converts the file as it stands."""
    kept: dict = {}
    for key, value in mapping.items():
        here = (*path, key)
        if value is None and (any(_matches_3x(here, p) for p in _PATTERNS_3X)
                              or _leads_to_allowed_3x(here)):
            continue
        if any(_matches_3x(here, pattern) for pattern in _PATTERNS_3X):
            kept[key] = value
        elif _leads_to_allowed_3x(here) and isinstance(value, dict):
            inner = allowed_3x(value, here)
            if inner:
                kept[key] = inner
    return kept


def _clear_3x(origins: dict, path: KeyPath) -> None:
    """`_clear`, `tcw/config.py:412-414` at v3.0.2."""
    for key in [k for k in origins if k[:len(path)] == path]:
        del origins[key]


def _stamp_3x(origins: dict, path: KeyPath, value: Any, origin: Any) -> None:
    """`_stamp`, `tcw/config.py:417-430` at v3.0.2."""
    if isinstance(value, dict):
        if not value and path:
            origins[path] = origin
        for key, inner in value.items():
            _stamp_3x(origins, (*path, key), inner, origin)
        return
    origins[path] = origin
    if isinstance(value, list):
        for i in range(len(value)):
            origins[(*path, i)] = origin


def _chain_3x(below: Any, below_origins: list, value: list,
              origin: Any) -> tuple[list, list]:
    """`_chain`, `tcw/config.py:433-451` at v3.0.2."""
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


@dataclass(frozen=True)
class Origin3:
    """The layer a merged value came from: `Origin`'s layer and file
    (`tcw/config.py:63-90` at v3.0.2)."""

    layer: str                       # "project", "user" or "local"
    file: Path | None = None


def merge_3x(values: dict, origins: dict, written: dict, layer: dict,
             origin: Origin3, path: KeyPath = ()) -> None:
    """`_merge`, `tcw/config.py:454-499` at v3.0.2: `layer` merged into
    `values` key by key, chain lists resolving their `inherit` entry. TCW
    4.0's merge reads a `null` differently (TCW-109), which is why this one
    is copied."""
    for key, value in layer.items():
        here = (*path, key)
        lower = values.get(key)
        if _is_chain_3x(here) and isinstance(value, list):
            below = lower if isinstance(lower, list) else []
            below_origins = [origins.get((*here, i), origin) for i in range(len(below))]
            entries, entry_origins = _chain_3x(below, below_origins, value, origin)
            _clear_3x(origins, here)
            values[key] = entries
            origins[here] = origin
            for i, entry_origin in enumerate(entry_origins):
                origins[(*here, i)] = entry_origin
            written.setdefault(here, []).append(origin)
        elif isinstance(value, dict) and isinstance(lower, dict):
            if value:
                origins.pop(here, None)
            elif not lower:
                origins[here] = origin
            merge_3x(lower, origins, written, value, origin, here)
        elif value is None and origin.layer == "project" and isinstance(lower, dict):
            continue
        elif isinstance(value, dict):
            _clear_3x(origins, here)
            values[key] = {}
            merge_3x(values[key], origins, written, value, origin, here)
            if not value:
                origins[here] = origin
        else:
            _clear_3x(origins, here)
            values[key] = copy.deepcopy(value)
            _stamp_3x(origins, here, value, origin)
            if _is_chain_3x(here):
                written.setdefault(here, []).append(origin)


# ---------------------------------------------------------------------------
# The Jira settings of the project's own layers (plan, Decided 11)


@dataclass
class JiraLayers:
    """`work.jira` merged from the project's own layers, with the file each
    value came from."""

    jira: dict | None
    origins: dict = field(default_factory=dict)
    files: list[Path] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    def file_of(self, key_path: KeyPath) -> Path | None:
        """The file the value at `key_path` (below `work.jira`) came from,
        else the shared file."""
        full = ("work", "jira", *key_path)
        while full:
            origin = self.origins.get(full)
            if origin is not None:
                return origin.file
            full = full[:-1]
        return self.files[0] if self.files else None


def _jira_only(data: dict | None) -> dict:
    """A layer's `work.jira`, alone in its `work` section."""
    work = data.get("work") if isinstance(data, dict) else None
    jira = work.get("jira") if isinstance(work, dict) else None
    return {"work": {"jira": jira}} if jira is not None else {}


def own_jira_layers(root: Path) -> JiraLayers:
    """The `work.jira` of the project's own layers, in whichever form they are
    on disk (TCW-116 Design 5.1; plan, Decided 11): the shared layer from the
    root `tcw-config.yaml` when present, else `.tcw/tcw-config.yaml`; the
    user-wide file; and the personal layer from the root
    `tcw-config.local.yaml` when present, else `.tcw/tcw-config.local.yaml`.
    Each is read raw, only its `work.jira` kept, and merged by 3.x's rule,
    the personal layers through 3.x's allowlist. No parent and no
    environment override is read."""
    root = Path(root)
    shared_path = root / ROOT_CONFIG
    if not shared_path.exists():
        shared_path = root / SENTINEL
    personal_path = root / ROOT_LOCAL
    if not personal_path.exists():
        personal_path = root / LOCAL_SENTINEL
    found = JiraLayers(None)
    values: dict = {}
    written: dict = {}
    layers = [(shared_path, "project")]
    if personal_layers_read_3x():
        user = user_config_path_3x()
        if user is not None:
            layers.append((user, "user"))
        layers.append((personal_path, "local"))
    for path, name in layers:
        layer = read_layer_3x(path, name)
        if not layer.present:
            continue
        found.files.append(path)
        if layer.problem:
            found.problems.append(f"{path}: {layer.problem}")
            continue
        mapping = _jira_only(without_version(layer.data))
        if name != "project":
            mapping = allowed_3x(mapping)
        merge_3x(values, found.origins, written, mapping, Origin3(name, path))
    work = values.get("work")
    found.jira = work.get("jira") if isinstance(work, dict) else None
    return found


# ---------------------------------------------------------------------------
# The objects 3.x lists


def _within_store_3x(path: Path, resolved_root: Path) -> bool:
    """`_within_store`, `tcw/store/fs.py:1373-1390` at v3.0.2."""
    try:
        return path.resolve().is_relative_to(resolved_root)
    except (OSError, RuntimeError):
        return False


def _entry_readable_3x(d: Path, resolved_root: Path) -> bool:
    """`_entry_readable`, `tcw/store/fs.py:1362-1371` at v3.0.2: the folder
    and its own `meta.yaml` both stay inside the store."""
    return (_within_store_3x(d, resolved_root)
            and _within_store_3x(d / "meta.yaml", resolved_root))


def objects_3x(store_root: Path, namespace: str) -> list[str]:
    """The id-paths 3.x lists in the store at `store_root` (TCW-116 Design
    4.1), sorted:

    - taxonomy, every folder (`_local_slugs`, `tcw/store/fs.py:1743-1749` at
      v3.0.2);
    - capabilities, every folder holding `meta.yaml`, hidden parts skipped
      (`_all_meta_dirs` and `_is_capability`, `:2235-2251`);
    - work, every folder holding `item.yaml`, hidden parts skipped, found on
      disk in both backends rather than through a backend's listing.
    """
    root = Path(store_root)
    if not root.is_dir():
        return []
    resolved = root.resolve()
    out = []
    for p in sorted(root.rglob("*")):
        if not p.is_dir():
            continue
        rel = p.relative_to(root)
        if namespace == "taxonomy":
            if _entry_readable_3x(p, resolved):
                out.append(rel.as_posix())
            continue
        if any(part.startswith(".") for part in rel.parts):
            continue
        if namespace == "capabilities":
            if _entry_readable_3x(p, resolved) and (p / "meta.yaml").is_file():
                out.append(rel.as_posix())
        elif (p / "item.yaml").is_file() and _within_store_3x(p / "item.yaml", resolved):
            out.append(rel.as_posix())
    return sorted(out)


# ---------------------------------------------------------------------------
# Store folders, as 3.x's `resolve_store` placed them


@dataclass(frozen=True)
class StoreFolder3:
    """Where 3.x put one store: `folder`, with the configured text (None for
    the default `docs/<component>`), or `form` naming why part 1 cannot say:
    `outside` (a path leading out of the project) or `repository` (a store
    with only a `repository`)."""

    component: str
    folder: Path | None
    configured: str | None = None
    form: str | None = None
    problem: str | None = None


def store_folder_3x(root: Path, component: str, section: Any) -> StoreFolder3:
    """The path rungs of 3.x's `resolve_store` (`tcw/store/fs.py:3162-3300` at
    v3.0.2) with `_local_root` (`:1291-1300`) and `anchor_configured_path`
    (`:1192-1226`): `<component>.path`, else `docs/<component>`; `~`
    expanded; absolute as written; relative re-anchored only when it leaves a
    linked worktree. A store declaring a `repository` and no path is
    `form="repository"`; one whose folder is outside the project is
    `form="outside"`."""
    from tcw.store.project import _below, worktree_anchors
    root = Path(root)
    section = section if isinstance(section, dict) else {}
    configured = section.get("path")
    if configured is not None and (not isinstance(configured, str)
                                   or not configured.strip()):
        return StoreFolder3(component, None, None,
                            problem=f"{component}.path must be a non-empty path string")
    if configured is None:
        if section.get("repository") is not None:
            return StoreFolder3(component, None, None, form="repository")
        return StoreFolder3(component, root / "docs" / component)
    value = Path(configured).expanduser()
    if value.is_absolute():
        folder = value
    else:
        anchor = root
        anchors = worktree_anchors(root)
        if anchors is not None:
            top, main = anchors
            resolved = (root / value).resolve()
            inside = _below(root.resolve(), top)
            if inside is not None and _below(resolved, top) is None:
                anchor = main / inside
        folder = anchor / value
    # Lexically, so a `..` that comes back into the project stays inside.
    lexical = Path(os.path.normpath(folder.absolute()))
    if _below(lexical, Path(os.path.normpath(root.absolute()))) is None:
        return StoreFolder3(component, folder, configured, form="outside")
    return StoreFolder3(component, folder, configured)


# ---------------------------------------------------------------------------
# Links, as 3.x's link check read them


#: `tcw/validate.py:48-56` at v3.0.2.
_LINK_RE_3X = re.compile(r"\]\((tcw://[^)\s]+)\)")
_FENCE_RE_3X = re.compile(r"^[ \t]*(`{3,}|~{3,})[^\n]*\n.*?^[ \t]*\1[ \t]*$",
                          re.MULTILINE | re.DOTALL)
_INLINE_CODE_RE_3X = re.compile(r"(?<!`)(`+)(?!`).*?(?<!`)\1(?!`)", re.DOTALL)

#: `tcw/refs.py` at v3.0.2.
_SCHEME_3X = "tcw://"
_AXES_3X = ("T", "C", "W")


class TcwRef3(NamedTuple):
    """`TcwRef`, `tcw/refs.py` at v3.0.2: a parsed `tcw://` link."""

    namespace: str
    axis: str
    ref: str


def _segment_ok_3x(seg: str) -> bool:
    """`_segment_ok`, `tcw/refs.py:51-56` at v3.0.2."""
    if seg in (".", ".."):
        return False
    return not any(ord(c) < 0x20 or c == "\x7f" or c == "\\" for c in seg)


def parse_tcw_uri_3x(uri: str) -> TcwRef3 | None:
    """`parse_tcw_uri`, `tcw/refs.py:59-81` at v3.0.2: the namespace, axis and
    ref of a 3.x `tcw://` link, or None."""
    if not isinstance(uri, str) or not uri.startswith(_SCHEME_3X):
        return None
    raw_segs = [s for s in uri[len(_SCHEME_3X):].split("/") if s]
    segs = [unquote(s) for s in raw_segs]
    if not all(_segment_ok_3x(s) for s in segs):
        return None
    axis_idx = next((i for i, s in enumerate(segs) if s.upper() in _AXES_3X), -1)
    if axis_idx == -1:
        return None
    ref = "/".join(segs[axis_idx + 1:])
    if not ref:
        return None
    return TcwRef3("/".join(segs[:axis_idx]), segs[axis_idx].upper(), ref)


def _removed(text: str, pattern: re.Pattern, index: list[int]) -> tuple[str, list[int]]:
    """`pattern.sub("", text)`, keeping for each character left the position
    it had in the original (through `index`, the positions `text` had)."""
    out, kept, at = [], [], 0
    for match in pattern.finditer(text):
        out.append(text[at:match.start()])
        kept += index[at:match.start()]
        at = match.end()
    out.append(text[at:])
    kept += index[at:]
    return "".join(out), kept


@dataclass(frozen=True)
class Link3:
    """One `](tcw://…)` link outside code: the link's text, its span in the
    file's text, and how 3.x parsed it (None when it did not)."""

    uri: str
    start: int
    end: int
    parsed: TcwRef3 | None


def links_3x(text: str) -> list[Link3]:
    """Every `tcw://` link 3.x's link check reads in a Markdown text
    (`_strip_code`, `tcw/validate.py:69-71`, and `_LINK_RE`, `:48`, at
    v3.0.2): outside fenced and inline code, each with its position in the
    original text. A link whose characters a removed code span had split is
    left out, since it is not one stretch of the file."""
    index = list(range(len(text)))
    stripped, index = _removed(text, _FENCE_RE_3X, index)
    stripped, index = _removed(stripped, _INLINE_CODE_RE_3X, index)
    found = []
    for match in _LINK_RE_3X.finditer(stripped):
        start, end = match.start(1), match.end(1)
        first, last = index[start], index[end - 1]
        if last - first != end - start - 1:
            continue
        found.append(Link3(match.group(1), first, last + 1,
                           parse_tcw_uri_3x(match.group(1))))
    return found
