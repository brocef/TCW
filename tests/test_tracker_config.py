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


def test_the_transition_keys_c3_adds_are_not_accepted_yet():
    """Forward-incompatible on purpose. C3 adds submit/rework/complete mappings;
    until then, accepting them silently would mean not doing what a user asked."""
    transitions = {**VALID["transitions"], "complete": "Done"}
    config, problems = parse_tracker_config({**VALID, "transitions": transitions})
    assert config is None
    assert any("complete" in p for p in problems), problems


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
