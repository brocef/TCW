import json
import socket
import subprocess
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from tcw.cli import build_parser, main
from tcw.serve import HOST, TcwServer
from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore, FsWorkStore, init


def node(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["taxonomy", "capabilities", "work"], root, "repo")
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
    # /open is a mutating action: send the JSON content type it now requires.
    req = Request(f"{base}{path}", method="POST")
    req.add_header("Content-Type", "application/json")
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


def test_api_lists_all_three_axes(server):
    base, slug = server
    work = get_json(base, "/api/work")
    taxonomy = get_json(base, "/api/taxonomy")
    capabilities = get_json(base, "/api/capabilities")

    assert work[0]["slug"] == slug
    assert work[0]["modified"].endswith("Z")
    assert taxonomy[0]["slug"] == "work-item"
    assert taxonomy[0]["modified"].endswith("Z")
    assert capabilities[0]["path"] == "web"
    assert capabilities[0]["modified"].endswith("Z")


def test_unknown_api_route_still_404s(server):
    base, _ = server
    with pytest.raises(HTTPError) as exc:
        urlopen(f"{base}/api/does-not-exist")
    assert exc.value.code == 404


def test_inherited_taxonomy_term_detail_is_200_not_500(tmp_path):
    # Regression: selecting an inherited term returned 500 because get_term_detail
    # read files under the extending store's root. Serve the qualified ref → 200.
    shared = node(tmp_path)
    FsTaxonomyStore.open(shared).add("Argument", slug="argument")
    cons = tmp_path / "consumer"
    cons.mkdir()
    subprocess.run(["git", "init", "-q", str(cons)], check=True)
    init(["taxonomy", "capabilities", "work"], cons, "consumer")
    (cons / "tcw-config.yaml").write_text(
        "id: consumer\nconnected-projects:\n  children:\n    repo: ../repo\n"
    )
    (shared / "tcw-config.yaml").write_text(
        "id: repo\nconnected-projects:\n  parent:\n    consumer: ../consumer\n"
    )
    (cons / "docs" / "taxonomy" / "config.yaml").write_text(
        "extends:\n  - repo\n", encoding="utf-8")

    httpd = TcwServer((HOST, 0), cons)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://{HOST}:{httpd.server_port}"
        detail = get_json(base, "/api/taxonomy/repo%2Fargument")
        assert detail["term"]["name"] == "Argument"
        assert detail["term"]["origin"] == "repo"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def test_work_detail_includes_artifacts_without_paths(server):
    base, slug = server
    payload = get_json(base, f"/api/work/{slug}")

    assert payload["item"]["slug"] == slug
    assert payload["item"]["blocked_by"] == [{"external": "vendor"}]
    assert payload["item"]["capabilities"] == {"links": ["web"]}
    artifacts = {a["name"]: a for a in payload["artifacts"]}
    assert artifacts["initial-request"]["name"] == "initial-request"
    assert artifacts["initial-request"]["present"] is True
    assert "revision" in artifacts["initial-request"]  # revision-bearing
    assert artifacts["spec"]["name"] == "spec"
    assert artifacts["spec"]["present"] is True
    assert "locator" not in artifacts["spec"]
    # New fields in detail payload
    assert "coreRevision" in payload
    assert "sidecars" in payload


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


def test_open_endpoint_rejects_non_json_content_type(server, monkeypatch):
    """#4 — /open spawns the desktop opener, so it is a mutating action: a
    cross-origin simple POST (non-JSON content type) must be rejected before
    dispatch, and the opener must never run."""
    base, slug = server
    calls = []
    monkeypatch.setattr("tcw.serve.subprocess.Popen", lambda argv: calls.append(argv))
    req = Request(f"{base}/api/work/{slug}/artifacts/spec/open", method="POST")
    req.add_header("Content-Type", "text/plain")
    with pytest.raises(HTTPError) as err:
        urlopen(req)
    assert err.value.code == 400
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


def test_private_sidecar_rejects_direct_requests(seeded_node):
    root, _slug = seeded_node
    httpd = TcwServer((HOST, 0), root, token="secret", api_only=True)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://{HOST}:{httpd.server_port}"
    try:
        with pytest.raises(HTTPError) as missing:
            urlopen(f"{base}/api/work")
        assert missing.value.code == 403
        request = Request(f"{base}/api/work", headers={"X-TCW-Sidecar-Token": "secret"})
        with urlopen(request) as response:
            assert response.status == 200
        static_request = Request(f"{base}/", headers={"X-TCW-Sidecar-Token": "secret"})
        with pytest.raises(HTTPError) as no_static:
            urlopen(static_request)
        assert no_static.value.code == 404
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)
