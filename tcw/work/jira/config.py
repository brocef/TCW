"""`work.jira`, and a connected project's `jira` block (TCW-71 Design 1, 8).

TCW-69's `parse_work_config` passes `work.jira` through unparsed; this module
reads it. Values are never secrets: the configuration names the environment
variables that hold the credentials, and only the client reads their values,
inside `_request`. So a malformed credential variable name is reported by its
key and the rule it breaks, never by its value, which may be a token pasted
into the wrong place.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from tcw.work.config import ConfigProblem, KeyPath
from tcw.work.model import PRIORITIES

SITE = re.compile(r"^https://[A-Za-z0-9.-]+(:[0-9]+)?$")
PROJECT_KEY = re.compile(r"^[A-Z][A-Z0-9_]+$")
VARIABLE = re.compile(r"^[A-Z_][A-Z0-9_]*$")

#: Jira's priority names when `priorities` maps none, in the order of
#: `PRIORITIES` (highest first).
DEFAULT_PRIORITY_NAMES = ("Highest", "High", "Medium", "Low", "Lowest")
DEFAULT_ISSUE_TYPE = "Task"
DEFAULT_TIMEOUT = 15

KEYS = ("site", "project", "credentials", "fields", "priorities", "issue-type",
        "inbox-query", "timeout")
REQUIRED = ("site", "project", "credentials", "fields")
CREDENTIAL_KEYS = ("email-env", "token-env")
FIELD_KEYS = ("project", "item", "effort", "complexity")
REQUIRED_FIELDS = ("project", "item")
DELEGATION_KEYS = ("site", "project", "inbox-status", "credentials", "fields")


@dataclass(frozen=True)
class JiraFields:
    """Jira field *display names*; they are resolved to field ids at run time
    from the project's create metadata (Design 12)."""
    project: str
    item: str
    effort: str | None = None
    complexity: str | None = None


@dataclass(frozen=True)
class JiraConfig:
    """`work.jira`, parsed. `site`, `timeout`, `email_env` and `token_env` are
    the attributes the client reads."""
    site: str
    project: str
    email_env: str
    token_env: str
    fields: JiraFields
    priorities: Mapping[str, str] = field(
        default_factory=lambda: dict(zip(PRIORITIES, DEFAULT_PRIORITY_NAMES)))
    issue_type: str = DEFAULT_ISSUE_TYPE
    inbox_query: str | None = None
    timeout: float = DEFAULT_TIMEOUT


@dataclass(frozen=True)
class DelegationTarget:
    """A connected project's `jira` block: what delegation needs to create a
    ticket in a Jira-mode project that is not on this machine."""
    site: str
    project: str
    inbox_status: str
    email_env: str
    token_env: str
    project_field: str
    timeout: float = DEFAULT_TIMEOUT


class _Problems(list):
    def add(self, path: KeyPath, message: str) -> None:
        self.append(ConfigProblem(tuple(path), message))


def _kind(value: Any) -> str:
    return type(value).__name__


def _mapping(raw: Any, where: KeyPath, problems: _Problems) -> dict | None:
    if not isinstance(raw, dict):
        problems.add(where, f"expected a mapping, got {_kind(raw)}")
        return None
    return raw


def _unknown(raw: dict, known: tuple[str, ...], where: KeyPath,
             problems: _Problems) -> None:
    for key in sorted(map(str, set(raw) - set(known))):
        problems.add((*where, key), f"unknown key; expected one of {', '.join(known)}")


def _missing(raw: dict, required: tuple[str, ...], where: KeyPath,
             problems: _Problems) -> bool:
    absent = [k for k in required if k not in raw]
    for key in absent:
        problems.add((*where, key), "required")
    return bool(absent)


def _text(raw: dict, key: str, where: KeyPath, problems: _Problems) -> str | None:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        problems.add((*where, key), "must be a non-empty string")
        return None
    return value


def _site(raw: dict, where: KeyPath, problems: _Problems) -> str | None:
    value = _text(raw, "site", where, problems)
    if value is not None and not SITE.match(value):
        problems.add((*where, "site"),
                     "must be https://<host>, with no path and no trailing /")
        return None
    return value


def _project(raw: dict, where: KeyPath, problems: _Problems) -> str | None:
    value = _text(raw, "project", where, problems)
    if value is not None and not PROJECT_KEY.match(value):
        problems.add((*where, "project"),
                     "must be a Jira project key: capital letters, digits and _, "
                     "starting with a letter")
        return None
    return value


def _credentials(raw: dict, where: KeyPath,
                 problems: _Problems) -> tuple[str, str] | None:
    path = (*where, "credentials")
    block = _mapping(raw.get("credentials"), path, problems)
    if block is None:
        return None
    _unknown(block, CREDENTIAL_KEYS, path, problems)
    if _missing(block, CREDENTIAL_KEYS, path, problems):
        return None
    names = []
    for key in CREDENTIAL_KEYS:
        value = block[key]
        # The value is never echoed: it may be a token pasted here by mistake.
        if not isinstance(value, str) or not VARIABLE.match(value):
            problems.add((*path, key),
                         "must name an environment variable: capital letters, "
                         "digits and _, not starting with a digit (the value is "
                         "not shown)")
            return None
        names.append(value)
    return names[0], names[1]


def _timeout(raw: dict, where: KeyPath, problems: _Problems) -> float | None:
    value = raw.get("timeout", DEFAULT_TIMEOUT)
    try:
        good = (not isinstance(value, bool) and isinstance(value, (int, float))
                and math.isfinite(value) and value > 0)
    except OverflowError:
        good = False
    if not good:
        problems.add((*where, "timeout"), "must be a positive number of seconds")
        return None
    return float(value)


def parse_jira_config(raw: Any) -> tuple[JiraConfig | None, list[ConfigProblem]]:
    """`work.jira` as a `JiraConfig`, and every problem with it. The config is
    `None` whenever there is any problem."""
    where: KeyPath = ("work", "jira")
    problems = _Problems()
    block = _mapping(raw, where, problems)
    if block is None:
        return None, problems
    _unknown(block, KEYS, where, problems)
    _missing(block, REQUIRED, where, problems)
    site = _site(block, where, problems) if "site" in block else None
    project = _project(block, where, problems) if "project" in block else None
    credentials = (_credentials(block, where, problems)
                   if "credentials" in block else None)

    fields = None
    if "fields" in block:
        path = (*where, "fields")
        given = _mapping(block["fields"], path, problems)
        if given is not None:
            _unknown(given, FIELD_KEYS, path, problems)
            _missing(given, REQUIRED_FIELDS, path, problems)
            names = {k: _text(given, k, path, problems) for k in FIELD_KEYS if k in given}
            fields = JiraFields(names.get("project") or "", names.get("item") or "",
                                names.get("effort"), names.get("complexity"))

    priorities = dict(zip(PRIORITIES, DEFAULT_PRIORITY_NAMES))
    if "priorities" in block:
        path = (*where, "priorities")
        given = _mapping(block["priorities"], path, problems)
        if given is not None:
            _unknown(given, tuple(PRIORITIES), path, problems)
            for key in PRIORITIES:
                if key in given:
                    name = _text(given, key, path, problems)
                    if name is not None:
                        priorities[key] = name

    issue_type = DEFAULT_ISSUE_TYPE
    if "issue-type" in block:
        issue_type = _text(block, "issue-type", where, problems) or issue_type
    inbox_query = None
    if "inbox-query" in block:
        inbox_query = _text(block, "inbox-query", where, problems)
    timeout = _timeout(block, where, problems)

    if problems:
        return None, problems
    return JiraConfig(site=site, project=project, email_env=credentials[0],
                      token_env=credentials[1], fields=fields, priorities=priorities,
                      issue_type=issue_type, inbox_query=inbox_query,
                      timeout=timeout), problems


def parse_delegation_block(raw: Any, where: KeyPath
                           ) -> tuple[DelegationTarget | None, list[ConfigProblem]]:
    """A connected project's `jira` block, `{site, project, inbox-status,
    credentials: {email-env, token-env}, fields: {project}}`, with the same
    rules as `work.jira`. `where` is the entry's key path."""
    where = tuple(where)
    problems = _Problems()
    block = _mapping(raw, where, problems)
    if block is None:
        return None, problems
    _unknown(block, DELEGATION_KEYS, where, problems)
    _missing(block, DELEGATION_KEYS, where, problems)
    site = _site(block, where, problems) if "site" in block else None
    project = _project(block, where, problems) if "project" in block else None
    inbox = _text(block, "inbox-status", where, problems) if "inbox-status" in block \
        else None
    credentials = (_credentials(block, where, problems)
                   if "credentials" in block else None)
    project_field = None
    if "fields" in block:
        path = (*where, "fields")
        given = _mapping(block["fields"], path, problems)
        if given is not None:
            _unknown(given, ("project",), path, problems)
            if not _missing(given, ("project",), path, problems):
                project_field = _text(given, "project", path, problems)
    if problems:
        return None, problems
    return DelegationTarget(site=site, project=project, inbox_status=inbox,
                            email_env=credentials[0], token_env=credentials[1],
                            project_field=project_field), problems


def connected_block_problems(raw_config: Any) -> list[ConfigProblem]:
    """The problems of every `jira` block among a project's own
    `connected-projects` entries, by key path."""
    problems: list[ConfigProblem] = []
    sections = raw_config.get("connected-projects") if isinstance(raw_config, dict) \
        else None
    if not isinstance(sections, dict):
        return problems
    for relation, entries in sections.items():
        if not isinstance(entries, dict):
            continue
        for project_id, entry in entries.items():
            if isinstance(entry, dict) and "jira" in entry:
                problems.extend(parse_delegation_block(
                    entry["jira"], ("connected-projects", str(relation),
                                    str(project_id), "jira"))[1])
    return problems
