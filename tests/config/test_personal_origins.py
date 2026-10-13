"""Origins at work: where a `file:` is read from, `TCW_CONFIG_DIR`, the layer
of a failed `post` hook, and the personal-change note (TCW-72 AC 10, 11)."""

from __future__ import annotations

from pathlib import Path

from tcw.work.advance import advance
from tcw.work.backend import Query
from tcw.work.gates import project_reader
from tcw.store.project import FsProjectRegistry
from tcw.work.open import open_backend
from tests.config.conftest import tcw


def project(personal, work: dict | None = None) -> Path:
    (personal.root / "docs" / "work").mkdir(parents=True, exist_ok=True)
    if work is not None:
        personal.project({"work": work})
    return personal.root


def stage_prompt(personal, *, local=None, project_list=None):
    project(personal, None if project_list is None else
            {"stages": {"spec": {"prompt": project_list}}})
    if local is not None:
        personal.local({"work": {"stages": {"spec": {"prompt": local}}}})
    return tcw(personal.root, "work", "stage", "prompt", "spec")


NOTE = "note: this prompt was changed by personal configuration: tcw-config.local.yaml"


# -- AC 10: paths and commands ----------------------------------------------------


def test_a_user_wide_file_binding_reads_from_the_user_folder(personal):
    project(personal)
    prompts = personal.xdg / "tcw" / "prompts"
    prompts.mkdir(parents=True)
    (prompts / "spec.md").write_text("MY OWN WORDS\n")
    (personal.root / "prompts").mkdir()
    (personal.root / "prompts" / "spec.md").write_text("THE PROJECT'S WORDS\n")
    personal.user({"work": {"stages": {"spec": {"prompt": [{"file": "prompts/spec.md"}]}}}})
    result = tcw(personal.root, "work", "stage", "prompt", "spec")
    assert result.code == 0, result
    assert "MY OWN WORDS" in result.out and "THE PROJECT'S WORDS" not in result.out


def test_a_user_wide_file_leaving_its_folder_stops_work_list(personal):
    project(personal)
    personal.user({"work": {"stages": {"spec": {"prompt": [{"file": "../x.md"}]}}}})
    result = tcw(personal.root, "work", "list")
    assert result.code == 1 and str(personal.user_file) in result.err, result


def _post_hook_record(personal, layer: str, tmp_path) -> tuple[str, str]:
    record = tmp_path / f"{layer}.txt"
    project(personal)
    hook = {"work": {"stages": {"spec": {"post": [
        {"command": f'printf "%s|%s" "$TCW_CONFIG_DIR" "$PWD" > {record}'}]}}}}
    getattr(personal, layer)(hook)
    made = tcw(personal.root, "work", "new", "X")
    assert made.code == 0, made
    moved = tcw(personal.root, "work", "advance", made.out.strip())
    assert moved.code == 0, moved
    config_dir, cwd = record.read_text().split("|")
    return config_dir, cwd


def test_a_local_post_hook_runs_with_the_project_as_its_config_dir(personal, tmp_path):
    config_dir, cwd = _post_hook_record(personal, "local", tmp_path)
    assert Path(config_dir).resolve() == personal.root.resolve()
    assert Path(cwd).resolve() == personal.root.resolve()


def test_a_user_wide_post_hook_gets_the_user_folder(personal, tmp_path):
    config_dir, cwd = _post_hook_record(personal, "user", tmp_path)
    assert Path(config_dir) == personal.xdg / "tcw"
    assert Path(cwd).resolve() == personal.root.resolve()


def test_a_generate_binding_gets_its_config_dir(personal, tmp_path):
    project(personal)
    personal.user({"work": {"stages": {"spec": {"prompt": [
        {"generate": 'printf "from %s" "$TCW_CONFIG_DIR"'}]}}}})
    result = tcw(personal.root, "work", "stage", "prompt", "spec")
    assert result.code == 0, result
    assert f"from {personal.xdg / 'tcw'}" in result.out


# -- AC 11: origins in results ---------------------------------------------------------


def test_a_failing_user_wide_post_hook_names_its_file(personal, monkeypatch):
    root = project(personal)
    personal.user({"work": {"stages": {"spec": {"post": [{"command": "exit 1"}]}}}})
    made = tcw(root, "work", "new", "X")
    assert made.code == 0, made
    monkeypatch.chdir(root)
    backend = open_backend(root)
    slug = backend.list(Query())[0].slug
    outcome = advance(backend, backend.config, backend.layout,
                      project_reader(root, FsProjectRegistry.open(root)), root, slug)
    assert outcome.code == 6
    assert len(outcome.post_failures) == 1
    binding, origin, detail = outcome.post_failures[0]
    assert origin.layer == "user" and binding.value == "exit 1"
    assert str(personal.user_file) in detail
    assert any(str(personal.user_file) in m for m in outcome.messages)


def test_the_cli_names_the_file_of_a_failed_post_hook(personal):
    root = project(personal)
    personal.user({"work": {"stages": {"spec": {"post": [{"command": "exit 1"}]}}}})
    slug = tcw(root, "work", "new", "X").out.strip()
    moved = tcw(root, "work", "advance", slug)
    assert (moved.code, moved.out) == (6, "spec\n"), moved
    assert str(personal.user_file) in moved.err


def test_a_pre_gate_failure_names_no_file(personal):
    root = project(personal, {"stages": {"spec": {"pre": [{"command": "exit 1"}]}}})
    slug = tcw(root, "work", "new", "X").out.strip()
    refused = tcw(root, "work", "advance", slug)
    assert refused.code == 3
    assert " from " not in refused.err, refused.err


def test_the_note_when_the_local_file_sets_the_prompt(personal):
    result = stage_prompt(personal, local=[{"blob": "mine"}])
    assert result.code == 0 and NOTE in result.err.splitlines(), result


def test_no_note_without_a_personal_prompt(personal):
    result = stage_prompt(personal)
    assert result.code == 0 and "personal configuration" not in result.err, result


def test_a_local_inherit_alone_changes_nothing_on_stdout(personal):
    plain = stage_prompt(personal)
    with_inherit = stage_prompt(personal, local=[{"inherit": True}])
    assert with_inherit.out == plain.out
    assert NOTE in with_inherit.err.splitlines()


def test_the_note_for_a_procedure(personal):
    project(personal)
    personal.local({"work": {"procedures": {"audit-backlog": [{"blob": "mine"}]}}})
    result = tcw(personal.root, "work", "procedure", "audit-backlog")
    assert result.code == 0, result
    assert result.out == "mine\n"
    assert NOTE in result.err.splitlines()
