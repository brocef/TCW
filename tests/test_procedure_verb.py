"""`tcw work procedure <id> [slug]` — spec criteria 1 and 3–7, end to end."""

import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.store.base import PROCEDURE_IDS
from tcw.store.fs import init

REPO = Path(__file__).resolve().parent.parent
ARGPARSE_REFUSAL = "invalid choice"


def _node(tmp_path: Path, name: str = "repo") -> Path:
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root, name)
    return root


def _configure(root: Path, procedures) -> None:
    """Every test states its own `work.procedures`; there is no default here."""
    cfg_path = root / "tcw-config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    cfg.setdefault("work", {})["procedures"] = procedures
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))


def _run(root: Path, *args: str):
    return subprocess.run(["tcw", "work", "procedure", *args],
                          cwd=str(root), capture_output=True, text=True)


def _default(pid: str) -> str:
    return (REPO / "tcw" / "work" / "procedures" / f"{pid}.md").read_text(
        encoding="utf-8").rstrip()


def test_an_unconfigured_node_prints_every_default(tmp_path):
    """Criterion 1."""
    root = _node(tmp_path)
    for pid in PROCEDURE_IDS:
        r = _run(root, pid)
        assert r.returncode == 0, (pid, r.stderr)
        assert r.stdout == _default(pid) + "\n", pid
        assert r.stderr == "", (pid, r.stderr)


def test_configured_bindings_compose_in_declaration_order(tmp_path):
    """Criterion 3."""
    root = _node(tmp_path)
    _configure(root, {"search": [{"blob": "A"}, {"builtin": True}, {"blob": "B"}],
                      "delegation": [{"blob": "ONLY"}]})
    r = _run(root, "search")
    assert r.returncode == 0, r.stderr
    assert r.stdout == "A\n\n" + _default("search") + "\n\nB\n"
    r = _run(root, "delegation")
    assert r.stdout == "ONLY\n"


def test_conditional_only_bindings_without_a_slug_say_why_nothing_printed(tmp_path):
    """Criterion 5."""
    root = _node(tmp_path)
    _configure(root, {"search": [{"blob": "BUG", "when": {"tags": ["bug"]}}]})
    r = _run(root, "search")
    assert r.returncode == 0
    assert r.stdout == ""
    assert "'search'" in r.stderr and "when:" in r.stderr
    assert "Without a work item a when: never matches" in r.stderr


def test_a_procedure_silenced_on_purpose_prints_no_note(tmp_path):
    root = _node(tmp_path)
    _configure(root, {"search": [{"blob": ""}]})
    r = _run(root, "search")
    assert (r.returncode, r.stdout, r.stderr) == (0, "", "")


def test_an_unknown_id_is_refused_by_name(tmp_path):
    """Criterion 6."""
    root = _node(tmp_path)
    r = _run(root, "postmortem")
    assert r.returncode == 1 and r.stdout == ""
    assert "unknown procedure 'postmortem'" in r.stderr
    assert "post-mortem" in r.stderr
    assert ARGPARSE_REFUSAL not in r.stderr


def test_an_unknown_slug_is_refused_by_name(tmp_path):
    root = _node(tmp_path)
    r = _run(root, "search", "2026-01-01-no-such-thing")
    assert r.returncode == 1 and r.stdout == ""
    assert "no such work item: 2026-01-01-no-such-thing" in r.stderr
    assert ARGPARSE_REFUSAL not in r.stderr


def test_a_deleted_file_binding_is_refused_by_name(tmp_path):
    root = _node(tmp_path)
    _configure(root, {"search": [{"blob": "BEFORE"}, {"file": "gone.md"}]})
    r = _run(root, "search")
    assert r.returncode == 1 and r.stdout == ""
    assert "gone.md" in r.stderr and r.stderr.startswith("tcw work procedure:")


def test_no_exec_runs_nothing_and_prints_nothing(tmp_path):
    """Criterion 7."""
    root = _node(tmp_path)
    _configure(root, {"search": [{"generate": "touch ran; echo X"},
                                 {"blob": "B", "when": {"tags": ["bug"]}}]})
    r = _run(root, "search", "--no-exec")
    assert r.returncode == 0, r.stderr
    assert r.stdout == ""
    assert not (root / "ran").exists()
    assert "generate — matched" in r.stderr
    assert "blob — skipped (condition)" in r.stderr


def test_outside_a_work_node_it_prints_tcws_default(tmp_path):
    """A skill such as documentation-sync runs in projects that are not TCW
    nodes. There is no project configuration to compose, so the answer is
    TCW's own text — not a refusal a skill would have to paper over."""
    r = _run(tmp_path, "search")
    assert r.returncode == 0, r.stderr
    assert r.stdout.rstrip() == _default("search")
    assert "no tcw work node here" not in r.stderr


def test_outside_a_work_node_a_work_item_still_refuses(tmp_path):
    r = _run(tmp_path, "search", "2026-01-01-anything")
    assert r.returncode == 1 and r.stdout == ""
    assert "no tcw work node here" in r.stderr


@pytest.mark.parametrize("args", [(), ("--help",)])
def test_the_verb_is_listed(tmp_path, args):
    r = subprocess.run(["tcw", "work", "procedure", *args], cwd=tmp_path,
                       capture_output=True, text=True)
    assert "procedure" in r.stdout + r.stderr
    assert ARGPARSE_REFUSAL not in r.stderr
