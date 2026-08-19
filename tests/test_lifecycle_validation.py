"""Every configuration mistake the roles/kinds model can make, rejected by name.

Criterion 9 of `2026-08-12-give-lifecycle-hooks-roles-kinds-and-conditions`, and
criterion 10 — the `command`-in-a-prompt exception, asserted in both directions
in one test so neither half can be tidied away.

Each assertion checks the *message*, not just that something was rejected: a
validator that returns one generic problem for every mistake is not telling
anyone what to fix.
"""

import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.store.base import parse_lifecycle_policy
from tcw.store.fs import FsWorkStore, init


def problems(raw) -> list[str]:
    _policy, found = parse_lifecycle_policy(raw)
    return found


def only(raw) -> str:
    found = problems(raw)
    assert len(found) == 1, found
    return found[0]


# ── role/kind legality ───────────────────────────────────────────────────────


def test_an_unknown_key_under_a_stage_is_rejected():
    p = only({"stages": {"spec": {"during": []}}})
    assert "during" in p and "'pre' or 'prompt'" in p


def test_command_under_an_explicit_prompt_names_generate():
    p = only({"stages": {"spec": {"prompt": [{"command": "./x.sh"}]}}})
    assert "'command' is not allowed in a prompt position" in p
    assert "use 'generate'" in p


def test_command_under_artifacts_names_generate():
    p = only({"artifacts": {"spec": [{"command": "./x.sh"}]}})
    assert "not allowed in a artifact position" in p and "generate" in p


def test_skill_under_artifacts_is_rejected():
    p = only({"artifacts": {"spec": [{"skill": "some-skill"}]}})
    assert "'skill' is not allowed in a artifact position" in p


def test_blob_in_a_check_position_is_rejected():
    p = only({"transitions": {"complete": {"pre": [{"blob": "text"}]}}})
    assert "'blob' is not allowed in a check position" in p


def test_a_bare_legacy_stage_list_still_accepts_command_and_prompt_does_not():
    """Criterion 10, both halves, deliberately in one test.

    The prohibition is real and so is the exception; applying either rule
    everywhere breaks the other. Splitting these into two tests would let one be
    deleted as redundant.
    """
    assert problems({"stages": {"spec": [{"command": "./legacy.sh"}]}}) == []
    p = only({"stages": {"spec": {"prompt": [{"command": "./legacy.sh"}]}}})
    assert "not allowed in a prompt position" in p


def test_an_unknown_artifact_name_is_rejected():
    p = only({"artifacts": {"blueprint": [{"blob": "x"}]}})
    assert "blueprint" in p and "unknown artifact" in p


def test_builtin_must_be_the_value_true():
    assert "'builtin' must be the value true" in only(
        {"stages": {"spec": {"prompt": [{"builtin": "yes"}]}}})
    assert "'builtin' must be the value true" in only(
        {"stages": {"spec": {"prompt": [{"builtin": False}]}}})


# ── conditions ───────────────────────────────────────────────────────────────


def test_an_unknown_when_key_is_rejected():
    p = only({"stages": {"spec": {"prompt": [
        {"blob": "x", "when": {"parent": "y"}}]}}})
    assert "unknown 'when' key(s) parent" in p


def test_a_bare_string_tags_value_names_the_list_form():
    p = only({"stages": {"spec": {"prompt": [
        {"blob": "x", "when": {"tags": "bug"}}]}}})
    assert "'when.tags' must be a list of tags" in p
    assert "[bug]" in p          # the message shows the fix


def test_a_non_string_tag_element_is_rejected():
    p = only({"stages": {"spec": {"prompt": [
        {"blob": "x", "when": {"tags": [1]}}]}}})
    assert "must be a non-blank string" in p


def test_a_null_when_is_rejected():
    p = only({"stages": {"spec": {"prompt": [{"blob": "x", "when": None}]}}})
    assert "'when' must be a non-empty mapping" in p


def test_an_empty_when_is_rejected():
    p = only({"stages": {"spec": {"prompt": [{"blob": "x", "when": {}}]}}})
    assert "'when' must be a non-empty mapping" in p


def test_a_non_string_type_is_rejected():
    p = only({"stages": {"spec": {"prompt": [
        {"blob": "x", "when": {"type": 3}}]}}})
    assert "'when.type' must be a string" in p


def test_an_unknown_type_value_is_rejected():
    """A typo that silently never matches is worse than a rejection."""
    p = only({"stages": {"spec": {"prompt": [
        {"blob": "x", "when": {"type": "epik"}}]}}})
    assert "'epik' is not a known item type" in p


# ── artifact ordering ────────────────────────────────────────────────────────


def test_builtin_must_be_last_in_an_artifact_list():
    p = only({"artifacts": {"spec": [{"builtin": True}, {"blob": "never"}]}})
    assert "must be last" in p and "shadow" in p


def test_a_conditional_builtin_artifact_is_rejected():
    p = only({"artifacts": {"spec": [
        {"blob": "a", "when": {"tags": ["bug"]}},
        {"builtin": True, "when": {"tags": ["x"]}}]}})
    assert "cannot carry a 'when'" in p


def test_an_entry_after_an_unconditional_one_is_unreachable():
    p = only({"artifacts": {"spec": [
        {"blob": "always"}, {"blob": "never", "when": {"tags": ["bug"]}}]}})
    assert "unreachable" in p and "first match wins" in p


def test_a_conditional_entry_before_a_fallback_is_fine():
    assert problems({"artifacts": {"spec": [
        {"blob": "for bugs", "when": {"tags": ["bug"]}},
        {"builtin": True}]}}) == []


# ── duplicates ───────────────────────────────────────────────────────────────


def test_the_same_binding_under_different_conditions_is_not_a_duplicate():
    """Identity is (kind, value, when). Rejecting this — as the old `ref`-only
    rule would — makes conditions unusable for their main purpose."""
    assert problems({"stages": {"spec": {"prompt": [
        {"generate": "./p.sh", "when": {"tags": ["bug"]}},
        {"generate": "./p.sh", "when": {"tags": ["feature"]}}]}}}) == []


def test_the_same_binding_under_identical_conditions_is_a_duplicate():
    p = only({"stages": {"spec": {"prompt": [
        {"generate": "./p.sh", "when": {"tags": ["bug"]}},
        {"generate": "./p.sh", "when": {"tags": ["bug"]}}]}}})
    assert "duplicate binding" in p


# ── output cap ───────────────────────────────────────────────────────────────


def test_a_non_positive_output_cap_is_rejected():
    assert "output-cap" in only({"output-cap": 0})
    assert "output-cap" in only({"output-cap": "big"})


# ── file bindings, which need a node on disk ─────────────────────────────────


def _node(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root, "repo")
    return root


def _configure(root: Path, lifecycle: dict) -> None:
    cfg_path = root / "tcw-config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    cfg.setdefault("work", {})["lifecycle"] = lifecycle
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))


def test_a_file_binding_that_does_not_exist_is_rejected(tmp_path):
    root = _node(tmp_path)
    _configure(root, {"stages": {"spec": {"prompt": [{"file": "missing.md"}]}}})
    found = FsWorkStore.open(root).lifecycle_problems()
    assert any("does not exist" in p and "missing.md" in p for p in found), found


def test_a_file_binding_escaping_the_node_root_is_rejected(tmp_path):
    root = _node(tmp_path)
    (tmp_path / "outside.md").write_text("secrets\n")
    _configure(root, {"stages": {"spec": {"prompt": [{"file": "../outside.md"}]}}})
    found = FsWorkStore.open(root).lifecycle_problems()
    assert any("outside the node root" in p for p in found), found


def test_a_symlink_escaping_the_node_root_is_rejected(tmp_path):
    """The check a lexical `..` scan passes while reading the file anyway."""
    root = _node(tmp_path)
    (tmp_path / "outside.md").write_text("secrets\n")
    (root / "link.md").symlink_to(tmp_path / "outside.md")
    _configure(root, {"stages": {"spec": {"prompt": [{"file": "link.md"}]}}})
    found = FsWorkStore.open(root).lifecycle_problems()
    assert any("outside the node root" in p for p in found), found


def test_a_file_binding_inside_the_node_is_accepted(tmp_path):
    root = _node(tmp_path)
    (root / "guide.md").write_text("# Guide\n")
    _configure(root, {"stages": {"spec": {"prompt": [{"file": "guide.md"}]}}})
    assert FsWorkStore.open(root).lifecycle_problems() == []


def test_a_malformed_policy_still_does_not_break_reading(tmp_path):
    """Reading is not validating — the rule the whole parser is built around,
    re-checked against the new model's rejections."""
    root = _node(tmp_path)
    _configure(root, {"stages": {"spec": {"prompt": [{"command": "./x.sh"}]}}})
    assert FsWorkStore.open(root).lifecycle_policy().stage("spec") == []
    assert FsWorkStore.open(root).board() == []


# ── an empty prompt list ─────────────────────────────────────────────────────


def test_a_bare_empty_stage_list_is_rejected():
    """The legacy spelling. It always meant nothing, and now that an
    unconfigured stage resolves to TCW's built-in it reads as an opt-out it is
    not — so `validate` refuses it rather than the model guessing."""
    p = only({"stages": {"spec": []}})
    assert "spec" in p and "blob" in p


def test_an_explicit_empty_prompt_list_is_rejected():
    p = only({"stages": {"spec": {"prompt": []}}})
    assert "spec" in p and "blob" in p


def test_an_empty_pre_list_is_untouched():
    """Asserted so the check cannot overreach into a different key: `pre: []`
    has no built-in behind it and means exactly what it says."""
    assert problems({"stages": {"spec": {"pre": []}}}) == []
    assert problems({"transitions": {"complete": {"pre": [], "post": []}}}) == []


def test_a_non_empty_prompt_list_is_still_accepted():
    assert problems({"stages": {"spec": [{"blob": "x"}]}}) == []
    assert problems({"stages": {"spec": {"prompt": [{"blob": "x"}]}}}) == []


def test_the_rejected_spelling_still_resolves_to_the_builtin(tmp_path):
    """Rejection is the parser's advisory problem list; `lifecycle_policy()`
    discards it. So the config `validate` now refuses still *runs*, and what it
    runs as is the built-in — which is the ambiguity the rejection exists to
    make visible rather than to change."""
    from tcw.work.resolve import (
        load_builtins, resolve_prompts, substitute_body)

    policy, found = parse_lifecycle_policy({"stages": {"spec": []}})
    assert found
    res = resolve_prompts(policy, "spec", None, tmp_path, load_builtins())
    # No artifacts are passed, so `{{tcw:body}}` resolves to its own inner text.
    assert res.text == substitute_body(
        load_builtins().stage_prompts["spec"], ()).rstrip()


def test_the_legacy_corpus_config_is_the_one_now_rejected():
    """Pinned to a config that demonstrably existed before this break rather
    than one written to fail it: `stage_empty.config.yaml` is part of C3's
    back-compat corpus, and its recorded `tcw work lifecycle` render — which
    reads the policy and discards problems — is unchanged."""
    corpus = Path(__file__).parent / "fixtures" / "lifecycle_baseline"
    raw = yaml.safe_load((corpus / "stage_empty.config.yaml").read_text())
    p = only(raw)
    assert "spec" in p
