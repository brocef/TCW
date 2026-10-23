"""Work item identifiers and folder names (TCW-69 AC 1, 2; TCW-110 Design
1 and 3.1)."""

import pytest

from tcw.errors import NotFound, UsageError
from tcw.ids import ThreeXReference
from tcw.work.model import FOLDER_LIMIT, Slug, title_words


def test_a_full_identifier_is_project_and_folder():
    assert Slug.typed("tcw.work/add-x", "other") == Slug("tcw", "add-x")
    assert Slug.typed("tcw://tcw.work/add-x", "other") == Slug("tcw", "add-x")


def test_a_bare_folder_belongs_to_the_current_project():
    assert Slug.typed("add-x", "tcw") == Slug("tcw", "add-x")


@pytest.mark.parametrize("text", [
    "",
    "tcw/",
    "/f",
    "tcw.work/",
    "tcw.work/has space",
    "has space",
    "Upper.work/f",
    "tcw.work/-leading-dash",
    "tcw.work/f\n",
    "tcw\n.work/f",
    "f\n",
    "tcw.work/" + "x" * (FOLDER_LIMIT + 1),
    "tcw.taxonomy/f",
])
def test_anything_else_is_a_usage_error(text):
    with pytest.raises(UsageError):
        Slug.typed(text, "tcw")


@pytest.mark.parametrize("text", ["a/b/c", "tcw/f"])
def test_an_id_path_of_several_parts_names_no_work_item(text):
    """A work item's id-path is one folder name until TCW-111, and a 3.x
    `<project>/<folder>` reads as such an id-path (TCW-110 Design 3.4)."""
    with pytest.raises(NotFound) as caught:
        Slug.typed(text, "tcw")
    assert f"no work item {text} in project 'tcw'" in str(caught.value)


def test_a_folder_at_the_limit_is_accepted():
    assert Slug.typed("x" * FOLDER_LIMIT, "tcw").folder == "x" * FOLDER_LIMIT


def test_a_2x_status_name_is_only_an_unknown_project_now():
    # The 2.x reserved project names kept project ids apart from status
    # folders; 3.0 has none, so `backlog` is an ordinary project id.
    assert Slug.typed("backlog.work/f", "tcw") == Slug("backlog", "f")


def test_a_jira_key_in_the_folder_keeps_its_case():
    assert str(Slug.typed("tcw.work/TCW-67-x", "tcw")) == "tcw.work/TCW-67-x"


def test_a_stored_reference_is_a_full_identifier_and_3x_is_reported():
    assert Slug.stored("tcw.work/add-x") == Slug("tcw", "add-x")
    for value in ("tcw/add-x", "add-x"):
        with pytest.raises(ThreeXReference) as caught:
            Slug.stored(value)
        assert "tcw migrate" in str(caught.value)


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
