"""`body_title` — reading an item's title out of an intake body.

Storage-neutral: a heading lives in the body a store hands back, so any adapter
inherits this rather than reimplementing it. `tests/test_work.py` covers the
`inbox accept` wiring; this file covers the scan itself.
"""

import pytest

from tcw.store.base import body_title, frontmatter_end
from tcw.store.fs import FsWorkStore

BASIC = [
    ("# Another Raw Request\n\nBody.\n", "Another Raw Request"),
    ("Just body text, no heading.\n", None),
    (None, None),                                  # binary primary resource
    ("## Sub\n\n# Real\n", "Real"),                # `##` is not an H1
    ("#\n\n#   \n\n# Real\n", "Real"),             # an empty heading is no match
    ("# Support C#\n", "Support C#"),
    ("# Fix auth #\n", "Fix auth #"),              # no ATX-closing mangling
    ("  # Indented\n\n# Real\n", "Real"),          # a heading starts at column 0
]

FRONTMATTER = [
    ("---\nfrom: parent\ninitiative: e\n---\n\n# Do the thing\n\ndetails\n", "Do the thing"),
    # CRLF and a BOM are not frontmatter per `_frontmatter`, so the whole body
    # is scanned and the H1 still wins.
    ("---\r\nfrom: parent\r\n---\r\n\r\n# CRLF Title\r\n", "CRLF Title"),
    ("﻿---\nfrom: p\n---\n\n# BOM Title\n", "BOM Title"),
    # A leading thematic break is treated as frontmatter and swallows the first
    # H1. Documented miss, asserted so it stays deliberate.
    ("---\n\n# Swallowed\n\n---\n\n# Real\n", "Real"),
    # Unterminated: no frontmatter, whole body scanned, no H1. Unreachable
    # through `inbox_accept` (which raises at `_inbox_initiative` first).
    ("---\nfrom: p\n---", None),
]

FENCES = [
    ("```sh\n# shell comment\n```\n\n# Real\n", "Real"),
    ("```sh\n# only a comment\n```\n", None),
    # The run-length case: a three-backtick line does not close a four-backtick
    # fence. A bare toggle returns "Still inside the four-backtick fence".
    ("````\n# Example inside documentation\n```\n# Still inside the four-backtick fence\n"
     "````\n\n# Real request title\n", "Real request title"),
    ("```\n~~~\n# not a title\n```\n\n# Real\n", "Real"),   # tildes cannot close backticks
    ("~~~\n# in tilde fence\n~~~\n\n# Real\n", "Real"),     # symmetric
    # An unclosed fence suppresses every later heading — the safe direction.
    ("```sh\n# comment\n\n# Real\n", None),
]


@pytest.mark.parametrize("body,expected", BASIC + FRONTMATTER + FENCES)
def test_body_title(body, expected):
    assert body_title(body) == expected


def test_frontmatter_end_agrees_with_the_frontmatter_parser(tmp_path):
    """One predicate defines "leading frontmatter"; both callers use it.

    `FsWorkStore._frontmatter` parses the block `frontmatter_end` delimits.
    Two definitions would drift, and the drift would be invisible — the title
    would simply come from the wrong half of the file.
    """
    for body, _ in FRONTMATTER:
        delimited = body.startswith("---\n") and body.find("\n---\n", 4) >= 0
        assert (frontmatter_end(body) != 0) is delimited
        if body.startswith("---\n") and not delimited:
            with pytest.raises(ValueError, match="malformed"):
                FsWorkStore._frontmatter(body, "label")
        else:
            # No raise: the parser accepts exactly the blocks the offset
            # delimits (what it *parses* out of one is not this test's claim).
            FsWorkStore._frontmatter(body, "label")
