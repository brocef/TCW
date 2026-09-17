"""`work.tracker` parsing: the shape, and the two properties that matter.

The properties, which are the reason this file exists rather than a handful of
happy-path asserts:

- **It fails closed.** Any problem means no config at all, not a partial one. A
  half-read tracker config whose `token-env` is mistyped but whose `base-url`
  parses would send an unauthenticated request to a real site.
- **It never holds a secret.** The config carries the *names* of two environment
  variables. Nothing on it holds a value read from them.
"""

from __future__ import annotations

import pytest

from tcw.store.base import parse_tracker_config

VALID = {
    "provider": "jira-cloud",
    "base-url": "https://example.atlassian.net",
    "candidate-query": 'assignee = currentUser() AND status = "To Do"',
    "credentials": {"email-env": "TCW_JIRA_EMAIL", "token-env": "TCW_JIRA_API_TOKEN"},
    "transitions": {"claim": "Start Progress"},
}


def _without(key):
    """VALID minus one top-level key."""
    return {k: v for k, v in VALID.items() if k != key}


# ── the happy path ───────────────────────────────────────────────────────────


def test_a_valid_block_parses_with_no_problems():
    config, problems = parse_tracker_config(VALID)
    assert problems == []
    assert config is not None
    assert config.provider == "jira-cloud"
    assert config.base_url == "https://example.atlassian.net"
    assert config.candidate_query == VALID["candidate-query"]
    assert config.email_env == "TCW_JIRA_EMAIL"
    assert config.token_env == "TCW_JIRA_API_TOKEN"
    assert config.claim_transition == "Start Progress"


def test_the_timeout_defaults_to_fifteen_seconds():
    config, problems = parse_tracker_config(VALID)
    assert problems == []
    assert config.timeout_seconds == 15


def test_an_explicit_timeout_is_kept():
    config, problems = parse_tracker_config({**VALID, "timeout-seconds": 45})
    assert problems == []
    assert config.timeout_seconds == 45


def test_an_absent_block_is_not_a_problem():
    """No tracker configured is a state, not a defect — the overwhelmingly
    common case, and it must produce no noise."""
    for raw in (None, {}):
        config, problems = parse_tracker_config(raw)
        assert config is None
        assert problems == []


# ── required keys ────────────────────────────────────────────────────────────


@pytest.mark.parametrize("key", ["provider", "base-url", "candidate-query",
                                 "credentials", "transitions"])
def test_a_missing_required_key_is_reported_by_name(key):
    config, problems = parse_tracker_config(_without(key))
    assert config is None
    assert any(f"work.tracker.{key}" in p for p in problems), problems


@pytest.mark.parametrize("key", ["email-env", "token-env"])
def test_a_missing_credential_key_is_reported_by_name(key):
    creds = {k: v for k, v in VALID["credentials"].items() if k != key}
    config, problems = parse_tracker_config({**VALID, "credentials": creds})
    assert config is None
    assert any(f"work.tracker.credentials.{key}" in p for p in problems), problems


def test_a_missing_claim_transition_is_reported_by_name():
    config, problems = parse_tracker_config({**VALID, "transitions": {}})
    assert config is None
    assert any("work.tracker.transitions.claim" in p for p in problems), problems


def test_required_keys_are_required_independently():
    """Each key is reported on its own, so a config missing two hears about both
    rather than being told to fix one, rerun, and be told about the next."""
    raw = {"provider": "jira-cloud", "transitions": {"claim": "Start Progress"}}
    config, problems = parse_tracker_config(raw)
    assert config is None
    joined = " ".join(problems)
    for key in ("base-url", "candidate-query", "credentials"):
        assert key in joined, (key, problems)


# ── rejected values ──────────────────────────────────────────────────────────


def test_a_provider_other_than_jira_cloud_is_reported_with_the_value():
    config, problems = parse_tracker_config({**VALID, "provider": "github"})
    assert config is None
    assert any("github" in p for p in problems), problems


@pytest.mark.parametrize("value", [0, -1, "soon", None, True])
def test_a_non_positive_or_non_numeric_timeout_is_reported(value):
    config, problems = parse_tracker_config({**VALID, "timeout-seconds": value})
    assert config is None
    assert any("timeout-seconds" in p for p in problems), problems


@pytest.mark.parametrize("raw", ["a string", 7, ["a", "list"], True])
def test_a_non_mapping_block_is_reported_rather_than_crashing(raw):
    config, problems = parse_tracker_config(raw)
    assert config is None
    assert problems, "a non-mapping block must be reported, not silently ignored"


@pytest.mark.parametrize("key", ["credentials", "transitions"])
def test_a_non_mapping_nested_block_is_reported(key):
    config, problems = parse_tracker_config({**VALID, key: "not a mapping"})
    assert config is None
    assert any(key in p for p in problems), problems


# ── unknown keys, including the one C4 will add ──────────────────────────────


def test_an_unknown_top_level_key_is_reported():
    config, problems = parse_tracker_config({**VALID, "webhook": "https://x.test"})
    assert config is None
    assert any("webhook" in p for p in problems), problems


def test_an_unknown_nested_key_is_reported():
    creds = {**VALID["credentials"], "password": "hunter2"}
    config, problems = parse_tracker_config({**VALID, "credentials": creds})
    assert config is None
    assert any("password" in p for p in problems), problems


def test_strict_is_reported_as_unknown_because_c4_owns_it():
    """`strict` is deliberately not accepted here. The gates that honour it land
    two children later, and a flag that is accepted but only half-honoured tells
    a user their work is gated when it is not."""
    config, problems = parse_tracker_config({**VALID, "strict": True})
    assert config is None
    assert any("strict" in p for p in problems), problems


# ── the two properties ───────────────────────────────────────────────────────


def test_one_problem_yields_no_config_at_all():
    """Fails closed. Every other key here is valid; the config is still None."""
    config, problems = parse_tracker_config({**VALID, "provider": "github"})
    assert problems
    assert config is None, "a config with any problem must not be partially usable"


def test_the_config_holds_no_credential_value():
    """It carries variable *names*. If a future change starts resolving them at
    parse time, this fails — which is the point."""
    import os
    os.environ["TCW_JIRA_API_TOKEN"] = "sentinel-token-value"
    try:
        config, problems = parse_tracker_config(VALID)
        assert problems == []
        assert "sentinel-token-value" not in repr(config)
        for value in vars(config).values():
            assert value != "sentinel-token-value"
    finally:
        del os.environ["TCW_JIRA_API_TOKEN"]


# ── transitions per move ─────────────────────────────────────────────────────


def _with_transitions(**moves):
    return {**VALID, "transitions": {"claim": "Start Progress", **moves}}


def test_a_transition_per_move_parses():
    config, problems = parse_tracker_config(_with_transitions(
        submit="Ready for Review", rework="Back to Progress", complete="Finish",
        discard="Abandon"))
    assert problems == []
    assert config.move_transitions == {
        "submit": "Ready for Review", "rework": "Back to Progress",
        "complete": "Finish", "discard": "Abandon"}
    assert config.claim_transition == "Start Progress"


def test_a_discard_transition_may_be_named_per_resolution_and_may_be_partial():
    """Unlike `statuses.discarded` under strict mode, which must cover every
    resolution, `transitions` is an optional override: it exists to disambiguate,
    so naming only the ambiguous resolution has to be enough."""
    config, problems = parse_tracker_config(
        _with_transitions(discard={"wontfix": "Abandon"}))
    assert problems == []
    assert config.move_transitions["discard"] == {"wontfix": "Abandon"}


def test_transitions_are_absent_by_default():
    config, problems = parse_tracker_config(VALID)
    assert problems == [] and config.move_transitions == {}


@pytest.mark.parametrize("moves, key", [
    ({"submit": 5}, "work.tracker.transitions.submit"),
    ({"complete": ""}, "work.tracker.transitions.complete"),
    ({"discard": {"nonsense": "X"}}, "work.tracker.transitions.discard.nonsense"),
    ({"discard": {"wontfix": 7}}, "work.tracker.transitions.discard.wontfix"),
    ({"discard": {"done": "X"}}, "work.tracker.transitions.discard.done"),
], ids=["not-a-string", "empty", "unknown-resolution", "bad-name", "done-is-not-a-discard"])
def test_a_malformed_transition_is_a_problem(moves, key):
    config, problems = parse_tracker_config(_with_transitions(**moves))
    assert config is None
    matched = [p for p in problems if p.startswith(key)]
    assert matched, problems
    # The key is known now, so the complaint must be about the value. "unknown key"
    # here would mean the move was never wired in and the test passes by accident.
    assert not any("unknown key" in p for p in matched), problems


def test_an_unknown_transition_key_is_still_reported():
    config, problems = parse_tracker_config(_with_transitions(wander="Nowhere"))
    assert config is None
    assert any(p.startswith("work.tracker.transitions.wander") for p in problems), problems


# ── inbox-query ──────────────────────────────────────────────────────────────


def test_an_inbox_query_parses_onto_the_config():
    config, problems = parse_tracker_config({**VALID, "inbox-query": "  status = Triage "})
    assert problems == []
    assert config.inbox_query == "status = Triage"
    assert config.candidate_query == VALID["candidate-query"]


def test_an_absent_inbox_query_is_empty_and_not_a_problem():
    config, problems = parse_tracker_config(VALID)
    assert problems == []
    assert config.inbox_query == ""


@pytest.mark.parametrize("value, kind", [("", "str"), ("   ", "str"), (42, "int")])
def test_a_blank_or_non_string_inbox_query_fails_the_whole_block(value, kind):
    """A blank JQL selects every ticket on the site, so blank is a problem, not absent."""
    config, problems = parse_tracker_config({**VALID, "inbox-query": value})
    assert config is None
    assert problems == [f"work.tracker.inbox-query: expected a non-empty string, got {kind}"]


def test_an_inbox_query_does_not_stand_in_for_the_candidate_query():
    config, problems = parse_tracker_config({**_without("candidate-query"),
                                             "inbox-query": "status = Triage"})
    assert config is None
    assert "work.tracker.candidate-query: required" in problems


def test_a_lone_null_inbox_query_is_reported_as_the_wrong_type_not_as_required():
    config, problems = parse_tracker_config({**VALID, "inbox-query": None})
    assert config is None
    assert problems == ["work.tracker.inbox-query: expected a non-empty string, got NoneType"]


# ── the opt-in exclusivity assertion ─────────────────────────────────────────


def test_no_exclusive_claim_transition_is_the_default_and_not_a_problem():
    """Absent means a claim applies no transition at all, which is the whole point
    of the key being optional: every config that exists today reads this way."""
    config, problems = parse_tracker_config(VALID)
    assert problems == []
    assert config.exclusive_claim_transition == ""


def test_an_exclusive_claim_transition_is_kept():
    config, problems = parse_tracker_config(
        {**VALID, "exclusive-claim-transition": "Start Progress"})
    assert problems == []
    assert config.exclusive_claim_transition == "Start Progress"
    # It is not `transitions.claim`, and setting one must not set the other: they
    # answer different questions, and running them together is what the key exists
    # to stop.
    assert config.claim_transition == "Start Progress"
    config, _problems = parse_tracker_config(
        {**VALID, "exclusive-claim-transition": "Take It"})
    assert (config.exclusive_claim_transition, config.claim_transition) == (
        "Take It", "Start Progress")


@pytest.mark.parametrize("value", [None, "", "   ", 7, True])
def test_a_present_but_unusable_exclusive_claim_transition_is_reported(value):
    """Present-and-wrong is a mistake; absent is a choice. Only the first is a
    problem, and it fails the whole block closed like every other one."""
    config, problems = parse_tracker_config(
        {**VALID, "exclusive-claim-transition": value})
    assert config is None
    assert any("exclusive-claim-transition" in p for p in problems), problems


def test_a_misspelled_exclusive_claim_transition_is_an_unknown_key():
    """An unknown key under work.tracker takes the whole tracker surface down with
    it, so the misspelling has to be named rather than ignored."""
    config, problems = parse_tracker_config(
        {**VALID, "exclusive-claim-transitions": "Start Progress"})
    assert config is None
    assert ["work.tracker.exclusive-claim-transitions: unknown key"] == problems
