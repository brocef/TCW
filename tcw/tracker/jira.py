"""A Jira Cloud REST client, standard library only.

TCW ships with PyYAML and nothing else, and that does not change for this. So the
transport is `urllib.request`, with a basic-authentication header built by hand.

**One seam.** Every operation goes through `JiraClient._request`, which is the only
function here that touches `urllib.request`. Tests replace it. That is a design
decision rather than an accident: with `urlopen` called inline in four places the
only way to test would be a live server or a monkeypatched module attribute, and
several of this item's acceptance criteria depend on substituting the transport.

**Two writes, and their responses are never interpreted.** `apply_transition` and
`assign` exist for claiming a ticket. What a write returns is read only as success
or as one of the error types below; whether a claim actually took effect is decided
by the caller re-reading the issue (`tcw/tracker/intake.py`).

**The error taxonomy is a deliverable, not an afterthought.** A live experiment
against Jira recorded *three different* `HTTP 400` bodies for the same logical
condition — a transition that did not apply — one of which blames permissions for
what was actually a lost race. So a status code says what failed and nothing
reliable about why. Callers get a typed exception per cause and are expected to
re-read state to decide, never to parse a message. Nothing here is named
"conflict" or "already claimed", and `tests/test_tracker_client.py` fails if that
changes.
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

DEFAULT_SEARCH_LIMIT = 50


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
    """One transition an issue offers right now."""
    id: str
    name: str
    to_status: str
    to_status_id: str = ""


@dataclass(frozen=True)
class SearchResult:
    """Issues the query selected, and whether there were more.

    `truncated` exists because silently returning a short list would make a user
    believe they have no other assigned tickets.

    **There is no total.** The endpoint this uses reports only whether the page it
    returned is the last one; it does not count matches. An earlier version of this
    class carried a `total` read from the old `/rest/api/3/search`, which Atlassian
    has since removed outright — the live error names the replacement and links a
    migration note. Inventing a total from a page size would be a number that looks
    authoritative and is not.
    """
    issues: list[dict]
    truncated: bool


# ── the client ───────────────────────────────────────────────────────────────


class JiraClient:
    """The Jira Cloud operations TCW needs: four reads and the two claim writes.

    Holds a `TrackerConfig`, which carries the *names* of the two environment
    variables. The values are read in `_request` and nowhere else, so an instance
    that never makes a call never touches a secret.
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
                f"tracker credentials are not set: {', '.join(missing)}. "
                f"Export them, or correct work.tracker.credentials in tcw-config.yaml.")

        payload = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            f"{self.config.base_url}{path}", data=payload, method=method)
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
                f"could not reach the tracker at {self.config.base_url} "
                f"({error.reason}); the timeout was {timeout}s") from error
        except (socket.timeout, TimeoutError) as error:
            raise TrackerUnavailable(
                f"the tracker at {self.config.base_url} did not respond within "
                f"{timeout}s") from error
        except (ConnectionError, http.client.HTTPException) as error:
            # A connection dropped after the request was sent is neither a
            # `URLError` nor a timeout (`http.client.RemoteDisconnected` is both a
            # `ConnectionResetError` and an `HTTPException`). The request may have
            # landed, so it is "unavailable" — which a claim answers by reading
            # the issue back — never an uncaught crash.
            raise TrackerUnavailable(
                f"the connection to the tracker at {self.config.base_url} was lost "
                f"before it answered ({error.__class__.__name__})") from error

    def _json(self, method: str, path: str, body: dict | None = None) -> dict:
        _status, _headers, raw = self._request(
            method, path, body, timeout=self.config.timeout_seconds)
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except ValueError as error:
            raise TrackerError(
                f"the tracker returned a response that is not JSON for {path}") from error

    # -- operations --

    def myself(self) -> dict:
        """The account the configured credentials authenticate as."""
        return self._json("GET", "/rest/api/3/myself")

    def search(self, jql: str, limit: int = DEFAULT_SEARCH_LIMIT) -> SearchResult:
        """Issues the query selects, and whether there are more pages.

        `/rest/api/3/search/jql`, not `/rest/api/3/search`. The latter has been
        **removed**: a live call returns 400 with "The requested API has been
        removed. Please migrate to the /rest/api/3/search/jql API." Found by running
        this code against a real site rather than by reading a changelog.

        The replacement is token-paginated and reports `isLast` instead of a match
        count, so there is no total to report. Only the first page is fetched: this
        item lists what a developer should look at next, and walking every page of a
        badly-scoped query is not that.
        """
        payload = self._json("POST", "/rest/api/3/search/jql", {
            "jql": jql,
            "maxResults": limit,
            "fields": ["summary", "status", "assignee"],
        })
        issues = payload.get("issues") or []
        # `isLast` absent is treated as "this is the last page": a response that
        # does not say there is more must not be reported as truncated.
        return SearchResult(issues=issues, truncated=payload.get("isLast") is False)

    def issue(self, key: str) -> dict:
        """One issue, with the fields this item prints.

        `key` is whatever the user typed, so it is quoted: a slash in it must not
        address a different resource. Jira accepts a numeric issue id here too.
        """
        quoted = urllib.parse.quote(key, safe="")
        return self._json(
            "GET", f"/rest/api/3/issue/{quoted}?fields=summary,status,assignee,description")

    def transitions(self, key: str) -> list[Transition]:
        """The transitions this issue offers **right now**, from its current status.

        This is the whole basis of the claimability report: it needs no permission
        beyond viewing the issue, and it behaves the same on team-managed and
        company-managed projects, which is why it was chosen over reading a
        project's workflow definition.
        """
        payload = self._json("GET", f"/rest/api/3/issue/{key}/transitions")
        out: list[Transition] = []
        for raw in payload.get("transitions") or []:
            to = raw.get("to") or {}
            out.append(Transition(
                id=str(raw.get("id", "")),
                name=str(raw.get("name", "")),
                to_status=str(to.get("name", "")),
                to_status_id=str(to.get("id", "")),
            ))
        return out


    def apply_transition(self, issue_id: str, transition_id: str) -> None:
        """Apply one transition. Success says only that Jira accepted the request.

        A refused transition raises `TrackerRequestInvalid` whatever the reason —
        a lost race, a validator, a misconfigured id — so the caller re-reads the
        issue to learn what happened.
        """
        self._json("POST", f"/rest/api/3/issue/{issue_id}/transitions",
                   {"transition": {"id": transition_id}})

    def assign(self, issue_id: str, account_id: str | None) -> None:
        """Assign the issue to an account. Overwrites whatever assignee it had.

        `None` unassigns it, which is what Jira documents `{"accountId": null}` to
        mean. An empty string is not an account id and is answered with 400, so
        callers wanting nobody to hold the ticket pass `None` rather than `""`.

        A project configured to forbid unassigned issues refuses the unassignment
        with 400 as well, which surfaces as `TrackerRequestInvalid`. That is a
        refusal a caller reports, not a bug — and no fake can produce it, so it is
        the one behaviour here that only a live project confirms.
        """
        self._json("PUT", f"/rest/api/3/issue/{issue_id}/assignee",
                   {"accountId": account_id})

    def description(self, issue_id: str) -> str:
        """The issue's description as text, or `""`.

        From the **v2** endpoint, which returns the description as a wiki-markup
        string. The v3 endpoint returns a rich-text document tree that would need
        converting, and a converter that silently drops parts of a description is
        worse than markup a person can read.
        """
        payload = self._json("GET", f"/rest/api/2/issue/{issue_id}?fields=description")
        value = (payload.get("fields") or {}).get("description")
        return value if isinstance(value, str) else ""

    def add_comment(self, issue_id: str, document: dict) -> None:
        """Add a comment, given as a Jira document. The v3 document, not v2's wiki
        markup, in which square brackets are link syntax and text would not read
        back as written."""
        self._json("POST", f"/rest/api/3/issue/{issue_id}/comment", {"body": document})

    def recent_comments(self, issue_id: str) -> list[tuple[str, str]]:
        """The newest page of comments, newest first, as `(author account id, text)`.
        The text is the document's text nodes joined, a line per block."""
        payload = self._json(
            "GET", f"/rest/api/3/issue/{issue_id}/comment?orderBy=-created&maxResults=100")
        out = []
        for raw in payload.get("comments") or []:
            author = raw.get("author") if isinstance(raw.get("author"), dict) else {}
            out.append((str(author.get("accountId", "")), _document_text(raw.get("body"))))
        return out


def _document_text(node) -> str:
    """The text of a Jira document: text nodes joined, one line per top-level block."""
    def walk(value) -> str:
        if not isinstance(value, dict):
            return ""
        if value.get("type") == "text":
            return str(value.get("text", ""))
        return "".join(walk(child) for child in value.get("content") or [])
    if not isinstance(node, dict):
        return ""
    return "\n".join(walk(block) for block in node.get("content") or [])


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
            f"variables named in work.tracker.credentials. {detail}".strip())
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
