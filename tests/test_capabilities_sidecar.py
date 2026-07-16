"""declared_capabilities — canonical read of a work item's capabilities.yaml."""

import pytest

from tcw.store.base import SidecarError, declared_capabilities


def test_canonical_new_and_changed():
    obj = {"new": ["a/one", "b/two"], "changed": ["c/three"]}
    assert declared_capabilities(obj) == {"new": ["a/one", "b/two"],
                                          "changed": ["c/three"]}


def test_added_is_alias_for_new():
    obj = {"added": ["a/one"], "changed": ["b/two"]}
    assert declared_capabilities(obj) == {"new": ["a/one"], "changed": ["b/two"]}


def test_new_and_added_merge():
    obj = {"new": ["a/one"], "added": ["b/two"]}
    assert declared_capabilities(obj)["new"] == ["a/one", "b/two"]


def test_trailing_comment_stripped():
    # YAML already strips ` # comment`; this guards the belt-and-suspenders path.
    obj = {"new": ["a/one # was added at planning"]}
    assert declared_capabilities(obj)["new"] == ["a/one"]


def test_internal_hash_kept():
    # A legacy namespace#slug token keeps its '#' so it fails resolution downstream
    # rather than being silently "repaired".
    obj = {"changed": ["work#view-the-board"]}
    assert declared_capabilities(obj)["changed"] == ["work#view-the-board"]


def test_none_and_empty():
    assert declared_capabilities(None) == {"new": [], "changed": []}
    assert declared_capabilities({}) == {"new": [], "changed": []}


def test_list_form_declares_nothing():
    # reconcile's {file, heading, from, to} list shape is not a gate declaration.
    obj = [{"file": "x", "heading": "y", "from": "Missing", "to": "Supported"}]
    assert declared_capabilities(obj) == {"new": [], "changed": []}


def test_parse_error_sentinel_raises():
    with pytest.raises(SidecarError, match="broken"):
        declared_capabilities({"_tcw_parse_error": "broken: yaml: here"})


def test_non_list_value_raises():
    with pytest.raises(SidecarError, match="must be a list"):
        declared_capabilities({"new": "a/one"})
