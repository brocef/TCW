"""TCW 4.0 names every object one way (TCW-110 AC 21): nothing in TCW's own
code spells a 3.x reference or builds an identifier by hand.

`findings(root)` is the whole check, so a later item can run it over another
tree. Over the `.py`, `.ts`, `.tsx` and `.mjs` files under `tcw/`,
`web/client/src/`, `scripts/` and `evals/`, test files excepted, it reports:

- `parse_tcw_uri`, `.qualified`, `tcw://W/`, `tcw://T/` or `tcw://C/`, the
  3.x link grammar and the 3.x name, outside `tcw/ids.py`, which holds the
  one recogniser of a 3.x reference (Design 2.4);
- anywhere, a project ID joined to a name with `/` by hand
  (`{...project...}/{`), which is how a 3.x slug was built (spec 5.4).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FOLDERS = ("tcw", "web/client/src", "scripts", "evals")
SUFFIXES = {".py", ".ts", ".tsx", ".mjs"}
#: Folders never read, matched by whole path parts: the built web client.
SKIPPED_FOLDERS = (("tcw", "serve", "dist"),)
#: Folders that must spell 3.x forms to rewrite them; `tcw migrate` (TCW-116)
#: adds its own here.
MIGRATION_FOLDERS: tuple[tuple[str, ...], ...] = ()
#: The one file that recognises a 3.x reference.
RECOGNISER = ("tcw", "ids.py")

THREE_X = re.compile(r"parse_tcw_uri|\.qualified\b|tcw://[WTC]/")
BY_HAND = re.compile(r"\{[^}]*project[^}]*\}/\$?\{")


def _is_test_file(path: Path) -> bool:
    name = path.name
    return (name.startswith("test_") or ".test." in name
            or name in ("test-setup.ts", "test-fixtures.ts"))


def _under(parts: tuple[str, ...], folder: tuple[str, ...]) -> bool:
    return parts[:len(folder)] == folder


def findings(root: Path) -> list[str]:
    """Each line breaking the rules above, as `<path>:<line>: <text>`, the
    path relative to `root`."""
    found = []
    for folder in FOLDERS:
        for path in sorted((root / folder).rglob("*")):
            if path.suffix not in SUFFIXES or not path.is_file() or _is_test_file(path):
                continue
            parts = path.relative_to(root).parts
            if any(_under(parts, skipped)
                   for skipped in (*SKIPPED_FOLDERS, *MIGRATION_FOLDERS)):
                continue
            text = path.read_text(encoding="utf-8")
            for number, line in enumerate(text.splitlines(), 1):
                if (THREE_X.search(line) and parts != RECOGNISER) or BY_HAND.search(line):
                    found.append(f"{'/'.join(parts)}:{number}: {line.strip()}")
    return found


def test_no_3x_reference_or_hand_built_identifier_is_left():
    assert findings(ROOT) == []


def _copy(tmp_path: Path, relative: str, text: str) -> Path:
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_the_guard_reports_a_3x_name_and_a_hand_built_identifier(tmp_path):
    _copy(tmp_path, "tcw/work/one.py", "slug = item.qualified\n")
    _copy(tmp_path, "web/client/src/two.ts", "const s = `${project}/${folder}`\n")
    _copy(tmp_path, "scripts/three.py", 'name = f"{self.project}/{folder}"\n')
    _copy(tmp_path, "evals/four.py", 'link = "tcw://W/2026-01-01-x"\n')
    assert [line.split(":")[0] for line in findings(tmp_path)] == [
        "tcw/work/one.py", "web/client/src/two.ts", "scripts/three.py", "evals/four.py"]


def test_the_guard_leaves_the_recogniser_tests_and_the_built_client_alone(tmp_path):
    _copy(tmp_path, "tcw/ids.py", 'THREE_X = "tcw://T/"\n')
    _copy(tmp_path, "tcw/test_x.py", "x.qualified\n")
    _copy(tmp_path, "web/client/src/a.test.ts", "tcw://C/x\n")
    _copy(tmp_path, "tcw/serve/dist/client/x.mjs", "tcw://W/x\n")
    _copy(tmp_path, "tcw/serve/distant.py", "x.qualified\n")
    assert findings(tmp_path) == ["tcw/serve/distant.py:1: x.qualified"]


def test_the_recogniser_may_not_build_an_identifier_by_hand(tmp_path):
    _copy(tmp_path, "tcw/ids.py", 'return f"{full.project}/{rest}"\n')
    assert len(findings(tmp_path)) == 1
