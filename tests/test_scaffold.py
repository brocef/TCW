"""`write_draft` and `tcw work scaffold` — drafts, and everything they are not.

A draft is a file to type into. It is never the artifact: no surface reports it,
and `scaffold` refuses rather than overwrite either the real artifact or a draft
someone has already started.
"""

import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.store.base import (
    LIFECYCLE_STEPS, STAGE_STATUSES, WORK_ARTIFACTS, WORK_STATUSES,
)
from tcw.store.fs import FsWorkStore, init
from tcw.work.resolve import load_builtins
from tcw.work.templates import ARTIFACT_TEMPLATES


def _node(tmp_path: Path, name: str = "repo") -> Path:
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root, name.lower())
    return root


def _configure(root: Path, lifecycle: dict) -> None:
    cfg_path = root / "tcw-config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    cfg.setdefault("work", {})["lifecycle"] = lifecycle
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))


def _cli(root: Path, *args: str):
    return subprocess.run(["tcw", "work", "scaffold", *args], cwd=str(root),
                          capture_output=True, text=True)


def _list(root: Path) -> str:
    return subprocess.run(["tcw", "work", "list"], cwd=str(root),
                          capture_output=True, text=True).stdout


# Where each artifact can legally be scaffolded — derived from the same two
# tables the verb consults, so the sweep below covers what the verb allows rather
# than what its author remembered.
_STATUS_FOR = {
    name: (STAGE_STATUSES[s.id][0] if STAGE_STATUSES.get(s.id) else "backlog")
    for s in LIFECYCLE_STEPS for name in s.produces
}


def _item_in(st: FsWorkStore, status: str, title: str = "Thing") -> str:
    """An item in `status` with **no** artifacts present — `create` writes
    `initial-request.md` only when handed a body."""
    slug = st.create(title).slug
    if status in ("active", "review"):
        st.start(slug)
    if status == "review":
        st.submit(slug)
    return slug


@pytest.fixture
def item(tmp_path):
    """A node with one backlog item."""
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    return root, st, st.create("Thing", body="req\n").slug


# ── the built-in templates ───────────────────────────────────────────────────


def test_every_artifact_has_exactly_one_built_in_template():
    assert set(ARTIFACT_TEMPLATES) == set(WORK_ARTIFACTS)


def test_intakes_template_is_empty():
    """Intake is whatever someone supplied, so it has no prescribed structure.
    Pinned so nobody helpfully adds headings later."""
    assert ARTIFACT_TEMPLATES["intake"] == ""


def test_load_builtins_carries_the_templates():
    """One loader for every kind of built-in TCW ships — two would resolve a
    stage's prompt and the same stage's template from different places."""
    assert load_builtins().artifact_templates == ARTIFACT_TEMPLATES


# ── the store method ─────────────────────────────────────────────────────────


def test_write_draft_writes_the_file_and_returns_its_locator(item):
    _root, st, slug = item
    locator = st.write_draft(slug, "spec", "# Draft\n")
    assert Path(locator).read_text() == "# Draft\n"


def test_write_draft_refuses_a_present_draft_and_leaves_it_alone(item):
    _root, st, slug = item
    locator = st.write_draft(slug, "spec", "typed by hand\n")
    with pytest.raises(ValueError) as e:
        st.write_draft(slug, "spec", "clobbered\n")
    assert locator in str(e.value)
    assert Path(locator).read_text() == "typed by hand\n"


def test_force_overwrites_a_present_draft(item):
    _root, st, slug = item
    locator = st.write_draft(slug, "spec", "typed by hand\n")
    st.write_draft(slug, "spec", "regenerated\n", force=True)
    assert Path(locator).read_text() == "regenerated\n"


def test_an_empty_draft_is_not_present_and_needs_no_force(item):
    """The canonical presence rule, not `.exists()` — which is what makes
    `intake`, whose template is empty, work with no carve-out."""
    _root, st, slug = item
    locator = st.write_draft(slug, "intake", "")
    assert Path(locator).is_file()
    st.write_draft(slug, "intake", "now with content\n")
    assert Path(locator).read_text() == "now with content\n"


def test_an_unknown_artifact_name_raises_naming_the_legal_set(item):
    _root, st, slug = item
    with pytest.raises(ValueError) as e:
        st.write_draft(slug, "speck", "x")
    assert "speck" in str(e.value)
    assert all(name in str(e.value) for name in WORK_ARTIFACTS)


def test_a_draft_never_lands_on_the_artifact(item):
    _root, st, slug = item
    st.write_draft(slug, "spec", "# Draft\n")
    assert st.read_artifact(slug, "spec") is None
    assert {a.name for a in st.artifacts(slug) if a.present} == {"initial-request"}


# ── the verb ─────────────────────────────────────────────────────────────────


def test_the_draft_is_the_resolved_template_byte_for_byte(item):
    root, st, slug = item
    _configure(root, {"artifacts": {"spec": [{"blob": "# Project spec\n\n## One\n"}]}})

    r = _cli(root, "spec", slug)
    assert r.returncode == 0, r.stderr
    locator = r.stdout.strip()
    assert r.stdout == f"{locator}\n"                 # the locator, and nothing else
    assert Path(locator).read_text() == "# Project spec\n\n## One\n"


@pytest.mark.parametrize("artifact", WORK_ARTIFACTS)
def test_scaffolding_never_creates_the_artifact_itself(tmp_path, artifact):
    """The whole design rests on this: a draft must not light a stage letter on
    the board before anyone has written the document."""
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    slug = _item_in(st, _STATUS_FOR.get(artifact, "backlog"))
    before = _list(root)

    assert _cli(root, artifact, slug).returncode == 0
    assert not (st.path(slug) / f"{artifact}.md").is_file()
    assert _list(root) == before


@pytest.mark.parametrize("artifact", WORK_ARTIFACTS)
def test_with_nothing_configured_every_artifact_scaffolds_to_its_builtin(tmp_path, artifact):
    """`resolve_artifact` returns empty text when no binding is declared, which
    is every project today — so the verb supplies the fallback."""
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    slug = _item_in(st, _STATUS_FOR.get(artifact, "backlog"))

    r = _cli(root, artifact, slug)
    assert r.returncode == 0, r.stderr
    assert Path(r.stdout.strip()).read_text() == ARTIFACT_TEMPLATES[artifact]


def test_scaffolding_intake_creates_an_empty_draft_rather_than_refusing(item):
    root, _st, slug = item
    r = _cli(root, "intake", slug)
    assert r.returncode == 0, r.stderr
    assert Path(r.stdout.strip()).read_text() == ""


def test_an_unknown_artifact_names_the_legal_ones(item):
    root, _st, slug = item
    r = _cli(root, "speck", slug)
    assert r.returncode == 1 and r.stdout == ""
    assert "speck" in r.stderr and "spec" in r.stderr


def test_an_unknown_item_is_refused(item):
    root, _st, _slug = item
    r = _cli(root, "spec", "no-such-item")
    assert r.returncode == 1 and r.stdout == ""


# ── the two refusals ─────────────────────────────────────────────────────────


def test_it_refuses_when_the_real_artifact_is_present(item):
    root, st, slug = item
    st.write_artifact(slug, "spec", "# The real spec\n")

    r = _cli(root, "spec", slug)
    assert r.returncode == 1 and r.stdout == ""
    assert "spec.md" in r.stderr
    assert not (st.path(slug) / "spec.draft.md").exists()


def test_a_whitespace_only_artifact_does_not_block_scaffolding(item):
    """The board says no spec exists, so the verb must agree — an implementation
    using `.exists()` fails here."""
    root, st, slug = item
    st.write_artifact(slug, "spec", "   \n\n")

    r = _cli(root, "spec", slug)
    assert r.returncode == 0, r.stderr
    assert Path(r.stdout.strip()).name == "spec.draft.md"
    assert (st.path(slug) / "spec.md").read_text() == "   \n\n"   # untouched


def test_it_refuses_a_present_draft_and_leaves_it_byte_identical(item):
    root, st, slug = item
    draft = st.path(slug) / "spec.draft.md"
    draft.write_text("half a spec I typed\n")

    r = _cli(root, "spec", slug)
    assert r.returncode == 1 and r.stdout == ""
    assert str(draft) in r.stderr
    assert draft.read_text() == "half a spec I typed\n"


def test_force_replaces_a_present_draft(item):
    root, st, slug = item
    draft = st.path(slug) / "spec.draft.md"
    draft.write_text("half a spec I typed\n")

    r = _cli(root, "spec", slug, "--force")
    assert r.returncode == 0, r.stderr
    assert draft.read_text() == ARTIFACT_TEMPLATES["spec"]


def test_an_empty_draft_is_regenerated_with_no_flag(item):
    root, st, slug = item
    draft = st.path(slug) / "spec.draft.md"
    draft.write_text("")

    assert _cli(root, "spec", slug).returncode == 0
    assert draft.read_text() == ARTIFACT_TEMPLATES["spec"]


# ── legality ─────────────────────────────────────────────────────────────────


def test_an_artifact_no_stage_can_produce_yet_is_refused(item):
    """`outcome` belongs to `implement`, which runs in `active`."""
    root, st, slug = item
    r = _cli(root, "outcome", slug)
    assert r.returncode == 1 and r.stdout == ""
    assert "backlog" in r.stderr
    assert not (st.path(slug) / "outcome.draft.md").exists()


def test_intake_is_legal_in_every_status(tmp_path):
    """No stage produces `intake`, so there is no legality row to look up — and
    an implementation indexing the table anyway raises `KeyError` here."""
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    for status in WORK_STATUSES:
        it = st.create(f"Item {status}", body="req\n")
        if status in ("active", "review", "completed", "discarded"):
            st.start(it.slug)
        if status == "review":
            st.submit(it.slug)
        if status == "completed":
            st.complete(it.slug, "done", dod_ack=list(st.dod_checklist()), force=True)
        if status == "discarded":
            st.complete(it.slug, "wontfix", dod_ack=[], force=True)
        r = _cli(root, "intake", it.slug)
        assert r.returncode == 0, f"{status}: {r.stderr}"


# ── resolve, then write ──────────────────────────────────────────────────────


@pytest.mark.parametrize("broken,fixed", [
    ({"generate": "exit 7"}, {"generate": "printf 'recovered'"}),
    ({"generate": "sleep 30"}, {"generate": "printf 'recovered'"}),
    ({"generate": "printf 'aaaaaaaaaaaaaaaaaaaa'"}, {"generate": "printf 'recovered'"}),
    ({"file": "gone.md"}, {"blob": "recovered"}),
])
def test_a_failed_resolution_writes_nothing_and_retries_clean(item, broken, fixed):
    root, st, slug = item
    _configure(root, {"timeout": 1, "output-cap": 16,
                      "artifacts": {"spec": [broken]}})

    r = _cli(root, "spec", slug)
    assert r.returncode == 1 and r.stdout == ""
    assert r.stderr.strip()
    assert not (st.path(slug) / "spec.draft.md").exists()

    _configure(root, {"timeout": 1, "output-cap": 16,
                      "artifacts": {"spec": [fixed]}})
    r = _cli(root, "spec", slug)
    assert r.returncode == 0, r.stderr
    assert Path(r.stdout.strip()).read_text() == "recovered"


def test_an_unwritable_target_reports_and_prints_no_path(item):
    root, st, slug = item
    folder = st.path(slug)
    folder.chmod(0o500)
    try:
        r = _cli(root, "spec", slug)
    finally:
        folder.chmod(0o700)
    assert r.returncode == 1
    assert r.stdout == ""
    assert "Traceback" not in r.stderr and r.stderr.strip()


# ── conditions ───────────────────────────────────────────────────────────────


def test_a_project_template_overrides_the_builtin_and_conditions_select(tmp_path):
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    st.register_tags(["bug"])
    tagged = st.create_work("A bug", tags=["bug"]).item.slug
    plain = st.create("Not a bug").slug
    _configure(root, {"artifacts": {"spec": [
        {"blob": "# Bug spec\n", "when": {"tags": ["bug"]}},
        {"builtin": True}]}})

    r = _cli(root, "spec", tagged)
    assert Path(r.stdout.strip()).read_text() == "# Bug spec\n"
    r = _cli(root, "spec", plain)
    assert Path(r.stdout.strip()).read_text() == ARTIFACT_TEMPLATES["spec"]


# ── through the store, not beside it ─────────────────────────────────────────


def test_the_draft_is_written_through_the_store(item, monkeypatch):
    """The portable half: a Jira-backed adapter has no item folder, so the draft
    has to be a store operation rather than a path the CLI composes."""
    from tcw.cli import main
    root, _st, slug = item
    calls = []
    monkeypatch.setattr(FsWorkStore, "write_draft",
                        lambda self, *a, **k: calls.append((a, k)) or "LOCATOR")
    monkeypatch.chdir(root)
    assert main(["work", "scaffold", "spec", slug]) == 0
    assert calls and calls[0][0][:2] == (slug, "spec")


def test_the_cli_module_composes_no_draft_path():
    """`<artifact>.draft.md` exists in exactly one place, and it is the adapter."""
    from tcw.work import cli
    source = Path(cli.__file__).read_text()
    assert ".draft.md" not in source
    assert not [ln for ln in source.splitlines()
                if "path(" in ln and "draft" in ln]


# ── no surface reports a draft ───────────────────────────────────────────────


def _every_draft(root: Path, st: FsWorkStore, slug: str) -> None:
    for name in WORK_ARTIFACTS:
        st.write_draft(slug, name, f"# draft of {name}\n")


def test_no_surface_reports_a_draft_as_an_artifact(tmp_path):
    """Four surfaces, not the two anyone would remember. `serve` is included
    because it changes not at all here — the property already holds through its
    registry gate, and it has to survive."""
    import json
    import threading
    from urllib.request import urlopen

    from tcw.serve import HOST, TcwServer

    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    slug = st.create("Thing").slug
    before = _list(root)
    _every_draft(root, st, slug)

    # 1. the board
    assert _list(root) == before
    # 2. the store's own presence report
    assert all(not a.present for a in st.artifacts(slug))
    # 3. `tcw work show --json`
    shown = json.loads(subprocess.run(["tcw", "work", "show", slug, "--json"],
                                      cwd=str(root), capture_output=True,
                                      text=True).stdout)
    assert set(shown["artifacts"]) == set(WORK_ARTIFACTS)
    assert not any(shown["artifacts"].values())

    # 4. `tcw serve`'s detail response
    httpd = TcwServer((HOST, 0), root)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        with urlopen(f"http://{HOST}:{httpd.server_port}/api/work/{slug}") as res:
            detail = json.loads(res.read())
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)
    assert detail["artifacts"], "no artifact list to check — the test is vacuous"
    assert not [a for a in detail["artifacts"] if a["present"]]
