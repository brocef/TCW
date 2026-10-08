"""`work.procedures` — every configuration mistake rejected by name, and reading
never broken by one. Spec criteria 8 and 11."""

import subprocess
from pathlib import Path

import yaml

from tcw.store.fs import init


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
    cfg_path = root / "tcw-config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    cfg.setdefault("work", {})["procedures"] = procedures
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))


def test_tcw_validate_fails_on_a_bad_block(tmp_path):
    root = _node(tmp_path)
    _configure(root, {"serach": [{"blob": "A"}]})
    r = subprocess.run(["tcw", "validate"], cwd=root, capture_output=True, text=True)
    assert r.returncode != 0
    assert "work.procedures.serach" in r.stdout + r.stderr


