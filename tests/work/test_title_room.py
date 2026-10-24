"""The room left for a new item's title words under the 255-character limit
(TCW-111 Design 4.2, 4.3; AC 14's numbers). Every length named is of a full
identifier: the room is 255 - parent - 1 - prefix."""

from __future__ import annotations

import pytest

from tcw.errors import UsageError
from tcw.ids import ID_LIMIT
from tcw.work.model import MIN_TITLE_WORDS, PREFIX_ALLOWANCE, fitted_words, words_room

DATE_PREFIX = 11                                 # `2026-10-22-`


def parent_of(length: int, project: str = "demo") -> str:
    """A parent id-path whose full identifier is `length` characters."""
    path = "a" * (length - len(project) - len(".work/"))
    # Kept to legal id-parts of at most 128 characters each.
    parts = [path[i:i + 100] for i in range(0, len(path), 100)]
    joined = "/".join(parts)
    while len(project) + 6 + len(joined) > length:
        joined = joined[:-1]
    while len(project) + 6 + len(joined) < length:
        joined += "a"
    return joined


def test_the_parent_builder_makes_the_length_asked():
    for n in (200, 226, 227, 235, 240):
        assert len(f"demo.work/{parent_of(n)}") == n


def test_a_parent_of_235_leaves_exactly_eight():
    parent = parent_of(235)
    assert words_room("demo", parent, DATE_PREFIX) == MIN_TITLE_WORDS == 8
    words = fitted_words("A much longer title than fits", project="demo",
                         parent=parent, prefix=DATE_PREFIX)
    assert len(words) <= 8
    assert len(f"demo.work/{parent}/2026-10-22-{words}") <= ID_LIMIT


def test_a_parent_of_227_at_the_allowance_leaves_seven_and_refuses_naming_it():
    parent = parent_of(227)
    assert words_room("demo", parent, PREFIX_ALLOWANCE) == 7
    with pytest.raises(UsageError) as refused:
        fitted_words("x", project="demo", parent=parent, prefix=PREFIX_ALLOWANCE)
    assert f"demo.work/{parent}" in str(refused.value)
    assert "--nest" in str(refused.value)


def test_a_project_id_of_231_leaves_no_room_for_any_item():
    project = "p" * 231
    assert words_room(project, None, DATE_PREFIX) == 7
    with pytest.raises(UsageError) as refused:
        fitted_words("x", project=project, parent=None, prefix=DATE_PREFIX)
    assert project in str(refused.value) and "no room for any item" in str(refused.value)


def test_with_room_enough_the_words_are_todays():
    assert fitted_words("Add login", project="demo", parent=None,
                        prefix=DATE_PREFIX) == "add-login"


def test_after_a_ticket_exists_the_words_are_cut_however_short():
    parent = parent_of(226)
    # 255 - 226 - 1 - (24 + 1) = 3
    words = fitted_words("Long title words", project="demo", parent=parent,
                         prefix=25, refuse=False)
    assert words == "lon"
    assert fitted_words("!!!", project="demo", parent=parent, prefix=25,
                        refuse=False) == "unt"
    assert fitted_words("x", project="demo", parent=parent, prefix=29,
                        refuse=False) is None
