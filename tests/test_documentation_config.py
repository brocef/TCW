"""`work.documentation`: the pure parser, and what `tcw validate` reports.

Table-driven, because the value of a shape-validating parser is entirely in
which shapes it rejects and which it lets through — and the second list matters
as much as the first. Entries naming a file that does not exist yet, and
project-defined triggers outside the base vocabulary, are both **legal** and are
asserted here so a later tightening has to argue with a red test.
"""

import pytest

from tcw.store.base import DocEntry, parse_documentation_entries

GOOD = [
    {"path": "README.md", "trigger": "Public-API", "description": "Overview."},
    {"path": "docs/changelogs/upcoming.md", "trigger": "Any-Code-Change",
     "description": "Developer changelog."},
]


def _problems(raw):
    return parse_documentation_entries(raw)[1]


def _entries(raw):
    return parse_documentation_entries(raw)[0]


# -- the happy path ---------------------------------------------------------

def test_absent_configuration_is_not_a_problem():
    entries, problems = parse_documentation_entries(None)
    assert entries == [] and problems == []


def test_well_formed_entries_parse_in_order():
    entries, problems = parse_documentation_entries(GOOD)
    assert problems == []
    assert [e.path for e in entries] == ["README.md", "docs/changelogs/upcoming.md"]
    assert entries[0] == DocEntry(path="README.md", trigger="Public-API",
                                  description="Overview.")


def test_entries_are_frozen():
    with pytest.raises(Exception):
        _entries(GOOD)[0].path = "elsewhere.md"


# -- what must be reported (acceptance criterion 1) -------------------------

@pytest.mark.parametrize("raw, needle", [
    ({"path": "x"}, "expected a list"),
    ("README.md", "expected a list"),
    ([["not", "a", "mapping"]], "entry 0"),
    (["README.md"], "entry 0"),
    ([{"trigger": "Public-API", "description": "d"}], "path"),
    ([{"path": "", "trigger": "Public-API", "description": "d"}], "path"),
    ([{"path": "   ", "trigger": "Public-API", "description": "d"}], "path"),
    ([{"path": "a.md", "description": "d"}], "trigger"),
    ([{"path": "a.md", "trigger": "", "description": "d"}], "trigger"),
    ([{"path": "a.md", "trigger": "Public-API"}], "description"),
    ([{"path": "a.md", "trigger": "Public-API", "description": "  "}], "description"),
    ([{"path": "/etc/passwd", "trigger": "T", "description": "d"}], "absolute"),
    ([{"path": "../outside.md", "trigger": "T", "description": "d"}], "escape"),
    ([{"path": "a.md", "trigger": "Public API", "description": "d"}], "whitespace"),
    ([{"path": "a\nb.md", "trigger": "T", "description": "d"}], "newline"),
    ([{"path": "a.md", "trigger": "T\nU", "description": "d"}], "newline"),
])
def test_malformed_configuration_is_reported(raw, needle):
    problems = _problems(raw)
    assert problems, f"expected a problem for {raw!r}"
    assert any(needle in p for p in problems), (needle, problems)


def test_a_duplicate_path_is_reported():
    problems = _problems(GOOD + [dict(GOOD[0])])
    assert any("duplicate" in p for p in problems)


# -- one file, several triggers ---------------------------------------------

PAIR = [
    {"path": "README.md", "trigger": "Public-CLI-API", "description": "d1"},
    {"path": "README.md", "trigger": "Validation-Rules", "description": "d2"},
]


def test_one_path_may_carry_two_triggers():
    """The identity is the pair, not the path — a README whose CLI section and
    validation section answer to different triggers is the motivating case."""
    entries, problems = parse_documentation_entries(PAIR)
    assert problems == []
    assert [e.trigger for e in entries] == ["Public-CLI-API", "Validation-Rules"]


def test_the_same_path_and_trigger_twice_is_still_a_duplicate():
    entries, problems = parse_documentation_entries(
        [PAIR[0], dict(PAIR[1], trigger="Public-CLI-API")])
    assert len(problems) == 1
    assert all(needle in problems[0]
               for needle in ("entry 1", "README.md", "Public-CLI-API"))
    assert len(entries) == 1


def test_a_duplicate_names_the_entry_that_first_declared_the_pair():
    """Reported against the *stored* index, not a position in the kept list —
    entry 2 collides with entry 0 even though entry 1 sits between them."""
    entries, problems = parse_documentation_entries(PAIR + [dict(PAIR[0])])
    assert len(problems) == 1
    assert "entry 2" in problems[0] and "entry 0" in problems[0]
    assert [e.trigger for e in entries] == ["Public-CLI-API", "Validation-Rules"]


def test_every_problem_names_the_entry_index():
    problems = _problems([GOOD[0], {"path": "", "trigger": "", "description": ""}])
    assert problems and all("entry 1" in p for p in problems)


def test_the_parser_never_raises():
    for raw in [0, 1.5, True, b"bytes", [None], [{"path": 3, "trigger": 4,
                                                  "description": 5}]]:
        parse_documentation_entries(raw)          # must not raise


def test_a_malformed_list_still_yields_the_entries_it_could_read():
    """Advisory, like `parse_lifecycle_policy`: one bad entry must not blank the
    rest, or a typo would silently empty a project's documentation gate."""
    entries, problems = parse_documentation_entries([GOOD[0], {"path": ""}])
    assert [e.path for e in entries] == ["README.md"]
    assert problems


# -- what must NOT be reported (acceptance criterion 2) ---------------------

def test_a_path_that_does_not_exist_is_legal():
    """The parser touches no filesystem, and an entry naming a file the project
    intends to create is correct — `references/setup.md` exists to create them."""
    assert _problems([{"path": "docs/not-written-yet.md", "trigger": "Public-API",
                       "description": "Planned."}]) == []


def test_a_project_defined_trigger_is_legal():
    """`skills/documentation-sync/SKILL.md` declares the vocabulary open:
    'Treat any such project-defined trigger as authoritative for that project.'"""
    assert _problems([{"path": "a.md", "trigger": "Skill-Driven-Component",
                       "description": "d"}]) == []
    assert _problems([{"path": "b.md", "trigger": "Wildly-Bespoke-Trigger",
                       "description": "d"}]) == []


def test_a_path_placeholder_is_legal():
    """This repository's own entry is `skills/<component>/SKILL.md` — a pattern,
    not a resolvable path. Rejecting it would reject the node writing the rule."""
    assert _problems([{"path": "skills/<component>/SKILL.md",
                       "trigger": "Skill-Driven-Component",
                       "description": "d"}]) == []


def test_a_multiline_description_is_legal():
    """YAML block scalars are the natural way to write these, and rendering
    collapses their newlines rather than the parser refusing them."""
    assert _problems([{"path": "a.md", "trigger": "T",
                       "description": "one\ntwo\nthree"}]) == []


def test_an_empty_list_is_legal():
    entries, problems = parse_documentation_entries([])
    assert entries == [] and problems == []


# -- the `tcw validate` boundary (acceptance criteria 1 and 2) --------------

import subprocess
from pathlib import Path

import yaml


def _node(tmp_path: Path, documentation) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(tmp_path), "config", k, v], check=True)
    subprocess.run(["tcw", "init", "--id", "docs-node", "work"], cwd=tmp_path,
                   capture_output=True, check=True, stdin=subprocess.DEVNULL)
    cfg = tmp_path / "tcw-config.yaml"
    conf = yaml.safe_load(cfg.read_text()) or {}
    if documentation is not None:
        conf.setdefault("work", {})["documentation"] = documentation
    cfg.write_text(yaml.safe_dump(conf, sort_keys=False))
    return tmp_path


def _validate(root: Path):
    return subprocess.run(["tcw", "validate"], cwd=root, capture_output=True,
                          text=True, stdin=subprocess.DEVNULL)


def test_validate_reports_a_malformed_entry(tmp_path):
    root = _node(tmp_path, [{"path": "", "trigger": "Public API",
                             "description": "d"}])
    r = _validate(root)
    assert r.returncode != 0
    assert "work.documentation entry 0" in r.stdout + r.stderr


def test_validate_accepts_a_well_formed_block(tmp_path):
    root = _node(tmp_path, GOOD)
    r = _validate(root)
    assert r.returncode == 0, r.stdout + r.stderr


def test_validate_accepts_a_nonexistent_path_and_a_custom_trigger(tmp_path):
    """Acceptance criterion 2, at the CLI rather than in the parser."""
    root = _node(tmp_path, [{"path": "docs/not-written-yet.md",
                             "trigger": "Skill-Driven-Component",
                             "description": "Planned."}])
    r = _validate(root)
    assert r.returncode == 0, r.stdout + r.stderr


def test_an_unconfigured_node_still_validates(tmp_path):
    r = _validate(_node(tmp_path, None))
    assert r.returncode == 0, r.stdout + r.stderr


def test_a_malformed_block_does_not_break_the_board(tmp_path):
    """The adapter discards problems: `tcw work list` must keep working even
    when the configuration is wrong, which is what 'advisory' buys."""
    root = _node(tmp_path, "not-a-list")
    r = subprocess.run(["tcw", "work", "list"], cwd=root, capture_output=True,
                       text=True, stdin=subprocess.DEVNULL)
    assert r.returncode == 0, r.stderr
