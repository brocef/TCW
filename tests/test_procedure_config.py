"""`work.procedures` — every configuration mistake rejected by name, and reading
never broken by one. Spec criteria 8 and 11."""

import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.store.fs import init
from tests.projectfiles import config_file, write_config_file


# ── on disk ──────────────────────────────────────────────────────────────────


def _node(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root, "repo")
    return root


def _configure(root: Path, procedures) -> None:
    cfg_path = config_file(root)
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    cfg.setdefault("work", {})["procedures"] = procedures
    write_config_file(cfg_path, yaml.safe_dump(cfg, sort_keys=False))


def test_tcw_validate_fails_on_a_bad_block(tmp_path):
    root = _node(tmp_path)
    _configure(root, {"serach": [{"blob": "A"}]})
    r = subprocess.run(["tcw", "validate"], cwd=root, capture_output=True, text=True)
    assert r.returncode != 0
    assert "work.procedures.serach" in r.stdout + r.stderr




def test_a_removed_procedure_id_is_a_problem_naming_the_known_ids(tmp_path):
    """TCW-74 criterion 6: `delegation` was a procedure in 2.x and is not one
    now, so configuring it is refused by name, with the ids that exist."""
    from tcw.store.base import PROCEDURE_IDS
    root = _node(tmp_path)
    _configure(root, {"delegation": [{"blob": "A"}]})
    r = subprocess.run(["tcw", "validate"], cwd=root, capture_output=True, text=True)
    assert r.returncode != 0
    out = r.stdout + r.stderr
    assert "work.procedures.delegation" in out
    assert all(known in out for known in PROCEDURE_IDS)


@pytest.mark.parametrize("pid, says", [
    ("post-mortem", "work.stages.postmortem.prompt"),
    ("decompose", "work.stages.plan.prompt"),
    ("delegation", 'tcw -C <folder> work new "<title>" --parent <full id>'),
    ("consolidate-plans", "tcw work new"),
])
def test_a_removed_procedure_id_says_where_its_text_went(pid, says):
    """A project upgrading from 2.x learns where to move the text, not only
    that the id is unknown (TCW-74 Design 5.1)."""
    from tcw.work.config import parse_work_config
    _, problems = parse_work_config({"procedures": {pid: [{"blob": "A"}]}})
    [problem] = [str(p) for p in problems]
    assert problem.startswith(f"work.procedures.{pid}: unknown procedure")
    assert "removed in TCW 3.0" in problem and says in problem


def test_a_misspelled_procedure_id_gets_no_removal_hint():
    from tcw.work.config import parse_work_config
    _, problems = parse_work_config({"procedures": {"serach": [{"blob": "A"}]}})
    assert "removed in TCW 3.0" not in str(problems[0])
