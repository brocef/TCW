#!/usr/bin/env python3
"""Cut a new tcw version, deterministically.

    python scripts/cut_version.py <patch|minor|major|X.Y.Z>

Bumps the version in all 5 version-bearing files in lockstep, combines the
entry files in `docs/{changelogs,release-notes}/upcoming/` into each folder's
`v{version}.md` (deleting them, keeping the folder's README.md), then commits
and tags. Does NOT push — publishing stays a human step.

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

# upcoming entry folder → the section headings that lead its combined document,
# in this order; every other heading follows in the order it first appears.
UPCOMING = {
    "docs/changelogs/upcoming": ("Added", "Changed", "Fixed", "Removed", "Internal"),
    "docs/release-notes/upcoming": (),
}
# Drafting guidance for whoever writes an entry; never combined, and it keeps the
# folder in git when there are no entries.
GUIDANCE = "README.md"


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


def combine(texts: list[str], order: tuple[str, ...] = ()) -> str:
    """Combine entry files into one body, merging `## ` sections by heading.

    Each text splits into a leading block (anything before its first `## ` line)
    and `## ` sections, each running to the next `## ` line, so a `###` heading
    stays with the section above it. Sections with the same heading merge, their
    bodies joined in the order given. Headings in `order` lead, in that order;
    the rest follow in the order they first appear. Leading blocks come first."""
    leading: list[str] = []
    sections: dict[str, list[str]] = {}
    for text in texts:
        heading, lines = None, []
        for line in text.splitlines() + ["## "]:          # sentinel flushes the last part
            if line.startswith("## "):
                part = "\n".join(lines).strip()
                if heading is None:
                    if part:
                        leading.append(part)
                elif part:
                    sections.setdefault(heading, []).append(part)
                else:
                    sections.setdefault(heading, [])
                heading, lines = line[3:].strip(), []
            else:
                lines.append(line)
    ordered = [h for h in order if h in sections] + [h for h in sections if h not in order]
    blocks = leading + ["\n\n".join([f"## {h}", *sections[h]]) for h in ordered]
    return "\n\n".join(blocks)


def combine_upcoming(root: Path, version: str) -> list[str]:
    """Write each folder's entries to `v{version}.md` beside it and `git rm` them.

    Returns the written paths, to stage. The shipped file is titled `# v{version}`
    and carries none of the folder's README.md, which is addressed to whoever
    writes an entry rather than to whoever reads the release."""
    written = []
    for rel, order in UPCOMING.items():
        folder = root / rel
        entries = sorted(p for p in folder.glob("*.md") if p.name != GUIDANCE)
        body = combine([p.read_text(encoding="utf-8") for p in entries], order)
        dst = folder.parent / f"v{version}.md"
        dst.write_text(f"# v{version}\n" + (f"\n{body}\n" if body else ""), encoding="utf-8")
        written.append(str(dst.relative_to(root)))
        if entries:
            _git(root, "rm", "-q", "--", *(str(p) for p in entries))
    return written


def main(argv: list[str] | None = None, root: Path | None = None) -> int:
    ap = argparse.ArgumentParser(description="Cut a new tcw version.")
    ap.add_argument("bump", help="patch | minor | major | explicit X.Y.Z")
    args = ap.parse_args(argv)

    root = root or repo_root()
    old = current_version(root)
    new = next_version(old, args.bump)
    if new == old:
        sys.exit(f"cut_version: {new} is already the current version")

    missing = [rel for rel in UPCOMING if not (root / rel).is_dir()]
    if missing:
        # Checked before anything is touched: a cut without its entries would
        # ship empty notes under a real version number.
        sys.exit(f"cut_version: no entry folder at {', '.join(missing)}")

    bump_files(root, old, new)
    combined = combine_upcoming(root, new)
    _git(root, "add", "--", *VERSION_FILES.keys(), *combined)
    _git(root, "commit", "-qm", f"chore(release): cut v{new}")  # picks up the staged removals too
    _git(root, "tag", f"v{new}")
    print(f"cut v{new} (was v{old}). Push with: git push origin main --tags")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
