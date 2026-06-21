"""Plugin manifests parse, and the version is in lockstep across all 5 files.

The single automated guard against *authoring* drift (runtime cache-vs-installed
drift is `/tcw-doctor`'s job, not this test's).
"""
import json
import tomllib
from pathlib import Path

import tcw

REPO = Path(__file__).resolve().parent.parent

CLAUDE_PLUGIN = REPO / ".claude-plugin" / "plugin.json"
CLAUDE_MARKET = REPO / ".claude-plugin" / "marketplace.json"
CODEX_PLUGIN = REPO / ".codex-plugin" / "plugin.json"
AGENTS_MARKET = REPO / ".agents" / "plugins" / "marketplace.json"

ALL_MANIFESTS = [CLAUDE_PLUGIN, CLAUDE_MARKET, CODEX_PLUGIN, AGENTS_MARKET]


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def test_all_manifests_exist_and_parse():
    for m in ALL_MANIFESTS:
        assert m.is_file(), f"missing manifest: {m}"
        _load(m)  # raises on malformed JSON


def test_five_version_fields_agree():
    pyproject = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    versions = {
        "pyproject.toml": pyproject["project"]["version"],
        "tcw/__init__.py": tcw.__version__,
        ".claude-plugin/plugin.json": _load(CLAUDE_PLUGIN)["version"],
        ".claude-plugin/marketplace.json": _load(CLAUDE_MARKET)["plugins"][0]["version"],
        ".codex-plugin/plugin.json": _load(CODEX_PLUGIN)["version"],
    }
    assert len(set(versions.values())) == 1, f"version drift: {versions}"


def test_agents_marketplace_carries_no_version():
    """Deliberately version-free (per spec) — keep it that way so it never
    becomes a 6th drift source."""
    data = _load(AGENTS_MARKET)
    assert "version" not in data
    assert all("version" not in p for p in data.get("plugins", []))


def test_symlink_points_at_repo_root():
    link = REPO / "plugins" / "tcw"
    assert link.is_symlink(), f"{link} must be a symlink"
    assert link.resolve() == REPO, "plugins/tcw must resolve to the repo root"
