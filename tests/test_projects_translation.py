"""The reader's temporary translation of the 3.x `projects:` key into
`parents:` and `children:` (TCW-108 plan, Step 4), on parsed mappings.

Transitional: it exists only while this repository's own fixtures move off
`projects:`, and goes, with these tests, before the item completes."""

from __future__ import annotations

from tcw.store.links import translate_projects

FILE = ".tcw/tcw-config.yaml"


def translated(raw):
    out, problems = translate_projects(raw, FILE)
    assert problems == [], problems
    return out


def test_a_parent_becomes_a_parent_passing_everything():
    out = translated({"id": "a", "projects": {"parent": {"ws": None}}})
    assert out == {"id": "a", "parents": ["ws"], "children": []}


def test_children_become_children_in_order():
    out = translated({"id": "ws", "projects": {"children": {"a": None, "b": None}}})
    assert out["children"] == ["a", "b"] and out["parents"] == []


def test_an_upstream_passes_what_extends_takes_from_it():
    assert translated({"id": "app", "projects": {"upstream": {"core": None}}})[
        "parents"] == [{"id": "core", "inherit": "none"}]
    assert translated({"id": "app", "projects": {"upstream": {"core": None}},
                       "taxonomy": {"extends": ["core"]}})["parents"] == [
        {"id": "core", "inherit": ["taxonomy"]}]
    assert translated({"id": "app", "projects": {"upstream": {"core": None}},
                       "taxonomy": {"extends": ["core"]},
                       "capabilities": {"extends": ["core"]}})["parents"] == [
        {"id": "core", "inherit": ["taxonomy", "capabilities"]}]


def test_an_extends_naming_a_project_not_named_here_becomes_a_parent_after_the_others():
    out = translated({"id": "x", "projects": {"parent": {"p": None}},
                      "taxonomy": {"extends": ["y"]}})
    assert out["parents"] == ["p", {"id": "y", "inherit": ["taxonomy"]}]


def test_an_extends_of_a_parent_or_a_child_adds_nothing():
    out = translated({"id": "x", "projects": {"parent": {"p": None},
                                              "children": {"k": None}},
                      "taxonomy": {"extends": ["p", "k"]}})
    assert out["parents"] == ["p"] and out["children"] == ["k"]


def test_the_refusals_of_tcw_107_s_reader_are_kept():
    for raw, words in [
        ({"projects": {"parent": {"ws": "../ws"}}}, "a location goes in .tcw/tcw-manifest.yaml"),
        ({"projects": {"parent": {"a": None, "b": None}}},
         "projects.parent must contain at most one entry"),
        ({"projects": ["a"]}, "projects must be a mapping"),
        ({"projects": {"sideways": {"a": None}}}, "unknown projects keys: sideways"),
        ({"projects": {"children": ["a"]}}, "projects.children must be a mapping"),
        ({"projects": {"children": {"A": None}}}, "children key: project ID must match"),
    ]:
        out, problems = translate_projects({"id": "me", **raw}, FILE)
        assert any(words in problem for problem in problems), (raw, problems)
        assert "parents" not in out and "projects" not in out


def test_projects_beside_parents_or_children_is_a_problem():
    for key in ("parents", "children"):
        _, problems = translate_projects({"id": "a", key: [], "projects": {}}, FILE)
        assert any("'projects'" in p and f"'{key}'" in p for p in problems), problems


def test_a_file_with_no_projects_key_is_unchanged():
    raw = {"id": "a", "parents": ["ws"], "children": ["k"]}
    assert translate_projects(raw, FILE) == (raw, [])
    assert translate_projects(translated({"id": "a", "projects": {"parent": {"ws": None}}}),
                              FILE)[1] == []
