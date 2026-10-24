"""One definition of the fields that hold references (TCW-114 Design 6.1,
AC 26; plan Steps 9 and 10)."""

from __future__ import annotations

import pytest

from tcw.reference_fields import FIELDS, field, fields_of, names, values

ROWS = {
    ("work-item", "parent"), ("work-item", "blocked-by"),
    ("jira-item", "parent"), ("jira-item", "blocked-by"),
    ("jira-ticket", "TCW Item"),
    ("capabilities-yaml", "new"), ("capabilities-yaml", "changed"),
    ("capabilities-yaml", "removed"), ("capabilities-yaml", "taxonomy.new"),
    ("capabilities-yaml", "taxonomy.changed"), ("capabilities-yaml", "taxonomy.removed"),
    ("term", "relatesTo"), ("term", "vocabulary"), ("term", "parent"),
    ("capability", "Subject"), ("capability", "Feature"),
    ("capability", "Superseded by"), ("capability", "Blocked by"),
    ("capability", "Roles"), ("capability", "When"), ("capability", "parent"),
    ("markdown", "link"),
}


def test_the_table_holds_exactly_the_reference_fields():
    assert {(f.record, f.name) for f in FIELDS} == ROWS
    assert len(FIELDS) == len(ROWS)


@pytest.mark.parametrize("record,name,many,namespace", [
    ("capability", "Subject", True, "taxonomy"),
    ("capability", "Feature", False, "taxonomy"),
    ("capability", "Superseded by", False, "capabilities"),
    ("capability", "Blocked by", False, "capabilities"),
    ("capability", "Roles", True, "capabilities"),
    ("capability", "When", True, "capabilities"),
    ("capability", "parent", False, "capabilities"),
    ("term", "relatesTo", True, "taxonomy"),
    ("term", "vocabulary", True, "taxonomy"),
    ("term", "parent", False, "taxonomy"),
    ("work-item", "parent", False, "work"),
    ("work-item", "blocked-by", True, "work"),
    ("jira-item", "blocked-by", True, "work"),
    ("capabilities-yaml", "changed", True, "capabilities"),
    ("capabilities-yaml", "taxonomy.removed", True, "taxonomy"),
    ("markdown", "link", True, None),
])
def test_each_rows_shape(record, name, many, namespace):
    row = field(record, name)
    assert (row.many, row.namespace) == (many, namespace)


def test_groups_and_negation_belong_to_roles_and_when_only():
    assert {(f.name, f.group) for f in FIELDS if f.group} == {
        ("Roles", "roles"), ("When", "conditions")}
    assert {f.name for f in FIELDS if f.negatable} == {"Roles", "When"}


def test_fields_of_filters_by_namespace_and_parent():
    assert names("capability", namespace="taxonomy") == ("Subject", "Feature")
    assert names("capability", namespace="capabilities", parent=False) == (
        "Superseded by", "Blocked by", "Roles", "When")
    assert [f.name for f in fields_of("term")] == ["relatesTo", "vocabulary", "parent"]


def test_values_finds_every_reference_in_a_record():
    found = values("capability", {
        "Status": "Supported", "Subject": ["a.taxonomy/s", "a.taxonomy/t"],
        "Roles": "a.capabilities/roles/x, !a.capabilities/roles/y",
        "Blocked by": "a.capabilities/b", "parent": "a.capabilities/p"})
    assert [(f.name, v, n) for f, v, n in found] == [
        ("Subject", "a.taxonomy/s", False), ("Subject", "a.taxonomy/t", False),
        ("Blocked by", "a.capabilities/b", False),
        ("Roles", "a.capabilities/roles/x", False),
        ("Roles", "a.capabilities/roles/y", True),
        ("parent", "a.capabilities/p", False)]


def test_values_reads_a_dotted_name_inside_a_mapping():
    found = values("capabilities-yaml", {"new": ["a/b"],
                                         "taxonomy": {"changed": ["t"]}})
    assert [(f.name, v) for f, v, _ in found] == [("new", "a/b"),
                                                  ("taxonomy.changed", "t")]


# -- AC 26, the second half: every row's values are checked ----------------------------

from tests.objectcli import findings, item, obj, project, tcw  # noqa: E402,F401

import yaml  # noqa: E402

TERM_ROWS = {"relatesTo": ["demo.taxonomy/gone"], "vocabulary": ["demo.taxonomy/gone"],
             "parent": "demo.taxonomy/gone"}
CAP_ROWS = {"Subject": ["demo.taxonomy/gone"], "Feature": "demo.taxonomy/gone",
            "Superseded by": "demo.capabilities/gone",
            "Blocked by": "demo.capabilities/gone",
            "Roles": "demo.capabilities/roles/gone",
            "When": "demo.capabilities/conditions/gone", "parent": "demo.capabilities/gone"}


@pytest.fixture
def demo(tmp_path):
    root = project(tmp_path, "demo", work={})
    obj(root, "taxonomy", "v", name="V", kind="Vocabulary")
    return root


def _reported(tcw, root, where: str, *words: str) -> list[str]:
    result = tcw(["validate"], root)
    return [line for line in findings(result)
            if where in line and all(w in line for w in words)]


@pytest.mark.parametrize("name", sorted(TERM_ROWS))
def test_a_dangling_term_field_is_reported(tcw, demo, name):
    obj(demo, "taxonomy", "t", name="T", kind="Feature" if name == "vocabulary"
        else "Vocabulary", **{name: TERM_ROWS[name]},
        **({"vocabulary": ["demo.taxonomy/v"]} if name != "vocabulary" else {}))
    assert _reported(tcw, demo, "docs/taxonomy/t", name, "demo.taxonomy/gone")


@pytest.mark.parametrize("name", sorted(CAP_ROWS))
def test_a_dangling_capability_field_is_reported(tcw, demo, name):
    obj(demo, "capabilities", "x", name="X", Status="Missing", **{name: CAP_ROWS[name]})
    assert _reported(tcw, demo, "docs/capabilities/x", name, "gone")


@pytest.mark.parametrize("name", ["parent", "blocked-by"])
def test_a_dangling_work_item_field_is_reported(tcw, demo, name):
    value = "demo.work/2026-10-01-gone"
    item(demo, "2026-10-01-a", **{name: [value] if name == "blocked-by" else value})
    assert _reported(tcw, demo, "2026-10-01-a", name, value)


@pytest.mark.parametrize("name", ["new", "changed", "removed", "taxonomy.new",
                                  "taxonomy.changed", "taxonomy.removed"])
def test_a_capabilities_yaml_field_is_checked(tcw, demo, name):
    """Mid-work, a declared change not made yet is not reported until the
    gate (`records_problems`), so a value no reader accepts shows that the
    field is read: a 3.x name."""
    namespace = "taxonomy" if name.startswith("taxonomy.") else "capabilities"
    kind = name.split(".")[-1]
    declared = {kind: ["gone"]} if namespace == "capabilities" else \
        {"taxonomy": {kind: ["gone"]}}
    folder = item(demo, "2026-10-01-a")
    (folder / "capabilities.yaml").write_text(yaml.safe_dump(declared))
    said = "term gone:" if namespace == "taxonomy" else "capabilities.yaml: gone:"
    assert _reported(tcw, demo, "capabilities.yaml", said)


def test_a_dangling_link_is_reported(tcw, demo):
    folder = obj(demo, "capabilities", "x", name="X", Status="Missing")
    (folder / "description.md").write_text("See [it](tcw://demo.taxonomy/gone).\n")
    assert _reported(tcw, demo, "docs/capabilities/x", "tcw://demo.taxonomy/gone")


@pytest.mark.xfail(strict=True, reason="recorded references arrive in Steps 13-15")
@pytest.mark.parametrize("name", ["parent", "blocked-by"])
def test_a_dangling_jira_item_field_is_reported(name):
    raise NotImplementedError("written with Step 15")


def test_a_row_added_to_the_table_is_checked_with_no_other_change(tcw, demo,
                                                                  monkeypatch):
    import tcw.reference_fields as table
    from tcw.reference_fields import Field
    monkeypatch.setattr(table, "FIELDS", (*table.FIELDS, Field(
        "capability", "Reviewed by", False, "capabilities")))
    obj(demo, "capabilities", "x", name="X", Status="Missing",
        **{"Reviewed by": "demo.capabilities/gone"})
    assert _reported(tcw, demo, "docs/capabilities/x", "Reviewed by",
                     "demo.capabilities/gone")
