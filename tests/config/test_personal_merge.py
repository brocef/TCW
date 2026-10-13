"""Merging, the `inherit` chain, and built-in entries (TCW-72 AC 3, 4, 5)."""

from __future__ import annotations

import pytest

from tcw.config import load_config
from tests.config.conftest import problem_lines

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
    assert lines[0].startswith("tcw-config.local.yaml: work.stages.spec.prompt[0]: ")
    assert words in lines[0]


def test_two_inherit_entries_are_one_problem(personal):
    personal.local({"work": {"stages": {"spec": {"prompt": [INHERIT, INHERIT]}}}})
    lines = problem_lines(load_config(personal.root))
    assert lines == [lines[0]] and "work.stages.spec.prompt[1]" in lines[0]


def test_inherit_outside_a_chain_list_is_one_problem(personal):
    personal.project({"work": {"tags": [INHERIT]}})
    # The tag parser also says the entry is not a tag; this is the one
    # problem about `inherit` itself.
    lines = [line for line in problem_lines(load_config(personal.root))
             if "'inherit' is allowed only" in line]
    assert len(lines) == 1 and lines[0].startswith("tcw-config.yaml: work.tags[0]: ")


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
    assert len(lines) == 1 and lines[0].startswith("tcw-config.yaml: ")


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
    personal.project_file.write_text("id: p\nwork:\n")
    config = load_config(personal.root)
    assert config.problems == []
    assert config.values["work"]["stages"]["spec"]["prompt"] == [{"builtin": True}]


def test_other_lists_are_replaced_whole(personal):
    personal.project({"work": {"tags": ["a", "b"]}})
    config = load_config(personal.root)
    assert config.values["work"]["tags"] == ["a", "b"]
    assert config.origins[("work", "tags", 1)].layer == "project"
