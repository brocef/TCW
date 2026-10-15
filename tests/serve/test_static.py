"""The prebuilt client served from Python (TCW-77 criterion 3)."""

from __future__ import annotations

from pathlib import Path

import pytest

CLIENT = Path(__file__).resolve().parents[2] / "tcw" / "serve" / "dist" / "client"
INDEX = (CLIENT / "index.html").read_bytes()


def built_script() -> str:
    found = sorted((CLIENT / "assets").glob("*.js"))
    assert found, "the built client holds no script"
    return found[0].name


@pytest.mark.parametrize("path", ["/", "/work/anything", "/taxonomy",
                                  "/capabilities/web%2Fediting"])
def test_app_routes_load_index_html(fs, path):
    answer = fs.get(path)
    assert answer.status == 200
    assert answer.body == INDEX
    assert answer.headers["content-type"].startswith("text/html")


def test_a_built_script_is_javascript(fs):
    name = built_script()
    answer = fs.get(f"/assets/{name}")
    assert answer.status == 200
    assert answer.headers["content-type"] == "application/javascript"
    assert answer.body == (CLIENT / "assets" / name).read_bytes()


@pytest.mark.parametrize("path", ["/../pyproject.toml", "/%2e%2e/pyproject.toml",
                                  "/assets/..%2f..%2findex.html",
                                  "/assets/..%2f..%2f..%2f__init__.py",
                                  "/%2e%2e%2f%2e%2e%2f%2e%2e%2fpyproject.toml"])
def test_nothing_outside_the_client_folder_is_served(fs, path):
    answer = fs.get(path)
    outside = [p.read_bytes() for p in (CLIENT.parents[3] / "pyproject.toml",
                                        CLIENT.parents[1] / "__init__.py")]
    assert answer.body not in outside
    assert answer.status in (200, 404)
    if answer.status == 200:
        assert answer.body == INDEX


def test_a_traversal_that_escapes_is_not_found(fs):
    answer = fs.get("/%2e%2e/%2e%2e/%2e%2e/pyproject.toml")
    assert answer.status == 404
    assert answer.json["code"] == "not-found"


def test_an_unknown_api_path_is_a_json_404(fs):
    answer = fs.get("/api/nope")
    assert answer.status == 404
    assert answer.headers["content-type"].startswith("application/json")
    assert answer.json["code"] == "not-found" and answer.json["error"]
