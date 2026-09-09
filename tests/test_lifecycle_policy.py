"""`parse_lifecycle_policy` — the pure parser behind both `tcw validate` and the
FS adapter.

Pure on purpose: two implementations of "what is a legal policy" would drift, and
drift between a tool and its documentation is the thing this initiative exists to
remove. `tcw validate` reports the problems; the adapter discards them, because
reading a policy must not break `tcw work list` over a mistyped key.

Every rejection is tested for the *message*, not just the count. An unparseable
config whose error does not name the offending key is barely better than no
check at all.
"""
import re

from tcw.store.base import (
    DEFAULT_HOOK_TIMEOUT, LIFECYCLE_STEPS, LIFECYCLE_STEPS_BY_ID, STAGE_IDS,
    TRANSITION_IDS, WORK_ARTIFACTS, Binding, parse_lifecycle_policy,
)


def parse(raw):
    return parse_lifecycle_policy(raw)


def problems_for(raw) -> list[str]:
    return parse_lifecycle_policy(raw)[1]


def only_problem(raw) -> str:
    problems = problems_for(raw)
    assert len(problems) == 1, problems
    return problems[0]


# ── the id sets are public API ───────────────────────────────────────────────

def test_stage_ids_match_the_epic_contract():
    assert STAGE_IDS == ("inbox", "request", "spec", "plan", "implement",
                         "verify", "postmortem")


def test_transition_ids_match_the_epic_contract():
    assert TRANSITION_IDS == ("start", "submit", "complete", "rework", "discard",
                              "auto-delete")


def test_produces_is_a_tuple_of_artifact_names():
    """One artifact per stage was never true — `inbox` produces none and `verify`
    produces one of two — so the field holds names, not a sentence."""
    for step in LIFECYCLE_STEPS:
        assert isinstance(step.produces, tuple), step.id
        assert set(step.produces) <= set(WORK_ARTIFACTS), step.id
    assert LIFECYCLE_STEPS_BY_ID["verify"].produces == ("refined-outcome", "rework")
    assert LIFECYCLE_STEPS_BY_ID["inbox"].produces == ()


def test_every_artifact_but_intake_is_produced_by_a_stage():
    """`intake` is raw input — no stage writes it, which is why `tcw work
    scaffold intake` has no stage legality row to look up."""
    produced = {n for s in LIFECYCLE_STEPS for n in s.produces}
    assert produced == set(WORK_ARTIFACTS) - {"intake"}


def test_produces_and_produces_note_describe_the_same_artifacts():
    """Two fields carrying one fact drift silently. `produces_note` is prose and
    `produces` is machine-readable; the filenames in the prose must be exactly
    the tuple's, `inbox`'s empty pair included."""
    for step in LIFECYCLE_STEPS:
        in_note = set(re.findall(r"\b([a-z][a-z0-9-]*\.md)\b", step.produces_note))
        assert in_note == {f"{n}.md" for n in step.produces}, step.id


def test_every_transition_id_except_discard_is_a_cli_verb():
    """Two transitions have no verb spelled the same way, for different reasons.

    `discard` has no verb at all — it is reached as
    `complete --resolution <not-done>`, because the resolution picks the
    destination. Bindings key on the *move*, so the two resolutions of `complete`
    fire different hooks.

    `auto-delete` has one under a different name. It normally runs as part of a
    resolving transition rather than being typed, and the manual entry point that
    finishes an interrupted one is `tcw work delete <slug>` — "auto-delete" reads
    wrong as something a person types, while the config key it binds must say
    that the deletion is automatic.

    Pinned because a future reader will otherwise assume the id set and the verb
    set are the same thing."""
    from tcw.work.cli import SUBCOMMANDS
    assert set(TRANSITION_IDS) - SUBCOMMANDS == {"discard", "auto-delete"}
    assert "delete" in SUBCOMMANDS


# ── valid shapes ─────────────────────────────────────────────────────────────

def test_an_absent_policy_is_empty_and_clean():
    policy, problems = parse(None)
    assert problems == []
    assert policy.stages == {} and policy.transitions == {}
    assert policy.timeout == DEFAULT_HOOK_TIMEOUT


def test_a_stage_binding_parses():
    policy, problems = parse({"stages": {"spec": [{"skill": "superpowers:brainstorming"}]}})
    assert problems == []
    assert policy.stage("spec") == [Binding("skill", "superpowers:brainstorming")]
    assert policy.stage("spec")[0].kind == "skill"
    assert policy.stage("spec")[0].ref == "superpowers:brainstorming"


def test_a_command_binding_parses():
    policy, problems = parse({"transitions": {"complete": {"pre": [{"command": "pytest -q"}]}}})
    assert problems == []
    assert policy.transition("complete").pre == [Binding("command", "pytest -q")]
    assert policy.transition("complete").pre[0].kind == "command"


def test_declaration_order_is_significant_and_preserved():
    policy, problems = parse({"stages": {"plan": [
        {"skill": "a"}, {"command": "b"}, {"skill": "c"},
    ]}})
    assert problems == []
    assert [b.ref for b in policy.stage("plan")] == ["a", "b", "c"]


def test_pre_and_post_are_independent():
    policy, problems = parse({"transitions": {"start": {
        "pre": [{"command": "check"}],
        "post": [{"command": "notify"}],
    }}})
    assert problems == []
    assert policy.transition("start").pre[0].ref == "check"
    assert policy.transition("start").post[0].ref == "notify"


def test_an_unconfigured_id_reads_as_empty_rather_than_missing():
    policy, _ = parse({"stages": {"spec": [{"skill": "x"}]}})
    assert policy.stage("implement") == []
    assert policy.transition("complete").pre == []
    assert policy.transition("complete").post == []


def test_a_custom_timeout_parses():
    policy, problems = parse({"timeout": 30})
    assert problems == [] and policy.timeout == 30


def test_binding_values_are_stripped():
    policy, _ = parse({"stages": {"spec": [{"skill": "  a:b  "}]}})
    assert policy.stage("spec")[0].ref == "a:b"


# ── the rejections, each naming its offender ─────────────────────────────────

def test_a_non_mapping_policy_is_rejected():
    assert "expected a mapping" in only_problem(["not", "a", "mapping"])


def test_an_unknown_top_level_key_is_rejected():
    assert "stagez" in only_problem({"stagez": {}})


def test_an_unknown_stage_id_is_rejected_and_names_the_legal_set():
    p = only_problem({"stages": {"brainstorm": [{"skill": "x"}]}})
    assert "brainstorm" in p and "postmortem" in p


def test_an_unknown_transition_id_is_rejected():
    p = only_problem({"transitions": {"finish": {"pre": []}}})
    assert "finish" in p and "rework" in p


def test_a_non_mapping_stages_value_is_rejected():
    assert "work.lifecycle.stages" in only_problem({"stages": ["spec"]})


def test_a_non_mapping_transitions_value_is_rejected():
    assert "work.lifecycle.transitions" in only_problem({"transitions": ["start"]})


def test_a_stage_value_that_is_not_a_list_is_rejected():
    p = only_problem({"stages": {"spec": {"skill": "x"}}})
    assert "stages.spec" in p and "list" in p


def test_a_transition_value_that_is_not_a_mapping_is_rejected():
    p = only_problem({"transitions": {"start": [{"command": "x"}]}})
    assert "transitions.start" in p and "pre" in p


def test_an_unknown_transition_phase_is_rejected():
    p = problems_for({"transitions": {"start": {"during": [{"command": "x"}]}}})
    assert any("during" in x for x in p)


def test_a_non_list_pre_is_rejected():
    p = only_problem({"transitions": {"start": {"pre": {"command": "x"}}}})
    assert "transitions.start.pre" in p


def test_a_binding_that_is_not_a_mapping_is_rejected():
    p = only_problem({"stages": {"spec": ["superpowers:brainstorming"]}})
    assert "stages.spec[0]" in p and "mapping" in p


def test_a_bare_string_binding_is_never_inferred():
    """The explicit-declaration rule. Guessing whether a plain string meant a
    skill or a shell command is a whole class of bug bought for nothing."""
    policy, problems = parse({"stages": {"spec": ["pytest -q"]}})
    assert problems and policy.stage("spec") == []


def test_a_binding_with_neither_key_is_rejected():
    p = only_problem({"stages": {"spec": [{}]}})
    assert "declares no kind" in p


def test_a_binding_with_both_keys_is_rejected():
    p = only_problem({"stages": {"spec": [{"skill": "a", "command": "b"}]}})
    assert "declares skill and command" in p and "choose one" in p


def test_an_unknown_binding_key_is_rejected():
    p = only_problem({"stages": {"spec": [{"skil": "typo"}]}})
    assert "skil" in p


def test_a_blank_binding_value_is_rejected():
    p = only_problem({"stages": {"spec": [{"skill": "   "}]}})
    assert "non-blank" in p


def test_a_non_string_binding_value_is_rejected():
    p = only_problem({"stages": {"spec": [{"command": 42}]}})
    assert "non-blank string" in p


def test_a_duplicate_ref_within_one_id_is_rejected():
    p = only_problem({"stages": {"spec": [{"skill": "a"}, {"skill": "a"}]}})
    assert "duplicate" in p and "a" in p


def test_the_same_ref_under_two_different_ids_is_fine():
    """Duplication is rejected *within* an id, not across the policy — running
    the same check at two stages is a legitimate configuration."""
    policy, problems = parse({"stages": {"spec": [{"skill": "a"}],
                                         "plan": [{"skill": "a"}]}})
    assert problems == []
    assert policy.stage("spec") == policy.stage("plan")


def test_a_non_positive_timeout_is_rejected():
    assert "positive integer" in only_problem({"timeout": 0})
    assert "positive integer" in only_problem({"timeout": -5})
    assert "positive integer" in only_problem({"timeout": "30"})


def test_a_boolean_timeout_is_rejected():
    """`True` is an `int` in Python; without an explicit check `timeout: true`
    would silently become a one-second timeout."""
    assert "positive integer" in only_problem({"timeout": True})


# ── partial parsing ──────────────────────────────────────────────────────────

def test_one_bad_binding_does_not_discard_its_siblings():
    """The adapter discards problems and keeps the policy, so a single typo must
    not silently empty a whole stage's configuration."""
    policy, problems = parse({"stages": {"spec": [
        {"skill": "good"}, {"nonsense": 1}, {"command": "also-good"},
    ]}})
    assert len(problems) == 1
    assert [b.ref for b in policy.stage("spec")] == ["good", "also-good"]


def test_a_bad_stage_does_not_discard_a_good_transition():
    policy, problems = parse({
        "stages": {"nope": [{"skill": "x"}]},
        "transitions": {"start": {"pre": [{"command": "ok"}]}},
    })
    assert len(problems) == 1
    assert policy.transition("start").pre[0].ref == "ok"


def test_every_problem_is_reported_not_just_the_first():
    problems = problems_for({"stages": {"spec": [{}], "nope": []},
                             "transitions": {"alsonope": {}},
                             "timeout": -1})
    assert len(problems) == 4


# ── the FS adapter and tcw validate ──────────────────────────────────────────

import subprocess
from pathlib import Path

import yaml

from tcw.store.fs import FsWorkStore, init


def node(tmp_path: Path, name: str = "repo") -> Path:
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root, name.lower())
    return root


def write_lifecycle(root: Path, lifecycle) -> None:
    p = root / "tcw-config.yaml"
    cfg = yaml.safe_load(p.read_text()) or {}
    cfg.setdefault("work", {})["lifecycle"] = lifecycle
    p.write_text(yaml.safe_dump(cfg, sort_keys=False))


def test_a_node_with_no_lifecycle_config_has_an_empty_policy(tmp_path):
    policy = FsWorkStore.open(node(tmp_path)).lifecycle_policy()
    assert policy.stages == {} and policy.transitions == {}
    assert policy.timeout == DEFAULT_HOOK_TIMEOUT


def test_the_adapter_round_trips_a_policy_in_declared_order(tmp_path):
    root = node(tmp_path)
    write_lifecycle(root, {
        "stages": {"spec": [{"skill": "z"}, {"command": "a"}]},
        "transitions": {"complete": {"pre": [{"command": "pytest -q"}]}},
    })
    policy = FsWorkStore.open(root).lifecycle_policy()
    assert [b.ref for b in policy.stage("spec")] == ["z", "a"]
    assert policy.transition("complete").pre[0].ref == "pytest -q"


def test_a_malformed_policy_does_not_break_reading_the_board(tmp_path):
    """Reading is not validating. A mistyped key must not take `tcw work list`
    down — `tcw validate` is where it surfaces."""
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Task", created="2026-01-01")
    write_lifecycle(root, {"stages": {"nonsense": ["bare string"]}})

    st = FsWorkStore.open(root)
    assert [i.slug for i in st.board()] == [item.slug]
    assert st.lifecycle_policy().stages == {}          # degraded, not raised


def test_validate_reports_a_malformed_policy(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    write_lifecycle(root, {"stages": {"brainstorm": [{"skill": "x"}]}})
    monkeypatch.chdir(root)

    assert main(["validate"]) == 1
    err = capsys.readouterr().err
    assert "tcw-config.yaml" in err and "brainstorm" in err


def test_validate_passes_on_a_valid_policy(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    write_lifecycle(root, {"stages": {"spec": [{"skill": "superpowers:brainstorming"}]}})
    monkeypatch.chdir(root)
    assert main(["validate"]) == 0


def test_validate_leaves_unrelated_config_byte_identical(tmp_path, monkeypatch):
    """Validation reads; it must never rewrite or reorder the sentinel."""
    from tcw.cli import main
    root = node(tmp_path)
    p = root / "tcw-config.yaml"
    cfg = yaml.safe_load(p.read_text()) or {}
    cfg["zzz-last"] = {"deliberately": "unsorted"}
    cfg["aaa-first"] = ["a", "b"]
    cfg.setdefault("work", {})["tags"] = ["cli", "docs"]
    cfg["work"]["lifecycle"] = {"stages": {"plan": [{"command": "true"}]}}
    p.write_text(yaml.safe_dump(cfg, sort_keys=False))
    before = p.read_bytes()

    monkeypatch.chdir(root)
    assert main(["validate"]) == 0
    assert p.read_bytes() == before


def test_the_policy_coexists_with_the_tag_registry_and_commit_keys(tmp_path):
    """All four live under `work:`; none may read as replacing another."""
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    st.register_tags(["bug"])
    p = root / "tcw-config.yaml"
    cfg = yaml.safe_load(p.read_text())
    cfg["work"].update({"auto-commit-transitions": False, "trunk-branch": "main",
                        "lifecycle": {"stages": {"spec": [{"skill": "x"}]}}})
    p.write_text(yaml.safe_dump(cfg, sort_keys=False))

    st = FsWorkStore.open(root)
    assert st.registered_tags() == ["bug"]
    assert st.auto_commit_transitions() is False
    assert st.trunk_branch() == "main"
    assert st.lifecycle_policy().stage("spec")[0].ref == "x"
