"""The configuration keys TCW knows, and the environment variables that
override them (TCW-109 Design 4).

A variable `TCW_<KEY>__<PROJECT>` sets one key of one project's
configuration: the key's parts joined by `_`, then `__`, then the project ID,
all in capitals, each `-` written `_`. Every key and every project ID follows
TCW-106's naming rule (lower-case letters and digits joined by single
hyphens), so `__` splits the two parts and no name stands for two keys.

`known_keys` is the table of every key reachable through mappings in
`.tcw/tcw-config.yaml`, with the kind of value each takes. It has two uses
only: decoding a variable's key part, and, for `work.tags` and `work.jira`,
deciding which keys a missing parent leaves undecided. Nothing reports a key
of a file because the table lacks it.

Pure functions; the constants are imported lazily, as `built_in_values`
does, since `tcw.work.config` imports `tcw.config`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

import yaml

KeyPath = tuple

MAPPING, TEXT, LIST, NUMBER, BOOLEAN = "mapping", "text", "list", "number", "boolean"

#: Design 4.2: the form every override's name must have.
NAME = re.compile(r"^TCW_[A-Z0-9]+(_[A-Z0-9]+)*__[A-Z0-9]+(_[A-Z0-9]+)*$")

_TABLE: dict[KeyPath, str] | None = None
_BY_NAME: dict[str, KeyPath] | None = None


def known_keys() -> dict[KeyPath, str]:
    """Every key reachable through mappings in `.tcw/tcw-config.yaml`, and the
    kind of value it takes. No `tcw-version` (information about the file, not
    a key) and no key inside a list entry, which has no name of its own."""
    global _TABLE
    if _TABLE is not None:
        return _TABLE
    from tcw.store.base import PROCEDURE_IDS
    from tcw.work.config import HOOK_KEYS, SIDE_STAGE_KEYS, STAGE_KEYS
    from tcw.work.model import SIDE, STAGES
    table: dict[KeyPath, str] = {("id",): TEXT, ("parents",): LIST,
                                 ("children",): LIST, ("user",): MAPPING,
                                 ("user", "name"): TEXT}

    def repository(at: KeyPath) -> None:
        table[(*at, "repository")] = MAPPING
        for key in ("url", "ref", "path", "checkout"):
            table[(*at, "repository", key)] = TEXT

    for component in ("taxonomy", "capabilities"):
        table[(component,)] = MAPPING
        table[(component, "path")] = TEXT
        repository((component,))
        # TCW-112 takes these two out when it removes the keys.
        table[(component, "extends")] = LIST
    work = ("work",)
    table[work] = MAPPING
    table[(*work, "path")] = TEXT
    repository(work)
    table[(*work, "backend")] = TEXT
    table[(*work, "tags")] = LIST
    table[(*work, "documentation")] = LIST
    table[(*work, "procedures")] = MAPPING
    for name in PROCEDURE_IDS:
        table[(*work, "procedures", name)] = LIST
    table[(*work, "stages")] = MAPPING
    kinds = {"enabled": BOOLEAN, "status": TEXT, "prompt": LIST, "pre": LIST,
             "post": LIST}
    for row in STAGES:
        table[(*work, "stages", row.name)] = MAPPING
        for key in (SIDE_STAGE_KEYS if row.kind == SIDE else STAGE_KEYS):
            table[(*work, "stages", row.name, key)] = kinds[key]
    table[(*work, "hooks")] = MAPPING
    for key in HOOK_KEYS:
        table[(*work, "hooks", key)] = NUMBER
    table.update(jira_keys())
    _TABLE = table
    return table


def jira_keys() -> dict[KeyPath, str]:
    """`work.jira` and every key under it (Design 1.1)."""
    from tcw.work.jira.config import CREDENTIAL_KEYS, FIELD_KEYS
    from tcw.work.model import PRIORITIES
    jira = ("work", "jira")
    table = {jira: MAPPING, (*jira, "site"): TEXT, (*jira, "project"): TEXT,
             (*jira, "credentials"): MAPPING}
    for key in CREDENTIAL_KEYS:
        table[(*jira, "credentials", key)] = TEXT
    table[(*jira, "fields")] = MAPPING
    for key in FIELD_KEYS:
        table[(*jira, "fields", key)] = TEXT
    table[(*jira, "priorities")] = MAPPING
    for key in PRIORITIES:
        table[(*jira, "priorities", key)] = TEXT
    table[(*jira, "issue-type")] = TEXT
    table[(*jira, "inbox-query")] = TEXT
    table[(*jira, "timeout")] = NUMBER
    return table


def _encode(part: str) -> str:
    return part.upper().replace("-", "_")


def key_part(key_path: KeyPath) -> str:
    """The key part of a variable's name: `work.jira.issue-type` is
    `WORK_JIRA_ISSUE_TYPE`."""
    return "_".join(_encode(str(part)) for part in key_path)


def override_name(key_path: KeyPath, project_id: str) -> str:
    """Design 4.1: the variable that sets `key_path` of `project_id`."""
    return f"TCW_{key_part(key_path)}__{_encode(project_id)}"


def decode_key(part: str) -> KeyPath | None:
    """The one key of the table whose encoding is `part`, or None."""
    global _BY_NAME
    if _BY_NAME is None:
        _BY_NAME = {key_part(path): path for path in known_keys()}
    return _BY_NAME.get(part)


def project_of(part: str) -> str:
    """A name's project part as a project ID: lower case, each `_` a `-`,
    which is unambiguous because IDs have no `_` (Design 4.4)."""
    return part.lower().replace("_", "-")


# ---------------------------------------------------------------------------
# Reading the variables


@dataclass(frozen=True)
class Override:
    """One override variable that passed every check: its name, the project
    it names, the key it sets and the value, read by the key's kind, already
    cut to what the allowed list lets it set."""

    name: str
    project: str
    key_path: KeyPath
    value: Any

    @property
    def mapping(self) -> dict:
        """The value as the layer it is merged as: nested under its key."""
        out: Any = self.value
        for part in reversed(self.key_path):
            out = {part: out}
        return out


MALFORMED = ("a variable starting TCW_ that holds '__' sets configuration, and is "
             "written TCW_<KEY>__<PROJECT>: the key's parts and the project ID in "
             "capitals, each '.' and '-' written '_'")


def is_override(name: str) -> bool:
    """Design 4.2: a name starting `TCW_` and holding `__`."""
    return name.startswith("TCW_") and "__" in name


def read_overrides(environ: Mapping[str, str]) -> tuple[dict[str, list[Override]], list]:
    """Every override variable in `environ`, checked (Design 4.2-4.7): the
    ones that passed, by the project they name, each project's fewest key
    parts first (the more specific applied later, so it wins); and a
    `tcw.config.Problem` for each that did not, none naming a value."""
    from tcw.config import Problem
    found: dict[str, list[Override]] = {}
    problems: list = []
    for name in sorted(n for n in environ if is_override(n)):
        override, found_problems = read_override(name, environ[name])
        problems += [Problem(None, (), message) for message in found_problems]
        if override is not None:
            found.setdefault(override.project, []).append(override)
    for overrides in found.values():
        overrides.sort(key=lambda o: len(o.key_path))
    return found, problems


def read_override(name: str, text: str) -> tuple[Override | None, list[str]]:
    """One override: what it sets, or None, and its problems' messages, each
    starting with the name."""
    from tcw.config import _allowed, _leads_to_allowed, _list_problems, _matches, \
        _PATTERNS, Origin, dotted
    from tcw.project_files import key_problems
    if not NAME.match(name):
        return None, [f"{name}: {MALFORMED}"]
    key, _, project = name[len("TCW_"):].partition("__")
    key_path = decode_key(key)
    if key_path is None:
        return None, [f"{name}: no configuration key is written {key}; a key's parts "
                      f"are joined by '_', and a '-' inside a part is written '_' too"]
    allowed = any(_matches(key_path, p) for p in _PATTERNS)
    if not allowed and not _leads_to_allowed(key_path):
        return None, [f"{name}: {dotted(key_path)} is a shared key; an environment "
                      f"variable cannot set it"]
    kind = known_keys()[key_path]
    if kind == TEXT:
        value: Any = text
    else:
        try:
            from tcw.store.yaml_source import UniqueKeyLoader
            value = yaml.load(text, UniqueKeyLoader)
        except yaml.YAMLError as error:
            if str(error).startswith("duplicate key"):
                return None, [f"{name}: is not valid YAML: a key appears twice"]
            return None, [f"{name}: is not valid YAML"]
        if value is None:
            return None, [f"{name}: null has no meaning in an environment variable; "
                          f"unset it instead"]
        wanted = {LIST: list, MAPPING: dict, NUMBER: (int, float), BOOLEAN: bool}[kind]
        if not isinstance(value, wanted) or (kind == NUMBER and isinstance(value, bool)):
            article = {LIST: "a list", MAPPING: "a mapping", NUMBER: "a number",
                       BOOLEAN: "true or false"}[kind]
            return None, [f"{name}: {dotted(key_path)} must be {article}"]
    origin = Origin("environment", variable=name, project=project_of(project))
    nested: Any = value
    for part in reversed(key_path):
        nested = {part: nested}
    messages: list[str] = []
    kept, problems = _allowed(nested, origin, None, [], variable=name)
    messages += [p.message for p in problems]
    messages += [f"{name}: {dotted(path)}: {message}"
                 for path, message in key_problems(kept)]
    messages += [f"{name}: {p.detail}" for p in _list_problems(kept, origin, None)]
    messages += _credential_problems(name, kept)
    if messages:
        return None, messages
    inner: Any = kept
    for part in key_path:
        if not isinstance(inner, dict) or part not in inner:
            return None, []
        inner = inner[part]
    return Override(name, project_of(project), tuple(key_path), inner), []


def _credential_problems(name: str, mapping: dict) -> list[str]:
    """A credential variable's name must look like one (TCW-71 Design 1); the
    value is never shown."""
    from tcw.config import dotted
    from tcw.work.jira.config import VARIABLE
    work = mapping.get("work")
    jira = work.get("jira") if isinstance(work, dict) else None
    credentials = jira.get("credentials") if isinstance(jira, dict) else None
    if not isinstance(credentials, dict):
        return []
    return [f"{name}: {dotted(('work', 'jira', 'credentials', key))} must name an "
            f"environment variable: capital letters, digits and _, not starting with "
            f"a digit (the value is not shown)"
            for key, value in credentials.items()
            if not isinstance(value, str) or not VARIABLE.match(value)]
