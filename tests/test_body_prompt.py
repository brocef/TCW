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


def test_a_body_token_inside_rendered_documentation_is_substituted():
    """The sharp edge of the substitution order, pinned so it stays deterministic.

    `resolve_prompts` renders documentation first, so a body token that only
    exists because a `work.documentation` description contained one is text the
    body pass then sees and rewrites. Documented on `substitute_body`; asserted
    here so an accidental reordering is a failing test rather than a surprise.
    """
    from tcw.store.base import DocEntry
    from tcw.work.resolve import substitute_documentation
    entries = [DocEntry(path="README.md", trigger="Public-API",
                        description=f"Mentions {SPAN} verbatim.")]
    rendered = substitute_documentation(
        "{{tcw:documentation}}nothing configured{{/tcw:documentation}}", entries)
    assert SPAN in rendered
    assert "`intake.md`" in substitute_body(rendered, [INTAKE])


def test_text_with_no_span_is_untouched():
    text = "**Inputs.** `spec.md` and `plan.md`.\n"
    assert substitute_body(text, [INTAKE]) == text


# ── end to end, through the real CLI ──────────────────────────────────────────

def _tcw(root, *args):
    r = subprocess.run(["tcw", *args], cwd=str(root), capture_output=True,
                       text=True, stdin=subprocess.DEVNULL)
    assert r.returncode == 0, f"tcw {' '.join(args)} failed: {r.stderr}"
    return r.stdout


@pytest.fixture
def node(tmp_path):
    """Same shape as `tests/test_documentation_prompt.py::_node` — the other
    place a shipped prompt is checked through the real CLI."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(tmp_path), "config", k, v], check=True)
    _tcw(tmp_path, "init", "--id", "body-node", "work")
    return tmp_path


def _new(root, title, *, intake=None, body=None):
    """An item in one of the three body states. `create` takes the two apart the
    way the store does: `intake` is raw arrival, `body` is what the `request`
    stage would have written."""
    from tcw.store.fs import FsWorkStore
    kwargs = {}
    if intake is not None:
        kwargs["intake"] = intake
    if body is not None:
        kwargs["body"] = body
    return FsWorkStore.open(root).create(title, **kwargs).slug


def _inputs_paragraph(text):
    """The `**Inputs.**` paragraph alone — the claim is about that paragraph, not
    about the whole prompt, which legitimately names other artifacts."""
    lines = text.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("**Inputs.**"))
    end = next((i for i in range(start + 1, len(lines)) if not lines[i].strip()),
               len(lines))
    return "\n".join(lines[start:end])


@pytest.mark.parametrize("stage", ["spec", "plan"])
def test_an_intake_only_item_is_told_to_read_its_intake(node, stage):
    """Asserted on what the span resolved to, which is the sentence's subject.
    `spec` also *mentions* `initial-request.md` further down the paragraph to
    explain how the two differ; that is prose about the artifacts, not a claim
    that this item has one."""
    slug = _new(node, "Intake only item", intake="# Raw\n\nWhat arrived.\n")
    para = _inputs_paragraph(_tcw(node, "work", "stage", stage, slug))
    assert para.startswith("**Inputs.** `intake.md`")


@pytest.mark.parametrize("stage", ["spec", "plan"])
def test_a_request_bearing_item_is_told_to_read_its_request(node, stage):
    slug = _new(node, "Request item", body="# Written up\n")
    para = _inputs_paragraph(_tcw(node, "work", "stage", stage, slug))
    assert para.startswith("**Inputs.** `initial-request.md`")


@pytest.mark.parametrize("stage", ["spec", "plan"])
def test_the_request_still_wins_when_the_item_also_has_intake(node, stage):
    slug = _new(node, "Both item", intake="# Raw\n", body="# Written up\n")
    para = _inputs_paragraph(_tcw(node, "work", "stage", stage, slug))
    assert para.startswith("**Inputs.** `initial-request.md`")


@pytest.mark.parametrize("stage", ["spec", "plan"])
def test_an_item_with_no_body_falls_back_instead_of_naming_a_phantom(node, stage):
    """`tcw work new "<title>"` with nothing piped writes no body file. The
    prompt must not hand the agent a filename to go open.

    Asserted on the *substituted value*, not on the paragraph: `spec`'s prose
    names both artifacts to explain how they differ, and that is descriptive
    rather than a claim about this item."""
    slug = _new(node, "Bodyless item")
    para = _inputs_paragraph(_tcw(node, "work", "stage", stage, slug))
    assert "**Inputs.** the item's body artifact" in para
    assert "`initial-request.md`, read as filed" not in para
    assert "`intake.md`, read as filed" not in para
    assert "`intake.md` and `spec.md`" not in para


def test_the_nobody_asked_conclusion_is_scoped_to_the_request(node):
    """The defect this item fixes: on an intake-only item the `request` stage
    never ran, so a missing `## References` proves nothing about the requester.

    The prompt's branch prose is static, so the clause is always *present*; what
    must hold is that it is **scoped** — every sentence drawing that conclusion
    also names `initial-request.md` — and that the intake branch states what to
    do instead. Both halves asserted: the scoping check alone would pass on
    deleting the intake guidance."""
    slug = _new(node, "Intake only item", intake="# Raw\n")
    para = _inputs_paragraph(_tcw(node, "work", "stage", "spec", slug))

    flat = " ".join(para.split())
    carriers = [s for s in flat.split(". ") if "nobody asked" in s]
    # Asserted non-empty first: the scoping loop below is vacuous if the clause
    # disappears entirely, and a prompt that simply dropped the guidance would
    # otherwise pass this test.
    assert carriers, f"the 'nobody asked' guidance is gone entirely: {flat}"
    for sentence in carriers:
        assert "`initial-request.md`" in sentence, (
            f"unscoped conclusion: {sentence}")

    # The intake branch, asserted positively.
    assert "work from the" in flat and "intake itself" in flat
    assert "the `request` stage has not run" in flat


def test_the_postmortem_spine_names_the_intake(node):
    """`postmortem` carries no span — it reads whatever the item has, so it names
    both artifacts in prose. The fixture in `test_prompt_fallback.py` pins its
    bytes; this asserts the intent, so a re-baseline cannot quietly drop it."""
    slug = _new(node, "Intake only item", intake="# Raw\n")
    for transition in ("start", "submit"):
        _tcw(node, "work", transition, slug)
    out = _tcw(node, "work", "stage", "postmortem", slug)
    assert "intake.md" in out
    assert "initial-request.md" in out


@pytest.mark.parametrize("stage", ["spec", "plan"])
@pytest.mark.parametrize("state", ["intake", "request", "none"])
def test_no_token_survives_into_a_resolved_prompt(node, stage, state):
    """Scoped to the two stages that carry a body span, and to well-formed
    spans: an unterminated token in a project's own prompt is required to
    survive (see `test_an_unterminated_token_is_left_verbatim`)."""
    kwargs = {"intake": "# Raw\n"} if state == "intake" else (
        {"body": "# Written\n"} if state == "request" else {})
    slug = _new(node, f"Item {state}", **kwargs)
    out = _tcw(node, "work", "stage", stage, slug)
    assert "{{tcw:" not in out
    assert "{{/tcw:" not in out
