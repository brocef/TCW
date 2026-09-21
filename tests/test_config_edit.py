"""Editing one key of `tcw-config.yaml` in place (spec:
2026-09-21-keep-comments-and-formatting-when-tcw-writes-a-key-into-tcw-config-yaml).

Pure text in, text out: no store, no git. The command-level half — raw bytes on
disk, the git index, refusals leaving everything alone — is
`tests/test_config_edit_writers.py`.
"""

from pathlib import Path

import pytest
import yaml

from tcw.store import config_edit
from tcw.store.config_edit import (
    ConfigEditRefused, Remove, SetId, SetList, SetScalar, edit_text,
)

PATH = Path("/node/tcw-config.yaml")


def edit(text, *edits):
    return edit_text(PATH, text, list(edits))


def assert_only_added(before: str, after: str, *added: str) -> None:
    """`after` is `before` with exactly the lines `added` inserted, in order —
    the one assertion every "nothing else changed" test goes through."""
    old, new = before.splitlines(keepends=True), after.splitlines(keepends=True)
    remaining = list(new)
    for line in added:
        assert line in remaining, f"{line!r} not added:\n{after}"
        remaining.remove(line)
    assert remaining == old, f"lines other than the added ones changed:\n{after}"


def assert_only_removed(before: str, after: str, *removed: str) -> None:
    assert_only_added(after, before, *removed)


# ── scalars, new keys, new sections ──────────────────────────────────────────

ANNOTATED = """\
# Node configuration for the web app.
# Keep the tracker query in sync with the board.
id: web
taxonomy:
    path: docs/taxonomy   # shared with the api
work:
    lifecycle:
        # the spec stage runs our own checklist
        spec: [checklist]
    tracker:
        candidate-query: "project = WEB AND status in ('To Do', 'In Progress') AND labels = tcw ORDER BY rank"
# trailing note
"""


def test_a_new_key_goes_into_the_existing_section_at_its_indentation():
    after = edit(ANNOTATED, SetList("taxonomy", "extends", ("shared",)))
    assert_only_added(ANNOTATED, after, "    extends:\n", "        - shared\n")
    assert after.index("extends:") < after.index("work:")


def test_a_comment_after_the_section_stays_below_it():
    text = "taxonomy:\n  path: t\n# about work\nwork:\n  tags: [a]\n"
    after = edit(text, SetList("taxonomy", "extends", ("x",)))
    assert after == "taxonomy:\n  path: t\n  extends:\n    - x\n# about work\nwork:\n  tags: [a]\n"


def test_a_missing_section_is_appended_at_the_end():
    after = edit(ANNOTATED, SetList("capabilities", "extends", ("shared",)))
    assert after == ANNOTATED + "capabilities:\n    extends:\n        - shared\n"


def test_a_missing_section_goes_before_a_document_end_marker():
    text = "id: a\n...\n"
    assert edit(text, SetScalar("work", "path", "w")) == "id: a\nwork:\n  path: w\n...\n"


def test_a_file_without_a_final_line_break_gets_the_new_key_on_its_own_line():
    after = edit("id: a", SetScalar("work", "path", "w"))
    assert after == "id: a\nwork:\n  path: w\n"


def test_a_replaced_scalar_keeps_the_comment_after_it():
    after = edit(ANNOTATED, SetScalar("taxonomy", "path", "docs/tax"))
    assert "    path: docs/tax   # shared with the api\n" in after
    assert_only_added(ANNOTATED.replace("docs/taxonomy", "docs/tax"), after)


def test_a_scalar_that_needs_quoting_is_quoted():
    after = edit("id: a\n", SetScalar("work", "path", "a: b"))
    assert yaml.safe_load(after)["work"]["path"] == "a: b"


# ── nulls ────────────────────────────────────────────────────────────────────

def test_a_section_stub_keeps_its_commented_children():
    text = "taxonomy:\n  # extends:\n  #   - old\nwork:\n  tags: [a]\n"
    after = edit(text, SetList("taxonomy", "extends", ("x",)))
    assert after == ("taxonomy:\n  extends:\n    - x\n  # extends:\n  #   - old\n"
                     "work:\n  tags: [a]\n")


def test_an_empty_key_keeps_the_comment_on_its_line():
    text = "taxonomy:\n  extends: # inherited\n  path: t\n"
    after = edit(text, SetList("taxonomy", "extends", ("x",)))
    assert after == "taxonomy:\n  extends: # inherited\n    - x\n  path: t\n"


def test_an_explicit_null_scalar_is_replaced():
    assert edit("work:\n  path: ~  # set me\n", SetScalar("work", "path", "w")) \
        == "work:\n  path: w  # set me\n"


# ── id ───────────────────────────────────────────────────────────────────────

def test_id_goes_below_the_leading_comment_block():
    text = "# header\n\nwork:\n  path: w\n"
    assert edit(text, SetId("proj")) == "# header\n\nid: proj\nwork:\n  path: w\n"


def test_id_goes_after_a_document_start_marker():
    assert edit("---\nwork: {}\n", SetId("p")) == "---\nid: p\nwork: {}\n"


def test_a_null_id_is_replaced():
    after = edit("id: null\n# keep me\nwork: {}\n", SetId("p"))
    assert after == "id: p\n# keep me\nwork: {}\n"


def test_id_in_a_comment_only_file_is_appended():
    assert edit("# just a note\n", SetId("p")) == "# just a note\nid: p\n"


# ── removal ──────────────────────────────────────────────────────────────────

def test_removing_a_key_deletes_only_its_lines():
    text = "taxonomy:\n  path: t\n  # inherited\n  extends:\n    - a\nwork: {}\n"
    after = edit(text, Remove("taxonomy", "extends"))
    assert_only_removed(text, after, "  extends:\n", "    - a\n")


def test_removing_a_block_list_keeps_the_comment_after_it():
    text = "taxonomy:\n  extends:\n    - a\n  # about the path\n  path: t\n"
    after = edit(text, Remove("taxonomy", "extends"))
    assert after == "taxonomy:\n  # about the path\n  path: t\n"


def test_a_new_key_after_a_block_list_goes_above_the_comment_that_follows_it():
    text = "work:\n  tags:\n    - a\n# about taxonomy\ntaxonomy: {}\n"
    after = edit(text, SetScalar("work", "path", "w"))
    assert after == "work:\n  tags:\n    - a\n  path: w\n# about taxonomy\ntaxonomy: {}\n"


def test_removing_the_last_key_removes_the_section_line_too():
    text = "id: n\ntaxonomy:\n  extends: [a]\nwork: {}\n"
    assert edit(text, Remove("taxonomy", "extends")) == "id: n\nwork: {}\n"


def test_removing_the_last_key_keeps_a_comment_above_it():
    text = "id: n\ntaxonomy:\n  # why we inherit\n  extends: [a]\n"
    assert edit(text, Remove("taxonomy", "extends")) == "id: n\n  # why we inherit\n"


# ── line endings and byte-order mark ─────────────────────────────────────────

def test_windows_line_endings_are_kept_on_every_line():
    text = ANNOTATED.replace("\n", "\r\n")
    after = edit(text, SetList("taxonomy", "extends", ("shared",)))
    assert "\n" not in after.replace("\r\n", "")
    assert "    extends:\r\n        - shared\r\n" in after


def test_a_byte_order_mark_is_kept():
    after = edit("\ufeffid: a\nwork:\n  tags: [x]\n", SetId("a"), SetScalar("work", "path", "w"))
    assert after.startswith("\ufeffid: a\n")
    after = edit("\ufeffwork:\n  tags: [x]\n", SetId("p"))
    assert after == "\ufeffid: p\nwork:\n  tags: [x]\n"


# ── missing, empty, comment-only ─────────────────────────────────────────────

@pytest.mark.parametrize("text", [None, "", "  \n\n"])
def test_a_missing_or_empty_file_is_written_in_full(text):
    after = edit(text, SetId("p"), SetScalar("work", "path", "w"))
    assert yaml.safe_load(after) == {"id": "p", "work": {"path": "w"}}


def test_nothing_to_change_returns_none():
    assert edit("id: p\n", SetId("p")) is None
    assert edit(None, Remove("taxonomy", "extends")) is None


# ── refusals ─────────────────────────────────────────────────────────────────

def refused(text, *edits) -> str:
    with pytest.raises(ConfigEditRefused) as caught:
        edit(text, *edits)
    message = str(caught.value)
    assert message.startswith(f"{PATH}: cannot "), message
    assert "would lose its comments and formatting" in message
    return message


def test_a_flow_section_needing_a_new_key_is_refused_with_a_brace_instruction():
    message = refused("taxonomy: {path: docs/t}\n", SetList("taxonomy", "extends", ("acme",)))
    assert "(`taxonomy` is written inside braces)" in message
    assert "inside the braces" in message
    assert ", extends: [acme]" in message
    assert "taxonomy:\n" not in message       # never a restated section


def test_a_value_inside_a_flow_section_may_still_be_replaced():
    text = "work: {path: a, tags: [x]}  # note\n"
    assert edit(text, SetScalar("work", "path", "b")) == "work: {path: b, tags: [x]}  # note\n"


def test_an_alias_target_is_refused():
    message = refused("base: &t [a]\nwork:\n  tags: *t\n", SetList("work", "tags", ("a", "b")))
    assert "(`work.tags` is an alias)" in message


def test_removing_a_value_that_carries_an_aliased_anchor_is_refused():
    text = "taxonomy:\n  extends: &ids [a]\ncapabilities:\n  extends: *ids\n"
    refused(text, Remove("taxonomy", "extends"))


def test_a_block_scalar_target_is_refused():
    refused("taxonomy:\n  path: |\n    docs/t\n", SetScalar("taxonomy", "path", "x"))


def test_a_flow_top_level_is_refused():
    refused("{id: a, work: {path: w}}\n", SetScalar("taxonomy", "path", "t"))


def test_a_non_mapping_section_is_refused():
    refused("work: docs/work\n", SetList("work", "tags", ("a",)))


def test_a_removal_message_does_not_restate_the_section():
    message = refused("taxonomy: {extends: [a], path: t}\n", Remove("taxonomy", "extends"))
    assert "delete" in message and "leaving its other keys" in message
    assert "taxonomy:\n" not in message


def test_an_add_message_says_not_to_add_a_second_section():
    # `b` before `a` makes it a reorder, and the comment inside forbids that.
    text ="taxonomy:\n  path: t\n  extends:\n    - b # note\n    - a\n"
    message = refused(text, SetList("taxonomy", "extends", ("a", "b", "c")))
    assert "do not add a second one" in message
    assert "extends: [a, b, c]" in message


# ── the verifier catches what the editor could get wrong ─────────────────────

def test_the_verifier_refuses_a_comment_lost_outside_the_edit():
    original = "id: a  # keep\nwork: {}\n"
    new = "id: a\nwork: {}\n"
    with pytest.raises(ConfigEditRefused):
        config_edit._verify(PATH, original, new, [], set(), {"id": "a", "work": {}},
                            instruction="x")


def test_the_verifier_refuses_an_edit_over_an_anchor():
    # Means what it says, parses, and stays inside its span — refused only
    # because it rewrites an anchor, which changes every key that aliases it.
    original = "a: &x [1]\nb: *x\n"
    span = config_edit._Replacement(3, 9, "&x [2]")
    with pytest.raises(ConfigEditRefused, match="anchor"):
        config_edit._verify(PATH, original, "a: &x [2]\nb: *x\n", [span], set(),
                            {"a": [2], "b": [2]}, instruction="x")


def test_the_verifier_refuses_a_comment_inside_the_edit():
    original = "a:\n- 1\n# note\n- 2\n"
    span = config_edit._Replacement(3, len(original), "- 2\n")
    with pytest.raises(ConfigEditRefused):
        config_edit._verify(PATH, original, "a:\n- 2\n", [span], set(),
                            {"a": [2]}, instruction="x")


def test_the_verifier_refuses_a_change_of_meaning():
    original = "a: 1\n"
    span = config_edit._Replacement(3, 4, "2")
    with pytest.raises(ConfigEditRefused):
        config_edit._verify(PATH, original, "a: 2\n", [span], set(), {"a": 1},
                            instruction="x")


# ── lists ────────────────────────────────────────────────────────────────────

COMMENTED_LIST = """\
taxonomy:
  extends:
    - a  # the first
    # why b comes next
    - b  # the second
  # after the list
  path: t
"""


def test_adding_to_a_block_list_inserts_one_line_after_its_predecessor():
    after = edit(COMMENTED_LIST, SetList("taxonomy", "extends", ("a", "b", "c")))
    assert_only_added(COMMENTED_LIST, after, "    - c\n")
    assert after.index("- c") < after.index("# after the list")


def test_removing_from_a_block_list_deletes_only_that_line():
    after = edit(COMMENTED_LIST, SetList("taxonomy", "extends", ("b",)))
    assert_only_removed(COMMENTED_LIST, after, "    - a  # the first\n")


def test_a_sorted_insert_lands_between_its_neighbours():
    text = "work:\n  tags:\n  - alpha  # first\n  - gamma\n"
    after = edit(text, SetList("work", "tags", ("alpha", "beta", "gamma")))
    assert after == "work:\n  tags:\n  - alpha  # first\n  - beta\n  - gamma\n"


def test_an_insert_before_the_first_item_uses_its_dash_column():
    text = "work:\n    tags:\n        - m\n"
    after = edit(text, SetList("work", "tags", ("a", "m")))
    assert after == "work:\n    tags:\n        - a\n        - m\n"


def test_a_flow_list_stays_a_flow_list_on_its_line():
    text = "work:\n  tags: [alpha, gamma]  # registered\n"
    assert edit(text, SetList("work", "tags", ("alpha", "beta", "gamma"))) \
        == "work:\n  tags: [alpha, beta, gamma]  # registered\n"
    assert edit(text, SetList("work", "tags", ("gamma",))) \
        == "work:\n  tags: [gamma]  # registered\n"


def test_emptying_a_list_writes_an_empty_flow_list():
    text = "work:\n  tags:\n  - a\n  path: w\n"
    assert edit(text, SetList("work", "tags", ())) == "work:\n  tags: []\n  path: w\n"


def test_a_reordered_list_without_comments_is_replaced_whole():
    text = "id: n\nwork:\n  tags:\n  - b\n  - a\n  path: w\n"
    after = edit(text, SetList("work", "tags", ("a", "b", "c")))
    assert after == "id: n\nwork:\n  tags:\n  - a\n  - b\n  - c\n  path: w\n"


def test_a_reordered_list_with_a_comment_is_refused():
    text = "work:\n  tags:\n  - b  # keep\n  - a\n"
    refused(text, SetList("work", "tags", ("a", "b", "c")))


def test_adding_an_item_that_is_already_there_changes_nothing():
    assert edit(COMMENTED_LIST, SetList("taxonomy", "extends", ("a", "b"))) is None


def test_a_comment_line_straight_after_the_list_survives_add_and_remove():
    text = "work:\n  tags:\n  - a\n  # end of tags\nother: 1\n"
    assert "  # end of tags\n" in edit(text, SetList("work", "tags", ("a", "b")))
    assert "  # end of tags\n" in edit(text, SetList("work", "tags", ()))


def test_a_multi_line_flow_list_with_a_comment_is_refused():
    text = "work:\n  tags: [a,  # first\n    b]\n"
    refused(text, SetList("work", "tags", ("a", "b", "c")))


# ── equivalence with the whole-file writer this replaced ─────────────────────

def old_writer(mapping: dict, edit) -> dict:
    """What each writer's own dict logic produced before, round-tripped through
    `yaml.safe_dump` as it used to be — a copy of that logic, kept here as the
    reference rather than imported, because the code it copies is gone."""
    config = dict(mapping)
    if isinstance(edit, SetId):
        return yaml.safe_load(yaml.safe_dump({"id": edit.value, **config}))
    section = config.get(edit.section)
    section = dict(section) if isinstance(section, dict) else {}
    if isinstance(edit, Remove):                           # _persist_extends([])
        section.pop(edit.key, None)
    elif isinstance(edit, SetList):                        # extends / tags
        section[edit.key] = list(edit.values)
    else:                                                  # init's path
        section = {**section, edit.key: edit.value}
    if section:
        config[edit.section] = section
    else:
        config.pop(edit.section, None)
    return yaml.safe_load(yaml.safe_dump(config, sort_keys=False))


SHAPES = [
    "id: n\n",
    "# only a comment\n",
    "id: n\ntaxonomy:\n  extends:\n  - a\n  - b\nwork:\n  tags: [a, c]\n",
    "id: n\ntaxonomy:\n    path: t  # c\n    extends: [a, b]\nwork:\n    tags:\n        - a\n        - c\n",
    "id: n\r\ntaxonomy:\r\n  extends:\r\n  - a\r\n  - b\r\nwork:\r\n  path: w\r\n",
    "id: n\ntaxonomy:\n  # stub\nwork:\ncapabilities: ~\n",
    "id: n\ntaxonomy:\n  extends: # later\n  path: t\nwork:\n  tags: []\n",
]

EDITS = [
    SetList("taxonomy", "extends", ("a", "b", "c")),
    SetList("taxonomy", "extends", ("b",)),
    Remove("taxonomy", "extends"),
    SetList("work", "tags", ("a", "b", "c")),
    SetList("work", "tags", ()),
    SetScalar("work", "path", "planning/work"),
    SetScalar("capabilities", "path", "docs/caps"),
]


@pytest.mark.parametrize("text", SHAPES)
@pytest.mark.parametrize("change", EDITS, ids=repr)
def test_the_result_means_what_the_whole_file_writer_produced(text, change):
    mapping = yaml.safe_load(text) or {}
    if isinstance(change, Remove) and change.key not in (mapping.get(change.section) or {}):
        pytest.skip("extends rm refuses an id that is not there before writing")
    after = edit(text, change)
    assert (yaml.safe_load(after if after is not None else text) or {}) == old_writer(mapping, change)


@pytest.mark.parametrize("text", ["# only a comment\n", "work:\n  tags: [a]  # c\n",
                                  "\ufeff# header\nwork: {}\n"])
def test_a_backfilled_id_means_what_the_whole_file_writer_produced(text):
    mapping = yaml.safe_load(text) or {}
    assert yaml.safe_load(edit(text, SetId("p"))) == old_writer(mapping, SetId("p"))
