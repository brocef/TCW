"""TCW-113 plan Step 2: the family every scope test starts from is one the
earlier items accept, so a later test fails for what it checks and never
for a fixture TCW would refuse."""

from __future__ import annotations

import pytest

from tests.families import PRESENT, build_family


@pytest.fixture
def family(tmp_path):
    return build_family(tmp_path, docs_passes="none")


@pytest.mark.parametrize("project_id", PRESENT)
def test_each_project_validates(family, project_id):
    ran = family.run(project_id, "validate")
    errors = [line for line in ran.out.splitlines() if line.startswith("error:")]
    assert errors == [], ran.out + ran.err


def test_shared_names_its_parent_and_children(family):
    ran = family.run("shared", "projects", "list", "--json")
    assert ran.code == 0, ran.err
    rows = {p["id"]: p for p in ran.json["projects"]}
    assert [p["id"] for p in ran.json["projects"]] == [
        "shared", "docs", "desktop", "server", "mobile"]
    assert rows["docs"]["relation"] == "parent"
    assert {rows[c]["relation"] for c in ("desktop", "server", "mobile")} == {"child"}
    assert rows["mobile"]["present"] is False
    assert rows["desktop"]["present"] is True and rows["server"]["present"] is True
