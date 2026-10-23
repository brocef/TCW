"""Exit code 7 is documented wherever the codes are listed (TCW-108 Design
8.3, AC 25), and the rows for 3 and 5 no longer speak of upstream projects
or a `jira` block (Design 7.1, 7.2)."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TABLES = ["docs/guide/cli.md",
          "docs/capabilities/cli/rely-on-one-output-contract/description.md",
          "skills/work/references/commands.md"]


def rows(path: str) -> dict[str, str]:
    """The exit-code table's rows by code, the table found by its header row
    (a first column headed `Code`), not by line number."""
    lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines)
                 if line.startswith("|") and line.strip("| ").lower().startswith("code"))
    found: dict[str, str] = {}
    for line in lines[start + 2:]:
        if not line.startswith("|"):
            break
        code = line.strip("|").split("|")[0].strip()
        found[code] = line
    return found


@pytest.mark.parametrize("path", TABLES)
def test_each_table_has_a_row_for_seven(path):
    table = rows(path)
    assert set(table) >= {str(code) for code in range(8)}, table.keys()
    assert "inherit" in table["7"]


@pytest.mark.parametrize("path", TABLES)
def test_rows_three_and_five_name_no_upstream_or_jira_block(path):
    table = rows(path)
    for code in ("3", "5"):
        assert "upstream" not in table[code]
        assert "jira` block" not in table[code] and "jira block" not in table[code]
