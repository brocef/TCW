"""Resolving bindings to text: conditions, kinds, ordering, and plan mode."""

import json
import os
from pathlib import Path

import pytest
import yaml

from tcw.store.base import (
    STAGE_IDS, Artifact, Binding, Condition, LifecyclePolicy, StageBindings,
    WorkItem, parse_lifecycle_policy,
)
from tcw.work.projection import WORK_ITEM_SCHEMA
from tcw.work.resolve import (
    Builtins, ResolveError, hook_payload, load_builtins, resolve_artifact,
    resolve_prompts, select, substitute_documentation,
)

ENV = dict(os.environ)


def policy_of(raw: dict) -> LifecyclePolicy:
    policy, problems = parse_lifecycle_policy(raw)
    assert problems == [], problems
    return policy


def item(**kw) -> WorkItem:
    base = dict(slug="s", title="T", status="backlog")
    base.update(kw)
    return WorkItem(**base)


# ── conditions, in every role ────────────────────────────────────────────────


@pytest.mark.parametrize("when, tags, kind, expected", [
    ({"tags": ["bug"]},                       ["bug"],        "", True),
    ({"tags": ["bug"]},                       ["feature"],    "", False),
    ({"tags": ["bug", "regression"]},         ["regression"], "", True),   # any-of
    ({"not_tags": ["spike"]},                 ["bug"],        "", True),
    ({"not_tags": ["spike"]},                 ["spike"],      "", False),
    ({"tags": ["bug"], "not_tags": ["spike"]}, ["bug"],       "", True),   # AND
    ({"tags": ["bug"], "not_tags": ["spike"]}, ["bug", "spike"], "", False),
    ({"type": "epic"},                        [],         "epic", True),
    ({"type": "epic"},                        [],             "", False),
    ({"type": ""},                            [],             "", True),   # non-epic
    ({"type": ""},                            [],         "epic", False),
    ({"tags": ["bug"], "type": "epic"},       ["bug"],    "epic", True),
    ({"tags": ["bug"], "type": "epic"},       ["bug"],        "", False),
])
def test_the_when_truth_table(when, tags, kind, expected):
    policy = policy_of({"stages": {"spec": {"prompt": [
        {"blob": "matched", "when": when}]}}})
    res = resolve_prompts(policy, "spec", item(tags=tags, type=kind),
                          Path("."), Builtins(), env=ENV)
    assert (res.text == "matched") is expected


def test_a_conditional_binding_never_matches_without_an_item():
    """Resolution can be called with no item — an artifact template for one that
    does not exist yet. Treating that as a match would fire every conditional
    binding at the moment nothing is known."""
    policy = policy_of({"stages": {"spec": {"prompt": [
        {"blob": "conditional", "when": {"tags": ["bug"]}},
        {"blob": "unconditional"}]}}})
    res = resolve_prompts(policy, "spec", None, Path("."), Builtins(), env=ENV)
    assert res.text == "unconditional"


def test_conditions_select_transition_checks_too():
    """The third role. A matcher unit-tested but never wired into checks is the
    escape this exists to close — `select` is what the check path calls."""
    policy = policy_of({"transitions": {"complete": {"pre": [
        {"command": "for-bugs", "when": {"tags": ["bug"]}},
        {"command": "always"}]}}})
    pre = policy.transition("complete").pre
    assert [b.ref for b in select(pre, item(tags=["bug"]))] == ["for-bugs", "always"]
    assert [b.ref for b in select(pre, item(tags=["feature"]))] == ["always"]
    assert [b.ref for b in select(pre, None)] == ["always"]


def test_conditions_select_artifact_bindings():
    policy = policy_of({"artifacts": {"spec": [
        {"blob": "bug template", "when": {"tags": ["bug"]}},
        {"blob": "default template"}]}})
    assert resolve_artifact(policy, "spec", item(tags=["bug"]), Path("."),
                            Builtins(), env=ENV).text == "bug template"
    assert resolve_artifact(policy, "spec", item(tags=["x"]), Path("."),
                            Builtins(), env=ENV).text == "default template"


# ── ordering: all-match vs first-match ───────────────────────────────────────


def test_prompts_concatenate_every_match_in_declaration_order():
    policy = policy_of({"stages": {"spec": {"prompt": [
        {"blob": "first"}, {"blob": "second"}, {"blob": "third"}]}}})
    res = resolve_prompts(policy, "spec", item(), Path("."), Builtins(), env=ENV)
    assert res.text == "first\n\nsecond\n\nthird"


def test_concatenation_is_exact():
    """`--directive` and the corpus baselines are byte-level contracts, so
    "concatenate" has to mean something specific."""
    policy = policy_of({"stages": {"spec": {"prompt": [
        {"blob": "one   \n\n"}, {"blob": "two\n"}]}}})
    res = resolve_prompts(policy, "spec", item(), Path("."), Builtins(), env=ENV)
    assert res.text == "one\n\ntwo"


def test_an_artifact_stops_at_the_first_match(tmp_path):
    """First-match-*wins*, not first-match-is-returned: a `generate` below the
    winner must not run."""
    sentinel = tmp_path / "ran"
    # `_check_artifact_list` rejects this order in a config — an entry after an
    # unconditional one can never run. Built directly, because the point here is
    # the resolver's behaviour if it ever did.
    policy = LifecyclePolicy(artifacts={"spec": [
        Binding("blob", "the winner"),
        Binding("generate", f"touch {sentinel}"),
    ]})
    res = resolve_artifact(policy, "spec", item(), tmp_path, Builtins(), env=ENV)
    assert res.text == "the winner"
    assert not sentinel.exists()


# ── kinds ────────────────────────────────────────────────────────────────────


def test_a_file_binding_reads_the_file_verbatim(tmp_path):
    (tmp_path / "guide.md").write_text("# Guide\n\nread me\n")
    policy = policy_of({"stages": {"spec": {"prompt": [{"file": "guide.md"}]}}})
    res = resolve_prompts(policy, "spec", item(), tmp_path, Builtins(), env=ENV)
    assert res.text == "# Guide\n\nread me"


def test_a_file_binding_escaping_the_node_root_is_refused(tmp_path):
    outside = tmp_path.parent / "outside.md"
    outside.write_text("secrets\n")
    node = tmp_path / "node"
    node.mkdir()
    policy = LifecyclePolicy(stages={"spec": StageBindings(
        prompt=[Binding("file", "../outside.md")])})
    with pytest.raises(ResolveError, match="outside the node root"):
        resolve_prompts(policy, "spec", item(), node, Builtins(), env=ENV)


def test_a_symlink_out_of_the_node_root_is_refused(tmp_path):
    """A lexical `..` check passes this and reads the file anyway."""
    outside = tmp_path / "outside.md"
    outside.write_text("secrets\n")
    node = tmp_path / "node"
    node.mkdir()
    (node / "link.md").symlink_to(outside)
    policy = LifecyclePolicy(stages={"spec": StageBindings(
        prompt=[Binding("file", "link.md")])})
    with pytest.raises(ResolveError, match="outside the node root"):
        resolve_prompts(policy, "spec", item(), node, Builtins(), env=ENV)


def test_a_file_that_vanished_after_validation_names_itself(tmp_path):
    policy = LifecyclePolicy(stages={"spec": StageBindings(
        prompt=[Binding("file", "gone.md")])})
    with pytest.raises(ResolveError, match="no longer exists"):
        resolve_prompts(policy, "spec", item(), tmp_path, Builtins(), env=ENV)


def test_builtin_resolves_from_the_stage_registry():
    policy = policy_of({"stages": {"spec": {"prompt": [
        {"builtin": True}, {"blob": "and this node's addition"}]}}})
    res = resolve_prompts(policy, "spec", item(), Path("."),
                          Builtins(stage_prompts={"spec": "TCW's own words"}),
                          env=ENV)
    assert res.text == "TCW's own words\n\nand this node's addition"


def test_builtin_with_an_empty_registry_resolves_to_nothing(tmp_path):
    """The state C3 ships in, before C5 and C6 fill the registries. Legal, not a
    failure — including a prompt list that is *only* a builtin."""
    policy = policy_of({"stages": {"spec": {"prompt": [{"builtin": True}]}}})
    res = resolve_prompts(policy, "spec", item(), tmp_path, Builtins(), env=ENV)
    assert res.text == ""
    assert res.plan[0].matched is True


def test_the_two_registries_do_not_collide():
    """`spec` is both a stage id and an artifact name; one map could not hold
    both at once."""
    b = Builtins(stage_prompts={"spec": "how to write a spec"},
                 artifact_templates={"spec": "# Spec\n"})
    pol = policy_of({"stages": {"spec": {"prompt": [{"builtin": True}]}},
                     "artifacts": {"spec": [{"builtin": True}]}})
    assert resolve_prompts(pol, "spec", item(), Path("."), b,
                           env=ENV).text == "how to write a spec"
    # Verbatim: an artifact template's trailing newline is part of the template.
    assert resolve_artifact(pol, "spec", item(), Path("."), b,
                            env=ENV).text == "# Spec\n"


# ── generate ─────────────────────────────────────────────────────────────────


def test_a_generate_hook_receives_a_schema_valid_item_and_its_own_metadata(tmp_path):
    jsonschema = pytest.importorskip("jsonschema")
    policy = policy_of({"stages": {"spec": {"prompt": [{"generate": "cat"}]}}})
    res = resolve_prompts(policy, "spec", item(slug="the-slug", body="req"),
                          tmp_path, Builtins(),
                          artifacts=[Artifact("spec", True)], env=ENV)
    payload = json.loads(res.text)
    # Validated against the published schema, not merely checked for a slug: a
    # payload the hook author cannot rely on is the thing this criterion is for.
    jsonschema.validate(payload["item"], WORK_ITEM_SCHEMA)
    assert payload["item"]["slug"] == "the-slug"
    assert payload["hook"] == {"role": "prompt", "kind": "generate",
                               "id": "spec", "phase": "prompt",
                               "body_truncated": False}


def test_a_generate_hook_gets_its_metadata_in_the_environment(tmp_path):
    policy = policy_of({"stages": {"spec": {"prompt": [
        {"generate": 'printf "%s/%s" "$TCW_HOOK_ROLE" "$TCW_HOOK_ID"'}]}}})
    res = resolve_prompts(policy, "spec", item(), tmp_path, Builtins(), env=ENV)
    assert res.text == "prompt/spec"


def test_the_body_cap_is_bytes_cut_at_a_character_boundary():
    jsonschema = pytest.importorskip("jsonschema")
    cap = 1000
    # Three-byte characters: a cap on *characters* would let 3000 bytes through,
    # and a blind byte slice at 1000 would cut one in half — 1000 is not a
    # multiple of 3, so this input catches both mistakes.
    text, _ = hook_payload(item(body="好" * 2000), [], "prompt", "generate",
                           "spec", "prompt", cap)
    payload = json.loads(text)                     # invalid UTF-8 would fail here
    encoded = payload["item"]["body"].encode("utf-8")
    assert len(encoded) <= cap
    assert encoded == "好".encode() * (cap // 3)
    assert payload["hook"]["body_truncated"] is True
    jsonschema.validate(payload["item"], WORK_ITEM_SCHEMA)


def test_the_body_cap_is_not_the_output_cap():
    """Two limits, two reasons. A node tightening `output-cap` to keep prompts
    short must not silently start truncating the request its hooks read."""
    from tcw.work.resolve import BODY_CAP
    policy = policy_of({"output-cap": 512})
    assert policy.output_cap == 512
    assert BODY_CAP == 64 * 1024


def test_a_body_over_the_cap_reaches_a_real_hook_truncated(tmp_path):
    # The hook *reports* rather than echoing: `cat` would write the whole
    # payload back, and a 64 KiB body echoed through a 64 KiB output cap fails
    # the cap — correctly, but it would be testing the wrong thing.
    hook = ("python3 -c \"import sys,json; d=json.load(sys.stdin); "
            "print(len(d['item']['body']), d['hook']['body_truncated'])\"")
    policy = policy_of({"stages": {"spec": {"prompt": [{"generate": hook}]}}})
    res = resolve_prompts(policy, "spec", item(body="x" * (70 * 1024)), tmp_path,
                          Builtins(), env=ENV)
    assert res.text == f"{64 * 1024} True"


def test_a_small_body_is_not_truncated(tmp_path):
    policy = policy_of({"stages": {"spec": {"prompt": [{"generate": "cat"}]}}})
    res = resolve_prompts(policy, "spec", item(body="short"), tmp_path,
                          Builtins(), env=ENV)
    payload = json.loads(res.text)
    assert payload["item"]["body"] == "short"
    assert payload["hook"]["body_truncated"] is False


def test_a_failing_generate_contributes_nothing_and_names_the_exit(tmp_path):
    # The command is echoed in the message, so the leaked-output check uses a
    # string the command line does not contain.
    script = tmp_path / "half.sh"
    script.write_text("#!/bin/sh\nprintf 'LEAKED'\nexit 4\n")
    script.chmod(0o755)
    policy = policy_of({"stages": {"spec": {"prompt": [
        {"blob": "kept"}, {"generate": str(script)}]}}})
    with pytest.raises(ResolveError) as e:
        resolve_prompts(policy, "spec", item(), tmp_path, Builtins(), env=ENV)
    assert "exit 4" in str(e.value)
    assert "LEAKED" not in str(e.value)


# ── plan mode ────────────────────────────────────────────────────────────────


def test_plan_mode_executes_nothing_and_still_plans(tmp_path):
    """`--no-exec` is a branch of the same traversal, so the plan cannot disagree
    with what would really happen — deriving it from a real run is a report, not
    a dry run."""
    sentinel = tmp_path / "ran"
    (tmp_path / "guide.md").write_text("read me\n")
    policy = policy_of({"stages": {"spec": {"prompt": [
        {"blob": "static"},
        {"file": "guide.md"},
        {"generate": f"touch {sentinel}; printf 'generated'"}]}}})

    res = resolve_prompts(policy, "spec", item(), tmp_path, Builtins(),
                          env=ENV, execute=False)
    assert not sentinel.exists()
    assert "generated" not in res.text
    assert "read me" not in res.text            # a file read is observable too
    assert res.text == "static"
    assert [(p.kind, p.ref, p.matched, p.executed) for p in res.plan] == [
        ("blob", "static", True, False),
        ("file", "guide.md", True, False),
        ("generate", f"touch {sentinel}; printf 'generated'", True, False),
    ]

    # The same traversal with execution on reaches all three.
    real = resolve_prompts(policy, "spec", item(), tmp_path, Builtins(), env=ENV)
    assert sentinel.exists()
    assert real.text == "static\n\nread me\n\ngenerated"


def test_the_plan_records_a_binding_that_did_not_match(tmp_path):
    policy = policy_of({"stages": {"spec": {"prompt": [
        {"blob": "for bugs", "when": {"tags": ["bug"]}},
        {"blob": "for all"}]}}})
    res = resolve_prompts(policy, "spec", item(tags=["feature"]), tmp_path,
                          Builtins(), env=ENV)
    assert [(p.ref, p.matched) for p in res.plan] == [
        ("for bugs", False), ("for all", True)]


# ── the floor: a stage the node never configured ─────────────────────────────


@pytest.mark.parametrize("sid", sorted(set(STAGE_IDS) - {"inbox"}))
def test_an_unconfigured_stage_resolves_to_the_builtin(sid, tmp_path):
    """The floor. A node that configures nothing is the common case — TCW's own
    repo has no `work.lifecycle` key at all — and it gets TCW's instructions."""
    b = load_builtins()
    res = resolve_prompts(LifecyclePolicy(), sid, item(), tmp_path, b, env=ENV)
    # `_join` rstrips each part, and a `{{tcw:documentation}}` span with nothing
    # configured resolves to its own inner text; the result is otherwise
    # byte-for-byte the file's.
    assert res.text == substitute_documentation(b.stage_prompts[sid], ()).rstrip()
    assert [(p.kind, p.matched, p.executed) for p in res.plan] == [
        ("builtin", True, False)]


def test_the_floor_is_a_real_plan_entry(tmp_path):
    """`--no-exec` prints `res.plan`; a floor that resolved text while
    contributing no entry would make the dry run understate the real one."""
    res = resolve_prompts(LifecyclePolicy(), "spec", item(), tmp_path,
                          load_builtins(), env=ENV, execute=False)
    assert [p.kind for p in res.plan] == ["builtin"]


def test_a_configured_stage_wins_outright(tmp_path):
    """A floor, not a ceiling — and not an addition either. The built-in appears
    only where the node asks for it by name."""
    policy = policy_of({"stages": {"spec": {"prompt": [{"blob": "X"}]}}})
    res = resolve_prompts(policy, "spec", item(), tmp_path, load_builtins(),
                          env=ENV)
    assert res.text == "X"


def test_builtin_composes_with_the_nodes_own_text(tmp_path):
    """Declaration order, one blank line between — `_join`'s contract, asserted
    against the real shipped text rather than a fabricated registry."""
    b = load_builtins()
    policy = policy_of({"stages": {"spec": {"prompt": [
        {"builtin": True}, {"blob": "X"}]}}})
    res = resolve_prompts(policy, "spec", item(), tmp_path, b, env=ENV)
    assert res.text == b.stage_prompts["spec"].rstrip() + "\n\n" + "X"


def test_a_stage_whose_only_binding_does_not_match_stays_empty(tmp_path):
    """The boundary the floor must not cross: the condition is on the binding
    *list*, not on the resolved text. This node configured `spec`; it does not
    get the built-in back because its one binding sat out."""
    policy = policy_of({"stages": {"spec": {"prompt": [
        {"blob": "for bugs", "when": {"tags": ["bug"]}}]}}})
    res = resolve_prompts(policy, "spec", item(tags=["feature"]), tmp_path,
                          load_builtins(), env=ENV)
    assert res.text == ""
