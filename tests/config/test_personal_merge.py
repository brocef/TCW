"""Merging, the `inherit` chain, and built-in entries (TCW-72 AC 3, 4, 5)."""

from __future__ import annotations

import pytest

from tcw.config import load_config
from tests.config.conftest import problem_lines
from tests.projectfiles import write_config_file

B = {"builtin": True}
SPEC = ("work", "stages", "spec")


def a(name: str) -> dict:
    return {"blob": name}


INHERIT = {"inherit": True}


def test_mappings_merge_key_by_key(personal):
    personal.project({"work": {"stages": {"spec": {"pre": [{"command": "a"}]}}}})
    personal.local({"work": {"stages": {"spec": {"prompt": [{"blob": "x"}]}}}})
    config = load_config(personal.root)
    spec = config.values["work"]["stages"]["spec"]
    assert spec == {"prompt": [{"blob": "x"}], "pre": [{"command": "a"}]}
    assert config.origins[(*SPEC, "pre", 0)].layer == "project"
    assert config.origins[(*SPEC, "prompt", 0)].layer == "local"


# (project, user, local) -> resolved; None means the layer does not set it.
CHAIN = [
    (None, None, None, [B], ["built-in"]),
    ([a("a")], None, None, [a("a")], ["project"]),
    ([INHERIT, a("a")], None, None, [B, a("a")], ["built-in", "project"]),
    ([a("a")], [a("b"), INHERIT], None, [a("b"), a("a")], ["user", "project"]),
    ([a("a")], [a("b"), INHERIT], [INHERIT, a("c")], [a("b"), a("a"), a("c")],
     ["user", "project", "local"]),
    ([a("a")], [a("b"), INHERIT], [a("d")], [a("d")], ["local"]),
    ([a("a")], None, [], [], []),
]


@pytest.mark.parametrize("project, user, local, resolved, layers", CHAIN)
def test_the_chain(personal, project, user, local, resolved, layers):
    if project is not None:
        personal.project({"work": {"stages": {"spec": {"prompt": project}}}})
    if user is not None:
        personal.user({"work": {"stages": {"spec": {"prompt": user}}}})
    if local is not None:
        personal.local({"work": {"stages": {"spec": {"prompt": local}}}})
    config = load_config(personal.root)
    assert problem_lines(config) == []
    assert config.values["work"]["stages"]["spec"]["prompt"] == resolved
    assert [config.origins[(*SPEC, "prompt", i)].layer
            for i in range(len(resolved))] == layers
    assert [b.origin.layer for b in config.work.stage("spec").prompt] == layers


def test_inherit_in_pre_at_the_project_layer_adds_nothing(personal):
    personal.project({"work": {"stages": {"spec": {"pre": [INHERIT]}}}})
    config = load_config(personal.root)
    assert problem_lines(config) == []
    assert config.values["work"]["stages"]["spec"]["pre"] == []


def test_an_inherited_entry_keeps_its_when(personal):
    when = {"blob": "x", "when": {"tags": ["bug"]}}
    personal.project({"work": {"tags": ["bug"], "stages": {"spec": {"prompt": [when]}}}})
    personal.local({"work": {"stages": {"spec": {"prompt": [INHERIT, a("y")]}}}})
    config = load_config(personal.root)
    assert config.values["work"]["stages"]["spec"]["prompt"][0] == when
    assert config.work.stage("spec").prompt[0].when.tags == ("bug",)
    assert config.work.stage("spec").prompt[0].origin.layer == "project"


def test_a_procedure_list_resolves_through_the_chain(personal):
    personal.local({"work": {"procedures": {"audit-backlog": [a("mine"), INHERIT]}}})
    config = load_config(personal.root)
    assert config.values["work"]["procedures"]["audit-backlog"] == [a("mine"), B]


@pytest.mark.parametrize("entry, words", [
    ({"inherit": False}, "only the value true"),
    ({"inherit": True, "when": {"tags": ["bug"]}}, "stands alone"),
])
def test_a_bad_inherit_entry_is_one_problem(personal, entry, words):
    personal.local({"work": {"stages": {"spec": {"prompt": [entry]}}}})
    lines = problem_lines(load_config(personal.root))
    assert len(lines) == 1, lines
    assert lines[0].startswith(".tcw/tcw-config.local.yaml: work.stages.spec.prompt[0]: ")
    assert words in lines[0]


def test_two_inherit_entries_are_one_problem(personal):
    personal.local({"work": {"stages": {"spec": {"prompt": [INHERIT, INHERIT]}}}})
    lines = problem_lines(load_config(personal.root))
    assert lines == [lines[0]] and "work.stages.spec.prompt[1]" in lines[0]


def test_inherit_outside_a_chain_list_is_one_problem(personal):
    # TCW-109 Design 2.4: `work.tags` takes the entry now, so the list that
    # refuses it is another one, and the refusal names `work.tags`.
    personal.project({"work": {"documentation": [INHERIT]}})
    lines = [line for line in problem_lines(load_config(personal.root))
             if "'inherit' is allowed only" in line]
    assert len(lines) == 1 and lines[0].startswith(
        ".tcw/tcw-config.yaml: work.documentation[0]: ")
    assert "work.tags" in lines[0]


@pytest.mark.parametrize("layer", ["project", "user", "local"])
def test_builtin_in_any_file_is_one_problem_naming_the_guide(personal, layer):
    getattr(personal, layer)({"work": {"stages": {"spec": {"prompt": [B]}}}})
    lines = problem_lines(load_config(personal.root))
    assert len(lines) == 1, lines
    assert "inherit: true" in lines[0]
    assert "docs/migration-guide-2.8-to-3.0.0.md" in lines[0]
    assert "work.stages.spec.prompt[0]" in lines[0]


def test_a_repeated_entry_in_one_file_is_one_problem(personal):
    personal.project({"work": {"stages": {"spec": {"prompt": [{"file": "a.md"},
                                                              {"file": "a.md"}]}}}})
    lines = problem_lines(load_config(personal.root))
    assert len(lines) == 1 and lines[0].startswith(".tcw/tcw-config.yaml: ")


def test_the_same_entry_in_two_layers_is_no_problem(personal):
    (personal.root / "a.md").write_text("A\n")
    personal.project({"work": {"stages": {"spec": {"prompt": [{"file": "a.md"}]}}}})
    personal.local({"work": {"stages": {"spec": {"prompt": [INHERIT, {"file": "a.md"}]}}}})
    config = load_config(personal.root)
    assert problem_lines(config) == []
    assert config.values["work"]["stages"]["spec"]["prompt"] == [{"file": "a.md"}] * 2
    assert [config.origins[(*SPEC, "prompt", i)].layer for i in (0, 1)] == \
        ["project", "local"]


def test_with_nothing_set_a_stage_prompt_is_the_built_in_entry(personal):
    config = load_config(personal.root)
    assert config.values["work"]["stages"]["spec"]["prompt"] == [{"builtin": True}]
    assert config.origins[(*SPEC, "prompt", 0)].layer == "built-in"
    assert config.problems == []
    assert config.work.stage("spec").prompt[0].kind == "builtin"


def test_an_empty_work_key_keeps_the_built_in_prompts(personal):
    write_config_file(personal.project_file, "id: p\nwork:\n")
    config = load_config(personal.root)
    assert config.problems == []
    assert config.values["work"]["stages"]["spec"]["prompt"] == [{"builtin": True}]


def test_other_lists_are_replaced_whole(personal):
    personal.project({"work": {"tags": ["a", "b"]}})
    config = load_config(personal.root)
    assert config.values["work"]["tags"] == ["a", "b"]
    assert config.origins[("work", "tags", 1)].layer == "project"


# -- A mapping no lower layer holds (review finding L2) --------------------------------


@pytest.mark.parametrize("stage", ["completed", "discarded"])
def test_a_new_stage_mapping_resolves_its_chain_lists(personal, stage):
    personal.project({"work": {"stages": {stage: {"post": [INHERIT, {"command": "true"}]}}}})
    config = load_config(personal.root)
    assert problem_lines(config) == []
    assert config.values["work"]["stages"][stage]["post"] == [{"command": "true"}]
    assert [o.layer for o in config.written[("work", "stages", stage, "post")]] == \
        ["project"]
    assert [b.value for b in config.work.stage(stage).post] == ["true"]


def test_a_local_stage_mapping_resolves_when_the_project_sets_nothing(personal):
    personal.local({"work": {"stages": {"completed": {"post": [INHERIT, {"command": "x"}]}}}})
    config = load_config(personal.root)
    assert problem_lines(config) == []
    assert config.values["work"]["stages"]["completed"]["post"] == [{"command": "x"}]
    assert config.personal_files(("work", "stages", "completed", "post")) == \
        [personal.local_file]


# -- Origins of mappings (review finding L3) ---------------------------------------------


def test_an_empty_mapping_is_blamed_on_the_file_that_wrote_it(personal):
    personal.local({"work": {"procedures": {"custom": {}}}})
    config = load_config(personal.root)
    [problem] = config.problems
    assert problem.key_path == ("work", "procedures", "custom")
    assert problem.file == personal.local_file
    from tcw.config_cli import render
    [line] = [l for l in render(config, origin=True).splitlines() if "custom:" in l]
    assert line.endswith("custom: {}  # p, local .tcw/tcw-config.local.yaml"), line


def test_a_mapping_problem_is_blamed_on_the_highest_layer_under_it(personal):
    # Design 5.2's third rule: nothing at the key itself or above it has an
    # origin, so the highest layer that wrote anything under it is named.
    personal.project({"work": {"stages": {"nosuch": {"pre": [{"command": "a"}]}}}})
    personal.local({"work": {"stages": {"nosuch": {"prompt": [a("x")]}}}})
    config = load_config(personal.root)
    blamed = [p.file for p in config.problems if p.key_path == ("work", "stages", "nosuch")]
    assert blamed == [personal.local_file], problem_lines(config)
