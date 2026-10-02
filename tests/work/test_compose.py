"""Prompt composition on the 3.0 configuration (TCW-70 Design 7.1, 7.2; the
library half of AC 21)."""

import json
from datetime import date
from pathlib import Path

import pytest

from tcw.errors import BackendError
from tcw.work.backend import Query
from tcw.work.config import parse_work_config
from tcw.work.fs_backend import FsWorkBackend
from tcw.work.layout import Layout
from tcw.work.model import Changes
from tcw.work.record import item_record
from tcw.work.resolve import (
    generate_payload, packaged_text, procedure_prompt, stage_header,
    stage_prompt, substitute_request,
)


def config(**work):
    parsed, problems = parse_work_config(work)
    assert problems == [], problems
    return parsed


def compose(cfg, stage, root, **kw):
    return stage_prompt(cfg, stage, project_root=root, **kw).text


# -- which bindings compose (7.2) ------------------------------------------------------

def test_no_prompt_key_is_the_packaged_text(tmp_path):
    assert compose(config(), "spec", tmp_path) == packaged_text(
        "prompts", "spec").rstrip()


def test_a_list_without_builtin_replaces_the_packaged_text(tmp_path):
    cfg = config(stages={"spec": {"prompt": [{"blob": "Ours."}]}})
    assert compose(cfg, "spec", tmp_path) == "Ours."


def test_builtin_stands_where_it_is_written(tmp_path):
    cfg = config(stages={"spec": {"prompt": [{"blob": "Before."},
                                             {"builtin": True},
                                             {"blob": "After."}]}})
    text = compose(cfg, "spec", tmp_path)
    assert text.startswith("Before.\n\n") and text.endswith("\n\nAfter.")
    assert packaged_text("prompts", "spec").splitlines()[0] in text


def test_an_explicit_empty_list_composes_to_nothing(tmp_path):
    cfg = config(stages={"spec": {"prompt": []}})
    assert compose(cfg, "spec", tmp_path) == ""


def test_a_missing_packaged_prompt_names_the_file(tmp_path):
    with pytest.raises(BackendError, match="tcw/work/prompts/review.md"):
        compose(config(), "review", tmp_path)


def test_a_procedure_composes_the_same_way(tmp_path):
    cfg = config(procedures={"search": [{"blob": "Look."}]})
    assert procedure_prompt(cfg, "search", project_root=tmp_path).text == "Look."
    assert procedure_prompt(config(), "search", project_root=tmp_path).text == \
        packaged_text("procedures", "search").rstrip()


def test_skill_and_file_bindings(tmp_path):
    (tmp_path / "extra.md").write_text("From a file.\n")
    cfg = config(stages={"spec": {"prompt": [{"skill": "my-skill"},
                                             {"file": "extra.md"}]}})
    assert compose(cfg, "spec", tmp_path) == (
        "Invoke the my-skill skill.\n\nFrom a file.")


# -- when: filtering ------------------------------------------------------------------------

def make_item(tmp_path, tags=()):
    cfg = config(tags=["ui", "api"])
    backend = FsWorkBackend("p", tmp_path / "docs" / "work", cfg,
                            report=lambda l: None, today=lambda: date(2026, 10, 2))
    item = backend.create("Do it", Changes(add_tags=tuple(tags)), stage="spec",
                          request="The request.\n")
    layout = Layout(backend.work_path, backend.enabled, backend.external_stages)
    return backend, item, layout


def test_when_filters_by_tags(tmp_path):
    cfg = config(tags=["ui", "api"], stages={"spec": {"prompt": [
        {"blob": "UI only.", "when": {"tags": ["ui"]}},
        {"blob": "Not API.", "when": {"not_tags": ["api"]}}]}})
    _, ui_item, _ = make_item(tmp_path / "a", tags=("ui",))
    _, api_item, _ = make_item(tmp_path / "b", tags=("api",))
    assert compose(cfg, "spec", tmp_path, item=ui_item) == "UI only.\n\nNot API."
    assert compose(cfg, "spec", tmp_path, item=api_item) == ""
    assert compose(cfg, "spec", tmp_path) == "Not API."


# -- {{tcw:request}} ----------------------------------------------------------------------

def test_the_request_span(tmp_path):
    text = "Read {{tcw:request}}the request{{/tcw:request}} first."
    assert substitute_request(text, "Do X.\n") == "Read Do X. first."
    assert substitute_request(text, None) == "Read the request first."
    assert substitute_request(text, "  \n") == "Read the request first."


def test_an_unterminated_span_and_the_old_token_are_left_alone():
    assert substitute_request("a {{tcw:request}}b", "R") == "a {{tcw:request}}b"
    old = "{{tcw:body}}x{{/tcw:body}}"
    assert substitute_request(old, "R") == old


def test_no_request_token_is_left_in_composed_output(tmp_path):
    cfg = config(stages={"spec": {"prompt": [
        {"blob": "A {{tcw:request}}fallback{{/tcw:request}} B"}]}})
    for request in ("Real.", None):
        text = compose(cfg, "spec", tmp_path, request=request)
        assert "{{tcw:request}}" not in text and "{{/tcw:request}}" not in text


# -- generate: (7.1) ----------------------------------------------------------------------

SAVE = ("cat > \"$OUT/stdin.json\"; pwd > \"$OUT/pwd\"; env > \"$OUT/env\"; "
        "printf 'generated'")


def test_a_generate_binding_gets_the_record_request_and_environment(
        tmp_path, monkeypatch):
    out = tmp_path / "out"
    out.mkdir()
    monkeypatch.setenv("OUT", str(out))
    root = tmp_path / "project"
    backend, item, layout = make_item(root, tags=("ui",))
    record = item_record(item, backend.list(Query()), layout)
    cfg = config(stages={"spec": {"prompt": [{"generate": SAVE}]}})
    text = compose(cfg, "spec", root, item=item, record=record,
                   request=backend.read_request(item.slug.folder), layout=layout)
    assert text == "generated"

    payload = json.loads((out / "stdin.json").read_text())
    assert set(payload) == {"schema", "item", "request", "hook"}
    assert payload["schema"] == 1
    assert payload["item"] == record
    assert payload["request"] == "The request.\n"
    assert payload["hook"] == {"role": "prompt", "kind": "generate", "id": "spec",
                               "phase": "prompt", "body_truncated": False}
    assert Path((out / "pwd").read_text().strip()).resolve() == root.resolve()
    env = dict(line.split("=", 1) for line in
               (out / "env").read_text().splitlines() if "=" in line)
    assert env["TCW_SLUG"] == str(item.slug) and "/" in env["TCW_SLUG"]
    assert env["TCW_STAGE"] == "spec"
    assert env["TCW_HOOK_ROLE"] == "prompt"
    assert env["TCW_HOOK_KIND"] == "generate"
    assert env["TCW_PROJECT_ROOT"] == str(root)


def test_with_no_item_the_payload_item_is_null(tmp_path, monkeypatch):
    out = tmp_path / "out"
    out.mkdir()
    monkeypatch.setenv("OUT", str(out))
    cfg = config(stages={"spec": {"prompt": [{"generate": SAVE}]}})
    compose(cfg, "spec", tmp_path)
    payload = json.loads((out / "stdin.json").read_text())
    assert payload["item"] is None and payload["request"] is None


def test_a_long_request_is_cut_at_a_character_boundary():
    text, cut = generate_payload(None, "é" * 10, "prompt", "generate", "spec",
                                 "prompt", cap=5)
    payload = json.loads(text)
    assert cut and payload["hook"]["body_truncated"] is True
    assert payload["request"] == "éé"


def test_planning_runs_nothing(tmp_path, monkeypatch):
    out = tmp_path / "out"
    out.mkdir()
    monkeypatch.setenv("OUT", str(out))
    cfg = config(stages={"spec": {"prompt": [{"generate": SAVE}]}})
    res = stage_prompt(cfg, "spec", project_root=tmp_path, execute=False)
    assert list(out.iterdir()) == []
    assert [(p.kind, p.matched, p.executed) for p in res.plan] == [
        ("generate", True, False)]


def test_the_header_names_advance_dry_run():
    header = stage_header("spec", "p/2026-10-02-x")
    assert "tcw work advance p/2026-10-02-x --dry-run" in header
    assert "stage gate" not in header
