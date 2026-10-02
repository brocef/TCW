"""Item properties: validation and derived blocks (TCW-69 AC 3, 4)."""

from datetime import date

import pytest

from tcw.errors import UsageError
from tcw.work.model import (
    Changes, Item, Slug, UNSET, apply_changes, blocks_of, validate_changes,
)

A = Slug("tcw", "a")
B = Slug("tcw", "b")


def _item(slug, **fields):
    defaults = dict(title="t", stage="spec", created=date(2026, 10, 1),
                    priority="medium", effort=None, complexity=None, tags=(),
                    assignee=None, parent=None, blocked_by=())
    defaults.update(fields)
    return Item(slug=slug, **defaults)


def _validate(changes, *, item_slug=A, parents=None):
    parents = parents or {}
    validate_changes(changes, item_slug=item_slug,
                     registered_tags={"bug", "docs"}, current_project="tcw",
                     parent_of=parents.get)


@pytest.mark.parametrize("changes", [
    Changes(priority="urgent"),
    Changes(priority=3),
    Changes(effort="huge"),
    Changes(complexity="tiny"),
    Changes(add_tags=("unregistered",)),
    Changes(add_blocked_by=("waiting on legal",)),
    Changes(parent="not a slug"),
    Changes(parent=A),
    Changes(add_blocked_by=(A,)),
    Changes(add_blocked_by=("a",)),
    Changes(title=""),
])
def test_invalid_changes_are_usage_errors(changes):
    with pytest.raises(UsageError):
        _validate(changes)


def test_valid_changes_pass():
    _validate(Changes(title="new", priority="highest", effort="very-high",
                      complexity="low", add_tags=("Bug",), parent="b",
                      add_blocked_by=("other/x", B)))


def test_none_clears_a_property():
    _validate(Changes(priority=None, effort=None, parent=None, assignee=None))


def test_a_parent_that_closes_a_cycle_is_refused():
    with pytest.raises(UsageError, match="cycle"):
        _validate(Changes(parent=B), parents={B: A})


def test_a_deep_cycle_is_refused():
    c = Slug("tcw", "c")
    with pytest.raises(UsageError, match="cycle"):
        _validate(Changes(parent=B), parents={B: c, c: A})


def test_parents_in_other_projects_are_not_followed():
    elsewhere = Slug("other", "x")
    asked = []

    def parent_of(slug):
        asked.append(slug)
        return {B: elsewhere}.get(slug)

    validate_changes(Changes(parent=B), item_slug=A, registered_tags=set(),
                     current_project="tcw", parent_of=parent_of)
    assert elsewhere not in asked


def test_a_cycle_already_in_the_data_does_not_hang_the_check():
    c = Slug("tcw", "c")
    _validate(Changes(parent=B), parents={B: c, c: B})


def test_a_new_item_has_no_slug_to_cycle_through():
    validate_changes(Changes(parent=B), item_slug=None, registered_tags=set(),
                     current_project="tcw", parent_of=lambda s: None)


def test_apply_changes_sets_clears_and_edits():
    item = _item(A, tags=("bug",), blocked_by=(B,), effort="low")
    changed = apply_changes(item, Changes(
        title="renamed", effort=None, assignee="sam", parent="b",
        add_tags=("Docs", "bug"), remove_tags=("bug",),
        add_blocked_by=("other/x",), remove_blocked_by=("b",)))
    assert changed.title == "renamed"
    assert changed.effort is None
    assert changed.assignee == "sam"
    assert changed.parent == B
    assert changed.tags == ("docs",)
    assert changed.blocked_by == (Slug("other", "x"),)
    assert changed.priority == "medium"  # untouched
    assert item.title == "t"  # the original is frozen and unchanged


def test_unset_leaves_a_property_alone():
    assert Changes().title is UNSET
    item = _item(A, assignee="sam")
    assert apply_changes(item, Changes()) == item


def test_blocks_are_derived_not_stored():
    a = _item(A)
    b = _item(B)
    b = apply_changes(b, Changes(add_blocked_by=(A,)))
    assert blocks_of(A, [a, b]) == [B]
    assert a == _item(A)
    assert blocks_of(B, [a, b]) == []
