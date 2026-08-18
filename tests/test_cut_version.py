import importlib.util
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "cut_version.py"


def _load():
    spec = importlib.util.spec_from_file_location("cut_version", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cv = _load()


def make_repo(tmp_path: Path, version: str = "0.2.2") -> Path:
    root = tmp_path / "repo"
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".codex-plugin").mkdir(parents=True)
    (root / "tcw").mkdir()
    (root / "docs" / "changelogs").mkdir(parents=True)
    (root / "docs" / "release-notes").mkdir(parents=True)
    (root / "pyproject.toml").write_text(f'[project]\nname = "tcw"\nversion = "{version}"\n')
    (root / "tcw" / "__init__.py").write_text(f'__version__ = "{version}"\n')
    (root / ".claude-plugin" / "plugin.json").write_text(f'{{\n  "version": "{version}"\n}}\n')
    (root / ".claude-plugin" / "marketplace.json").write_text(
        f'{{\n  "plugins": [\n    {{\n      "version": "{version}"\n    }}\n  ]\n}}\n')
    (root / ".codex-plugin" / "plugin.json").write_text(f'{{\n  "version": "{version}"\n}}\n')
    (root / "docs/changelogs/upcoming.md").write_text("# Upcoming\n\nchangelog entries here\n")
    (root / "docs/release-notes/upcoming.md").write_text("# Upcoming\n\nrelease notes here\n")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "init"], check=True)
    return root


def test_next_version_increments():
    assert cv.next_version("0.2.2", "patch") == "0.2.3"
    assert cv.next_version("0.2.2", "minor") == "0.3.0"
    assert cv.next_version("0.2.2", "major") == "1.0.0"
    assert cv.next_version("0.2.2", "1.5.0") == "1.5.0"      # explicit passthrough


def test_next_version_invalid():
    with pytest.raises(SystemExit):
        cv.next_version("0.2.2", "bogus")


def test_current_version_reads_and_detects_drift(tmp_path):
    root = make_repo(tmp_path, "0.2.2")
    assert cv.current_version(root) == "0.2.2"
    (root / "tcw" / "__init__.py").write_text('__version__ = "9.9.9"\n')   # introduce drift
    with pytest.raises(SystemExit):
        cv.current_version(root)


def test_bump_files_updates_all_five(tmp_path):
    root = make_repo(tmp_path, "0.2.2")
    cv.bump_files(root, "0.2.2", "0.2.3")
    assert cv.current_version(root) == "0.2.3"


def test_main_end_to_end(tmp_path):
    root = make_repo(tmp_path, "0.2.2")
    cv.main(["patch"], root=root)
    assert cv.current_version(root) == "0.2.3"
    # old upcoming content rotated into the versioned files, retitled to the
    # version it shipped as. Rotation used to be a bare `git mv`, so a released
    # document kept the `# Upcoming` placeholder it was drafted under.
    assert (root / "docs/changelogs/v0.2.3.md").read_text() == "# v0.2.3\n\nchangelog entries here\n"
    assert (root / "docs/release-notes/v0.2.3.md").read_text() == "# v0.2.3\n\nrelease notes here\n"
    # fresh upcoming.md reset (header kept, old entries gone)
    fresh = (root / "docs/changelogs/upcoming.md").read_text()
    assert "# Upcoming" in fresh and "changelog entries here" not in fresh
    # commit + tag
    tags = subprocess.run(["git", "-C", str(root), "tag"], capture_output=True, text=True).stdout
    assert "v0.2.3" in tags
    msg = subprocess.run(["git", "-C", str(root), "log", "-1", "--pretty=%s"],
                         capture_output=True, text=True).stdout.strip()
    assert msg == "chore(release): cut v0.2.3"
    # everything the cut touched is *in* the commit — the retitle above used to
    # be left unstaged, so the tag pointed at a file still titled "# Upcoming".
    dirty = subprocess.run(["git", "-C", str(root), "status", "--porcelain"],
                           capture_output=True, text=True).stdout
    assert dirty == "", f"cut left uncommitted changes:\n{dirty}"


def test_rotation_drops_the_working_file_preamble(tmp_path):
    """A shipped release note must not carry the drafting instructions.

    The `upcoming.md` header says the file is "for the next version" and tells
    its *author* to use plain language — text addressed to whoever writes the
    notes, not to whoever reads the release. Retitling `# Upcoming` alone left
    that preamble in every published file from v0.6.2 through v1.0.0.
    """
    root = make_repo(tmp_path, "0.2.2")
    # The real templates the script recreates, not the fixture's short stand-in.
    for rel, header in cv.UPCOMING.items():
        (root / rel).write_text(header + "\n## Added\n\n- a thing\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "commit", "-aqm", "real headers"], check=True)

    cv.main(["minor"], root=root)

    for rel in cv.UPCOMING:
        shipped = (root / rel).with_name("v0.3.0.md").read_text(encoding="utf-8")
        assert shipped.startswith("# v0.3.0\n"), shipped[:40]
        assert "for the next version" not in shipped
        assert "## Added" in shipped and "- a thing" in shipped
        # the fresh working file keeps its preamble — it is drafting guidance
        assert "for the next version" in (root / rel).read_text(encoding="utf-8")
