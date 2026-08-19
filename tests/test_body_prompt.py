"""The `{{tcw:body}}` span: naming the artifact a stage should actually read.

The unit half pins the substitution; the end-to-end half drives the real CLI
against items in each body state, because the prompt text is only correct if it
survives `tcw work stage`.
"""

import subprocess

import pytest

from tcw.store.base import BODY_ORDER, Artifact
from tcw.work.resolve import resolved_body, substitute_body

REQUEST = Artifact("initial-request", True)
INTAKE = Artifact("intake", True)
SPEC = Artifact("spec", True)

SPAN = "{{tcw:body}}the item's body artifact{{/tcw:body}}"


def test_the_order_is_the_store_s_own():
    """Not a second copy of the rule: the resolver reads the same tuple the
    filesystem adapter resolves a body with."""
    assert BODY_ORDER == ("initial-request", "intake")


def test_the_request_wins_when_both_are_present():
    assert resolved_body([REQUEST, INTAKE, SPEC]) == "`initial-request.md`"
    assert substitute_body(SPAN, [REQUEST, INTAKE]) == "`initial-request.md`"


def test_intake_is_named_when_the_request_stage_has_not_run():
    assert resolved_body([INTAKE, SPEC]) == "`intake.md`"
    assert substitute_body(SPAN, [INTAKE]) == "`intake.md`"


def test_an_absent_artifact_does_not_count_as_present():
    """`Artifact.present` is the lifecycle rule — a blank file is absent — so a
    reported-but-empty request must not be named over a real intake."""
    assert resolved_body([Artifact("initial-request", False), INTAKE]) == "`intake.md`"


def test_with_no_body_at_all_the_span_becomes_its_own_text():
    """`tcw work new "<title>"` with nothing piped writes no body file. The
    prompt keeps its own prose rather than naming a document that never
    existed."""
    assert resolved_body([SPEC]) is None
    assert substitute_body(SPAN, [SPEC]) == "the item's body artifact"
    assert substitute_body(SPAN, []) == "the item's body artifact"


def test_the_span_is_replaced_in_place_not_as_a_block():
    """The regression this function exists to avoid: reusing
    `substitute_documentation`'s walk appends a newline and the span's indent,
    which breaks a sentence in half."""
    text = f"**Inputs.** {SPAN}. On an `initial-request.md`, read on."
    assert substitute_body(text, [INTAKE]) == (
        "**Inputs.** `intake.md`. On an `initial-request.md`, read on.")
    assert "\n" not in substitute_body(text, [INTAKE])


def test_an_indented_span_gains_no_indent_of_its_own():
    text = f"1. Read {SPAN} first.\n2. Then the code.\n"
    assert substitute_body(text, [REQUEST]) == (
        "1. Read `initial-request.md` first.\n2. Then the code.\n")


def test_every_span_in_the_text_is_replaced():
    text = f"{SPAN} and again {SPAN}"
    assert substitute_body(text, [INTAKE]) == "`intake.md` and again `intake.md`"


def test_an_unterminated_token_is_left_verbatim():
    """A malformed prompt should look wrong, not silently swallow its tail."""
    text = "before {{tcw:body}} after with no close"
    assert substitute_body(text, [INTAKE]) == text
    assert substitute_body(text, []) == text


def test_text_with_no_span_is_untouched():
    text = "**Inputs.** `spec.md` and `plan.md`.\n"
    assert substitute_body(text, [INTAKE]) == text
