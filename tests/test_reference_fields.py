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
