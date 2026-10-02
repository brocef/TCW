"""Slugs and folder names (TCW-69 AC 1, 2)."""

import pytest

from tcw.errors import UsageError
from tcw.work.model import FOLDER_LIMIT, Slug, title_words


def test_a_slug_is_project_and_folder():
    assert Slug.parse("tcw/add-x", "other") == Slug("tcw", "add-x")


def test_a_bare_folder_belongs_to_the_current_project():
    assert Slug.parse("add-x", "tcw") == Slug("tcw", "add-x")


@pytest.mark.parametrize("text", [
    "a/b/c",
    "",
    "tcw/",
    "/f",
    "tcw/has_underscore",
    "tcw/has space",
    "has space",
    "Upper/f",
    "tcw/-leading-dash",
    "tcw/f\n",
    "tcw\n/f",
    "f\n",
    "tcw/" + "x" * (FOLDER_LIMIT + 1),
])
def test_anything_else_is_a_usage_error(text):
    with pytest.raises(UsageError):
        Slug.parse(text, "tcw")


def test_a_folder_at_the_limit_is_accepted():
    assert Slug.parse("x" * FOLDER_LIMIT, "tcw").folder == "x" * FOLDER_LIMIT


def test_a_2x_status_name_is_only_an_unknown_project_now():
    # The 2.x reserved project names kept project ids apart from status
    # folders; 3.0 has none, so `backlog` is an ordinary project id.
    assert Slug.parse("backlog/f", "tcw") == Slug("backlog", "f")


def test_a_jira_key_in_the_folder_keeps_its_case():
    assert str(Slug.parse("tcw/TCW-67-x", "tcw")) == "tcw/TCW-67-x"


def test_title_words():
    assert title_words("Make tcw validate usable: a gate!") == \
        "make-tcw-validate-usable-a-gate"


def test_a_title_with_nothing_usable_is_untitled():
    assert title_words("!!!") == "untitled"
    assert title_words("") == "untitled"


def test_a_long_title_is_cut_at_a_word_boundary():
    words = title_words(" ".join(["word"] * 60))
    assert len(words) <= FOLDER_LIMIT - 20
    assert not words.endswith("-")
    assert set(words.split("-")) == {"word"}


def test_a_single_overlong_word_is_cut_hard():
    words = title_words("x" * 500, limit=30)
    assert words == "x" * 30
