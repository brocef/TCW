"""`resolve_procedure` — the stage-prompt resolver, reached from a procedure id."""

import json
import os
from pathlib import Path

from tcw.store.base import LifecyclePolicy, WorkItem, parse_procedures
from tcw.work.resolve import Builtins, resolve_procedure

ENV = dict(os.environ)
BUILTINS = Builtins(procedures={"search": "DEFAULT"})


def policy_of(raw: dict) -> LifecyclePolicy:
    procedures, problems = parse_procedures(raw)
    assert problems == [], problems
    return LifecyclePolicy(procedures=procedures)


def item(**kw) -> WorkItem:
    return WorkItem(**{"slug": "s", "title": "T", "status": "backlog", **kw})


def test_nothing_configured_is_the_default():
    res = resolve_procedure(LifecyclePolicy(), "search", None, Path("."), BUILTINS,
                            env=ENV)
    assert res.text == "DEFAULT"


def test_every_match_composes_in_declaration_order():
    policy = policy_of({"search": [{"blob": "A"}, {"builtin": True}, {"blob": "B"}]})
    res = resolve_procedure(policy, "search", None, Path("."), BUILTINS, env=ENV)
    assert res.text == "A\n\nDEFAULT\n\nB"


def test_a_configured_procedure_replaces_the_default():
    policy = policy_of({"search": [{"blob": "A"}]})
    res = resolve_procedure(policy, "search", None, Path("."), BUILTINS, env=ENV)
    assert res.text == "A"


def test_another_procedures_bindings_do_not_leak_in():
    policy = policy_of({"delegation": [{"blob": "A"}]})
    res = resolve_procedure(policy, "search", None, Path("."), BUILTINS, env=ENV)
    assert res.text == "DEFAULT"


def test_a_condition_matches_the_item_and_never_no_item():
    policy = policy_of({"search": [{"blob": "BUG", "when": {"tags": ["bug"]}}]})
    for subject, expected in ((item(tags=["bug"]), "BUG"),
                              (item(tags=["feature"]), ""), (None, "")):
        res = resolve_procedure(policy, "search", subject, Path("."), BUILTINS,
                                env=ENV)
        assert res.text == expected, subject
    assert [e.matched for e in res.plan] == [False]


def test_a_generate_hook_is_told_it_serves_a_procedure(tmp_path):
    policy = policy_of({"search": [
        {"generate": 'printf "%s/%s/%s " "$TCW_HOOK_ROLE" "$TCW_HOOK_ID" '
                     '"$TCW_HOOK_PHASE"; cat'}]})
    res = resolve_procedure(policy, "search", item(slug="the-slug"), tmp_path,
                            BUILTINS, env=ENV)
    env_part, stdin_part = res.text.split(" ", 1)
    assert env_part == "procedure/search/prompt"
    payload = json.loads(stdin_part)
    assert payload["item"]["slug"] == "the-slug"
    assert payload["hook"]["role"] == "procedure"
    assert payload["hook"]["id"] == "search"


def test_plan_mode_runs_nothing(tmp_path):
    policy = policy_of({"search": [{"generate": "touch ran"},
                                   {"blob": "X", "when": {"tags": ["bug"]}}]})
    res = resolve_procedure(policy, "search", None, tmp_path, BUILTINS, env=ENV,
                            execute=False)
    assert not (tmp_path / "ran").exists()
    assert [(e.kind, e.matched, e.executed) for e in res.plan] == [
        ("generate", True, False), ("blob", False, False)]
