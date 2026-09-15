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


# ── show --json and the schema ───────────────────────────────────────────────


def test_json_carries_the_bound_value(node):
    assert show_json(item(node, "Bound", document()))["tracker"] == BOUND


def test_json_is_null_for_an_unbound_and_an_unlinked_item(node):
    unbound = item(node, "Unbound", None)
    unlinked = item(node, "Unlinked", unlink_document(
        document(), reason="wrong ticket", today="2026-09-14"))
    assert show_json(unbound)["tracker"] is None
    assert show_json(unlinked)["tracker"] is None


def test_json_names_the_problem_with_an_unreadable_binding(node):
    assert show_json(item(node, "Missing keys", 'ticket: {id: "1"}\n'))["tracker"] \
        == {"problem": MISSING}
    assert set(show_json(item(node, "Not YAML", "ticket: [\n"))["tracker"]) \
        == {"problem"}


@pytest.mark.parametrize("where", ["tracker", "ticket"])
def test_the_schema_refuses_an_extra_key(node, where):
    doc = show_json(item(node, "Bound", document()))
    target = doc["tracker"] if where == "tracker" else doc["tracker"]["ticket"]
    target["claimed-by"] = "someone"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, WORK_ITEM_SCHEMA)


def test_the_schema_refuses_a_problem_with_anything_beside_it(node):
    doc = show_json(item(node, "Bound", document()))
    doc["tracker"] = {"problem": "x", "ticket": BOUND["ticket"]}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, WORK_ITEM_SCHEMA)


# ── show and list ────────────────────────────────────────────────────────────


def test_show_prints_the_binding_after_every_field_and_before_the_body(node):
    st = FsWorkStore.open(node)
    slug = item(node, "Bound", document())
    st.write_artifact(slug, "initial-request", "# Request\n\nThe body.\n")
    code, out, err = run("work", "show", slug)
    assert code == 0, err
    lines = out.splitlines()
    line = f"tracker: EX-1 (jira-cloud, part default) {URL}"
    assert tracker_lines(slug) == [line]
    assert lines.index(line) == lines.index("") - 1, out


def test_show_leaves_out_an_empty_url(node):
    slug = item(node, "No URL", document().replace(f"url: {URL}", "url: ''"))
    assert tracker_lines(slug) == ["tracker: EX-1 (jira-cloud, part default)"]


def test_show_reports_an_unreadable_binding(node):
    slug = item(node, "Missing keys", 'ticket: {id: "1"}\n')
    assert tracker_lines(slug) == [f"tracker: tracker.yaml cannot be read ({MISSING})"]


def test_list_ends_a_bound_row_with_its_ticket(node):
    assert row(item(node, "Bound", document())).endswith(" | ticket: EX-1")
    assert row(item(node, "Api part", document("api"))).endswith(
        " | ticket: EX-1 (part api)")


def test_list_marks_an_unreadable_binding(node):
    assert row(item(node, "Missing keys", 'ticket: {id: "1"}\n')).endswith(
        " | ticket: unreadable")


def test_an_unbound_and_an_unlinked_item_print_nothing_new(node):
    for slug in (item(node, "Unbound", None),
                 item(node, "Unlinked", unlink_document(
                     document(), reason="wrong ticket", today="2026-09-14"))):
        assert tracker_lines(slug) == []
        assert "ticket:" not in row(slug)


def test_a_bound_row_is_the_unbound_row_plus_the_segment(node):
    """Every segment before the new one is what the row printed without a binding —
    including the claim segment of an active item, which stays ahead of it."""
    st = FsWorkStore.open(node)
    slug = item(node, "Bound and started", document())
    st.start(slug, owner="a@b")
    bound = row(slug)
    st.write_sidecar(slug, "tracker.yaml",
                     unlink_document(document(), reason="x", today="2026-09-14"),
                     revision=st.read_sidecar(slug, "tracker.yaml").revision)
    assert bound == row(slug) + " | ticket: EX-1"
    assert " | owner: a@b | started: " in bound


# ── nothing tracker-shaped is loaded, and serve agrees ───────────────────────


_PROBE = """
import sys
sys.path.insert(0, {repo!r})
import io, contextlib
from tcw.cli import main
out = io.StringIO()
with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
    try:
        code = main({argv!r})
    except SystemExit as e:
        code = e.code or 0
print("EXIT", code)
print("TICKET", "EX-1" in out.getvalue())
print("LOADED", ",".join(sorted(n for n in sys.modules if n.startswith("tcw.tracker"))))
"""


@pytest.mark.parametrize("verb", ["list", "show"])
def test_reading_a_bound_item_loads_no_tracker_module(node, verb):
    """In a fresh interpreter, for the reason `test_tracker_absent.py` gives: in this
    process `tcw.tracker` is already imported, so the question cannot be asked here.
    `TICKET True` proves the command really did read the binding."""
    slug = item(node, "Bound", document())
    argv = ["work", "list"] if verb == "list" else ["work", "show", slug]
    result = subprocess.run(
        [sys.executable, "-c", _PROBE.format(repo=str(REPO), argv=argv)],
        cwd=node, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    assert "EXIT 0" in result.stdout and "TICKET True" in result.stdout, result.stdout
    loaded = [x for x in result.stdout.splitlines() if x.startswith("LOADED")][0]
    assert loaded.removeprefix("LOADED").strip() == "", loaded


def test_serve_detail_carries_the_same_value_as_show_json(node):
    from tcw.serve import HOST, TcwServer
    slug = item(node, "Bound", document())
    httpd = TcwServer((HOST, 0), node)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        with urlopen(f"http://{HOST}:{httpd.server_port}/api/work/{slug}") as res:
            payload = json.loads(res.read())
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)
    assert payload["item"]["tracker"] == show_json(slug)["tracker"] == BOUND
