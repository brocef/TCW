"""Every configuration key is documented once, in the `configure` skill, and
the table of who may set each key matches the code (TCW-75 spec, acceptance
criteria 6 and 7).

`skills/configure/references/` is the one place a configuration key is
documented. Each key path has its own `##` or `###` heading in exactly one
reference, and the section's first line says who may set it: `Shared:`,
`Overridable:` or `Personal only:`. `personal.md` holds one table of every key
path with the same label, and the labels other than `Shared` are exactly
`tcw.config.PERSONAL_KEYS`.

The key paths are listed here by hand, so a key that no parser accepts any
more fails `test_each_work_key_path_is_accepted`; a key a parser starts
accepting later is not caught, and is shared by default (spec, Risks).
"""

import copy
import re
import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.config import PERSONAL_KEYS, load_config
from tcw.work.layout import front_matter
from tests.doc_vocabulary import PATTERNS, scan
from tests.test_docs_describe_3_0 import FENCE, HEADING, links

REPO = Path(__file__).resolve().parent.parent
ROUTER = REPO / "skills/configure/SKILL.md"
REFERENCES = REPO / "skills/configure/references"
PERSONAL = REFERENCES / "personal.md"

# Every configuration key path (criterion 7). `*` is a name the project
# chooses: a stage, a procedure or a project ID.
KEY_PATHS = (
    "id", "user.name",
    "taxonomy.path", "taxonomy.repository", "taxonomy.extends",
    "capabilities.path", "capabilities.repository", "capabilities.extends",
    "work.path", "work.repository", "work.backend", "work.tags",
    "work.documentation", "work.procedures.*",
    *(f"work.stages.*.{key}" for key in ("enabled", "status", "prompt", "pre", "post")),
    "work.hooks.timeout", "work.hooks.output-cap",
    *(f"work.jira.{key}" for key in ("site", "project", "issue-type", "inbox-query",
                                     "timeout", "priorities")),
    "work.jira.credentials.email-env", "work.jira.credentials.token-env",
    *(f"work.jira.fields.{key}" for key in ("project", "item", "effort", "complexity")),
    *(f"projects.{relation}.*.{key}" for relation in ("parent", "children", "upstream")
      for key in ("path", "repository")),
    *(f"projects.{relation}.*.jira.{key}" for relation in ("parent", "children", "upstream")
      for key in ("site", "project", "inbox-status", "credentials.email-env",
                  "credentials.token-env", "fields.project")),
)

LABELS = ("Shared", "Overridable", "Personal only")


def test_the_key_path_list_has_no_repeats():
    assert len(KEY_PATHS) == len(set(KEY_PATHS)) == 57


# ── criterion 6: the router and its references ───────────────────────────────


def _router_targets() -> list[str]:
    text = ROUTER.read_text(encoding="utf-8")
    table = "\n".join(line for line in text.splitlines() if line.startswith("|"))
    return [target for _, target in links(table)]


def test_every_reference_is_linked_from_the_router():
    linked = {(ROUTER.parent / t).resolve() for t in _router_targets()}
    present = {p.resolve() for p in REFERENCES.glob("*.md")}
    assert present - linked == set(), f"not in the router: {sorted(present - linked)}"


def test_every_router_link_resolves():
    targets = _router_targets()
    assert targets
    missing = [t for t in targets if not (ROUTER.parent / t).is_file()]
    assert not missing, f"router links to nothing: {missing}"


def test_the_tracker_reference_is_gone():
    assert not (REFERENCES / "tracker.md").exists()


@pytest.mark.parametrize("key", ("description", "when_to_use"))
def test_the_router_frontmatter_names_no_2x_vocabulary(key):
    meta = front_matter(ROUTER.read_text(encoding="utf-8"))
    hits = scan(str(meta[key]), PATTERNS)
    assert not hits, f"{key}: {[h.text for h in hits]}"


def _sections(text: str) -> list[tuple[int, str, list[str]]]:
    """Each heading outside fenced code: its level, its text, and the lines
    up to the next heading."""
    blanked = FENCE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    lines, plain = text.splitlines(), blanked.splitlines()
    starts = [(i, HEADING.match(line)) for i, line in enumerate(plain)]
    starts = [(i, m) for i, m in starts if m]
    out = []
    for n, (i, m) in enumerate(starts):
        end = starts[n + 1][0] if n + 1 < len(starts) else len(lines)
        level = len(plain[i]) - len(plain[i].lstrip("#"))
        out.append((level, m.group(1), lines[i + 1:end]))
    return out


def _table() -> dict[str, list[str]]:
    """`personal.md`'s table: each key path with every label a row gives it."""
    rows: dict[str, list[str]] = {}
    for line in PERSONAL.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|", line)
        if m:
            rows.setdefault(m.group(1), []).append(m.group(2))
    return rows


@pytest.mark.parametrize("key", KEY_PATHS)
def test_each_key_has_one_heading_with_its_label(key):
    found = []
    for reference in sorted(REFERENCES.glob("*.md")):
        for level, heading, body in _sections(reference.read_text(encoding="utf-8")):
            if level in (2, 3) and f"`{key}`" in heading:
                found.append((reference.name, heading, body))
    assert len(found) == 1, f"`{key}` has {len(found)} headings: " \
        f"{[(name, heading) for name, heading, _ in found]}"
    name, heading, body = found[0]
    first = next((line.strip() for line in body if line.strip()), "")
    labels = _table().get(key, [])
    assert len(labels) == 1, f"personal.md's table gives `{key}` {labels}"
    assert first.startswith(f"{labels[0]}:"), \
        f"{name}, under {heading!r}, starts {first!r}, not {labels[0]}:"


# ── criterion 7: the table matches the code ───────────────────────────────────


def test_the_table_has_one_row_per_key_path():
    rows = _table()
    repeated = {k: v for k, v in rows.items() if len(v) != 1}
    assert not repeated, f"repeated rows: {repeated}"
    assert set(rows) == set(KEY_PATHS), (f"extra rows: {sorted(set(rows) - set(KEY_PATHS))}; "
                                         f"missing rows: {sorted(set(KEY_PATHS) - set(rows))}")
    bad = {k: v[0] for k, v in rows.items() if v[0] not in LABELS}
    assert not bad, f"unknown labels: {bad}"


def test_the_personal_rows_are_the_allowlist():
    rows = {k: v[0] for k, v in _table().items()}
    assert {k for k, label in rows.items() if label != "Shared"} == set(PERSONAL_KEYS)
    assert {k for k, label in rows.items() if label == "Personal only"} == {"user.name"}


# The sample value each `work.*` key path is set to (plan, choice 6). A path
# under `work.jira`, and a stage's `status`, are loaded in Jira mode, with a
# complete `work.jira` block and a status for every stage that needs one.
JIRA_BASE = {
    "backend": "jira",
    "jira": {
        "site": "https://example.atlassian.net",
        "project": "TCW",
        "credentials": {"email-env": "TCW_JIRA_EMAIL", "token-env": "TCW_JIRA_TOKEN"},
        "fields": {"project": "customfield_1", "item": "customfield_2",
                   "effort": "customfield_3", "complexity": "customfield_4"},
    },
    "stages": {stage: {"status": status} for stage, status in (
        ("inbox", "Inbox"), ("request", "Request"), ("spec", "Specifying"),
        ("plan", "Planning"), ("implement", "In Progress"), ("review", "In Review"),
        ("qa", "In QA"), ("completed", "Done"), ("discarded", "Discarded"))},
}

SAMPLES = {
    "work.path": "tcw-work",
    "work.repository": {"url": "https://example.com/store.git", "ref": "main"},
    "work.backend": "filesystem",
    "work.tags": ["auth"],
    "work.documentation": [],
    "work.procedures.*": [{"blob": "hello"}, {"inherit": True}],
    "work.stages.*.enabled": True,
    "work.stages.*.status": "Specifying",
    "work.stages.*.prompt": [{"inherit": True}],
    "work.stages.*.pre": [{"command": "true"}],
    "work.stages.*.post": [{"command": "true"}],
    "work.hooks.timeout": 60,
    "work.hooks.output-cap": 1000,
    "work.jira.issue-type": "Task",
    "work.jira.inbox-query": 'status = "To Do"',
    "work.jira.timeout": 30,
    "work.jira.priorities": {"highest": "Highest", "high": "High", "medium": "Medium",
                             "low": "Low", "lowest": "Lowest"},
}

# What `*` stands for in a sample.
CHOSEN = {"work.stages.*": "work.stages.spec", "work.procedures.*": "work.procedures.search"}

WORK_PATHS = [k for k in KEY_PATHS if k.startswith("work.")]


def _sample(key: str):
    if key in SAMPLES:
        return SAMPLES[key]
    # The rest of `work.jira` takes the base block's own value.
    value = {"work": JIRA_BASE}
    for part in key.split("."):
        value = value[part]
    return copy.deepcopy(value)


def _set(mapping: dict, key: str, value) -> None:
    for prefix, chosen in CHOSEN.items():
        if key.startswith(prefix):
            key = chosen + key[len(prefix):]
    *parents, last = key.split(".")
    for part in parents:
        mapping = mapping.setdefault(part, {})
    mapping[last] = value


@pytest.mark.parametrize("key", WORK_PATHS)
def test_each_work_key_path_is_accepted(key, tmp_path, monkeypatch):
    monkeypatch.setenv("TCW_NO_PERSONAL_CONFIG", "1")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    jira = key.startswith("work.jira.") or key == "work.stages.*.status"
    config = {"id": "x", "work": copy.deepcopy(JIRA_BASE) if jira else {}}
    _set(config, key, _sample(key))
    (tmp_path / "tcw-config.yaml").write_text(yaml.safe_dump(config, sort_keys=False),
                                              encoding="utf-8")
    problems = [str(p) for p in load_config(tmp_path).problems]
    assert not problems, f"{key} set to {_sample(key)!r}: {problems}"
