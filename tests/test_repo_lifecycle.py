"""This repository's own 3.0 configuration (TCW-76 Design 6 and 7; criteria
16 and 21).

TCW-70 deleted the 2.x file of this name together with the parser it
guarded. This one checks `tcw-config.yaml` against the 3.0 parser: it loads
with no problems, its `work.jira` block parses, every file a stage binds
exists and is not empty, every script a hook runs exists, `plan` binds no
spec template, both templates carry the sections the spec stage asks for
(read from its prompt), and the documentation entries are those of Design 6.4.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path

import pytest

from tcw.config import load_config
from tcw.work.jira.config import parse_jira_config

REPO = Path(__file__).resolve().parent.parent
TEMPLATES = ("docs/lifecycle/templates/spec.md",
             "docs/lifecycle/templates/spec-bug.md")



def _spec_headings() -> tuple[str, ...]:
    """The sections the built-in spec prompt asks for, read from its
    "**Produce**" list (`tcw/work/prompts/spec.md`), so a change to the
    prompt reaches this test."""
    prompt = " ".join((REPO / "tcw/work/prompts/spec.md").read_text(encoding="utf-8").split())
    found = re.search(r"with \w+ sections: (.*?)\.", prompt)
    assert found, "tcw/work/prompts/spec.md no longer lists the spec's sections"
    names = tuple(re.findall(r"\*\*([^*]+)\*\*", found.group(1)))
    assert names, f"no section names in {found.group(0)!r}"
    return names

# Design 6.4: `Tracker-Change` became `Jira-Change`; the upcoming entries are
# named by the item's folder name.
DOCUMENTATION = {
    ("README.md", "Public-API"),
    ("docs/guide/jira.md", "Jira-Change"),
    ("docs/guide/<topic>.md", "Guide-Topic-Change"),
    ("docs/release-notes/upcoming/<folder>.md", "Public-API"),
    ("docs/changelogs/upcoming/<folder>.md", "Any-Code-Change"),
    ("skills/<component>/SKILL.md", "Skill-Driven-Component"),
    ("skills/configure/references/<document>.md", "Configuration-Key-Change"),
}

# Programs a `command:` hook runs a script with; the script is then its
# first argument. Any other program (`tcw`) is found on PATH.
INTERPRETERS = ("sh", "bash", "python", "python3")


@pytest.fixture(scope="module")
def config():
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("TCW_NO_PERSONAL_CONFIG", "1")
        return load_config(REPO)


def _bindings(config, kind):
    for name, stage in config.work.stages.items():
        for role in ("prompt", "pre", "post"):
            for binding in getattr(stage, role) or ():
                if binding.kind == kind:
                    yield name, role, binding.value
    for name, bindings in config.work.procedures.items():
        for binding in bindings:
            if binding.kind == kind:
                yield name, "procedure", binding.value


def test_the_configuration_loads_with_no_problems(config):
    assert not config.unreadable
    assert config.problems == []
    assert config.work.backend == "jira"


def test_the_jira_block_parses_with_no_problems(config):
    jira, problems = parse_jira_config(config.work.jira)
    assert problems == []
    assert jira is not None and jira.project == "TCW"


def test_every_bound_file_exists_and_is_not_empty(config):
    files = list(_bindings(config, "file"))
    assert files, "no stage binds a file"
    for stage, role, value in files:
        path = REPO / value
        assert path.is_file(), f"{stage}.{role} binds {value}, which does not exist"
        assert path.read_text(encoding="utf-8").strip(), (
            f"{stage}.{role} binds {value}, which is empty")


def test_every_hook_script_exists(config):
    commands = list(_bindings(config, "command"))
    scripts = []
    for stage, role, value in commands:
        words = shlex.split(value)
        if words[0] in INTERPRETERS:
            scripts.append(words[1])
            assert (REPO / words[1]).is_file(), (
                f"{stage}.{role} runs {value!r}, but {words[1]} does not exist")
    assert "scripts/require_artifact.py" in scripts
    assert "docs/guide/examples/commit-item-after-move.sh" in scripts


def test_plan_binds_no_spec_template(config):
    bound = [value for _, _, value in _bindings(config, "file")
             if value in TEMPLATES]
    assert bound, "no stage binds a spec template"
    plan = config.work.stage("plan").prompt or ()
    assert not [b.value for b in plan if b.value in TEMPLATES]


@pytest.mark.parametrize("template", TEMPLATES)
def test_a_template_carries_every_spec_section(template):
    headings = {line[3:].strip() for line in
                (REPO / template).read_text(encoding="utf-8").splitlines()
                if line.startswith("## ")}
    missing = [h for h in _spec_headings() if h not in headings]
    assert not missing, f"{template} lacks {missing}"


def test_the_documentation_entries_are_those_of_design_6_4(config):
    entries = config.work.documentation
    assert {(e.path, e.trigger) for e in entries} == DOCUMENTATION
    assert not [e for e in entries if e.trigger == "Tracker-Change"]
    assert not [e for e in entries if "<slug>" in e.path]
    assert not [e for e in entries if "dod.yaml" in e.description]
    guide = next(e for e in entries if e.trigger == "Guide-Topic-Change")
    assert "Jira-Change" in guide.description
