"""Criterion 1: every config valid before the roles/kinds rewrite renders the same.

The baselines in `tests/fixtures/lifecycle_baseline/` were captured from the CLI
**before** `parse_lifecycle_policy` was touched, in their own commit. That is what
makes this an independent check rather than a record of what the code now does —
the expected bytes could not be edited into agreement with a regression without
the edit showing up in the diff as a fixture change.

One config per row of C3's back-compat table, plus this repository's own node.
"""

import json
import subprocess
from pathlib import Path

import pytest
import yaml

FIXTURES = Path(__file__).parent / "fixtures" / "lifecycle_baseline"
REPO = Path(__file__).resolve().parents[1]

CASES = sorted(p.stem for p in FIXTURES.glob("*.json") if p.stem != "self")


def _build_node(root: Path, lifecycle: object) -> None:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    subprocess.run(["tcw", "work", "init", "--id", "corpus"], cwd=str(root),
                   capture_output=True, check=True)
    cfg_path = root / "tcw-config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    if lifecycle is not None:
        cfg.setdefault("work", {})["lifecycle"] = lifecycle
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))


def _replay(root: Path, argv: list[str]) -> dict:
    r = subprocess.run(["tcw", "work", "lifecycle", *argv], cwd=str(root),
                       capture_output=True, text=True)
    return {"argv": argv, "returncode": r.returncode,
            "stdout": r.stdout, "stderr": r.stderr}


@pytest.mark.parametrize("case", CASES)
def test_a_legacy_config_renders_byte_identically(case, tmp_path):
    baseline = json.loads((FIXTURES / f"{case}.json").read_text())
    cfg_file = FIXTURES / f"{case}.config.yaml"
    lifecycle = yaml.safe_load(cfg_file.read_text()) if cfg_file.is_file() else None

    root = tmp_path / case
    _build_node(root, lifecycle)

    for expected in baseline:
        actual = _replay(root, expected["argv"])
        assert actual == expected, (
            f"{case} {' '.join(expected['argv']) or '(no args)'} changed:\n"
            f"  was: {expected['stdout']!r} / rc={expected['returncode']}\n"
            f"  now: {actual['stdout']!r} / rc={actual['returncode']}")


def test_this_repository_s_own_lifecycle_output_is_unchanged():
    """The corpus row nobody thought to write.

    If C3 changes how this node's config renders, every `tcw` command in the
    session that develops C3 starts behaving differently — the cheapest place in
    the world to find out.
    """
    baseline = json.loads((FIXTURES / "self.json").read_text())
    for expected in baseline:
        actual = _replay(REPO, expected["argv"])
        assert actual == expected, (
            f"this repo's `tcw work lifecycle "
            f"{' '.join(expected['argv'])}` changed")
