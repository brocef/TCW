"""Parsing the `work:` section of `tcw-config.yaml` for TCW 3.0.

`parse_work_config` never raises. It returns what it could read together with
a list of `ConfigProblem`s, each naming the key it is about, so `tcw validate`
can report every problem at once and a later layer (personal configuration)
can say which file a bad value came from.

The binding rules are written for 3.0 rather than reusing the 2.x parser,
which accepts `when: {type: …}` (3.0 items have no type), accepts a skill as a
gate, and refuses duplicates that a merged list may legitimately repeat.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from tcw.store.base import PROCEDURE_IDS, DocEntry, normalize_tag, parse_documentation_entries
from tcw.work.model import SIDE, STAGES, stage as table_stage

MIGRATION_GUIDE = "docs/migration-guide-2.8-to-3.0.0.md"

BACKENDS = ("filesystem", "jira")
DEFAULT_BACKEND = "filesystem"

# Which binding kinds each position takes. A prompt or a procedure is text to
# read; a `pre` binding is a gate TCW must be able to run; a `post` binding may
# also name a skill, which is reported for the agent to invoke.
KINDS = ("blob", "file", "generate", "builtin", "skill", "command")
TEXT_KINDS = frozenset({"blob", "file", "generate", "builtin", "skill"})
LEGAL_KINDS = {
    "prompt": TEXT_KINDS,
    "procedure": TEXT_KINDS,
    "pre": frozenset({"command"}),
    "post": frozenset({"command", "skill"}),
}

WORK_KEYS = ("path", "repository", "backend", "tags", "documentation",
             "procedures", "stages", "hooks", "jira")
STAGE_KEYS = ("enabled", "status", "prompt", "pre", "post")
SIDE_STAGE_KEYS = ("enabled", "prompt")
HOOK_KEYS = ("timeout", "output-cap")

_REMOVED_WORK_KEYS = {
    "lifecycle": (
        "stage bindings now live under `work.stages.<stage>`, and an "
        "`artifacts` template becomes a `file` binding with a `when:` "
        "condition in that stage's `prompt` list"),
    "tracker": "the Jira connection is now `backend: jira` and `work.jira`",
    "auto-commit-transitions": "TCW no longer commits",
    "publish-transitions": "TCW no longer pushes",
    "trunk-branch": "TCW no longer branches or merges",
    "retain": "TCW no longer deletes finished items",
}

KeyPath = tuple[str, ...]


@dataclass(frozen=True)
class ConfigProblem:
    key_path: KeyPath
    message: str

    def __str__(self) -> str:
        return f"{'.'.join(self.key_path)}: {self.message}"


@dataclass(frozen=True)
class When:
    """A binding applies to an item carrying any of `tags` and none of
    `not_tags`. Both are normalized tags; an empty `tags` matches every item."""

    tags: tuple[str, ...] = ()
    not_tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class Binding:
    """One configured entry: its kind, the text, file, command or skill it
    names, an optional condition, and an opaque label for where it came from."""

    kind: str
    value: str
    when: When | None = None
    origin: str | None = field(default=None, compare=False)

    @property
    def ref(self) -> str:
        """What the shared hook runner reads."""
        return self.value


@dataclass(frozen=True)
class StageConfig:
    """One stage's settings. A list left as None was not written; an empty
    tuple was written empty, which personal configuration gives a meaning."""

    enabled: bool = True
    status: str | None = None
    prompt: tuple[Binding, ...] | None = None
    pre: tuple[Binding, ...] | None = None
    post: tuple[Binding, ...] | None = None


@dataclass(frozen=True)
class HookLimits:
    timeout: float = 300
    output_cap: int = 65536


@dataclass(frozen=True)
class WorkConfig:
    backend: str = DEFAULT_BACKEND
    path: str | None = None
    repository: Any = None  # passed through to the store resolver unparsed
    tags: tuple[str, ...] = ()
    documentation: tuple[DocEntry, ...] = ()
    procedures: Mapping[str, tuple[Binding, ...]] = field(default_factory=dict)
    stages: Mapping[str, StageConfig] = field(default_factory=dict)
    hooks: HookLimits = HookLimits()
    jira: Any = None  # parsed by the Jira backend

    @property
    def enabled(self) -> frozenset[str]:
        return frozenset(s.name for s in STAGES
                         if self.stages.get(s.name, StageConfig()).enabled)

    def stage(self, name: str) -> StageConfig:
        return self.stages.get(name, StageConfig())


class _Problems(list):
    def add(self, path: KeyPath, message: str) -> None:
        self.append(ConfigProblem(path, message))


def _describe(value: Any) -> str:
    return type(value).__name__


# ---------------------------------------------------------------------------
# Bindings

def _parse_when(raw: Any, where: KeyPath, problems: _Problems) -> When | None:
    if not isinstance(raw, dict) or not raw:
        problems.add(where, "'when' must be a non-empty mapping with 'tags' "
                            "and/or 'not_tags'")
        return None
    if "type" in raw:
        problems.add(where, "'when.type' is not supported: work items have no "
                            "type in TCW 3.0; condition on tags instead")
        return None
    unknown = sorted(map(str, set(raw) - {"tags", "not_tags"}))
    if unknown:
        problems.add(where, f"unknown 'when' key(s) {', '.join(unknown)}; "
                            f"expected 'tags' or 'not_tags'")
        return None
    lists: dict[str, tuple[str, ...]] = {"tags": (), "not_tags": ()}
    for key in lists:
        if key not in raw:
            continue
        value = raw[key]
        if not isinstance(value, list):
            hint = (f" (write [{value}] rather than {value})"
                    if isinstance(value, str) else f", got {_describe(value)}")
            problems.add(where, f"'when.{key}' must be a list of tags{hint}")
            return None
        tags = []
        for element in value:
            if not isinstance(element, str) or not element.strip():
                problems.add(where, f"'when.{key}' element {element!r} must be "
                                    f"a non-blank string")
                return None
            if "," in element:
                parts = ", ".join(p.strip() for p in element.split(",") if p.strip())
                problems.add(where, f"'when.{key}' element {element!r} holds "
                                    f"several tags; write [{parts}]")
                return None
            try:
                tags.append(normalize_tag(element))
            except ValueError as error:
                problems.add(where, f"'when.{key}' element: {error}")
                return None
        lists[key] = tuple(tags)
    return When(lists["tags"], lists["not_tags"])


def _parse_binding(raw: Any, where: KeyPath, role: str, origin: str | None,
                   problems: _Problems) -> Binding | None:
    legal = LEGAL_KINDS[role]
    if not isinstance(raw, dict):
        problems.add(where, f"a binding must be a mapping "
                            f"({{{' | '.join(sorted(legal))}}}: …), got "
                            f"{_describe(raw)}")
        return None
    unknown = sorted(map(str, set(raw) - set(KINDS) - {"when"}))
    if unknown:
        problems.add(where, f"unknown binding key(s) {', '.join(unknown)}; "
                            f"expected one of {', '.join(KINDS)}")
        return None
    declared = [k for k in KINDS if k in raw]
    if len(declared) != 1:
        problems.add(where, (f"binding declares {' and '.join(declared)}; choose one"
                             if declared else
                             f"binding declares no kind; expected one of "
                             f"{', '.join(sorted(legal))}"))
        return None
    kind = declared[0]
    if kind == "skill" and role == "pre":
        problems.add(where, "a 'skill' binding cannot be a gate: TCW cannot run "
                            "a skill, so a gate that is only reported would "
                            "always pass; use a 'command'")
        return None
    if kind not in legal:
        hint = (" (use 'generate' to run a script whose output is the text)"
                if kind == "command" else "")
        problems.add(where, f"'{kind}' is not allowed in a {role} list; expected "
                            f"one of {', '.join(sorted(legal))}{hint}")
        return None

    value = raw[kind]
    if kind == "builtin":
        if value is not True:
            problems.add(where, f"'builtin' must be the value true, got {value!r}")
            return None
        text = ""
    else:
        # A blank `blob` is the one blank value with a meaning: say nothing.
        if not isinstance(value, str) or (not value.strip() and kind != "blob"):
            problems.add(where, f"binding '{kind}' must be a non-blank string")
            return None
        text = value if kind == "blob" else value.strip()
        if kind == "skill" and re.search(r"[\s/\\]", text):
            problems.add(where, f"'skill' {text!r} is not a skill name (no "
                                f"spaces or path separators; `plugin:skill` is "
                                f"allowed)")
            return None

    when = None
    if "when" in raw:
        when = _parse_when(raw["when"], where, problems)
        if when is None:
            return None
    return Binding(kind, text, when, origin)


def parse_bindings(raw: Any, where: KeyPath, role: str, problems: list,
                   origin: str | None = None) -> tuple[Binding, ...]:
    """A list of bindings for `role` (`prompt`, `procedure`, `pre` or `post`).

    Every entry that parses is kept, in order, and duplicates are allowed. An
    empty list is a valid, deliberate value.
    """
    found = _Problems()
    out: list[Binding] = []
    if not isinstance(raw, list):
        found.add(where, f"expected a list of bindings, got {_describe(raw)}")
    else:
        for i, entry in enumerate(raw):
            binding = _parse_binding(entry, (*where, str(i)), role, origin, found)
            if binding is not None:
                out.append(binding)
    problems.extend(found)
    return tuple(out)


# ---------------------------------------------------------------------------
# Sections

def _positive_number(value: Any, integer: bool) -> bool:
    if isinstance(value, bool):
        return False
    kinds = (int,) if integer else (int, float)
    return isinstance(value, kinds) and value > 0


def _parse_hooks(raw: Any, problems: _Problems) -> HookLimits:
    where = ("work", "hooks")
    if raw is None:
        return HookLimits()
    if not isinstance(raw, dict):
        problems.add(where, f"expected a mapping, got {_describe(raw)}")
        return HookLimits()
    for key in sorted(map(str, set(raw) - set(HOOK_KEYS))):
        problems.add((*where, key), f"unknown key; expected one of "
                                    f"{', '.join(HOOK_KEYS)}")
    limits = HookLimits()
    timeout, cap = limits.timeout, limits.output_cap
    if "timeout" in raw:
        if _positive_number(raw["timeout"], integer=False):
            timeout = raw["timeout"]
        else:
            problems.add((*where, "timeout"), f"must be a positive number of "
                                              f"seconds, got {raw['timeout']!r}")
    if "output-cap" in raw:
        if _positive_number(raw["output-cap"], integer=True):
            cap = raw["output-cap"]
        else:
            problems.add((*where, "output-cap"),
                         f"must be a positive whole number of bytes, got "
                         f"{raw['output-cap']!r}")
    return HookLimits(timeout, cap)


def _parse_stage(name: str, raw: Any, jira: bool, origins: Mapping,
                 problems: _Problems) -> StageConfig:
    where = ("work", "stages", name)
    row = table_stage(name)
    if raw is None:
        return StageConfig()
    if not isinstance(raw, dict):
        problems.add(where, f"expected a mapping, got {_describe(raw)}")
        return StageConfig()
    allowed = SIDE_STAGE_KEYS if row.kind == SIDE else STAGE_KEYS
    for key in sorted(map(str, raw)):
        if key in allowed:
            continue
        if key in STAGE_KEYS:
            problems.add((*where, key),
                         f"'{key}' is not allowed on {name}: nothing ever moves "
                         f"into a side stage, so it has no hooks and no status")
        else:
            problems.add((*where, key), f"unknown key; expected one of "
                                        f"{', '.join(allowed)}")

    enabled = True
    if "enabled" in raw:
        if not isinstance(raw["enabled"], bool):
            problems.add((*where, "enabled"), "must be true or false")
        elif not raw["enabled"] and not row.optional:
            problems.add((*where, "enabled"), f"{name} cannot be disabled")
        else:
            enabled = raw["enabled"]

    status = None
    if "status" in raw and "status" in allowed:
        value = raw["status"]
        if not jira:
            problems.add((*where, "status"),
                         "'status' maps a stage to a Jira status and is only "
                         "read with `backend: jira`")
        elif not isinstance(value, str) or not value.strip():
            problems.add((*where, "status"), "must be a non-empty string")
        else:
            status = value

    lists: dict[str, tuple[Binding, ...] | None] = {}
    for role in ("prompt", "pre", "post"):
        if role in raw and role in allowed:
            path = (*where, role)
            lists[role] = parse_bindings(raw[role], path, role, problems,
                                         origins.get(path))
        else:
            lists[role] = None
    return StageConfig(enabled, status, **lists)


def _parse_stages(raw: Any, jira: bool, origins: Mapping,
                  problems: _Problems) -> dict[str, StageConfig]:
    where = ("work", "stages")
    known = {s.name for s in STAGES}
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        problems.add(where, f"expected a mapping, got {_describe(raw)}")
        raw = {}
    for name in sorted(map(str, set(raw) - known)):
        problems.add((*where, name), f"unknown stage; the stages are "
                                     f"{', '.join(s.name for s in STAGES)}")
    stages = {s.name: _parse_stage(s.name, raw.get(s.name), jira, origins,
                                   problems) for s in STAGES}
    if jira:
        claimed: dict[str, str] = {}
        for row in STAGES:
            config = stages[row.name]
            if row.kind == SIDE or not config.enabled:
                continue
            if config.status is None:
                if "status" not in (raw.get(row.name) or {}):
                    problems.add((*where, row.name, "status"),
                                 "with `backend: jira` every enabled stage "
                                 "needs the Jira status it maps to")
                continue
            if config.status in claimed:
                problems.add((*where, claimed[config.status], "status"),
                             f"status {config.status!r} is also mapped by "
                             f"{row.name}; each stage needs its own status")
            else:
                claimed[config.status] = row.name
    return stages


def _parse_procedures(raw: Any, origins: Mapping,
                      problems: _Problems) -> dict[str, tuple[Binding, ...]]:
    where = ("work", "procedures")
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        problems.add(where, f"expected a mapping, got {_describe(raw)}")
        return {}
    out = {}
    for name, value in raw.items():
        path = (*where, str(name))
        if name not in PROCEDURE_IDS:
            problems.add(path, f"unknown procedure; expected one of "
                               f"{', '.join(PROCEDURE_IDS)}")
            continue
        out[name] = parse_bindings(value, path, "procedure", problems,
                                   origins.get(path))
    return out


def _parse_tags(raw: Any, problems: _Problems) -> tuple[str, ...]:
    where = ("work", "tags")
    if raw is None:
        return ()
    if not isinstance(raw, list):
        problems.add(where, f"expected a list of tags, got {_describe(raw)}")
        return ()
    tags: list[str] = []
    for value in raw:
        try:
            tag = normalize_tag(value)
        except (ValueError, AttributeError):
            problems.add(where, f"{value!r} is not a tag")
            continue
        if tag not in tags:
            tags.append(tag)
    return tuple(tags)


def parse_work_config(mapping: Any, origins: Mapping[KeyPath, str] | None = None
                      ) -> tuple[WorkConfig, list[ConfigProblem]]:
    """Read the mapping under `work:`. Never raises.

    `origins` maps a key path to a label (which file it came from); every
    binding built from a list at that path carries the label.
    """
    origins = origins or {}
    problems = _Problems()
    if mapping is None:
        mapping = {}
    if not isinstance(mapping, dict):
        problems.add(("work",), f"expected a mapping, got {_describe(mapping)}")
        return WorkConfig(stages=_parse_stages({}, False, origins, problems)), \
            list(problems)

    for key in mapping:
        if key in _REMOVED_WORK_KEYS:
            problems.add(("work", key),
                         f"removed in TCW 3.0: {_REMOVED_WORK_KEYS[key]}. See "
                         f"{MIGRATION_GUIDE}")
        elif key not in WORK_KEYS:
            problems.add(("work", str(key)),
                         f"unknown key; expected one of {', '.join(WORK_KEYS)}")

    backend = mapping.get("backend", DEFAULT_BACKEND)
    if backend not in BACKENDS:
        problems.add(("work", "backend"), f"must be one of {', '.join(BACKENDS)}, "
                                          f"got {backend!r}")
        backend = DEFAULT_BACKEND
    jira = backend == "jira"

    if "jira" in mapping and not jira:
        problems.add(("work", "jira"), "'jira' is only read with `backend: jira`")

    path = mapping.get("path")
    if path is not None and (not isinstance(path, str) or not path.strip()):
        problems.add(("work", "path"), "must be a non-empty string")
        path = None

    entries, doc_problems = parse_documentation_entries(mapping.get("documentation"))
    for message in doc_problems:
        problems.add(("work", "documentation"), message)

    config = WorkConfig(
        backend=backend,
        path=path,
        repository=mapping.get("repository"),
        tags=_parse_tags(mapping.get("tags"), problems),
        documentation=tuple(entries),
        procedures=_parse_procedures(mapping.get("procedures"), origins, problems),
        stages=_parse_stages(mapping.get("stages"), jira, origins, problems),
        hooks=_parse_hooks(mapping.get("hooks"), problems),
        jira=mapping.get("jira") if jira else None,
    )
    return config, list(problems)
