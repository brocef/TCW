"""Reading `parents:` and `children:` (TCW-108 Design 1.1-1.3 and 2.1), on
the parsed values alone: no file is read."""

from __future__ import annotations

import pytest

from tcw.store.base import AXES, ParentLink
from tcw.store.links import parse_children, parse_parents

FILE = ".tcw/tcw-config.yaml"
ALL = frozenset(AXES)


def links(value):
    found, problems = parse_parents(value, FILE)
    assert problems == [], problems
    return found


def refused(value):
    found, problems = parse_parents(value, FILE)
    assert found is None
    assert problems, "expected a problem"
    return problems


def test_no_parents_key_is_no_parents():
    assert parse_parents(None, FILE) == (None, [])


@pytest.mark.parametrize("value", [["core"], [{"id": "core"}],
                                   [{"id": "core", "inherit": "all"}],
                                   [{"id": "core", "inherit": ["taxonomy", "capabilities",
                                                               "config"]}]])
def test_every_spelling_of_all(value):
    assert links(value) == [ParentLink("core", ALL)]


def test_inherit_none_passes_nothing():
    assert links([{"id": "core", "inherit": "none"}]) == [ParentLink("core", frozenset())]


def test_inherit_list_in_any_order():
    assert links([{"id": "core", "inherit": ["config", "taxonomy"]}]) == [
        ParentLink("core", frozenset({"taxonomy", "config"}))]


def test_parents_keep_their_order():
    assert [link.id for link in links(["ws", {"id": "core"}, "app"])] == ["ws", "core", "app"]


@pytest.mark.parametrize("value, key, words", [
    ("core", "parents", "must be a list"),
    ([5], "parents[0]", "a project ID or a mapping"),
    ([{"inherit": "none"}], "parents[0].id", "required"),
    ([{"id": "Core"}], "parents[0].id", "project ID must match"),
    ([{"id": "core", "path": "../core"}], "parents[0]", "unknown key 'path'"),
    ([{"id": "core", "inherit": "some"}], "parents[0].inherit", "'all', 'none'"),
    ([{"id": "core", "inherit": ["taxonomy", "taxonomy"]}], "parents[0].inherit",
     "more than once"),
    ([{"id": "core", "inherit": ["work"]}], "parents[0].inherit", "'work'"),
    ([{"id": "core", "inherit": []}], "parents[0].inherit", "inherit: none"),
    (["core", "core"], "parents[1]", "listed twice"),
    (["ws", {"id": "core", "inherit": 3}], "parents[1].inherit", "'all', 'none'"),
])
def test_each_problem_names_its_key(value, key, words):
    problems = refused(value)
    assert any(path == key and words in message for path, message in problems), problems


def test_a_problem_in_one_entry_refuses_the_whole_list():
    # The links are unknown when any entry is wrong (Design 6.6): a
    # half-read list would put the project in a different load order.
    found, problems = parse_parents(["ws", 5], FILE)
    assert found is None and len(problems) == 1


def test_children_in_order():
    assert parse_children(["a", "b"], FILE, own_id="ws") == (["a", "b"], [])


def test_no_children_key_is_no_children():
    assert parse_children(None, FILE, own_id="ws") == ([], [])


@pytest.mark.parametrize("value, key, words", [
    ("a", "children", "must be a list"),
    ([{"id": "a"}], "children[0]", "a project ID"),
    (["A"], "children[0]", "project ID must match"),
    (["a", "a"], "children[1]", "listed twice"),
    (["ws"], "children[0]", "lists itself"),
])
def test_each_children_problem_names_its_key(value, key, words):
    _, problems = parse_children(value, FILE, own_id="ws")
    assert any(path == key and words in message for path, message in problems), problems


def test_a_bad_child_entry_is_left_out_and_the_rest_kept():
    found, problems = parse_children(["a", "B", "dd", "a"], FILE, own_id="ws")
    assert found == ["a", "dd"]
    assert len(problems) == 2
