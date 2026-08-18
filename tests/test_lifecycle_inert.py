"""`tcw work lifecycle` reports; it never runs.

Criterion 11 — the sentinel technique — and criterion 12, `--phase`.

The sentinel is at an **absolute** path so a hook whose cwd differs from the
test's cannot make the assertion vacuously true, and bindings are configured on
*every* stage and transition id so the check does not depend on which one someone
happened to try.
"""

import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.store.base import STAGE_IDS, TRANSITION_IDS
from tcw.store.fs import init


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


def _cli(root: Path, *args: str):
    return subprocess.run(["tcw", "work", "lifecycle", *args], cwd=str(root),
                          capture_output=True, text=True)


@pytest.fixture
def wired(tmp_path):
    """A node with a sentinel-writing binding on every id, in every position."""
    root = _node(tmp_path)
    sentinel = (tmp_path / "SENTINEL").resolve()
    touch = f"touch {sentinel}"
    _configure(root, {
        "stages": {sid: {"pre": [{"command": touch}],
                         "prompt": [{"generate": touch}, {"blob": "static"}]}
                   for sid in STAGE_IDS},
        "transitions": {tid: {"pre": [{"command": touch}],
                              "post": [{"command": touch}]}
                        for tid in TRANSITION_IDS},
    })
    return root, sentinel


def test_no_form_of_lifecycle_executes_anything(wired):
    root, sentinel = wired
    invocations = [
        (),
        ("--json",),
        *[("--stage", sid) for sid in STAGE_IDS],
        *[("--stage", sid, "--directive") for sid in STAGE_IDS],
        *[("--stage", sid, "--phase", "pre") for sid in STAGE_IDS],
        *[("--stage", sid, "--phase", "prompt") for sid in STAGE_IDS],
        *[("--transition", tid) for tid in TRANSITION_IDS],
        *[("--transition", tid, "--directive") for tid in TRANSITION_IDS],
        *[("--transition", tid, "--phase", "pre") for tid in TRANSITION_IDS],
        *[("--transition", tid, "--phase", "post") for tid in TRANSITION_IDS],
    ]
    for argv in invocations:
        r = _cli(root, *argv)
        assert r.returncode == 0, f"{argv}: {r.stderr}"
        assert not sentinel.exists(), (
            f"`tcw work lifecycle {' '.join(argv)}` executed a binding")


# ── --phase ──────────────────────────────────────────────────────────────────


def test_phase_pre_on_a_transition_reports_only_pre(tmp_path):
    root = _node(tmp_path)
    _configure(root, {"transitions": {"complete": {
        "pre": [{"command": "before"}], "post": [{"command": "after"}]}}})
    out = _cli(root, "--transition", "complete", "--phase", "pre",
               "--directive").stdout
    assert "before" in out and "after" not in out


def test_phase_post_on_a_transition_reports_only_post(tmp_path):
    root = _node(tmp_path)
    _configure(root, {"transitions": {"complete": {
        "pre": [{"command": "before"}], "post": [{"command": "after"}]}}})
    out = _cli(root, "--transition", "complete", "--phase", "post",
               "--directive").stdout
    assert "after" in out and "before" not in out


def test_phase_prompt_on_a_stage_reports_only_prompts(tmp_path):
    root = _node(tmp_path)
    _configure(root, {"stages": {"spec": {
        "pre": [{"command": "a-check"}], "prompt": [{"skill": "a-prompt"}]}}})
    out = _cli(root, "--stage", "spec", "--phase", "prompt", "--directive").stdout
    assert "a-prompt" in out and "a-check" not in out


def test_phase_post_on_a_stage_errors_naming_the_reason(tmp_path):
    """Silence would read as "nothing is configured", which is a different fact."""
    root = _node(tmp_path)
    r = _cli(root, "--stage", "spec", "--phase", "post")
    assert r.returncode == 1
    assert r.stdout == ""
    assert "stages have no 'post' phase" in r.stderr
    assert "next stage's 'pre'" in r.stderr


def test_phase_prompt_on_a_transition_errors(tmp_path):
    root = _node(tmp_path)
    r = _cli(root, "--transition", "complete", "--phase", "prompt")
    assert r.returncode == 1
    assert "transitions have no 'prompt' phase" in r.stderr


def test_phase_without_a_target_errors(tmp_path):
    root = _node(tmp_path)
    r = _cli(root, "--phase", "pre")
    assert r.returncode == 1
    assert "--phase needs --stage or --transition" in r.stderr


# ── the --json superset ──────────────────────────────────────────────────────


def test_stage_checks_appear_in_json_only_when_configured(tmp_path):
    import json
    root = _node(tmp_path)
    _configure(root, {"stages": {"spec": [{"skill": "legacy"}]}})
    spec = next(s for s in json.loads(_cli(root, "--json").stdout)["steps"]
                if s["id"] == "spec")
    # A legacy config's payload is exactly what it always was: `bind`, alone.
    assert spec["bindings"] == {"bind": [{"skill": "legacy"}]}

    _configure(root, {"stages": {"spec": {"pre": [{"command": "c"}],
                                          "prompt": [{"skill": "legacy"}]}}})
    spec = next(s for s in json.loads(_cli(root, "--json").stdout)["steps"]
                if s["id"] == "spec")
    assert spec["bindings"] == {"pre": [{"command": "c"}],
                                "bind": [{"skill": "legacy"}]}


def test_conditions_and_artifacts_appear_in_json_only_when_configured(tmp_path):
    import json
    root = _node(tmp_path)
    _configure(root, {
        "stages": {"spec": {"prompt": [
            {"blob": "b", "when": {"tags": ["bug"]}}]}},
        "artifacts": {"spec": [{"builtin": True}]},
        "output-cap": 4096,
    })
    doc = json.loads(_cli(root, "--json").stdout)
    assert doc["output-cap"] == 4096
    assert doc["artifacts"] == {"spec": [{"builtin": True}]}
    spec = next(s for s in doc["steps"] if s["id"] == "spec")
    assert spec["bindings"]["bind"] == [{"blob": "b", "when": {"tags": ["bug"]}}]
