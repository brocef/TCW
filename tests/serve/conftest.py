"""Fixtures for the web viewer: a filesystem-mode project, a server on a free
port in a thread, and a request helper that can send any `Host` and `Origin`,
or none."""

from __future__ import annotations

import http.client
import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
import yaml

from tcw.serve.server import HOST, TcwServer
from tcw.serve.services import Services
from tests.work.projects import commit_all, make_project

UNSET = object()


@dataclass
class Response:
    status: int
    headers: dict[str, str]
    body: bytes

    @property
    def json(self) -> Any:
        return json.loads(self.body)

    @property
    def text(self) -> str:
        return self.body.decode("utf-8")


@dataclass
class Served:
    root: Path
    server: TcwServer
    port: int
    default_headers: dict[str, str] = field(default_factory=dict)

    @property
    def host(self) -> str:
        return f"{HOST}:{self.port}"

    def request(self, method: str, path: str, body: Any = UNSET, *,
                host: "str | None | object" = UNSET, origin: str | None = None,
                content_type: "str | None | object" = UNSET,
                raw: bytes | None = None,
                headers: dict[str, str] | None = None) -> Response:
        """One request. `host=None` sends no `Host`; `raw` sends those bytes
        as the body; a body is JSON unless `content_type` says otherwise."""
        connection = http.client.HTTPConnection(HOST, self.port, timeout=30)
        try:
            connection.putrequest(method, path, skip_host=True,
                                  skip_accept_encoding=True)
            sent_host = self.host if host is UNSET else host
            if sent_host is not None:
                connection.putheader("Host", sent_host)
            if origin is not None:
                connection.putheader("Origin", origin)
            payload = raw if raw is not None else \
                (None if body is UNSET else json.dumps(body).encode("utf-8"))
            if payload is not None:
                kind = "application/json" if content_type is UNSET else content_type
                if kind is not None:
                    connection.putheader("Content-Type", kind)
                if "Content-Length" not in (headers or {}):
                    connection.putheader("Content-Length", str(len(payload)))
            for name, value in {**self.default_headers, **(headers or {})}.items():
                connection.putheader(name, value)
            connection.endheaders(payload)
            answer = connection.getresponse()
            return Response(answer.status, {k.lower(): v for k, v in answer.getheaders()},
                            answer.read())
        finally:
            connection.close()

    def get(self, path: str, **kw) -> Response:
        return self.request("GET", path, **kw)

    def post(self, path: str, body: Any, **kw) -> Response:
        return self.request("POST", path, body, **kw)

    def put(self, path: str, body: Any, **kw) -> Response:
        return self.request("PUT", path, body, **kw)

    def patch(self, path: str, body: Any, **kw) -> Response:
        return self.request("PATCH", path, body, **kw)


def start(root: Path, services: Services | None = None) -> tuple[TcwServer, threading.Thread]:
    server = TcwServer((HOST, 0), root, services=services)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


@pytest.fixture
def serve_project():
    """Start a server on `root` (with optional services); stopped at teardown."""
    started: list[tuple[TcwServer, threading.Thread]] = []

    def run(root: Path, services: Services | None = None) -> Served:
        server, thread = start(root, services)
        started.append((server, thread))
        return Served(root, server, server.server_port)

    yield run
    for server, thread in started:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)


def fs_project(tmp_path: Path, project_id: str = "p", *, tags=("ui", "api"),
               user: str | None = "ann", config: dict | None = None,
               monkeypatch=None) -> Path:
    """A filesystem-mode project in a git repository, with `user.name` set in
    its personal file (TCW-72). Every work key the code branches on is passed
    here explicitly by the caller through `config`."""
    work = {"tags": list(tags)} if config is None else config
    root = make_project(tmp_path, project_id, config=work)
    if user is not None:
        (root / "tcw-config.local.yaml").write_text(
            yaml.safe_dump({"user": {"name": user}}))
    commit_all(root)
    return root


@pytest.fixture
def personal_on(monkeypatch):
    """Personal configuration read again, from the project's local file."""
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG", raising=False)


@pytest.fixture
def fs(tmp_path, personal_on, serve_project) -> Served:
    return serve_project(fs_project(tmp_path))


@pytest.fixture
def records_root(tmp_path) -> Path:
    """A project with every store, for the taxonomy and capability routes."""
    from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore, init
    from tests.work.projects import git
    root = tmp_path / "r"
    root.mkdir()
    git(root, "init", "-q")
    init([], root, "r")
    FsTaxonomyStore.open(root).add("Work item", slug="work-item")
    FsTaxonomyStore.open(root).add("Admin", slug="admin")
    FsCapabilitiesStore.open(root).add("web", "Web app", status="Missing")
    return root


@pytest.fixture
def records(records_root, serve_project) -> Served:
    return serve_project(records_root)
