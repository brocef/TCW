"""The exit-code table in `docs/guide/cli.md` matches `tcw/exit.py` (TCW-75
spec, acceptance criterion 8): one row per exit code constant, with the same
numbers, and no other rows."""

import ast
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GUIDE = REPO / "docs/guide/cli.md"
EXIT = REPO / "tcw/exit.py"
HEADING = "## Exit codes"


def exit_codes() -> dict[str, int]:
    """Every module-level integer constant in `tcw/exit.py`, by name."""
    tree = ast.parse(EXIT.read_text(encoding="utf-8"))
    return {target.id: node.value.value
            for node in tree.body if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, int)}


def table_codes(text: str) -> list[str]:
    """The first cell of every body row of the first table under the
    exit-code heading, as written."""
    _, found, rest = text.partition("\n" + HEADING + "\n")
    assert found, f"{GUIDE.name} has no line {HEADING!r}"
    section = re.split(r"^## ", rest, maxsplit=1, flags=re.M)[0]
    rows = [line for line in section.splitlines() if line.startswith("|")]
    assert len(rows) >= 2, f"no table under {HEADING!r}"
    assert set(rows[1].replace("|", "").strip()) <= set("-: "), \
        "the table's second line is not its separator"
    return [row.strip("|").split("|")[0].strip() for row in rows[2:]]


def test_the_exit_table_has_one_row_per_code():
    codes = exit_codes()
    assert codes, "tcw/exit.py defines no exit codes"
    written = table_codes(GUIDE.read_text(encoding="utf-8"))
    assert all(re.fullmatch(r"\d+", cell) for cell in written), written
    assert len(written) == len(codes), (written, codes)
    assert {int(cell) for cell in written} == set(codes.values())


def test_the_table_reader_sees_an_extra_row():
    text = (f"x\n\n{HEADING}\n\n| Code | Meaning |\n| --- | --- |\n| 0 | ok |\n"
            f"| 9 | extra |\n\n## Next\n\n| 7 | not this table |\n")
    assert table_codes(text) == ["0", "9"]
