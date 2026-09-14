"""`work.tracker` inherited from parent nodes, key by key.

The properties this file holds, beyond the merge itself:

- **Opt-in.** Only a node whose own block is a non-empty mapping inherits. A node
  that writes nothing has no tracker and no problems, whatever its parents hold.
- **A token never goes to a site its node did not choose.** `credentials` must
  come from the same file as `base-url`, or a nearer one.
- **A problem names the file that caused it**, matched on the exact key path, and
  a key nobody set is blamed on the node being checked.
"""

from __future__ import annotations

import copy

import pytest

from tcw.store.base import (
    attribute_tracker_problems,
    merge_tracker_blocks,
    parse_tracker_config,
    tracker_credentials_problem,
)

COMPLETE = {
    "provider": "jira-cloud",
    "base-url": "https://root.example.invalid",
    "candidate-query": "project = EX",
    "credentials": {"email-env": "ROOT_EMAIL", "token-env": "ROOT_TOKEN"},
    "transitions": {"claim": "Start"},
}

CREDENTIALS_MESSAGE_START = "work.tracker.credentials: inherited from a parent node"


# ── the pure merge ───────────────────────────────────────────────────────────


@pytest.fixture()
def empty_cwd(tmp_path, monkeypatch):
    """The pure functions read no file, so they run from a directory holding none."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_nested_mappings_merge_key_by_key_and_the_record_names_each_source(empty_cwd):
    """C18, with criterion 4's mappings."""
    root = {**COMPLETE, "credentials": {"email-env": "A", "token-env": "B"}}
    pkg = {"candidate-query": "component = api", "credentials": {"token-env": "C"}}
    merged, record, whole = merge_tracker_blocks([("pkg", pkg), ("root", root)])
    assert whole is None
    assert merged["credentials"] == {"email-env": "A", "token-env": "C"}
    assert merged["candidate-query"] == "component = api"
    assert merged["base-url"] == COMPLETE["base-url"]
    assert record[("credentials", "token-env")] == "pkg"
    assert record[("credentials", "email-env")] == "root"


def test_the_nearest_block_wins_a_scalar(empty_cwd):
    merged, record, _ = merge_tracker_blocks(
        [("pkg", {"base-url": "https://pkg"}), ("repo", {"base-url": "https://repo"}),
         ("root", COMPLETE)])
    assert merged["base-url"] == "https://pkg"
    assert record[("base-url",)] == "pkg"


def test_a_nearer_null_lets_the_farther_value_show_through(empty_cwd):
    """C6 at merge level. The record keeps naming the file that supplied the value."""
    merged, record, _ = merge_tracker_blocks(
        [("pkg", {"timeout-seconds": None}), ("root", {**COMPLETE, "timeout-seconds": 30})])
    assert merged["timeout-seconds"] == 30
    assert record[("timeout-seconds",)] == "root"


def test_a_null_with_nothing_farther_is_kept_for_the_parser_to_report(empty_cwd):
    """C7 at merge level."""
    merged, record, _ = merge_tracker_blocks([("pkg", {**COMPLETE, "timeout-seconds": None})])
    assert "timeout-seconds" in merged and merged["timeout-seconds"] is None
    assert record[("timeout-seconds",)] == "pkg"


def test_all_null_credentials_are_recorded_against_the_file_that_supplied_them(empty_cwd):
    """The merge half of C23. Recording the nulls' file here would silence the
    credentials rule and send root's token to pkg's site."""
    pkg = {"base-url": "https://pkg", "credentials": {"email-env": None, "token-env": None}}
    merged, record, _ = merge_tracker_blocks([("pkg", pkg), ("root", COMPLETE)])
    assert merged["credentials"] == COMPLETE["credentials"]
    assert record[("credentials", "email-env")] == "root"
    assert record[("credentials", "token-env")] == "root"


def test_a_null_credentials_mapping_is_recorded_against_the_farther_file(empty_cwd):
    merged, record, _ = merge_tracker_blocks(
        [("pkg", {"credentials": None}), ("root", COMPLETE)])
    assert merged["credentials"] == COMPLETE["credentials"]
    assert record[("credentials", "token-env")] == "root"


def test_a_list_replaces_rather_than_concatenating(empty_cwd):
    merged, _, _ = merge_tracker_blocks([("pkg", {"extra": [3]}), ("root", {"extra": [1, 2]})])
    assert merged["extra"] == [3]


def test_a_value_replacing_a_mapping_drops_the_mappings_record_entries(empty_cwd):
    merged, record, _ = merge_tracker_blocks([("pkg", {"credentials": "x"}), ("root", COMPLETE)])
    assert merged["credentials"] == "x"
    assert record[("credentials",)] == "pkg"
    assert not [p for p in record if len(p) > 1 and p[0] == "credentials"]


def test_a_mapping_replacing_a_value_records_its_own_keys(empty_cwd):
    merged, record, _ = merge_tracker_blocks(
        [("pkg", {"credentials": {"token-env": "C"}}), ("root", {"credentials": "x"})])
    assert merged["credentials"] == {"token-env": "C"}
    assert record[("credentials", "token-env")] == "pkg"


def test_an_ancestor_that_is_not_a_mapping_stops_the_merge_and_owns_the_problem(empty_cwd):
    merged, record, whole = merge_tracker_blocks([("pkg", COMPLETE), ("root", "off")])
    assert merged == "off"
    assert record == {}
    assert whole == "root"


def test_empty_ancestors_contribute_nothing(empty_cwd):
    merged, _, whole = merge_tracker_blocks([("pkg", COMPLETE), ("repo", None), ("root", {})])
    assert merged == COMPLETE
    assert whole is None


def test_the_merge_does_not_change_its_inputs(empty_cwd):
    root = copy.deepcopy(COMPLETE)
    pkg = {"credentials": {"token-env": "C", "email-env": None}, "timeout-seconds": None}
    before = copy.deepcopy((pkg, root))
    merged, _, _ = merge_tracker_blocks([("pkg", pkg), ("root", root)])
    merged["credentials"]["email-env"] = "changed"
    assert (pkg, root) == before


# ── credentials stay with their site ─────────────────────────────────────────


def _credentials_problem(blocks):
    _merged, record, _ = merge_tracker_blocks(blocks)
    return tracker_credentials_problem(record, [label for label, _ in blocks])


def test_a_nearer_base_url_with_inherited_credentials_is_a_problem(empty_cwd):
    problem = _credentials_problem([("pkg", {"base-url": "https://pkg"}), ("root", COMPLETE)])
    assert problem is not None and problem.startswith(CREDENTIALS_MESSAGE_START)
    assert "in pkg;" in problem


def test_nearer_credentials_on_the_same_site_are_allowed(empty_cwd):
    assert _credentials_problem(
        [("pkg", {"credentials": {"email-env": "E", "token-env": "T"}}), ("root", COMPLETE)]) is None


def test_base_url_and_credentials_from_one_file_are_allowed(empty_cwd):
    assert _credentials_problem([("pkg", {"candidate-query": "q"}), ("root", COMPLETE)]) is None


def test_partly_inherited_credentials_count_by_their_farthest_key(empty_cwd):
    problem = _credentials_problem(
        [("pkg", {"base-url": "https://pkg", "credentials": {"token-env": "T"}}),
         ("root", COMPLETE)])
    assert problem is not None and problem.startswith(CREDENTIALS_MESSAGE_START)


def test_all_null_credentials_beside_a_nearer_base_url_are_a_problem(empty_cwd):
    """C23 at merge level."""
    problem = _credentials_problem(
        [("pkg", {"base-url": "https://pkg",
                  "credentials": {"email-env": None, "token-env": None}}),
         ("root", COMPLETE)])
    assert problem is not None and problem.startswith(CREDENTIALS_MESSAGE_START)


# ── naming the file a problem came from ──────────────────────────────────────


def _attributed(blocks):
    merged, record, whole = merge_tracker_blocks(blocks)
    _config, problems = parse_tracker_config(merged)
    return attribute_tracker_problems(problems, record, blocks[0][0], whole)


def test_an_unknown_top_level_key_names_the_file_that_wrote_it(empty_cwd):
    assert "root: work.tracker.colour: unknown key" in _attributed(
        [("pkg", {"candidate-query": "q"}), ("root", {**COMPLETE, "colour": "red"})])


def test_an_unknown_nested_key_names_the_file_that_wrote_it(empty_cwd):
    root = {**COMPLETE, "credentials": {**COMPLETE["credentials"], "x": 1}}
    assert "root: work.tracker.credentials.x: unknown key" in _attributed(
        [("pkg", {"candidate-query": "q"}), ("root", root)])


def test_a_wrong_type_names_the_file_that_wrote_it(empty_cwd):
    assert ("root: work.tracker.base-url: expected a non-empty string, got int"
            in _attributed([("pkg", {"candidate-query": "q"}), ("root", {**COMPLETE, "base-url": 42})]))


def test_an_unsupported_provider_names_the_file_that_wrote_it(empty_cwd):
    problems = _attributed([("pkg", {"candidate-query": "q"}),
                            ("root", {**COMPLETE, "provider": "github"})])
    assert [p for p in problems if p.startswith("root: work.tracker.provider: 'github'")]


def test_a_missing_top_level_key_is_blamed_on_the_node_being_checked(empty_cwd):
    root = {k: v for k, v in COMPLETE.items() if k != "candidate-query"}
    assert "pkg: work.tracker.candidate-query: required" in _attributed(
        [("pkg", {"timeout-seconds": 5}), ("root", root)])


def test_a_missing_nested_key_under_an_ancestors_mapping_is_blamed_on_the_node(empty_cwd):
    """C22 at merge level. Root supplied `transitions`, but nobody set `claim`."""
    problems = _attributed([("pkg", {"candidate-query": "q"}),
                            ("root", {**COMPLETE, "transitions": {}})])
    assert "pkg: work.tracker.transitions.claim: required" in problems
    assert not [p for p in problems if p.startswith("root:")]


def test_a_key_whose_name_contains_a_dot_is_one_key(empty_cwd):
    """C24 at merge level."""
    assert "root: work.tracker.a.b: unknown key" in _attributed(
        [("pkg", {"candidate-query": "q"}), ("root", {**COMPLETE, "a.b": 1})])


def test_a_whole_block_that_is_not_a_mapping_names_the_ancestor(empty_cwd):
    assert _attributed([("pkg", COMPLETE), ("root", "off")]) == [
        "root: work.tracker: expected a mapping, got str"]


def test_a_node_whose_own_block_is_not_a_mapping_is_named_itself(empty_cwd):
    assert _attributed([("pkg", "none")]) == ["pkg: work.tracker: expected a mapping, got str"]


# ── the parser no longer raises on mixed key types ───────────────────────────


def test_mixed_key_types_at_the_top_level_are_reported_not_raised():
    """C26."""
    config, problems = parse_tracker_config({**COMPLETE, 5: 1, "z": 2})
    assert config is None
    assert "work.tracker.5: unknown key" in problems
    assert "work.tracker.z: unknown key" in problems


def test_mixed_key_types_inside_a_nested_mapping_are_reported_not_raised():
    """C26."""
    config, problems = parse_tracker_config(
        {**COMPLETE, "credentials": {**COMPLETE["credentials"], 5: 1, "z": 2}})
    assert config is None
    assert "work.tracker.credentials.5: unknown key" in problems
    assert "work.tracker.credentials.z: unknown key" in problems
