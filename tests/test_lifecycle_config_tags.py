"""Tags and keys in the work configuration are reported, never ignored or
crashed on (spec: 2026-09-15-report-malformed-keys-and-unregistered-tags-in-lifecycle-config)."""

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from tcw.cli import main
from tcw.store.base import _parse_condition, parse_documentation_entries, parse_lifecycle_policy
from tcw.store.fs import FsWorkStore, init


def node(tmp_path: Path, work: dict) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root, "node")
    config = root / "tcw-config.yaml"
    data = yaml.safe_load(config.read_text()) or {}
    data["work"] = {**(data.get("work") or {}), **work}
    config.write_text(yaml.safe_dump(data, sort_keys=False))
    return root


def condition(when: dict):
    problems: list[str] = []
    return _parse_condition(when, "w", problems), problems


# ── criteria 1-2: conditions are normalized ─────────────────────────────────

def test_a_condition_tag_is_normalized():
    cond, problems = condition({"tags": ["CLI"], "not_tags": ["Docs Only"]})
    assert problems == []
    assert (cond.tags, cond.not_tags) == (("cli",), ("docs-only",))
    assert cond.matches(SimpleNamespace(tags=["cli"], type=""))
    assert not cond.matches(SimpleNamespace(tags=["cli", "docs-only"], type=""))


@pytest.mark.parametrize("element, expected", [
    ("cli,docs", "[cli, docs]"),
    ("!!!", "!!!"),
])
def test_a_condition_tag_that_cannot_be_a_tag_is_a_problem(element, expected):
    cond, problems = condition({"tags": [element]})
    assert cond is None
    assert len(problems) == 1 and expected in problems[0], problems


# ── criterion 3: an unregistered condition tag is reported, policy still loads ──

def test_an_unregistered_condition_tag_is_reported_but_the_policy_loads(tmp_path, monkeypatch, capsys):
    root = node(tmp_path, {"tags": ["bug"], "lifecycle": {"stages": {"spec": {"prompt": [
        {"blob": "for bugs", "when": {"tags": ["bug"]}},
        {"blob": "typo", "when": {"not_tags": ["clii"]}}]}}}})
    st = FsWorkStore.open(root)
    problems = st.lifecycle_problems()
    assert [p for p in problems if "clii" in p and "not a registered tag" in p], problems
    assert not [p for p in problems if "'bug'" in p], problems
    assert len(st.lifecycle_policy().stages["spec"].prompt) == 2
    monkeypatch.chdir(root)
    assert main(["work", "list"]) == 0


# ── criteria 4-5: every tag reader agrees ────────────────────────────────────

def test_registered_tags_are_normalized_and_a_bad_entry_is_reported(tmp_path):
    root = node(tmp_path, {"tags": ["Bug", "bug", "!!!"]})
    st = FsWorkStore.open(root)
    assert st.registered_tags() == ["bug"]
    assert [p for p in st.check() if "!!!" in p], st.check()


def test_a_plan_stage_tag_is_normalized(tmp_path):
    root = node(tmp_path, {"tags": ["cli"]})
    st = FsWorkStore.open(root)
    slug = st.create("Planned", created="2026-01-01").slug
    st.write_artifact(slug, "plan", "---\nstages:\n  - id: api\n    title: API\n"
                      "    depends_on: []\n    tags: [Cli]\n---\n\nPlan.\n")
    [stage] = st.plan_stages(slug)
    assert stage.tags == ("cli",)


def test_a_non_string_tag_is_a_value_error(tmp_path):
    root = node(tmp_path, {"tags": ["cli"]})
    st = FsWorkStore.open(root)
    slug = st.create("X", created="2026-01-01").slug
    with pytest.raises(ValueError, match="1"):
        st.update_work(slug, tags=[1])


# ── criterion 6: list --tags says when a tag is not registered ───────────────

def test_listing_by_an_unregistered_tag_says_so(tmp_path, monkeypatch, capsys):
    root = node(tmp_path, {"tags": ["cli"]})
    monkeypatch.chdir(root)
    assert main(["work", "list", "--tags", "nope"]) == 0
    assert "'nope' is not a registered tag" in capsys.readouterr().err
    assert main(["work", "list", "--tags", "CLI"]) == 0
    assert "not a registered tag" not in capsys.readouterr().err


# ── criterion 7: a non-string key is named, not a traceback ──────────────────

SPEC = {"blob": "x"}

JOIN_SITES = {
    "when": lambda k: parse_lifecycle_policy(
        {"stages": {"spec": {"prompt": [{**SPEC, "when": {"tags": ["a"], **k}}]}}}),
    "binding": lambda k: parse_lifecycle_policy(
        {"stages": {"spec": {"prompt": [{**SPEC, **k}]}}}),
    "stage": lambda k: parse_lifecycle_policy(
        {"stages": {"spec": {"prompt": [SPEC], **k}}}),
    "lifecycle": lambda k: parse_lifecycle_policy({"stages": {}, **k}),
    "transition": lambda k: parse_lifecycle_policy(
        {"transitions": {"start": {"pre": [], **k}}}),
    "documentation": lambda k: parse_documentation_entries(
        [{"path": "a", "trigger": "b", "description": "c", **k}]),
}


@pytest.mark.parametrize("keys", [{1: "x"}, {1: "x", "zz": "y"}], ids=["int", "mixed"])
@pytest.mark.parametrize("site", sorted(JOIN_SITES))
def test_a_non_string_key_is_named(site, keys):
    _parsed, problems = JOIN_SITES[site](keys)
    assert any("unknown" in p and "1" in p for p in problems), problems


# ── criterion 8: a skill binding's value must look like a skill name ─────────

@pytest.mark.parametrize("name, bad", [
    ("my skill", True), ("../x", True), ("a\\b", True),
    ("tcw:work", False), ("documentation-sync", False),
])
def test_a_skill_binding_name_is_checked_for_shape(name, bad):
    _policy, problems = parse_lifecycle_policy(
        {"stages": {"verify": {"prompt": [{"skill": name}]}}})
    assert bool([p for p in problems if "is not a skill name" in p]) == bad, problems


def test_an_empty_skill_name_is_reported():
    _policy, problems = parse_lifecycle_policy(
        {"stages": {"verify": {"prompt": [{"skill": ""}]}}})
    assert [p for p in problems if "skill" in p], problems
