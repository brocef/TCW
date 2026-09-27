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


README = "# Upcoming entries\n\nDrafting guidance for whoever writes an entry.\n"


def make_repo(tmp_path: Path, version: str = "0.2.2") -> Path:
    root = tmp_path / "repo"
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".codex-plugin").mkdir(parents=True)
    (root / "tcw").mkdir()
    (root / "docs" / "changelogs" / "upcoming").mkdir(parents=True)
    (root / "docs" / "release-notes" / "upcoming").mkdir(parents=True)
    (root / "pyproject.toml").write_text(f'[project]\nname = "tcw"\nversion = "{version}"\n')
    (root / "tcw" / "__init__.py").write_text(f'__version__ = "{version}"\n')
    (root / ".claude-plugin" / "plugin.json").write_text(f'{{\n  "version": "{version}"\n}}\n')
    (root / ".claude-plugin" / "marketplace.json").write_text(
        f'{{\n  "plugins": [\n    {{\n      "version": "{version}"\n    }}\n  ]\n}}\n')
    (root / ".codex-plugin" / "plugin.json").write_text(f'{{\n  "version": "{version}"\n}}\n')
    for kind in ("changelogs", "release-notes"):
        (root / f"docs/{kind}/upcoming/README.md").write_text(README)
    (root / "docs/changelogs/upcoming/a.md").write_text("## Added\n\n- changelog entry\n")
    (root / "docs/release-notes/upcoming/a.md").write_text("## Improvements\n\n- release note\n")
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


def _git_out(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args],
                          capture_output=True, text=True, check=True).stdout


def _entries(root: Path, kind: str, files: dict[str, str]) -> None:
    """Replace the fixture's entry files in `docs/<kind>/upcoming/` with `files`."""
    folder = root / "docs" / kind / "upcoming"
    for p in folder.glob("*.md"):
        if p.name != "README.md":
            p.unlink()
    for name, text in files.items():
        (folder / name).write_text(text, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "entries"], check=True)


def _headings(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith("## ")]


def _assert_cut_is_clean(root: Path, version: str) -> None:
    """Every entry file is gone, the guidance stays, and the cut is committed and tagged."""
    for kind in ("changelogs", "release-notes"):
        folder = root / "docs" / kind / "upcoming"
        assert sorted(p.name for p in folder.iterdir()) == ["README.md"]
        assert (folder / "README.md").read_text() == README
    assert f"v{version}" in _git_out(root, "tag").split()
    assert _git_out(root, "log", "-1", "--pretty=%s").strip() == f"chore(release): cut v{version}"
    assert _git_out(root, "status", "--porcelain") == ""


def test_main_end_to_end(tmp_path):
    root = make_repo(tmp_path, "0.2.2")
    cv.main(["patch"], root=root)
    assert cv.current_version(root) == "0.2.3"
    assert (root / "docs/changelogs/v0.2.3.md").read_text() == "# v0.2.3\n\n## Added\n\n- changelog entry\n"
    assert (root / "docs/release-notes/v0.2.3.md").read_text() == "# v0.2.3\n\n## Improvements\n\n- release note\n"
    _assert_cut_is_clean(root, "0.2.3")


def test_combine_merges_sections_by_heading(tmp_path):
    root = make_repo(tmp_path, "0.2.2")
    _entries(root, "changelogs", {
        "a.md": "## Fixed\n\n- a fixed\n\n## Added\n\n- a added\n",
        "b.md": "## Added\n\n- b added\n\n## Security\n\n- b security\n",
    })
    cv.main(["patch"], root=root)
    shipped = (root / "docs/changelogs/v0.2.3.md").read_text()
    assert shipped.startswith("# v0.2.3\n")
    assert _headings(shipped) == ["## Added", "## Fixed", "## Security"]
    assert shipped.index("- a added") < shipped.index("- b added") < shipped.index("## Fixed")
    assert "Drafting guidance" not in shipped
    _assert_cut_is_clean(root, "0.2.3")


def test_combine_with_no_entries_ships_only_the_title(tmp_path):
    root = make_repo(tmp_path, "0.2.2")
    _entries(root, "changelogs", {})
    _entries(root, "release-notes", {})
    cv.main(["patch"], root=root)
    for kind in ("changelogs", "release-notes"):
        assert (root / f"docs/{kind}/v0.2.3.md").read_text() == "# v0.2.3\n"
    _assert_cut_is_clean(root, "0.2.3")


def test_subheadings_stay_under_their_section(tmp_path):
    root = make_repo(tmp_path, "0.2.2")
    _entries(root, "changelogs", {
        "a.md": "## Added\n\n- a added\n",
        "b.md": "## Added\n\n- b added\n\n### Detail\n\n- b detail\n\n## Fixed\n\n- b fixed\n",
    })
    cv.main(["patch"], root=root)
    shipped = (root / "docs/changelogs/v0.2.3.md").read_text()
    assert shipped.index("- b added") < shipped.index("### Detail") < shipped.index("## Fixed")


def test_release_notes_keep_first_appearance_order(tmp_path):
    root = make_repo(tmp_path, "0.2.2")
    _entries(root, "release-notes", {
        "a.md": "## Zeta\n\n- a zeta\n",
        "b.md": "## Alpha\n\n- b alpha\n\n## Zeta\n\n- b zeta\n",
    })
    cv.main(["patch"], root=root)
    shipped = (root / "docs/release-notes/v0.2.3.md").read_text()
    assert _headings(shipped) == ["## Zeta", "## Alpha"]
    assert shipped.index("- a zeta") < shipped.index("- b zeta") < shipped.index("## Alpha")


def test_text_before_the_first_heading_follows_the_title(tmp_path):
    root = make_repo(tmp_path, "0.2.2")
    _entries(root, "changelogs", {
        "a.md": "## Added\n\n- a added\n",
        "b.md": "A loose paragraph.\n",
    })
    cv.main(["patch"], root=root)
    shipped = (root / "docs/changelogs/v0.2.3.md").read_text()
    assert shipped.startswith("# v0.2.3\n\nA loose paragraph.\n")
    assert shipped.index("A loose paragraph.") < shipped.index("## Added")


def test_readme_guidance_never_ships(tmp_path):
    """The folder's README.md is addressed to whoever writes an entry, not to
    whoever reads the release, so the cut must neither ship nor consume it —
    the same reason the old rotation dropped the `upcoming.md` preamble."""
    root = make_repo(tmp_path, "0.2.2")
    cv.main(["minor"], root=root)
    for kind in ("changelogs", "release-notes"):
        assert "Drafting guidance" not in (root / f"docs/{kind}/v0.3.0.md").read_text()
    _assert_cut_is_clean(root, "0.3.0")


def test_a_missing_upcoming_folder_aborts_before_anything_changes(tmp_path):
    root = make_repo(tmp_path, "0.2.2")
    subprocess.run(["git", "-C", str(root), "rm", "-rqf", "docs/release-notes/upcoming"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "drop"], check=True)
    with pytest.raises(SystemExit, match="docs/release-notes/upcoming"):
        cv.main(["patch"], root=root)
    assert cv.current_version(root) == "0.2.2"
    assert _git_out(root, "status", "--porcelain") == ""
