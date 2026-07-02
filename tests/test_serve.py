import json
import socket
import subprocess
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from tcw.cli import build_parser, main
from tcw.serve import HOST, TcwServer, _static_bytes
from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore, FsWorkStore, init


def node(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["taxonomy", "capabilities", "work"], root)
    return root


@pytest.fixture
def seeded_node(tmp_path):
    root = node(tmp_path)
    work = FsWorkStore.open(root)
    item = work.create("Build viewer", created="2026-01-01")
    d = work.path(item.slug)
    (d / "initial-request.md").write_text("# Request\n\nBrowse TCW.\n", encoding="utf-8")
    (d / "spec.md").write_text("spec\n", encoding="utf-8")
    work.set_field(item.slug, "blocked_by", [{"external": "vendor"}])
    (d / "capabilities.yaml").write_text("links:\n- web\n", encoding="utf-8")

    FsTaxonomyStore.open(root).add("Work Item", slug="work-item")
    FsCapabilitiesStore.open(root).add("web", "Browse TCW content", status="Missing")
    return root, item.slug


@pytest.fixture
def server(seeded_node):
    root, slug = seeded_node
    httpd = TcwServer((HOST, 0), root)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://{HOST}:{httpd.server_port}", slug
    httpd.shutdown()
    httpd.server_close()
    thread.join(timeout=2)


def get_json(base: str, path: str):
    with urlopen(f"{base}{path}") as res:
        return json.loads(res.read().decode("utf-8"))


def post(base: str, path: str):
    req = Request(f"{base}{path}", method="POST")
    with urlopen(req) as res:
        return res.status, res.read()


def test_help_lists_serve_group(capsys):
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--help"])
    assert "serve" in capsys.readouterr().out


def test_serve_outside_node_reports_helpfully(tmp_path, monkeypatch, capsys):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    monkeypatch.chdir(tmp_path)
    assert main(["serve", "--no-open"]) == 1
    assert "tcw init" in capsys.readouterr().err


def test_static_assets_resolve_from_package():
    body, ctype = _static_bytes("index.html")
    assert b'<script src="/app.js"' in body
    assert ctype.startswith("text/html")


def test_api_lists_all_three_axes(server):
    base, slug = server
    work = get_json(base, "/api/work")
    taxonomy = get_json(base, "/api/taxonomy")
    capabilities = get_json(base, "/api/capabilities")

    assert work[0]["slug"] == slug
    assert taxonomy[0]["slug"] == "work-item"
    assert capabilities[0]["ref"] == "web#browse-tcw-content"


def test_work_detail_includes_artifacts_without_paths(server):
    base, slug = server
    payload = get_json(base, f"/api/work/{slug}")

    assert payload["item"]["slug"] == slug
    assert payload["item"]["blocked_by"] == [{"external": "vendor"}]
    assert payload["item"]["capabilities"] == {"links": ["web"]}
    artifacts = {a["name"]: a for a in payload["artifacts"]}
    assert artifacts["initial-request"] == {"name": "initial-request", "present": True}
    assert artifacts["spec"] == {"name": "spec", "present": True}
    assert "locator" not in artifacts["spec"]


def test_open_endpoint_validates_inputs_without_popen(server, monkeypatch):
    base, slug = server
    calls = []
    monkeypatch.setattr("tcw.serve.subprocess.Popen", lambda argv: calls.append(argv))

    with pytest.raises(HTTPError) as bad_name:
        post(base, f"/api/work/{slug}/artifacts/../../etc/open")
    assert bad_name.value.code == 400

    with pytest.raises(HTTPError) as bad_slug:
        post(base, "/api/work/../../etc/artifacts/spec/open")
    assert bad_slug.value.code == 404

    with pytest.raises(HTTPError) as absent:
        post(base, f"/api/work/{slug}/artifacts/plan/open")
    assert absent.value.code == 404
    assert calls == []


def test_open_endpoint_launches_present_artifact(server, monkeypatch):
    base, slug = server
    calls = []
    monkeypatch.setattr("tcw.serve.subprocess.Popen", lambda argv: calls.append(argv))

    status, body = post(base, f"/api/work/{slug}/artifacts/spec/open")

    assert status == 204
    assert body == b""
    assert len(calls) == 1
    assert isinstance(calls[0], list) and calls[0][-1].endswith("spec.md")


def test_open_endpoint_opener_failure_is_500(server, monkeypatch):
    base, slug = server

    def fail(_argv):
        raise FileNotFoundError("missing opener")

    monkeypatch.setattr("tcw.serve.subprocess.Popen", fail)
    with pytest.raises(HTTPError) as err:
        post(base, f"/api/work/{slug}/artifacts/spec/open")
    assert err.value.code == 500

    assert get_json(base, "/api/work")[0]["slug"] == slug


def test_partial_node_empty_taxonomy_endpoint(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    init(["work"], root)
    httpd = TcwServer((HOST, 0), root)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        assert get_json(f"http://{HOST}:{httpd.server_port}", "/api/taxonomy") == []
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)
