"""The `work.*` configuration shape (TCW-69 Design 8; AC 6, 16)."""

from pathlib import Path

import pytest
import yaml

from tcw.work.config import (
    MIGRATION_GUIDE, Binding, ConfigProblem, When, parse_work_config,
)

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "tcw-config-2.8.yaml"


def problems_of(work):
    config, problems = parse_work_config(work)
    assert all(isinstance(p, ConfigProblem) for p in problems)
    return problems


def paths(problems):
    return [p.key_path for p in problems]


def test_an_empty_section_gives_the_defaults():
    config, problems = parse_work_config({})
    assert problems == []
    assert config.backend == "filesystem"
    assert config.hooks.timeout == 300
    assert config.hooks.output_cap == 65536
    assert "review" in config.enabled and "postmortem" in config.enabled
    assert config.stages["spec"].prompt is None


def test_none_is_an_empty_section():
    config, problems = parse_work_config(None)
    assert problems == []


@pytest.mark.parametrize("key", ["lifecycle", "tracker", "auto-commit-transitions",
                                 "publish-transitions", "trunk-branch", "retain"])
def test_each_removed_2x_key_names_the_migration_guide(key):
    [problem] = problems_of({key: {}})
    assert problem.key_path == ("work", key)
    assert MIGRATION_GUIDE in problem.message
    assert "removed" in problem.message


def test_the_lifecycle_message_says_where_artifact_templates_went():
    [problem] = problems_of({"lifecycle": {}})
    assert "prompt" in problem.message and "artifacts" in problem.message


def test_this_repository_s_2_8_config_reports_its_removed_keys():
    work = yaml.safe_load(FIXTURE.read_text())["work"]
    found = paths(problems_of(work))
    for key in ("lifecycle", "tracker", "retain"):
        assert ("work", key) in found


def test_unknown_keys_are_errors():
    assert paths(problems_of({"colour": 1})) == [("work", "colour")]
    assert paths(problems_of({"hooks": {"retries": 2}})) == [
        ("work", "hooks", "retries")]
    assert paths(problems_of({"stages": {"bogus": {}}})) == [
        ("work", "stages", "bogus")]
    assert paths(problems_of({"stages": {"spec": {"colour": 1}}})) == [
        ("work", "stages", "spec", "colour")]


@pytest.mark.parametrize("name", ["implement", "request", "inbox", "completed"])
def test_a_required_stage_cannot_be_disabled(name):
    assert paths(problems_of({"stages": {name: {"enabled": False}}})) == [
        ("work", "stages", name, "enabled")]


def test_disabling_optional_stages():
    config, problems = parse_work_config(
        {"stages": {"plan": {"enabled": False}, "qa": {"enabled": False}}})
    assert problems == []
    assert "plan" not in config.enabled and "qa" not in config.enabled
    assert "spec" in config.enabled


@pytest.mark.parametrize("key", ["pre", "post", "status"])
def test_a_side_stage_takes_no_hooks_or_status(key):
    value = "Done" if key == "status" else [{"command": "true"}]
    work = {"backend": "jira", "stages": {"postmortem": {key: value}}}
    assert ("work", "stages", "postmortem", key) in paths(problems_of(work))


def test_a_skill_in_pre_is_refused_with_its_own_reason():
    [problem] = problems_of({"stages": {"review": {"pre": [{"skill": "x"}]}}})
    assert "cannot run a skill" in problem.message


def test_a_skill_in_post_is_allowed():
    config, problems = parse_work_config(
        {"stages": {"review": {"post": [{"skill": "tell-the-team"}]}}})
    assert problems == []
    assert config.stages["review"].post == (Binding("skill", "tell-the-team", None),)


def test_when_type_is_refused_because_items_have_no_type():
    [problem] = problems_of({"stages": {"spec": {"prompt": [
        {"file": "x.md", "when": {"type": "epic"}}]}}})
    assert "have no type" in problem.message


def test_when_tags_are_normalized():
    config, _ = parse_work_config({"stages": {"spec": {"prompt": [
        {"file": "bug.md", "when": {"tags": ["Bug"], "not_tags": ["Docs"]}}]}}})
    assert config.stages["spec"].prompt[0].when == When(("bug",), ("docs",))


@pytest.mark.parametrize("binding", [
    {"command": "true"},                   # not a prompt kind
    {"file": "a", "blob": "b"},            # two kinds
    {},                                    # no kind
    {"builtin": "yes"},                    # builtin must be true
    {"file": "  "},                        # blank
    {"skill": "has space"},
    {"skill": "a/b"},
    {"file": "a", "when": {}},
    {"file": "a", "when": {"tags": "bug"}},
    {"file": "a", "when": {"tags": ["a,b"]}},
    "file: a",
])
def test_malformed_bindings_are_errors(binding):
    assert problems_of({"stages": {"spec": {"prompt": [binding]}}})


def test_a_blank_blob_is_an_explicit_nothing():
    config, problems = parse_work_config(
        {"stages": {"spec": {"prompt": [{"blob": ""}]}}})
    assert problems == []


def test_duplicate_bindings_are_allowed_after_a_merge():
    config, problems = parse_work_config({"stages": {"spec": {"prompt": [
        {"builtin": True}, {"builtin": True}]}}})
    assert problems == []
    assert len(config.stages["spec"].prompt) == 2


def test_an_empty_list_is_kept_as_empty_not_as_unset():
    config, problems = parse_work_config({
        "stages": {"spec": {"prompt": [], "pre": [], "post": []}},
        "procedures": {"create-work": []}})
    assert problems == []
    assert config.stages["spec"].prompt == ()
    assert config.procedures["create-work"] == ()


def test_procedures_are_parsed_and_unknown_ones_refused():
    config, problems = parse_work_config({"procedures": {
        "create-work": [{"builtin": True}, {"file": "x.md"}],
        "make-coffee": [{"builtin": True}]}})
    assert paths(problems) == [("work", "procedures", "make-coffee")]
    assert [b.kind for b in config.procedures["create-work"]] == ["builtin", "file"]


def test_status_and_jira_need_the_jira_backend():
    found = paths(problems_of({"jira": {}, "stages": {"spec": {"status": "Spec"}}}))
    assert ("work", "jira") in found
    assert ("work", "stages", "spec", "status") in found


def _jira_statuses(**override):
    statuses = {"inbox": "Triage", "request": "To Do", "spec": "Spec",
                "plan": "Plan", "implement": "In Progress", "review": "In Review",
                "qa": "QA", "completed": "Done", "discarded": "Won't Do"}
    statuses.update(override)
    return {"backend": "jira", "jira": {"site": "x"},
            "stages": {name: {"status": s} for name, s in statuses.items()
                       if s is not None}}


def test_a_complete_jira_mapping_passes():
    config, problems = parse_work_config(_jira_statuses())
    assert problems == []
    assert config.jira == {"site": "x"}
    assert config.stages["qa"].status == "QA"


def test_jira_mode_needs_a_status_for_every_enabled_stage_including_inbox():
    assert paths(problems_of(_jira_statuses(inbox=None))) == [
        ("work", "stages", "inbox", "status")]


def test_jira_mode_refuses_two_stages_with_one_status():
    [problem] = problems_of(_jira_statuses(qa="In Review"))
    assert problem.key_path[:3] == ("work", "stages", "review")
    assert "qa" in problem.message


def test_a_disabled_stage_needs_no_status():
    work = _jira_statuses(qa=None)
    work["stages"]["qa"] = {"enabled": False}
    assert problems_of(work) == []


@pytest.mark.parametrize("hooks, key", [
    ({"timeout": 0}, "timeout"), ({"timeout": -1}, "timeout"),
    ({"timeout": True}, "timeout"), ({"timeout": "60"}, "timeout"),
    ({"timeout": float("inf")}, "timeout"), ({"timeout": float("nan")}, "timeout"),
    ({"output-cap": 0}, "output-cap"), ({"output-cap": 1.5}, "output-cap"),
    ({"output-cap": True}, "output-cap"),
])
def test_hook_limits_must_be_positive(hooks, key):
    assert paths(problems_of({"hooks": hooks})) == [("work", "hooks", key)]


def test_a_huge_whole_number_is_read_not_raised():
    # math.isfinite converts an int to float, which overflows past ~10**308.
    config, problems = parse_work_config({"hooks": {"timeout": 10**400,
                                                    "output-cap": 10**400}})
    assert problems == []


def test_hook_limits_are_read():
    config, problems = parse_work_config({"hooks": {"timeout": 2.5,
                                                    "output-cap": 1024}})
    assert problems == []
    assert (config.hooks.timeout, config.hooks.output_cap) == (2.5, 1024)


def test_an_unknown_backend_is_an_error():
    assert paths(problems_of({"backend": "linear"})) == [("work", "backend")]


def test_origins_are_copied_onto_bindings():
    origins = {("work", "stages", "spec", "prompt"): "personal",
               ("work", "procedures", "create-work"): "team"}
    config, _ = parse_work_config({
        "stages": {"spec": {"prompt": [{"builtin": True}]},
                   "plan": {"prompt": [{"builtin": True}]}},
        "procedures": {"create-work": [{"builtin": True}]}}, origins)
    assert config.stages["spec"].prompt[0].origin == "personal"
    assert config.stages["plan"].prompt[0].origin is None
    assert config.procedures["create-work"][0].origin == "team"


def test_a_binding_exposes_ref_for_the_hook_runner():
    assert Binding("command", "make test", None).ref == "make test"


def test_tags_and_documentation_are_read():
    work = yaml.safe_load(FIXTURE.read_text())["work"]
    config, _ = parse_work_config(work)
    assert "bug" in config.tags
    assert any(entry.path == "README.md" for entry in config.documentation)


def test_a_section_that_is_not_a_mapping_is_an_error():
    assert paths(problems_of(["a"])) == [("work",)]
