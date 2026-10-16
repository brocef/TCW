"""The shared vocabulary scan reads a block at a time (pre-freeze clean-up,
T6; Design 16), so a phrase wrapped across a line break is found, and each
hit still names the line where it starts."""

import pytest

from tests.doc_vocabulary import blocks, scan


def test_a_phrase_wrapped_across_a_line_is_found_at_its_first_line():
    [hit] = scan("TCW no\nlonger reads it.\n")
    assert (hit.line, hit.start, hit.end) == (1, 4, 6)
    assert hit.text == "no longer"


def test_a_continuation_lines_indentation_reads_as_one_space():
    [hit] = scan("- TCW does it.\n  It no\n  longer reads it.\n")
    assert (hit.line, hit.start, hit.end) == (2, 5, 7)


def test_a_hit_inside_a_later_line_is_placed_in_that_line():
    [hit] = scan("Here is a sentence\nabout the old nodes.\n")
    assert (hit.line, hit.start, hit.end, hit.text) == (2, 14, 19, "nodes")


@pytest.mark.parametrize("text", [
    "TCW no\n\nlonger reads it.",       # a blank line
    "TCW no\n```\nlonger\n```",          # a fence
    "TCW no\n| longer | x |",            # a table row
    "TCW no\n- longer",                  # a list item
    "TCW no\n* longer",
    "TCW no\n+ longer",
    "TCW no\n1. longer",
    "TCW no\n2) longer",
    "TCW no\n# longer",                  # a heading
    "| TCW no |\nlonger",                # nothing continues a table row
    "# TCW no\nlonger",                  # or a heading
])
def test_a_phrase_is_not_joined_across_a_block_boundary(text):
    assert scan(text) == []


def test_fenced_lines_are_read_one_at_a_time():
    assert blocks("```sh\ntcw no\nlonger\n```\n") == [
        [(1, "```sh")], [(2, "tcw no")], [(3, "longer")], [(4, "```")]]
    [hit] = scan("```\nold nodes here\n```\n")
    assert hit.line == 2


def test_hits_keep_the_line_by_line_order():
    """By line, then pattern, then column, as the line-by-line scan gave."""
    hits = scan("nodes, then no longer, then nodes\nprevious nodes\n")
    assert [(h.line, h.text) for h in hits] == [
        (1, "nodes"), (1, "nodes"), (1, "no longer"), (2, "nodes")]
