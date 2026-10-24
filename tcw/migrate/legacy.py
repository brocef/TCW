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


# ---------------------------------------------------------------------------
# Related projects, as 3.x's registry declared and placed them (plan Step 15)

#: The three relations of `projects:`, in the order 3.x's `_follow_edges`
#: walked them (`tcw/store/project.py:542-551` at v3.0.2).
RELATIONS_3X = ("children", "parent", "upstream")


@dataclass(frozen=True)
class RepoDecl3:
    """`RepositoryDeclaration`, `tcw/store/base.py:679` at v3.0.2."""

    url: str
    ref: str | None = None
    path: str = ""
    checkout: str | None = None


def parse_repository_3x(raw: Any, where: str) -> tuple[RepoDecl3 | None, list[str]]:
    """`parse_repository_declaration`, `tcw/store/base.py:780-862` at v3.0.2:
    a `repository` mapping, or None with its problems. Fails closed."""
    problems: list[str] = []
    if raw is None:
        return None, problems
    if not isinstance(raw, dict):
        return None, [f"{where}: expected a mapping, got {type(raw).__name__}"]
    known = {"url", "ref", "path", "checkout"}
    unknown = set(raw) - known
    if unknown:
        problems.append(f"{where}: unknown key(s) {', '.join(sorted(map(str, unknown)))}; "
                        f"expected {', '.join(repr(k) for k in sorted(known))}")
    url = raw.get("url")
    if not isinstance(url, str) or not url.strip():
        problems.append(f"{where}.url: expected a non-empty string")

    def optional(key: str) -> str | None:
        value = raw.get(key)
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            problems.append(f"{where}.{key}: expected a non-empty string")
            return None
        return value.strip()

    ref, checkout = optional("ref"), optional("checkout")
    store_path = ""
    raw_path = raw.get("path")
    if raw_path is not None:
        if not isinstance(raw_path, str) or not raw_path.strip():
            problems.append(f"{where}.path: expected a non-empty string")
        else:
            candidate = raw_path.strip()
            parts = Path(candidate).parts
            if candidate.startswith("/") or (len(candidate) > 1 and candidate[1] == ":"):
                problems.append(f"{where}.path: must be relative to the repository root, "
                                f"got {candidate!r}")
            elif ".." in parts:
                problems.append(f"{where}.path: must not leave the repository root, "
                                f"got {candidate!r}")
            else:
                store_path = Path(candidate).as_posix().strip("/")
    if problems:
        return None, problems
    return RepoDecl3(url.strip(), ref, store_path, checkout), problems


@dataclass(frozen=True)
class Relation3:
    """One entry of a 3.x `projects:` block: `ConnectedProject`
    (`tcw/store/base.py` at v3.0.2) with the relation it is under."""

    kind: str                       # children, parent or upstream
    id: str
    locator: str | None = None
    repository: RepoDecl3 | None = None
    jira: Any = None


def _valid_id_3x(value: Any) -> str | None:
    """`validate_project_id`, `tcw/store/project.py:24-36` at v3.0.2, whose
    pattern and reserved IDs `tcw/project_files.py` keeps unchanged; the ID,
    or None."""
    from tcw.project_files import PROJECT_ID_PATTERN, RESERVED_PROJECT_IDS
    text = (value or "").strip() if isinstance(value, str) else ""
    if not PROJECT_ID_PATTERN.fullmatch(text) or text in RESERVED_PROJECT_IDS:
        return None
    return text


def parse_connected_3x(project_id: str, raw: Any, where: str
                       ) -> tuple[tuple | None, list[str]]:
    """`parse_connected_entry`, `tcw/store/base.py:865-917` at v3.0.2: a bare
    locator, or a mapping of `path`, `repository` and `jira`; the parts as
    `(locator, repository, jira)`, or None with its problems."""
    problems: list[str] = []
    if isinstance(raw, str):
        if not raw.strip():
            return None, [f"{where}: locator must be a nonempty string"]
        return (raw, None, None), problems
    if not isinstance(raw, dict):
        return None, [f"{where}: expected a locator string or a mapping, "
                      f"got {type(raw).__name__}"]
    known = {"path", "repository", "jira"}
    unknown = set(raw) - known
    if unknown:
        problems.append(f"{where}: unknown key(s) {', '.join(sorted(map(str, unknown)))}; "
                        f"expected {', '.join(repr(k) for k in sorted(known))}")
    locator = raw.get("path")
    if locator is not None and (not isinstance(locator, str) or not locator.strip()):
        problems.append(f"{where}.path: expected a non-empty string")
        locator = None
    declaration = None
    if "repository" in raw:
        declaration, more = parse_repository_3x(raw.get("repository"),
                                                f"{where}.repository")
        problems.extend(more)
    if locator is None and declaration is None and not problems:
        problems.append(f"{where}: needs 'path', 'repository', or both")
    if problems:
        return None, problems
    return (locator, declaration, raw.get("jira")), problems


def relations_3x(raw: dict, file: str) -> tuple[list[Relation3], list[str]]:
    """The `projects:` reader of 3.x's registry (`_read_config` and
    `_relation`, `tcw/store/project.py:614-668` at v3.0.2): every entry, in
    the order written within each relation, children then parent then
    upstream, and the problems 3.x would have reported, each naming `file`."""
    connected = raw.get("projects")
    if connected is None:
        return [], []
    if not isinstance(connected, dict):
        return [], [f"{file}: projects must be a mapping"]
    problems: list[str] = []
    unknown = set(connected) - set(RELATIONS_3X)
    if unknown:
        problems.append(f"{file}: unknown projects keys: "
                        f"{', '.join(sorted(map(str, unknown)))}")
    out: list[Relation3] = []
    for kind in RELATIONS_3X:
        value = connected.get(kind)
        if value is None:
            continue
        if not isinstance(value, dict):
            problems.append(f"{file}: projects.{kind} must be a mapping")
            continue
        for key, entry in value.items():
            valid = _valid_id_3x(key)
            if valid is None:
                problems.append(f"{file}: {kind} key: project ID must match "
                                f"^[a-z0-9]+(?:-[a-z0-9]+)*$")
                continue
            parts, more = parse_connected_3x(valid, entry, f"projects.{kind}.{valid}")
            if parts is None:
                problems += [f"{file}: {p}" for p in more]
                continue
            out.append(Relation3(kind, valid, *parts))
    return out, problems


def extends_3x(section: Any, label: str) -> list[str]:
    """`_extends_ids`, `tcw/store/fs.py:884-913` at v3.0.2: one store
    section's `extends`, or a `ValueError` naming `label`."""
    config = section if isinstance(section, dict) else {}
    value = config.get("extends") or []
    if isinstance(value, dict):
        raise ValueError(f"{label}: legacy extends map is unsupported; replace it with "
                         "a list of registered project IDs")
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        raise ValueError(f"{label}: extends must be a list of project IDs")
    ids = []
    for v in value:
        valid = _valid_id_3x(v)
        if valid is None:
            raise ValueError(f"{label}: project ID must match ^[a-z0-9]+(?:-[a-z0-9]+)*$")
        ids.append(valid)
    if len(ids) != len(set(ids)):
        raise ValueError(f"{label}: extends contains duplicate project IDs")
    return ids


def _cache_root_3x() -> Path:
    """`_cache_root`, `tcw/store/checkouts.py:60-68` at v3.0.2."""
    base = os.environ.get("XDG_CACHE_HOME") or "~/.cache"
    return Path(base).expanduser() / "tcw" / "stores"


def _cache_key_3x(declaration: RepoDecl3) -> str:
    """`_cache_key`, `tcw/store/checkouts.py:71-91` at v3.0.2."""
    import hashlib
    cleaned = declaration.url.strip().rstrip("/")
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]
    tokens = [token.rpartition("@")[2] for token in re.split(r"[/:]", cleaned) if token]
    slug = "-".join(re.sub(r"[^A-Za-z0-9._-]+", "-", token).strip("-.")
                    for token in tokens[-3:])
    slug = (slug.strip("-").lower() or "store")[:60]
    digest = hashlib.sha256(
        f"{declaration.url}\n{declaration.ref or ''}".encode("utf-8")).hexdigest()[:12]
    return f"{slug}-{digest}"


def checkout_folder_3x(project_root: Path, declaration: RepoDecl3) -> Path:
    """`checkout_root`, `tcw/store/checkouts.py:95-117` at v3.0.2: the
    declared `checkout`, or the per-machine cache folder. A `~name` naming no
    user is a `ValueError`."""
    if declaration.checkout:
        try:
            value = Path(declaration.checkout).expanduser()
        except RuntimeError as error:
            raise ValueError(f"repository.checkout '{declaration.checkout}' cannot be "
                             f"resolved: {error}") from None
        return value if value.is_absolute() else (Path(project_root) / value)
    return _cache_root_3x() / _cache_key_3x(declaration)


def cache_folder_3x(project_root: Path, declaration: RepoDecl3) -> Path:
    """`provisioned_root`, `tcw/store/checkouts.py:120-127` at v3.0.2: where
    3.x put a declared project, the repository's `path` appended."""
    root = checkout_folder_3x(project_root, declaration)
    return (root / declaration.path) if declaration.path else root


def holds_project(folder: Path) -> bool:
    """Whether `folder` holds a TCW project's configuration in either form."""
    return (folder / ROOT_CONFIG).is_file() or (folder / SENTINEL).is_file()


def override_folder_3x(project_id: str) -> Path | None:
    """Rule 0 of 3.x's `_target_path` (`_resolve_override`,
    `tcw/store/project.py:745-777` at v3.0.2): the folder
    `TCW_PROJECT_<ID>` names when it is a folder on this machine, else
    None. A relative value is the working folder's."""
    from tcw.store.project import override_variable
    value = (os.environ.get(override_variable(project_id)) or "").strip()
    if not value:
        return None
    folder = Path(value).expanduser()
    if not folder.is_absolute():
        folder = Path.cwd() / folder
    folder = folder.resolve()
    return folder if folder.is_dir() else None


def locate_3x(config_folder: Path, relation: Relation3) -> tuple[Path, str]:
    """Where 3.x's registry placed `relation`, declared by the project at
    `config_folder` (`_target_path` and `_locator_path`,
    `tcw/store/project.py:670-803` at v3.0.2), and how: `variable`,
    `locator`, `repository` or, when no candidate holds a project, the first
    candidate as `absent`. A candidate counts when it holds the project in
    either form, since a related project may be migrated already. The
    re-anchoring of a locator that leaves a linked worktree is not copied:
    Design 6.6 reads a worktree's related projects from where it sits."""
    override = override_folder_3x(relation.id)
    if override is not None:
        return override, "variable"
    source = Path(config_folder).resolve()
    candidates: list[tuple[Path, str]] = []
    if relation.locator is not None:
        target = Path(relation.locator)
        folder = target if target.is_absolute() else source / target
        candidates.append((Path(os.path.normpath(folder)), "locator"))
    if relation.repository is not None:
        try:
            candidates.append((Path(os.path.normpath(
                cache_folder_3x(source, relation.repository))), "repository"))
        except ValueError:
            pass
    for folder, how in candidates:
        if holds_project(folder):
            return folder, how
    return (candidates[0][0] if candidates else source), "absent"


@dataclass
class Ledger3:
    """One 3.x capabilities store as its readers saw it: the standalone
    capabilities (`_local_paths`, `tcw/store/fs.py:2253-2257` at v3.0.2),
    each id-path to its `id` (`""` for none), and the overrides, each
    id-path to its pointer and its whole `meta.yaml`."""

    capabilities: dict[str, str] = field(default_factory=dict)
    overrides: dict[str, tuple[str, dict]] = field(default_factory=dict)


def ledger_3x(store_folder: Path) -> Ledger3:
    """The capabilities store at `store_folder`, read as 3.x read it: a
    `meta.yaml` with an `overrides` pointer is an override, not a
    capability. A `meta.yaml` that cannot be read counts as a capability with
    no id, as the listing would still show its folder."""
    out = Ledger3()
    for path in objects_3x(Path(store_folder), "capabilities"):
        meta_path = Path(store_folder) / path / STATE_3X["capabilities"]
        try:
            data, _ = parse_mapping_3x(meta_path.read_text(encoding="utf-8"), meta_path)
        except (OSError, UnicodeDecodeError):
            data = None
        data = data if isinstance(data, dict) else {}
        pointer = data.get("overrides")
        if pointer:
            out.overrides[path] = (str(pointer), data)
        else:
            out.capabilities[path] = str(data.get("id") or "")
    return out


# ---------------------------------------------------------------------------
# Owners, as 3.x's stores gave them (plan Step 15)


class Ambiguous3(ValueError):
    """`AmbiguousRef` at v3.0.2: a bare reference more than one source has."""


def override_target_3x(pointer: str, sources: dict[str, dict[str, str]]
                       ) -> list[tuple[str, str]]:
    """The match of 3.x's override index (`_override_index` and
    `_apply_override`, `tcw/store/fs.py:2281-2289`, `:2324-2369`, the match
    at `:2332`, at v3.0.2): every capability of a source, `sources`
    being each `capabilities.extends` project's id to its own capabilities'
    `{cap-id: id-path}`, whose id is `pointer` bare, or `<alias>/<id>` with
    `<alias>` the source. 3.x applied the override to each such capability;
    more than one is the caller's B9."""
    found = []
    for alias, ids in sources.items():
        for cap_id, path in ids.items():
            if cap_id and pointer in (cap_id, f"{alias}/{cap_id}"):
                found.append((alias, path))
    return found


def bare_owner_3x(path: str, own: set[str], sources: dict[str, set[str]]
                  ) -> tuple[str | None, str]:
    """`get` of 3.x's capabilities store (`tcw/store/fs.py:2405-2420` at
    v3.0.2), and the taxonomy store's (`:1779-1796`): the owner of a
    reference and the id-path within it. A first folder naming a source is
    that source's; a path the project has is its own (None); else the one
    source that has it; more than one is `Ambiguous3`; none is the project's
    own, which is where 3.x looked first. `own` and `sources` hold the
    id-paths each store's `get_local` finds, so an override folder is not
    among them."""
    head, _, rest = path.partition("/")
    if head in sources:
        return head, rest
    if path in own:
        return None, path
    matches = [alias for alias, paths in sources.items() if path in paths]
    if len(matches) > 1:
        raise Ambiguous3(path)
    return (matches[0], path) if matches else (None, path)


def route_entry_3x(path: str, *, extends: set[str], children: list[str],
                   has_ledger: bool, own_namespaces: set[str], project_id: str
                   ) -> tuple[str | None, str] | str:
    """`route_capability_path`, `tcw/work/gates.py:331-380` at v3.0.2: the
    project a `capabilities.yaml` entry under `new:`, `changed:` or
    `removed:` is routed to (None for the project's own ledger, else a
    source or a child) and the path within it, or the router's problem.
    `own_namespaces` are the first folders of the project's resolved view,
    its own capabilities and the inherited ones, for the ambiguity check.
    A path routed to the project's own ledger is then read by `get`
    (`bare_owner_3x`)."""
    head, _, rest = path.partition("/")
    if has_ledger and head in extends:
        return None, path
    if head in children:
        if not rest:
            return f"{path}: names project '{head}' but no capability"
        if has_ledger and head in own_namespaces:
            return (f"{path}: ambiguous — '{head}' is both a child project of this "
                    f"project and a namespace in this project's capabilities ledger")
        return head, rest
    if has_ledger:
        return None, path
    qualifiers = ", ".join(children) or "it declares no child projects"
    return (f"{path}: this project ('{project_id}') keeps no capabilities ledger; "
            f"qualify the path with a child project id ({qualifiers})")


def link_owner_3x(link: TcwRef3, own: dict[str, set[str]],
                  sources: dict[str, dict[str, set[str]]]) -> tuple[str | None, str]:
    """`resolve_tcw_ref`, `tcw/refs.py:84-125` at v3.0.2, for a taxonomy or
    capability link: the reference `<namespace>/<ref>` read by the store's
    `get` (`bare_owner_3x`). `own` and `sources` hold each axis's id-paths,
    by `taxonomy` and `capabilities`."""
    axis = "taxonomy" if link.axis == "T" else "capabilities"
    ns_ref = f"{link.namespace}/{link.ref}" if link.namespace else link.ref
    return bare_owner_3x(ns_ref, own.get(axis, set()),
                         {alias: paths.get(axis, set()) for alias, paths in sources.items()})
