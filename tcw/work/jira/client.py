"""A Jira Cloud REST client, standard library only.

This module is the single home of all Jira HTTP work in TCW, so that a second
Jira client never gets written. It imports nothing from the rest of TCW.

TCW ships with PyYAML and nothing else, and that does not change for this. So the
transport is `urllib.request`, with a basic-authentication header built by hand.

**One seam.** Every operation goes through `JiraClient._request`, which is the only
function here that touches `urllib.request`. Tests replace it, and the fake Jira
(`tests/work/jira/fake.py`) is installed there.

**Writes are never interpreted.** What a write returns is read only as success or
as one of the error types below; whether it took effect is decided by the caller
reading the issue back.

**The error taxonomy is a deliverable, not an afterthought.** A live experiment
against Jira recorded *three different* `HTTP 400` bodies for the same logical
condition — a transition that did not apply — one of which blames permissions for
what was actually a lost race. So a status code says what failed and nothing
reliable about why. Callers get a typed exception per cause and are expected to
re-read state to decide, never to parse a message. Nothing here is named
"conflict" or "already claimed", and `tests/work/jira/test_client.py` fails if
that changes.
"""
from __future__ import annotations

import base64
import http.client
import json
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

#: Jira's largest page for searches and comment reads.
PAGE = 100


# ── errors ───────────────────────────────────────────────────────────────────


class TrackerError(Exception):
    """Anything that stopped a tracker call from succeeding."""


class TrackerAuthError(TrackerError):
    """The credentials were rejected (401), or are absent."""


class TrackerPermissionError(TrackerError):
    """Authenticated, but not allowed to see or touch this resource (403)."""


class TrackerNotFound(TrackerError):
    """No such issue, project or resource (404)."""


class TrackerRequestInvalid(TrackerError):
    """The tracker refused the request (400).

    **Deliberately not named for contention.** A rejected transition, a
    misconfigured transition id and a lost claim race all arrive here with
    different message bodies and the same status. Deciding which happened needs a
    re-read of the issue, and that decision does not belong to the transport.
    """


class TrackerRateLimited(TrackerError):
    """The tracker is rate limiting (429). `retry_after` when it said so."""

    def __init__(self, message: str, retry_after: str | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class TrackerUnavailable(TrackerError):
    """The tracker could not be reached: 5xx, a refused connection, a timeout."""


# ── values ───────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Transition:
    """One transition an issue offers right now, with what its screen shows.

    `fields` are the ids of every field on the transition's screen and
    `required` the ids of those Jira marks required; both are empty for a
    transition with no screen."""
    id: str
    name: str
    to_status: str
    to_status_id: str = ""
    fields: tuple[str, ...] = ()
    required: tuple[str, ...] = ()


@dataclass(frozen=True)
class JiraComment:
    """One comment as Jira gives it. `body` is the Atlassian Document Format
    (ADF) tree, turned into text by `tcw.work.jira.mapping.document_text`."""
    author_id: str | None
    author_name: str | None
    created: str
    body: object


# ── the client ───────────────────────────────────────────────────────────────


class JiraClient:
    """The Jira Cloud operations the Jira work backend needs.

    Holds a `JiraConfig` (`tcw.work.jira.config`), read by attribute: `site`,
    `timeout`, and the *names* of the two credential variables, `email_env` and
    `token_env`. The values are read in `_request` and nowhere else, so an
    instance that never makes a call never touches a secret.
    """

    def __init__(self, config):
        self.config = config

    # -- the only place urllib is touched, and the only place secrets are read --

    def _request(self, method: str, path: str, body: dict | None = None,
                 *, timeout: float | None = None) -> tuple[int, dict, bytes]:
        """Make one request. Returns `(status, headers, body_bytes)`.

        `timeout` is a parameter rather than read from the config here, so that
        every caller has to pass it and one test can walk the operations and prove
        they all do. `urlopen` with no timeout falls back to the global socket
        default, which is unset, making the omission an indefinite hang.
        """
        email = os.environ.get(self.config.email_env, "").strip()
        token = os.environ.get(self.config.token_env, "").strip()
        missing = [name for name, value in
                   ((self.config.email_env, email), (self.config.token_env, token))
                   if not value]
        if missing:
            raise TrackerAuthError(
                f"Jira credentials are not set: {', '.join(missing)}. "
                f"Export them, or correct work.jira.credentials in tcw-config.yaml.")

        payload = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            f"{self.config.site}{path}", data=payload, method=method)
        credentials = base64.b64encode(f"{email}:{token}".encode("utf-8")).decode("ascii")
        request.add_header("Authorization", f"Basic {credentials}")
        request.add_header("Accept", "application/json")
        if payload is not None:
            request.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.status, dict(response.headers), response.read()
        except urllib.error.HTTPError as error:
            detail = ""
            try:
                detail = error.read().decode("utf-8", "replace")[:500]
            except Exception:                      # noqa: BLE001 - detail is a bonus
                pass
            raise _for_status(error.code, dict(error.headers or {}), detail, path) from error
        except urllib.error.URLError as error:
            # Covers a refused connection, DNS failure and a timeout: `URLError`
            # wraps `socket.timeout` rather than letting it through.
            raise TrackerUnavailable(
                f"could not reach the tracker at {self.config.site} "
                f"({error.reason}); the timeout was {timeout}s") from error
        except (socket.timeout, TimeoutError) as error:
            raise TrackerUnavailable(
                f"the tracker at {self.config.site} did not respond within "
                f"{timeout}s") from error
        except (ConnectionError, http.client.HTTPException) as error:
            # A connection dropped after the request was sent is neither a
            # `URLError` nor a timeout (`http.client.RemoteDisconnected` is both a
            # `ConnectionResetError` and an `HTTPException`). The request may have
            # landed, so it is "unavailable" — which a claim answers by reading
            # the issue back — never an uncaught crash.
            raise TrackerUnavailable(
                f"the connection to the tracker at {self.config.site} was lost "
                f"before it answered ({error.__class__.__name__})") from error

    def _json(self, method: str, path: str, body: dict | None = None) -> dict:
        return _mapping(self._payload(method, path, body), path)

    def _payload(self, method: str, path: str, body: dict | None = None):
        """The decoded answer, whatever its shape; `{}` for an empty body."""
        _status, _headers, raw = self._request(
            method, path, body, timeout=self.config.timeout)
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except ValueError as error:
            raise TrackerError(
                f"the tracker returned a response that is not JSON for {path}") from error

    # -- operations: reads --

    def myself(self) -> dict:
        """The account the configured credentials authenticate as."""
        return self._json("GET", "/rest/api/3/myself")

    def issue(self, key: str, fields: tuple[str, ...] | list[str] = ()) -> dict:
        """One issue, with `fields` (every field Jira returns by default when
        none are named)."""
        path = f"/rest/api/3/issue/{_quote(key)}"
        if fields:
            path += "?fields=" + ",".join(urllib.parse.quote(f, safe="") for f in fields)
        return _check_issue(self._json("GET", path), path)

    def search(self, jql: str, fields: tuple[str, ...] | list[str],
               limit: int | None = None) -> list[dict]:
        """Every issue the query selects, reading page after page; at most
        `limit` when given, which is how a sample of one costs one small page.

        `/rest/api/3/search/jql`, not `/rest/api/3/search`, which Atlassian has
        removed. The endpoint is paged by `nextPageToken` and says `isLast`; a
        list that stopped at the first page would hide items, so every page is
        read. `isLast` absent, or no token, ends the walk.
        """
        path = "/rest/api/3/search/jql"
        issues: list[dict] = []
        token = None
        while True:
            size = PAGE if limit is None else min(PAGE, limit - len(issues))
            body: dict = {"jql": jql, "fields": list(fields), "maxResults": size}
            if token:
                body["nextPageToken"] = token
            payload = self._json("POST", path, body)
            page = _entries(payload.get("issues"), path)
            for found in page:
                _check_issue(found, path)
            issues.extend(page)
            if limit is not None and len(issues) >= limit:
                return issues[:limit]
            token = payload.get("nextPageToken")
            if payload.get("isLast") is not False or not isinstance(token, str) \
                    or not token:
                return issues

    def transitions(self, key: str) -> list[Transition]:
        """The transitions this issue offers **right now**, from its current
        status, each with the fields its screen shows. It needs no permission
        beyond viewing the issue, and reads the same in team-managed and
        company-managed projects."""
        path = f"/rest/api/3/issue/{_quote(key)}/transitions?expand=transitions.fields"
        payload = self._json("GET", path)
        out: list[Transition] = []
        for raw in _entries(payload.get("transitions"), path):
            to = _mapping(raw.get("to"), path)
            screen = _mapping(raw.get("fields"), path)
            out.append(Transition(
                id=str(raw.get("id", "")),
                name=str(raw.get("name", "")),
                to_status=str(to.get("name", "")),
                to_status_id=str(to.get("id", "")),
                fields=tuple(str(f) for f in screen),
                required=tuple(str(f) for f, meta in screen.items()
                               if isinstance(meta, dict) and meta.get("required")),
            ))
        return out

    def comments(self, key: str, limit: int | None) -> list[JiraComment]:
        """Up to `limit` comments (all when None), newest first, page by page."""
        out: list[JiraComment] = []
        start = 0
        while limit is None or len(out) < limit:
            size = PAGE if limit is None else min(PAGE, limit - len(out))
            path = (f"/rest/api/3/issue/{_quote(key)}/comment?orderBy=-created"
                    f"&startAt={start}&maxResults={size}")
            payload = self._json("GET", path)
            page = _entries(payload.get("comments"), path)
            for raw in page:
                author = _mapping(raw.get("author"), path)
                _text(author.get("accountId"), path)
                _text(author.get("displayName"), path)
                _text(raw.get("created"), path)
                out.append(JiraComment(
                    author_id=author.get("accountId") or None,
                    author_name=author.get("displayName") or None,
                    created=str(raw.get("created") or ""),
                    body=raw.get("body")))
            start += len(page)
            total = payload.get("total")
            if not page or (isinstance(total, int) and start >= total):
                break
        return out if limit is None else out[:limit]

    def user(self, account_id: str) -> dict:
        """One account, by id."""
        return self._json("GET", "/rest/api/3/user?accountId="
                          + urllib.parse.quote(account_id, safe=""))

    def assignable_users(self, project: str, query: str, limit: int) -> list[dict]:
        """The project's assignable users matching `query`."""
        path = ("/rest/api/3/user/assignable/search?project="
                + urllib.parse.quote(project, safe="")
                + "&query=" + urllib.parse.quote(query, safe="")
                + f"&maxResults={int(limit)}")
        return _entries(self._payload("GET", path), path)

    def project(self, key: str) -> dict:
        """The project, with its issue types and their hierarchy levels."""
        path = f"/rest/api/3/project/{_quote(key)}"
        payload = self._json("GET", path)
        _entries(payload.get("issueTypes"), path)
        return payload

    def project_statuses(self, key: str) -> list[dict]:
        """Each issue type of the project with the statuses it can be in."""
        path = f"/rest/api/3/project/{_quote(key)}/statuses"
        types = _entries(self._payload("GET", path), path)
        for kind in types:
            _entries(kind.get("statuses"), path)
        return types

    def create_metadata(self, project: str, issue_type_id: str) -> list[dict]:
        """Every field on the create screen of one issue type, page by page."""
        out: list[dict] = []
        start = 0
        while True:
            path = (f"/rest/api/3/issue/createmeta/{_quote(project)}/issuetypes/"
                    f"{_quote(issue_type_id)}?startAt={start}&maxResults={PAGE}")
            payload = self._json("GET", path)
            page = _entries(payload.get("fields", payload.get("values")), path)
            out.extend(page)
            start += len(page)
            total = payload.get("total")
            if not page or not isinstance(total, int) or start >= total:
                return out

    def edit_metadata(self, key: str) -> dict:
        """The fields this issue's edit screen allows, keyed by field id."""
        path = f"/rest/api/3/issue/{_quote(key)}/editmeta"
        return _mapping(self._json("GET", path).get("fields"), path)

    def link_types(self) -> list[dict]:
        """Every issue link type on the site."""
        path = "/rest/api/3/issueLinkType"
        return _entries(self._json("GET", path).get("issueLinkTypes"), path)

    def workflows(self, project_id: str, issue_type_id: str) -> dict:
        """The workflow definitions for one project and issue type: the answer
        holds `workflows` and, beside them, the `statuses` their transitions
        refer to. Needs administrator rights on many sites; a refusal is the
        caller's to read (`TrackerPermissionError`)."""
        path = "/rest/api/3/workflows"
        payload = self._json("POST", path, {"projectAndIssueTypes": [
            {"projectId": str(project_id), "issueTypeId": str(issue_type_id)}]})
        _entries(payload.get("workflows"), path)
        _entries(payload.get("statuses"), path)
        return payload

    # -- operations: writes --

    def create_issue(self, fields: dict):
        """Create an issue from a whole `fields` mapping and return the answer,
        normally `{"id", "key"}`.

        As it came, not shape-checked: the request may have made the ticket
        whatever the answer looks like. The issue lands in whatever status the
        project's workflow starts in, which is why callers move it afterwards.
        """
        return self._payload("POST", "/rest/api/3/issue", {"fields": fields})

    def edit_issue(self, key: str, fields: dict | None = None,
                   update: dict | None = None) -> None:
        """One edit: `fields` set values, `update` holds operations such as
        adding or removing one label."""
        body: dict = {}
        if fields:
            body["fields"] = fields
        if update:
            body["update"] = update
        self._payload("PUT", f"/rest/api/3/issue/{_quote(key)}", body)

    def apply_transition(self, key: str, transition_id: str,
                         comment: dict | None = None) -> None:
        """Apply one transition, with `comment` (a document) in the same request
        when given. Success says only that Jira accepted the request; a refused
        transition raises `TrackerRequestInvalid` whatever the reason, so the
        caller reads the issue back to learn what happened."""
        body: dict = {"transition": {"id": transition_id}}
        if comment is not None:
            body["update"] = {"comment": [{"add": {"body": comment}}]}
        self._payload("POST", f"/rest/api/3/issue/{_quote(key)}/transitions", body)

    def add_comment(self, key: str, document: dict) -> None:
        """Add a comment, given as a Jira document (ADF), in which text needs no
        escaping."""
        self._payload("POST", f"/rest/api/3/issue/{_quote(key)}/comment",
                      {"body": document})

    def add_link(self, type_name: str, inward_key: str, outward_key: str) -> None:
        """Link two issues. Which side is which for `Blocks` is decided in one
        place, `tcw.work.jira.mapping.block_link`."""
        self._payload("POST", "/rest/api/3/issueLink", {
            "type": {"name": type_name},
            "inwardIssue": {"key": inward_key},
            "outwardIssue": {"key": outward_key}})

    def delete_link(self, link_id: str) -> None:
        self._payload("DELETE", f"/rest/api/3/issueLink/{_quote(link_id)}")


def _quote(segment: str) -> str:
    """A path segment taken from data, quoted so a `/` in it cannot address a
    different resource."""
    return urllib.parse.quote(str(segment), safe="")


def _shape_error(path: str) -> "TrackerError":
    return TrackerError(f"the tracker returned a response of an unexpected shape for {path}")


def _mapping(value, path: str) -> dict:
    """`value` if it is a mapping, `{}` for null (which the readers already treat as
    absent), otherwise a `TrackerError` — never an `AttributeError` further on,
    which no command handles."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    raise _shape_error(path)


def _entries(value, path: str) -> list:
    """A list of mappings, `[]` for null, otherwise a `TrackerError`."""
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(v, dict) for v in value):
        raise _shape_error(path)
    return value


def _text(value, path: str) -> None:
    """Refuse a value that is present and not a string: `{"name": 5}` reached
    `.strip()` and crashed `tracker show`."""
    if value is not None and not isinstance(value, str):
        raise _shape_error(path)


def _check_issue(issue, path: str) -> dict:
    """An issue whose `fields`, `status`, `statusCategory` and `assignee` are each a
    mapping or null — every level the claim and create paths read with `.get` —
    and whose values read from them are each a string or null."""
    issue = _mapping(issue, path)
    fields = _mapping(issue.get("fields"), path)
    status = _mapping(fields.get("status"), path)
    category = _mapping(status.get("statusCategory"), path)
    assignee = _mapping(fields.get("assignee"), path)
    for value in (issue.get("key"), fields.get("summary"), status.get("name"),
                  category.get("key"), assignee.get("accountId"),
                  assignee.get("displayName")):
        _text(value, path)
    return issue


def _for_status(status: int, headers: dict, detail: str, path: str) -> TrackerError:
    """Map an HTTP status onto a cause.

    `detail` is carried into the message as opaque text and **never parsed**. The
    experiment recorded three different 400 bodies for one condition, so reading
    them would encode a guess as a fact.
    """
    where = f" ({path})"
    if status == 401:
        return TrackerAuthError(
            f"the tracker rejected the credentials{where}. Check the values of the "
            f"variables named in work.jira.credentials. {detail}".strip())
    if status == 403:
        return TrackerPermissionError(
            f"the account is not permitted to see this{where}. {detail}".strip())
    if status == 404:
        return TrackerNotFound(f"the tracker has no such resource{where}. {detail}".strip())
    if status == 429:
        retry = None
        for key, value in headers.items():
            if key.lower() == "retry-after":
                retry = str(value)
        suffix = f" Retry after {retry}s." if retry else ""
        return TrackerRateLimited(
            f"the tracker is rate limiting requests{where}.{suffix}".strip(), retry)
    if status >= 500:
        return TrackerUnavailable(
            f"the tracker returned {status}{where}. {detail}".strip())
    return TrackerRequestInvalid(
        f"the tracker refused the request{where}. {detail}".strip())
