import json
import subprocess
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from tcw.cli import build_parser, main
from tcw.serve import HOST, TcwServer
from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore, init


from nodeconfig import declare_extends


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
    FsTaxonomyStore.open(root).add("Work Item", slug="work-item")
    FsCapabilitiesStore.open(root).add("web", "Browse TCW content", status="Missing")
    return root, None


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

    assert work == []                     # the stub, until TCW-77
    assert taxonomy[0]["slug"] == "work-item"
    assert taxonomy[0]["modified"].endswith("Z")
    assert capabilities[0]["path"] == "web"
    assert capabilities[0]["modified"].endswith("Z")


def test_the_work_routes_are_a_two_route_stub(server):
    """Until TCW-77: the client loads `/api/work` beside taxonomy and
    capabilities and reads `/api/work/tags`, so both answer an empty list;
    every other work request is 404."""
    base, _ = server
    assert get_json(base, "/api/work") == []
    assert get_json(base, "/api/work/tags") == []
    for method, path in (("GET", "/api/work/2026-01-01-x"),
                         ("GET", "/api/work/interrupted-claims"),
                         ("POST", "/api/work"),
                         ("PATCH", "/api/work/2026-01-01-x"),
                         ("PUT", "/api/work/2026-01-01-x/artifacts/spec"),
                         ("DELETE", "/api/work/2026-01-01-x")):
        request = Request(f"{base}{path}", method=method,
                          data=b"{}" if method != "GET" else None,
                          headers={"Content-Type": "application/json"})
        with pytest.raises(HTTPError) as exc:
            urlopen(request)
        assert exc.value.code == 404, (method, path)


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
    declare_extends(cons, "taxonomy", "extends:\n  - repo\n")

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


