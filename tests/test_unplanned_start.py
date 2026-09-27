"""An item started before its spec and plan is warned about, and can still be
specified and planned (spec: 2026-09-16-stop-an-item-reaching-implement-without-
a-spec-and-plan-and-say-how-to-plan-an-item-started-too-early)."""

import subprocess
from pathlib import Path

import yaml

from tcw.store.fs import FsWorkStore, init


def _node(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    for cmd in (["init", "-q"], ["config", "user.email", "t@t"],
                ["config", "user.name", "t"]):
        subprocess.run(["git", "-C", str(root), *cmd], check=True)
    init(["work"], root, "repo")
    return root


def _tcw(root: Path, *args: str):
    return subprocess.run(["tcw", "work", *args], cwd=str(root),
                          capture_output=True, text=True)


def _started(root: Path, *, spec: bool = False, plan: bool = False):
    st = FsWorkStore.open(root)
    slug = st.create("Thing", created="2026-01-01").slug
    if spec:
        st.write_artifact(slug, "spec", "# Spec\n")
    if plan:
        st.write_artifact(slug, "plan", "# Plan\n")
    return slug, _tcw(root, "start", slug)


def _bind(root: Path, stage: str, command: str) -> None:
    cfg_path = root / "tcw-config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    stages = cfg.setdefault("work", {}).setdefault("lifecycle", {}) \
                .setdefault("stages", {})
    stages.setdefault(stage, {}).setdefault("pre", []).append({"command": command})
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))


# ── criterion 3: start warns, and still starts ───────────────────────────────

def test_start_names_the_missing_documents_and_how_to_write_them(tmp_path):
    root = _node(tmp_path)
    slug, out = _started(root)
    assert out.returncode == 0, out.stderr
    assert "spec.md" in out.stderr and "plan.md" in out.stderr, out.stderr
    assert f"tcw work stage gate spec {slug}" in out.stderr, out.stderr
    assert FsWorkStore.open(root).get(slug).status == "active"


def test_start_names_only_what_is_missing(tmp_path):
    slug, out = _started(_node(tmp_path), spec=True)
    assert "plan.md" in out.stderr and "spec.md" not in out.stderr, out.stderr


def test_start_says_nothing_when_both_are_written(tmp_path):
    _, out = _started(_node(tmp_path), spec=True, plan=True)
    assert out.returncode == 0 and "plan.md" not in out.stderr, out.stderr


# ── criteria 1-2: spec and plan run for an active item ───────────────────────

def test_spec_and_plan_gates_pass_for_an_active_item(tmp_path):
    root = _node(tmp_path)
    slug, _ = _started(root)
    for stage in ("spec", "plan"):
        out = _tcw(root, "stage", "gate", stage, slug)
        assert out.returncode == 0, (stage, out.stderr)


def test_a_bound_check_still_runs_for_an_active_item(tmp_path):
    root = _node(tmp_path)
    _bind(root, "plan", "false")
    slug, _ = _started(root)
    assert _tcw(root, "stage", "gate", "plan", slug).returncode != 0


def test_scaffold_writes_a_spec_draft_for_an_active_item(tmp_path):
    root = _node(tmp_path)
    slug, _ = _started(root)
    out = _tcw(root, "scaffold", "spec", slug)
    assert out.returncode == 0, out.stderr


# ── criterion 4: the implement gate warns; a project can make it refuse ──────

def test_implement_gate_warns_without_a_plan_but_passes(tmp_path):
    root = _node(tmp_path)
    slug, _ = _started(root, spec=True)
    out = _tcw(root, "stage", "gate", "implement", slug)
    assert out.returncode == 0, out.stderr
    assert "plan.md" in out.stderr, out.stderr


def test_implement_gate_is_quiet_when_both_are_written(tmp_path):
    root = _node(tmp_path)
    slug, _ = _started(root, spec=True, plan=True)
    out = _tcw(root, "stage", "gate", "implement", slug)
    assert out.returncode == 0 and "plan.md" not in out.stderr, out.stderr


def test_this_repository_refuses_implement_without_spec_and_plan():
    cfg = yaml.safe_load((Path(__file__).parent.parent / "tcw-config.yaml")
                         .read_text())
    pre = cfg["work"]["lifecycle"]["stages"]["implement"]["pre"]
    commands = {b["command"] for b in pre}
    assert {"python scripts/require_artifact.py spec",
            "python scripts/require_artifact.py plan"} <= commands


# ── criterion 5: resolved statuses still refuse ──────────────────────────────

def test_spec_is_still_refused_in_review(tmp_path):
    root = _node(tmp_path)
    slug, _ = _started(root)
    assert _tcw(root, "submit", slug).returncode == 0
    out = _tcw(root, "stage", "gate", "spec", slug)
    assert out.returncode == 1 and "not legal" in out.stderr, out.stderr


# ── review findings ──────────────────────────────────────────────────────────

def test_an_unreadable_spec_does_not_fail_a_start_that_happened(tmp_path):
    root = _node(tmp_path)
    st = FsWorkStore.open(root)
    slug = st.create("Thing", created="2026-01-01").slug
    (st.path(slug) / "spec.md").write_bytes(b"caf\xe9 latin-1\n")
    out = _tcw(root, "start", slug)
    assert out.returncode == 0, out.stderr
    assert f"started {slug}" in out.stdout


def test_a_qualified_reference_is_advised_as_typed(tmp_path):
    root = _node(tmp_path)
    child = root / "kid"
    child.mkdir()
    init(["work"], child, "kid")
    for path, links in ((root, {"children": {"kid": "kid"}}),
                        (child, {"parent": {"repo": ".."}})):
        cfg = yaml.safe_load((path / "tcw-config.yaml").read_text()) or {}
        cfg["connected-projects"] = links
        (path / "tcw-config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    slug = FsWorkStore.open(child).create("Thing", created="2026-01-01").slug
    out = _tcw(root, "start", f"kid/{slug}")
    assert out.returncode == 0, out.stderr
    assert f"`tcw work stage gate spec kid/{slug}`" in out.stderr, out.stderr
