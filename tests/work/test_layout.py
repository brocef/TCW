"""Item-folder layout, rounds, handoffs and verdicts (TCW-69 Design 4; AC 15)."""

from datetime import datetime, timedelta, timezone

import pytest

from tcw.errors import Refused, UsageError
from tcw.work.layout import HANDOFF_NAME, Layout, Verdict, round_verdict
from tcw.work.model import STAGES, Slug

ALL = frozenset(s.name for s in STAGES)
SLUG = Slug("tcw", "1-thing")
NOW = datetime(2026, 10, 2, 13, 4, 5, tzinfo=timezone.utc)


@pytest.fixture
def layout(tmp_path):
    return Layout(tmp_path / "work", ALL, frozenset())


def write(path, text=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def verdict(state, judges):
    return f"---\nverdict: {state}\njudges: {judges}\n---\n\nnotes\n"


def snapshot(root):
    return sorted(str(p) for p in root.rglob("*")) if root.exists() else []


def test_folders_and_documents(layout, tmp_path):
    item = tmp_path / "work" / "1-thing"
    assert layout.path(SLUG) == item
    assert layout.path(SLUG, "spec") == item / "spec" / "spec.md"
    assert layout.path(SLUG, "review") == item / "review"
    assert layout.capabilities_file(SLUG) == item / "capabilities.yaml"


@pytest.mark.parametrize("existing, expected", [
    ([1, 2], "round-3.md"), ([1, 5], "round-6.md"), ([], "round-1.md")])
def test_the_next_round(layout, existing, expected):
    for n in existing:
        write(layout.stage_dir(SLUG, "review") / f"round-{n}.md")
    assert layout.path(SLUG, "review", next=True).name == expected


def test_only_round_n_files_are_rounds(layout):
    folder = layout.stage_dir(SLUG, "review")
    for name in ("round-01.md", "Round-2.md", "round-3-draft.md", "round-0.md",
                 "notes.md"):
        write(folder / name)
    write(folder / "round-4.md")
    assert [n for n, _ in layout.rounds(SLUG, "review")] == [4]
    assert layout.latest_round(SLUG, "review")[0] == 4


def test_handoffs(layout):
    path = layout.path(SLUG, "implement", handoff=True, now=NOW)
    assert path.name == "handoff-20261002T130405Z.md"
    assert HANDOFF_NAME.match(path.name)
    assert layout.latest_handoff(SLUG, "implement") is None
    write(path)
    later = write(layout.stage_dir(SLUG, "implement")
                  / "handoff-20261002T130406Z.md")
    assert layout.latest_handoff(SLUG, "implement") == later


def test_a_handoff_time_is_written_in_utc(layout):
    local = NOW.astimezone(timezone(timedelta(hours=-7)))
    assert layout.path(SLUG, "plan", handoff=True, now=local).name == \
        "handoff-20261002T130405Z.md"


def test_a_handoff_that_exists_is_refused(layout):
    write(layout.path(SLUG, "implement", handoff=True, now=NOW))
    with pytest.raises(Refused):
        layout.path(SLUG, "implement", handoff=True, now=NOW)


def test_external_and_fileless_stages_are_refused(tmp_path):
    layout = Layout(tmp_path, ALL, frozenset({"request", "qa"}), backend="Jira")
    with pytest.raises(Refused, match="Jira"):
        layout.path(SLUG, "qa")
    with pytest.raises(Refused):
        layout.path(SLUG, "inbox")
    with pytest.raises(Refused):
        layout.path(SLUG, "completed")


def test_a_disabled_or_unknown_stage_is_a_usage_error(tmp_path):
    layout = Layout(tmp_path, ALL - {"plan"}, frozenset())
    with pytest.raises(UsageError):
        layout.path(SLUG, "plan")
    with pytest.raises(UsageError):
        layout.path(SLUG, "bogus")


def test_next_and_handoff_misuse_is_a_usage_error(layout):
    with pytest.raises(UsageError):
        layout.path(SLUG, "spec", next=True)
    with pytest.raises(UsageError):
        layout.path(SLUG, "review", next=True, handoff=True)
    with pytest.raises(UsageError):
        layout.path(SLUG, next=True)


def test_path_creates_nothing(layout, tmp_path):
    for stage in ("spec", "review", "implement"):
        layout.path(SLUG, stage)
    layout.path(SLUG, "review", next=True)
    layout.path(SLUG, "review", handoff=True, now=NOW)
    layout.path(SLUG)
    assert snapshot(tmp_path) == []


@pytest.mark.parametrize("text, expected", [
    (verdict("accepted", 2), Verdict("accepted", 2)),
    (verdict("rejected", 0), Verdict("rejected", 0)),
    ("no front matter\n", Verdict("invalid", None)),
    ("---\nverdict: maybe\njudges: 1\n---\n", Verdict("invalid", None)),
    ("---\nverdict: accepted\n---\n", Verdict("invalid", None)),
    ("---\nverdict: accepted\njudges: true\n---\n", Verdict("invalid", None)),
    ("---\nverdict: accepted\njudges: -1\n---\n", Verdict("invalid", None)),
    ("---\nverdict: accepted\njudges: '2'\n---\n", Verdict("invalid", None)),
    ("---\nverdict: [accepted\njudges: 1\n---\n", Verdict("invalid", None)),
    ("---\n- a list\n---\n", Verdict("invalid", None)),
    ("---\nverdict: accepted\njudges: 1\n", Verdict("invalid", None)),
])
def test_round_verdicts(tmp_path, text, expected):
    assert round_verdict(write(tmp_path / "round-1.md", text)) == expected


def test_current_verdict_none_accepted_rejected_invalid(layout):
    assert layout.current_verdict(SLUG, "review") == "none"
    write(layout.stage_dir(SLUG, "review") / "round-1.md", verdict("rejected", 0))
    assert layout.current_verdict(SLUG, "review") == "rejected"
    write(layout.stage_dir(SLUG, "review") / "round-2.md", verdict("accepted", 0))
    assert layout.current_verdict(SLUG, "review") == "accepted"
    write(layout.stage_dir(SLUG, "review") / "round-3.md", "oops")
    assert layout.current_verdict(SLUG, "review") == "invalid"


def test_a_verdict_about_an_older_implementation_is_stale(layout):
    write(layout.stage_dir(SLUG, "implement") / "round-1.md")
    write(layout.stage_dir(SLUG, "review") / "round-1.md", verdict("accepted", 1))
    assert layout.current_verdict(SLUG, "review") == "accepted"
    write(layout.stage_dir(SLUG, "implement") / "round-2.md")
    assert layout.current_verdict(SLUG, "review") == "stale"
