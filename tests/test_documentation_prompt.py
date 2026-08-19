"""Documentation entries reaching a stage prompt, and `tcw work docs`.

The back-compat half — that a node configuring nothing sees byte-identical
output — is pinned separately in `test_prompt_fallback.py`, against a fixture
captured before any of this existed.
"""

import hashlib
import json
import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.store.base import DocEntry
from tcw.work.resolve import (
    load_builtins, render_documentation, substitute_documentation,
)

ENTRIES = [
    DocEntry("README.md", "Public-API", "Public-facing overview and CLI usage."),
    DocEntry("docs/changelogs/upcoming.md", "Any-Code-Change",
             "Developer changelog; technical, grouped by category."),
]


# -- rendering --------------------------------------------------------------

def test_every_entry_appears_with_its_path_trigger_and_description():
    out = render_documentation(ENTRIES)
    for e in ENTRIES:
        assert e.path in out and e.trigger in out and e.description in out


def test_a_pipe_in_a_description_does_not_break_the_rendering():
    """The reason this is a list and not a Markdown table."""
    entry = DocEntry("a.md", "T", "fires on x | y | z")
    out = render_documentation([entry])
    assert "fires on x | y | z" in out
    assert out.count("\n") == render_documentation(
        [DocEntry("a.md", "T", "fires on x y z")]).count("\n")


def test_a_multiline_description_is_collapsed_to_one_line():
    """A YAML block scalar must not break out of its bullet."""
    entry = DocEntry("a.md", "T", "first line\nsecond line\n\nthird")
    out = render_documentation([entry])
    assert "first line second line third" in out


# -- substitution -----------------------------------------------------------

TEMPLATE = "3. {{tcw:documentation}}the old sentence\n   continued.{{/tcw:documentation}} Then more."


def test_with_nothing_configured_the_span_becomes_its_own_inner_text():
    assert substitute_documentation(TEMPLATE, ()) == (
        "3. the old sentence\n   continued. Then more.")


def test_with_entries_the_span_is_replaced():
    out = substitute_documentation(TEMPLATE, ENTRIES)
    assert "the old sentence" not in out
    assert "README.md" in out
    assert out.startswith("3. ")
    assert out.rstrip().endswith("Then more.")


def test_continuation_lines_are_indented_to_the_token_column():
    """A span inside a numbered item must render as part of that item."""
    out = substitute_documentation(TEMPLATE, ENTRIES)
    body = [ln for ln in out.splitlines()[1:] if ln.strip()]
    assert all(ln.startswith("   ") for ln in body), out


def test_an_unterminated_token_is_left_verbatim():
    """A malformed prompt should look wrong, not silently swallow its tail."""
    text = "before {{tcw:documentation}} after with no close"
    assert substitute_documentation(text, ENTRIES) == text
    assert substitute_documentation(text, ()) == text


def test_text_without_the_token_is_untouched():
    assert substitute_documentation("plain text", ENTRIES) == "plain text"


def test_both_shipped_prompts_carry_exactly_one_span():
    shipped = load_builtins().stage_prompts
    for stage in ("plan", "implement"):
        assert shipped[stage].count("{{tcw:documentation}}") == 1
        assert shipped[stage].count("{{/tcw:documentation}}") == 1
    for stage, text in shipped.items():
        if stage not in ("plan", "implement"):
            assert "{{tcw:documentation}}" not in text


# -- the CLI ----------------------------------------------------------------

def _node(tmp_path: Path, documentation=None) -> tuple[Path, str]:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(tmp_path), "config", k, v], check=True)
    subprocess.run(["tcw", "init", "--id", "docs-node", "work"], cwd=tmp_path,
                   capture_output=True, check=True, stdin=subprocess.DEVNULL)
    if documentation is not None:
        cfg = tmp_path / "tcw-config.yaml"
        conf = yaml.safe_load(cfg.read_text()) or {}
        conf.setdefault("work", {})["documentation"] = documentation
        cfg.write_text(yaml.safe_dump(conf, sort_keys=False))
    slug = subprocess.run(["tcw", "work", "new", "An item"], cwd=tmp_path,
                          capture_output=True, text=True, check=True,
                          stdin=subprocess.DEVNULL).stdout.strip()
    return tmp_path, slug


def _cli(root: Path, *argv):
    return subprocess.run(["tcw", *argv], cwd=root, capture_output=True,
                          text=True, stdin=subprocess.DEVNULL)


CONFIGURED = [
    {"path": "README.md", "trigger": "Public-API", "description": "Overview."},
    {"path": "docs/changelogs/upcoming.md", "trigger": "Any-Code-Change",
     "description": "Changelog."},
]


def test_a_configured_node_sees_its_entries_in_plan_and_implement(tmp_path):
    """Acceptance criterion 4."""
    root, slug = _node(tmp_path, CONFIGURED)
    r = _cli(root, "work", "stage", "plan", slug)
    assert r.returncode == 0, r.stderr
    for entry in CONFIGURED:
        assert entry["path"] in r.stdout
        assert entry["trigger"] in r.stdout
        assert entry["description"] in r.stdout
    assert "agent guide" not in r.stdout          # the fallback is gone

    _cli(root, "work", "start", slug)
    r = _cli(root, "work", "stage", "implement", slug)
    assert r.returncode == 0, r.stderr
    assert "README.md" in r.stdout and "agent guide" not in r.stdout


def test_an_unconfigured_node_still_names_the_agent_guide(tmp_path):
    root, slug = _node(tmp_path)
    r = _cli(root, "work", "stage", "plan", slug)
    assert r.returncode == 0, r.stderr
    assert "agent guide" in r.stdout
    assert "{{tcw:documentation}}" not in r.stdout


def test_a_stage_that_carries_no_span_is_unaffected(tmp_path):
    root, slug = _node(tmp_path, CONFIGURED)
    r = _cli(root, "work", "stage", "spec", slug)
    assert r.returncode == 0, r.stderr
    assert "README.md" not in r.stdout


# -- `tcw work docs` --------------------------------------------------------

def test_docs_lists_every_configured_entry(tmp_path):
    """Acceptance criterion 5."""
    root, _ = _node(tmp_path, CONFIGURED)
    r = _cli(root, "work", "docs")
    assert r.returncode == 0, r.stderr
    for entry in CONFIGURED:
        assert entry["path"] in r.stdout
        assert entry["trigger"] in r.stdout


def test_docs_json_reports_the_config_source(tmp_path):
    root, _ = _node(tmp_path, CONFIGURED)
    r = _cli(root, "work", "docs", "--json")
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["schema"] == 1
    assert payload["source"] == "config"
    assert [e["path"] for e in payload["entries"]] == [
        e["path"] for e in CONFIGURED]


def test_docs_json_on_an_unconfigured_node_says_agent_guide(tmp_path):
    """Acceptance criterion 6 — the branch that lets the skill fall back
    without guessing."""
    root, _ = _node(tmp_path)
    r = _cli(root, "work", "docs", "--json")
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["source"] == "agent-guide"
    assert payload["entries"] == []


def test_docs_on_an_unconfigured_node_says_so_on_stderr(tmp_path):
    root, _ = _node(tmp_path)
    r = _cli(root, "work", "docs")
    assert r.returncode == 0, r.stderr
    assert r.stdout == ""                     # nothing to list
    assert "agent guide" in r.stderr          # and the human is told where to look


def _manifest(root: Path) -> dict:
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and ".git" not in p.parts:
            out[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def test_docs_writes_nothing(tmp_path):
    """Acceptance criterion 7. Hashing every path, not `git status` — the tree is
    intentionally dirty during implementation, and a write-then-restore would
    pass a status check."""
    root, _ = _node(tmp_path, CONFIGURED)
    before = _manifest(root)
    assert _cli(root, "work", "docs").returncode == 0
    assert _cli(root, "work", "docs", "--json").returncode == 0
    assert _manifest(root) == before


def test_docs_needs_a_node(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    r = _cli(tmp_path, "work", "docs")
    assert r.returncode != 0
    assert r.stdout == ""                     # nothing on stdout on failure


# -- criteria 7a and 7b: where substitution does and does not happen --------

def test_a_span_in_an_artifact_template_is_left_verbatim(tmp_path):
    """Criterion 7a. Substitution is a prompt-role behavior; an artifact template
    must not be rewritten — and the two scaffold paths must agree, since
    `tcw work scaffold`'s implicit built-in fallback bypasses `_resolve_one`."""
    root, slug = _node(tmp_path, CONFIGURED)
    cfg = root / "tcw-config.yaml"
    conf = yaml.safe_load(cfg.read_text()) or {}
    conf["work"]["lifecycle"] = {"artifacts": {"spec": [
        {"blob": "template with {{tcw:documentation}}kept{{/tcw:documentation}}"}]}}
    cfg.write_text(yaml.safe_dump(conf, sort_keys=False))

    r = _cli(root, "work", "scaffold", "spec", slug)
    assert r.returncode == 0, r.stderr
    draft = Path(r.stdout.strip())
    assert "{{tcw:documentation}}" in draft.read_text(encoding="utf-8")


def test_a_span_in_a_project_prompt_binding_is_substituted(tmp_path):
    """Criterion 7b. Substitution runs over the composed text, so a project's own
    `blob:`/`file:` prompt gets it too — that is what makes this prompt
    generation rather than a built-in-only special case."""
    root, slug = _node(tmp_path, CONFIGURED)
    cfg = root / "tcw-config.yaml"
    conf = yaml.safe_load(cfg.read_text()) or {}
    conf["work"]["lifecycle"] = {"stages": {"spec": {"prompt": [
        {"blob": "ours: {{tcw:documentation}}fallback{{/tcw:documentation}}"}]}}}
    cfg.write_text(yaml.safe_dump(conf, sort_keys=False))

    r = _cli(root, "work", "stage", "spec", slug)
    assert r.returncode == 0, r.stderr
    assert "README.md" in r.stdout
    assert "fallback" not in r.stdout


def test_blank_lines_in_the_rendered_block_carry_no_indent():
    """Trailing whitespace on an otherwise-empty line is invisible and wrong."""
    out = substitute_documentation(TEMPLATE, ENTRIES)
    assert not any(line.strip() == "" and line != "" for line in out.splitlines())


def test_text_after_the_span_resumes_at_the_list_indent():
    """Not one column deeper. At four spaces after a list, CommonMark reads the
    continuation as a code block rather than prose — so this is a rendering
    correctness check, not a cosmetic one."""
    out = substitute_documentation(TEMPLATE, ENTRIES)
    tail = out.splitlines()[-1]
    assert tail == "   Then more.", repr(tail)


def test_the_shipped_prompts_render_without_a_code_block_hazard():
    """The same check against the real `implement` prompt, which is the one that
    carries prose after its span."""
    shipped = load_builtins().stage_prompts["implement"]
    out = substitute_documentation(shipped, ENTRIES)
    for line in out.splitlines():
        assert not line.startswith("    - "), "list item indented into a code block"
        if line.strip() and not line.startswith(("-", "#", "*", "|")):
            assert not line.startswith("    ") or line.startswith("     "), (
                f"prose at a code-block indent: {line!r}")
