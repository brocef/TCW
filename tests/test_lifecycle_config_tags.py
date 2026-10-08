"""Tags and keys in the work configuration are reported, never ignored or
crashed on (spec: 2026-09-15-report-malformed-keys-and-unregistered-tags-in-lifecycle-config)."""

import subprocess
from pathlib import Path

import yaml

from tcw.cli import main
from tcw.store.fs import init


def node(tmp_path: Path, work: dict) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root, "node")
    config = root / "tcw-config.yaml"
    data = yaml.safe_load(config.read_text()) or {}
    data["work"] = {**(data.get("work") or {}), **work}
    config.write_text(yaml.safe_dump(data, sort_keys=False))
    return root


# ── criteria 1-2: conditions are normalized ─────────────────────────────────


# ── criterion 3: an unregistered condition tag is reported, policy still loads ──


# ── criteria 4-5: every tag reader agrees ────────────────────────────────────


# ── criterion 6: list --tags says when a tag is not registered ───────────────

def test_listing_by_an_unregistered_tag_says_so(tmp_path, monkeypatch, capsys):
    root = node(tmp_path, {"tags": ["cli"]})
    monkeypatch.chdir(root)
    assert main(["work", "list", "--tags", "nope"]) == 0
    assert "'nope' is not a registered tag" in capsys.readouterr().err
    assert main(["work", "list", "--tags", "CLI"]) == 0
    assert "not a registered tag" not in capsys.readouterr().err


# ── criterion 7: a non-string key is named, not a traceback ──────────────────

SPEC = {"blob": "x"}


# ── criterion 8: a skill binding's value must look like a skill name ─────────


