"""The `tracker.yaml` binding: its registration as a sidecar, and the rules for
reading one.

A binding is what records that a work item answers a tracker ticket. Two
properties matter more than the rest:

- **A command writes it, so no edit surface offers to.** The web client hides its
  Edit affordance for a sidecar the server reports as `generated`.
- **An unreadable binding is never read as "no binding".** A lookup that skipped
  one could not say the ticket is not already bound, so it refuses instead.
"""

from __future__ import annotations

import json
import subprocess
import threading
from urllib.request import urlopen

import pytest

from tcw.serve import HOST, TcwServer
from tcw.store.fs import FsWorkStore, init

BINDING = """\
schema: 1
provider: jira-cloud
project: probe
part: default
ticket:
    id: "10052"
    key: TCWCLAIM-6
    url: https://example.invalid/browse/TCWCLAIM-6
claimed-by:
    account-id: acct-a
    name: Probe
bound: "2026-09-14"
unlinked: []
"""


@pytest.fixture()
def store(tmp_path):
    root = tmp_path / "node"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    init(["work"], root, project_id="probe")
    return FsWorkStore.open(root)


# ── the sidecar ──────────────────────────────────────────────────────────────


def test_a_binding_round_trips_through_the_sidecar_surface(store):
    item = store.create("Bound item")
    store.write_sidecar(item.slug, "tracker.yaml", BINDING)
    assert store.read_sidecar(item.slug, "tracker.yaml").content == BINDING


def test_a_binding_that_is_not_a_mapping_is_refused_on_write(store):
    item = store.create("Bound item")
    with pytest.raises(ValueError, match="must be a YAML mapping"):
        store.write_sidecar(item.slug, "tracker.yaml", "- TCWCLAIM-6\n")
    assert store.read_sidecar(item.slug, "tracker.yaml") is None


def test_the_web_api_reports_the_binding_as_generated(store):
    item = store.create("Bound item")
    httpd = TcwServer((HOST, 0), store.node_root)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        url = f"http://{HOST}:{httpd.server_port}/api/work/{item.slug}/sidecars"
        with urlopen(url) as response:
            sidecars = json.loads(response.read())
    finally:
        httpd.shutdown()
        httpd.server_close()
    tracker = next(s for s in sidecars if s["name"] == "tracker.yaml")
    assert tracker["generated"] is True
