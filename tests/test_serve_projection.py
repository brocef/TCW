"""Every work-item payload `tcw serve` emits goes through the versioned DTO.

Criterion 8 of `2026-08-12-project-a-work-item-as-json`. The test walks each
response for objects that *look like* a work item rather than checking the
endpoints someone remembered — a call site left on `_jsonable` is exactly the
kind of thing a hand-written endpoint list misses, and the point of the criterion
is that there is one projection rather than five that happen to agree.
"""

import json
import subprocess
import threading
from dataclasses import fields
from pathlib import Path
from urllib.request import Request, urlopen

import pytest

from tcw.serve import HOST, TcwServer
from tcw.store.base import WorkItem
from tcw.store.fs import FsWorkStore, init
from tcw.work.projection import SCHEMA_VERSION, WORK_ITEM_SCHEMA

# Keys the item payload carried before the DTO, from `asdict(WorkItem)`.
LEGACY_KEYS = {f.name for f in fields(WorkItem)}


@pytest.fixture
def served(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root)
    work = FsWorkStore.open(root)
    item = work.create("Build viewer", created="2026-01-01", body="# Request\n")
    work.write_artifact(item.slug, "spec", "spec content\n")

    httpd = TcwServer((HOST, 0), root)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield root, f"http://{HOST}:{httpd.server_port}", item.slug
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def _call(base, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else b""
    req = Request(f"{base}{path}", data=data or None,
                  headers={"Content-Type": "application/json"}, method=method)
    with urlopen(req) as res:
        raw = res.read()
    return json.loads(raw) if raw else None


def _item_objects(value, found=None):
    """Every dict in `value` that is a work-item payload.

    Identified by `slug` + `title` + `status` together — the three fields a
    work item always has and no other TCW object carries as a set. Deliberately
    *not* identified by `schema`, which would make the test tautological: it
    would only find the payloads that had already been migrated.
    """
    found = [] if found is None else found
    if isinstance(value, dict):
        if {"slug", "title", "status"} <= set(value):
            found.append(value)
        for sub in value.values():
            _item_objects(sub, found)
    elif isinstance(value, list):
        for sub in value:
            _item_objects(sub, found)
    return found


def test_the_helper_finds_an_unmigrated_payload():
    """Guard for the guard: if `_item_objects` missed a legacy-shaped item, every
    assertion below would pass vacuously."""
    legacy = {"item": {"slug": "s", "title": "T", "status": "backlog"}}
    assert _item_objects(legacy) == [legacy["item"]]


def test_every_work_item_payload_serve_emits_carries_the_schema(served):
    jsonschema = pytest.importorskip("jsonschema")
    root, base, slug = served

    responses = {
        "GET /api/work": _call(base, "GET", "/api/work"),
        "GET /api/work/<slug>": _call(base, "GET", f"/api/work/{slug}"),
        "POST /api/work": _call(base, "POST", "/api/work", {"title": "Another"}),
        "PATCH /api/work/<slug>": _call(base, "PATCH", f"/api/work/{slug}",
                                        {"title": "Renamed"}),
        "POST /api/work/<slug>/start": _call(
            base, "POST", f"/api/work/{slug}/actions/start", {}),
    }

    for label, payload in responses.items():
        items = _item_objects(payload)
        assert items, f"{label} returned no work-item payload to check"
        for doc in items:
            assert doc.get("schema") == SCHEMA_VERSION, (
                f"{label} emitted a work item without the versioned projection — "
                "a call site is still on _jsonable")
            jsonschema.validate(doc, WORK_ITEM_SCHEMA)


def test_the_detail_item_keeps_every_key_it_had_plus_exactly_two(served):
    root, base, slug = served
    payload = _call(base, "GET", f"/api/work/{slug}")
    assert set(payload["item"]) == LEGACY_KEYS | {"schema", "artifacts"}


# The qualified-slug echo — the UI derives subresource URLs from `item.slug`, so
# losing the prefix would break every descendant item's links — is covered by
# `test_serve_descendants.py::test_board_flag_on_qualifies_descendant`, which
# builds a real two-node tree and passed unmodified through this change. A
# version of it here that never creates a descendant would assert nothing.


def test_an_action_response_echoes_the_addressed_slug(served):
    root, base, slug = served
    payload = _call(base, "POST", f"/api/work/{slug}/actions/start", {})
    assert payload["slug"] == slug
    assert payload["status"] == "active"
    assert payload["schema"] == SCHEMA_VERSION
