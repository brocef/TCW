"""Where a tracker binding can be read: `show`, `list`, `show --json` and `tcw serve`.

Nothing here calls a tracker, so there is no fake one. Each binding is the text
`import` and `link` write (`binding_document`), or a broken variant of it, put in
the item's folder directly — the store's own sidecar write refuses text that is not
a YAML mapping, and a hand-edited file is exactly what an unreadable binding is. It
is read back through the item, which is the whole feature: the binding is shown as
the file records it, never as the tracker says it is.

The node has no `work.tracker` block on purpose. Showing a binding must not need a
tracker configured, and must not load the tracker package to do it.
"""

from __future__ import annotations

import contextlib
import io
import json
import pathlib
import subprocess
import sys
import threading
from urllib.request import urlopen

import jsonschema
import pytest

from tcw.store.base import binding_value, classify_binding
from tcw.store.fs import FsWorkStore, init
from tcw.tracker.intake import binding_document, read_binding, unlink_document
from tcw.work.projection import WORK_ITEM_SCHEMA

REPO = pathlib.Path(__file__).resolve().parents[1]
URL = "https://example.invalid/browse/EX-1"


def document(part: str = "default") -> str:
    return binding_document(provider="jira-cloud", project="probe", part=part,
                            ticket_id="10001", ticket_key="EX-1", ticket_url=URL,
                            bound="2026-09-14", unlinked=[])


BOUND = {"provider": "jira-cloud", "project": "probe", "part": "default",
         "ticket": {"id": "10001", "key": "EX-1", "url": URL}, "bound": "2026-09-14"}
MISSING = "missing or empty: ticket.key, provider, project, part"


@pytest.fixture()
def node(tmp_path, monkeypatch):
    root = tmp_path / "node"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root, project_id="probe")
    monkeypatch.chdir(root)
    return root


def item(root, title: str, sidecar: str | None) -> str:
    """An item whose `tracker.yaml` is `sidecar`, or which has none. No default: which
    binding an item has is the axis every test here varies."""
    st = FsWorkStore.open(root)
    slug = st.create(title).slug
    if sidecar is not None:
        (st.path(slug) / "tracker.yaml").write_text(sidecar, encoding="utf-8")
    return slug


def run(*argv):
    from tcw.cli import main
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(list(argv))
        except SystemExit as exit_:
            code = exit_.code or 0
    return code, out.getvalue(), err.getvalue()


def show_json(slug) -> dict:
    code, out, err = run("work", "show", slug, "--json")
    assert code == 0, err
    doc = json.loads(out)
    jsonschema.validate(doc, WORK_ITEM_SCHEMA)
    return doc


def row(slug) -> str:
    code, out, err = run("work", "list")
    assert code == 0, err
    lines = [line for line in out.splitlines() if line.startswith(slug + " |")]
    assert len(lines) == 1, out
    return lines[0]


def tracker_lines(slug) -> list[str]:
    code, out, err = run("work", "show", slug)
    assert code == 0, err
    return [line for line in out.splitlines() if line.startswith("tracker:")]


# ── the value, from a parsed binding ─────────────────────────────────────────


def test_a_written_binding_becomes_the_bound_value():
    assert binding_value(read_binding(document())) == BOUND


def test_a_bound_date_yaml_reads_as_a_date_is_rendered_as_text():
    text = document().replace("bound: '2026-09-14'", "bound: 2026-09-14")
    assert "bound: 2026-09-14\n" in text
    assert binding_value(read_binding(text))["bound"] == "2026-09-14"


def test_a_binding_with_no_url_and_no_bound_date_is_still_bound():
    value = binding_value(classify_binding({
        "provider": "jira-cloud", "project": "probe", "part": "default",
        "ticket": {"id": "10001", "key": "EX-1"}}))
    assert value["ticket"]["url"] == "" and value["bound"] == ""


def test_an_unlinked_binding_has_no_value():
    text = unlink_document(document(), reason="wrong ticket", today="2026-09-14")
    assert binding_value(read_binding(text)) is None
    assert binding_value(read_binding(None)) is None


def test_a_malformed_binding_becomes_a_problem():
    assert binding_value(read_binding('ticket: {id: "1"}\n')) == {"problem": MISSING}
    assert set(binding_value(read_binding("ticket: [\n"))) == {"problem"}
