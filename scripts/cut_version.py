#!/usr/bin/env python3
"""Cut a new tcw version, deterministically.

    python scripts/cut_version.py <patch|minor|major|X.Y.Z>

Bumps the version in all 5 version-bearing files in lockstep, rotates the
release-notes + changelog `upcoming.md` working files to `v{version}.md`,
recreates fresh `upcoming.md` files, then commits and tags. Does NOT push —
publishing stays a human step.

The version string lives in 5 files (see CLAUDE.md "Versioning");
`.agents/plugins/marketplace.json` deliberately carries none and is untouched.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

# file → regex capturing the version (one match expected per file)
VERSION_FILES = {
    "pyproject.toml":                  r'(?m)^version = "([0-9]+\.[0-9]+\.[0-9]+)"',
    "tcw/__init__.py":                 r'__version__ = "([0-9]+\.[0-9]+\.[0-9]+)"',
    ".claude-plugin/plugin.json":      r'"version": "([0-9]+\.[0-9]+\.[0-9]+)"',
    ".claude-plugin/marketplace.json": r'"version": "([0-9]+\.[0-9]+\.[0-9]+)"',
    ".codex-plugin/plugin.json":       r'"version": "([0-9]+\.[0-9]+\.[0-9]+)"',
}

# upcoming working file → its fresh header template (recreated after rotation)
UPCOMING = {
    "docs/changelogs/upcoming.md": (
        "# Upcoming\n\n"
        "Developer changelog for the next version. Technical and precise; grouped by\n"
        "category.\n"
    ),
    "docs/release-notes/upcoming.md": (
        "# Upcoming\n\n"
        "User-facing release notes for the next version. Plain language — no jargon or\n"
        "internal module names.\n"
    ),
}


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def current_version(root: Path) -> str:
    """The version, read from all 5 files. Aborts if they disagree (drift)."""
    found: dict[str, str] = {}
    for rel, pat in VERSION_FILES.items():
        m = re.search(pat, (root / rel).read_text(encoding="utf-8"))
        if not m:
            sys.exit(f"cut_version: no version field in {rel}")
        found[rel] = m.group(1)
    uniq = set(found.values())
    if len(uniq) != 1:
        sys.exit(f"cut_version: version drift across files: {found}")
    return uniq.pop()


def next_version(current: str, bump: str) -> str:
    """Increment `current` by `bump` (patch|minor|major), or pass an explicit X.Y.Z."""
    if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", bump):
        return bump
    try:
        major, minor, patch = (int(x) for x in current.split("."))
    except ValueError:
        sys.exit(f"cut_version: current version '{current}' is not X.Y.Z")
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    if bump == "patch":
        return f"{major}.{minor}.{patch + 1}"
    sys.exit(f"cut_version: unknown bump '{bump}' (use patch|minor|major or X.Y.Z)")


def bump_files(root: Path, old: str, new: str) -> None:
    """Rewrite the version in all 5 files (exactly one substitution each)."""
    o = re.escape(old)
    specs = [
        ("pyproject.toml",                  rf'(?m)^version = "{o}"',  f'version = "{new}"'),
        ("tcw/__init__.py",                 rf'__version__ = "{o}"',   f'__version__ = "{new}"'),
        (".claude-plugin/plugin.json",      rf'"version": "{o}"',      f'"version": "{new}"'),
        (".claude-plugin/marketplace.json", rf'"version": "{o}"',      f'"version": "{new}"'),
        (".codex-plugin/plugin.json",       rf'"version": "{o}"',      f'"version": "{new}"'),
    ]
    for rel, pat, repl in specs:
        p = root / rel
        text, n = re.subn(pat, repl, p.read_text(encoding="utf-8"), count=1)
        if n != 1:
            sys.exit(f"cut_version: {rel}: expected exactly 1 match for {old}, found {n}")
        p.write_text(text, encoding="utf-8")


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True)


def rotate_upcoming(root: Path, version: str) -> None:
    """`git mv` each upcoming.md → v{version}.md, then recreate a fresh upcoming.md.

    The rotated file is retitled `# v{version}` and **the working-file preamble is
    dropped**. Without the retitle every released document keeps the `# Upcoming`
    placeholder it was drafted under, which is how 84 of the first 92 shipped
    files came to be titled "Upcoming". Without dropping the preamble the shipped
    file still says it is "for the next version" and still carries the
    drafting instructions ("Plain language — no jargon"), which are addressed to
    whoever writes the notes, not to whoever reads the release."""
    for rel, header in UPCOMING.items():
        src = root / rel
        dst = src.with_name(f"v{version}.md")
        _git(root, "mv", str(src), str(dst))
        text = dst.read_text(encoding="utf-8")
        if text.startswith(header):
            # The whole working-file header goes, preamble included.
            text = f"# v{version}\n" + text[len(header):]
        elif text.startswith("# Upcoming\n"):
            # Preamble edited or absent — retitle only, never guess at prose.
            text = f"# v{version}\n" + text[len("# Upcoming\n"):]
        dst.write_text(text, encoding="utf-8")
        src.write_text(header, encoding="utf-8")


def main(argv: list[str] | None = None, root: Path | None = None) -> int:
    ap = argparse.ArgumentParser(description="Cut a new tcw version.")
    ap.add_argument("bump", help="patch | minor | major | explicit X.Y.Z")
    args = ap.parse_args(argv)

    root = root or repo_root()
    old = current_version(root)
    new = next_version(old, args.bump)
    if new == old:
        sys.exit(f"cut_version: {new} is already the current version")

    bump_files(root, old, new)
    rotate_upcoming(root, new)
    rotated = [str(Path(rel).with_name(f"v{new}.md")) for rel in UPCOMING]
    _git(root, "add", "--",
         *VERSION_FILES.keys(), *UPCOMING.keys(),          # version edits + fresh upcoming
         *rotated)                                          # …and the retitled rotated files
    _git(root, "commit", "-qm", f"chore(release): cut v{new}")  # picks up the staged renames too
    _git(root, "tag", f"v{new}")
    print(f"cut v{new} (was v{old}). Push with: git push origin main --tags")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
