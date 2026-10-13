"""Recording what a real Jira site answers, for `recorded/` (TCW-71 Design 15.2,
plan Task 15).

The live scenario installs this when `TCW_JIRA_CAPTURE=<dir>` is set. It wraps
`urllib.request.urlopen`, the one call `JiraClient._request` makes, so it sees
error bodies as well as successful ones, and writes one file per endpoint and
status: the first answer seen, with the request that produced it.

Before writing, it replaces every account id, email address, display name and
the site's host with fixed values, so that `test_recorded_shapes.py` can fail
on any `@` or the real host left in a file.
"""

from __future__ import annotations

import io
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from tests.work.jira.fake import SITE

#: Jira keys, numeric ids and link ids in a path become placeholders, so one
#: endpoint is one file whatever ticket it was called on.
_KEY = re.compile(r"/[A-Z][A-Z0-9]+-\d+(?=/|$)")
_ID = re.compile(r"/\d+(?=/|$)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
#: Keys whose values name a person.
_PEOPLE = {"accountId": "acct", "displayName": "Person", "emailAddress": "person"}


def template(path: str, project: str = "") -> str:
    route = urllib.parse.urlsplit(path).path.removeprefix("/rest/api/3")
    route = _KEY.sub("/{key}", route)
    if project:
        route = re.sub(rf"/{re.escape(project)}(?=/|$)", "/{project}", route)
    return "/rest/api/3" + _ID.sub("/{id}", route)


def file_name(method: str, route: str, status: int) -> str:
    route = route.removeprefix("/rest/api/3/")
    words = re.sub(r"[^a-z0-9]+", "-", route.replace("{", "").replace("}", "").lower())
    return f"{method.lower()}-{words.strip('-')}-{status}.json"


class Recorder:
    def __init__(self, directory: Path, site: str, project: str = ""):
        # Absolute: the scenario changes directory into the project it drives.
        self.directory = Path(directory).resolve()
        self.project = project
        self.site = site.rstrip("/")
        self.host = urllib.parse.urlsplit(self.site).netloc
        self.people: dict[str, str] = {}

    # -- scrubbing --------------------------------------------------------------

    def _collect(self, value) -> None:
        """Note every person-naming value, so it is replaced wherever it occurs,
        including inside URLs and free text."""
        if isinstance(value, dict):
            for key, inner in value.items():
                if key in _PEOPLE and isinstance(inner, str) and inner \
                        and inner not in self.people:
                    count = sum(1 for v in self.people.values()
                                if v.startswith(_PEOPLE[key]))
                    stand_in = f"{_PEOPLE[key]}-{count + 1}"
                    if key == "displayName":
                        stand_in = f"Person {count + 1}"
                    self.people[inner] = stand_in
                self._collect(inner)
        elif isinstance(value, list):
            for inner in value:
                self._collect(inner)

    def scrub(self, text: str) -> str:
        try:
            self._collect(json.loads(text))
        except ValueError:
            pass
        for real in sorted(self.people, key=len, reverse=True):
            text = text.replace(real, self.people[real])
            text = text.replace(urllib.parse.quote(real, safe=""), self.people[real])
        text = _EMAIL.sub("person-at-example", text)
        site_host = urllib.parse.urlsplit(SITE).netloc
        return text.replace(self.host, site_host).replace("%40", "-at-")

    # -- recording ---------------------------------------------------------------

    def record(self, method: str, url: str, sent: bytes | None, status: int,
               body: bytes) -> None:
        path = url.removeprefix(self.site)
        route = template(path, self.project)
        target = self.directory / file_name(method, route, status)
        if target.exists():
            return
        try:
            response = json.loads(body) if body else None
        except ValueError:
            response = body.decode("utf-8", "replace")
        entry = {
            "method": method,
            "template": route,
            "path": path,
            "status": status,
            "request": json.loads(sent) if sent else None,
            "response": response,
        }
        self.directory.mkdir(parents=True, exist_ok=True)
        target.write_text(self.scrub(json.dumps(entry, indent=2, sort_keys=True)) + "\n",
                          encoding="utf-8")

    def install(self, monkeypatch) -> "Recorder":
        real = urllib.request.urlopen

        def urlopen(request, *args, **kwargs):
            method, url, sent = request.get_method(), request.full_url, request.data
            try:
                with real(request, *args, **kwargs) as response:
                    status, headers, body = (response.status, response.headers,
                                             response.read())
            except urllib.error.HTTPError as error:
                body = error.read()
                self.record(method, url, sent, error.code, body)
                raise urllib.error.HTTPError(error.url, error.code, error.msg,
                                             error.headers, io.BytesIO(body)) from None
            self.record(method, url, sent, status, body)
            return _Answer(status, headers, body)

        monkeypatch.setattr(urllib.request, "urlopen", urlopen)
        return self


class _Answer:
    """What `_request` reads from `urlopen`: a context manager with `status`,
    `headers` and `read()`."""

    def __init__(self, status, headers, body: bytes):
        self.status, self.headers, self._body = status, headers, body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        return None
