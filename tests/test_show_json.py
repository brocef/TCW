"""`tcw work show --json`, and the promise that `tcw work show` did not change.

The baseline half is the point of the file's ordering: `tests/fixtures/show_baseline/`
was committed before `_show` was touched (commit `c2fe1fc`), so the expected bytes
here are not something the implementer wrote down after changing the behavior.
"""

import json
import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.store.base import WORK_ARTIFACTS
from tcw.store.fs import FsWorkStore, init
from tcw.work.projection import SCHEMA_VERSION, WORK_ITEM_SCHEMA

BASELINE = Path(__file__).parent / "fixtures" / "show_baseline"


def node(tmp_path: Path, name: str = "repo") -> Path:
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root, name.lower())
    return root


# ── the JSON document ─────────────────────────────────────────────────────────


def test_show_json_emits_a_document_that_validates(tmp_path, monkeypatch, capsys):
    jsonschema = pytest.importorskip("jsonschema")
    from tcw.cli import main
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("A thing", body="# A thing\n\nbody\n")
    monkeypatch.chdir(root)

    assert main(["work", "show", item.slug, "--json"]) == 0
    # Validate what the CLI actually printed, parsed back — not a dict rebuilt
    # beside it, which would test the projection twice and the command not at all.
    doc = json.loads(capsys.readouterr().out)
    jsonschema.validate(doc, WORK_ITEM_SCHEMA)
    assert doc["schema"] == SCHEMA_VERSION
    assert doc["slug"] == item.slug
    assert doc["artifacts"]["initial-request"] is True
    assert doc["artifacts"]["spec"] is False


def test_show_json_artifacts_agree_with_the_store(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Mixed", body="req\n")
    st.write_artifact(item.slug, "spec", "# Spec\n")
    monkeypatch.chdir(root)

    assert main(["work", "show", item.slug, "--json"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert set(doc["artifacts"]) == set(WORK_ARTIFACTS)
    assert doc["artifacts"] == {a.name: a.present for a in st.artifacts(item.slug)}
    assert doc["artifacts"]["spec"] is True and doc["artifacts"]["plan"] is False


def test_show_json_survives_a_capabilities_blob_yaml_can_produce(
        tmp_path, monkeypatch, capsys):
    jsonschema = pytest.importorskip("jsonschema")
    from tcw.cli import main
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Hostile", body="req\n")
    st.write_sidecar(item.slug, "capabilities.yaml",
                     "when: 2026-01-01\nraw: !!binary aGk=\nvals: !!set {a: null}\n")
    monkeypatch.chdir(root)

    assert main(["work", "show", item.slug, "--json"]) == 0
    doc = json.loads(capsys.readouterr().out)
    jsonschema.validate(doc, WORK_ITEM_SCHEMA)


def test_show_json_refuses_a_blob_whose_keys_collide(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Collides", body="req\n")
    # Both keys render as "1"; keeping one would drop the other's value.
    st.write_sidecar(item.slug, "capabilities.yaml", '1: "a"\n"1": "b"\n')
    monkeypatch.chdir(root)

    assert main(["work", "show", item.slug, "--json"]) == 1
    out = capsys.readouterr()
    assert out.out == ""                      # nothing for `jq` to half-parse
    assert "would be lost" in out.err


@pytest.mark.parametrize("ref", ["no-such-item", "nosuchproject/whatever"])
def test_show_json_error_paths_print_nothing_on_stdout(
        tmp_path, monkeypatch, capsys, ref):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "show", ref, "--json"]) == 1
    out = capsys.readouterr()
    assert out.out == ""
    assert out.err.strip()


def test_show_json_error_on_an_ambiguous_slug(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Twice", body="req\n")
    # Same slug in two statuses is the integrity break `MultipleMatch` reports.
    dup = root / "docs/work/active" / item.slug
    dup.mkdir(parents=True)
    (dup / "state.yaml").write_text(yaml.safe_dump({"title": "Twice"}))
    monkeypatch.chdir(root)

    assert main(["work", "show", item.slug, "--json"]) == 1
    out = capsys.readouterr()
    assert out.out == ""


# ── the promise that plain `show` did not change ──────────────────────────────


def _show(main, capsys, slug) -> str:
    assert main(["work", "show", slug]) == 0
    return capsys.readouterr().out


def test_plain_show_matches_the_pre_change_baselines(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    monkeypatch.chdir(root)

    with_req = st.create("With a request", body="# With a request\n\nSome prose.\n",
                         priority=5)
    st.update_work(with_req.slug, effort="medium", complexity="high")
    intake_only = st.create("Intake only", intake="raw intake text\n")
    neither = st.create("Neither")

    expected = (BASELINE / "with_a_request.txt").read_text()
    assert _show(main, capsys, with_req.slug) == expected.format(slug=with_req.slug)

    expected = (BASELINE / "intake_only.txt").read_text()
    assert _show(main, capsys, intake_only.slug) == expected.format(
        slug=intake_only.slug)

    expected = (BASELINE / "neither.txt").read_text()
    assert _show(main, capsys, neither.slug) == expected.format(slug=neither.slug)


def test_plain_show_matches_the_baseline_for_a_fully_populated_item(
        tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    monkeypatch.chdir(root)

    blocker = st.create("Neither")
    st.register_tags(["alpha", "beta"])
    rich = st.create("Rich fields", priority=9)
    st.update_work(rich.slug, effort="low", complexity="very-high",
                   tags=["alpha", "beta"],
                   blockers=[blocker.slug, "https://example.com/issue/1"])
    st.start(rich.slug, owner="someone@example.com", force=True)

    item = st.get(rich.slug)
    expected = (BASELINE / "rich_fields.txt").read_text().format(
        slug=rich.slug, started=item.started, blocker=blocker.slug)
    assert _show(main, capsys, rich.slug) == expected
