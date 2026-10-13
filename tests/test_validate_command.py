"""`tcw validate` from the command line (TCW-73 Design 6; AC 14, 15).

Findings on stdout, one per line as `<severity>: <where>: <message>`; the
closing count on stderr; exit 1 only when a finding is an error. The Jira
cases of AC 15 are in `tests/work/jira/test_jira_validate_remote.py`.
"""

import shutil

import pytest
import yaml

from tcw.cli import main
from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore, init
from tests.work.projects import connect, make_project, write_item


@pytest.fixture
def run(monkeypatch, capsys):
    def run(root, *argv):
        monkeypatch.chdir(root)
        code = main(["validate", *argv])
        printed = capsys.readouterr()
        return code, printed.out.splitlines(), printed.err
    return run


@pytest.fixture
def project(tmp_path):
    root = make_project(tmp_path, "p")
    init(["taxonomy", "capabilities"], root, "p")
    return root


def about(lines, text):
    return [line for line in lines if text in line]


def test_a_missing_blocker_is_a_warning(project, run):
    write_item(project, "2026-10-01-a", {"title": "a", "stage": "request",
                                        "blocked-by": ["2026-10-01-nothing"]})
    code, out, _ = run(project)
    [line] = about(out, "2026-10-01-nothing")
    assert line.startswith("warning: ") and code == 0


def test_a_blocker_in_an_unreachable_project_is_unresolved(tmp_path, run):
    p = make_project(tmp_path, "p")
    q = make_project(tmp_path, "q")
    connect(p, q, "children")
    connect(q, p, "parent")
    write_item(p, "2026-10-01-a", {"title": "a", "stage": "request",
                                  "blocked-by": ["q/2026-10-01-x"]})
    shutil.rmtree(q)
    code, out, _ = run(p)
    [line] = about(out, "q/2026-10-01-x")
    assert line.startswith("unresolved: ") and code == 0
    # The absent project itself is one more `unresolved` line, not exit 5.
    assert [l for l in out if l.startswith("unresolved: ") and "'q'" in l]


def test_a_blocker_in_a_project_that_cannot_be_read_is_a_warning(tmp_path, run):
    """Plan choice 9: the project is here, so not `unresolved`; its fault is
    its own, so not an error in this project's run."""
    p = make_project(tmp_path, "p")
    q = make_project(tmp_path, "q", config={"backend": "carrier-pigeon"})
    connect(p, q, "children")
    connect(q, p, "parent")
    write_item(p, "2026-10-01-a", {"title": "a", "stage": "request",
                                  "blocked-by": ["q/2026-10-01-x"]})
    code, out, _ = run(p)
    [line] = about(out, "q/2026-10-01-x")
    assert line.startswith("warning: ") and "tcw validate" in line, line
    assert code == 0, out


def test_an_unknown_records_key_is_an_error(project, run):
    folder = write_item(project, "2026-10-01-a", {"title": "a", "stage": "spec"})
    (folder / "capabilities.yaml").write_text("added: [x/y]\n")
    code, out, _ = run(project)
    [line] = about(out, "capabilities.yaml")
    assert line.startswith("error: ") and "2026-10-01-a/capabilities.yaml" in line
    assert code == 1


def test_an_undelivered_new_path_is_not_a_finding(project, run):
    folder = write_item(project, "2026-10-01-a", {"title": "a", "stage": "spec"})
    (folder / "capabilities.yaml").write_text("new: [x/y]\n")
    _, out, _ = run(project)
    assert about(out, "capabilities.yaml") == [] and about(out, "x/y") == []


def test_malformed_records_on_a_completed_item_come_from_the_file_scan(project, run):
    folder = write_item(project, "2026-10-01-a", {"title": "a", "stage": "completed"})
    (folder / "capabilities.yaml").write_text("new: [x/y\n")
    code, out, _ = run(project)
    [line] = about(out, "capabilities.yaml")
    assert line.startswith("error: ") and code == 1
    assert "while parsing" in line or "expected" in line, line


def test_an_absent_declared_project_is_unresolved_not_exit_5(tmp_path, run):
    p = make_project(tmp_path, "p")
    config = yaml.safe_load((p / "tcw-config.yaml").read_text())
    config["connected-projects"] = {"children": {"gone": "../gone"}}
    (p / "tcw-config.yaml").write_text(yaml.safe_dump(config))
    code, out, _ = run(p)
    [line] = about(out, "'gone'")
    assert line.startswith("unresolved: ") and code == 0


def _round(folder, stage, number, front):
    (folder / stage).mkdir(exist_ok=True)
    (folder / stage / f"round-{number}.md").write_text(f"---\n{front}---\nNotes.\n")


def test_an_invalid_latest_round_is_a_warning_naming_it(project, run):
    folder = write_item(project, "2026-10-01-a", {"title": "a", "stage": "review"})
    _round(folder, "review", 1, "verdict: accepted\n")
    code, out, _ = run(project)
    [line] = about(out, "round-1.md")
    assert line.startswith("warning: ") and "review/round-1.md" in line
    assert "review" in line and code == 0


def test_an_older_invalid_round_is_history(project, run):
    folder = write_item(project, "2026-10-01-a", {"title": "a", "stage": "review"})
    _round(folder, "review", 1, "verdict: accepted\n")
    _round(folder, "review", 2, "verdict: rejected\njudges: 0\n")
    _, out, _ = run(project)
    assert about(out, "round-") == []


def test_a_retired_capability_field_is_an_error(project, run):
    FsCapabilitiesStore.open(project).add("ns/thing")
    meta = project / "docs" / "capabilities" / "ns" / "thing" / "meta.yaml"
    meta.write_text(meta.read_text() + "Planning doc: x\n")
    code, out, _ = run(project)
    [line] = about(out, "Planning doc")
    assert line.startswith("error: docs/capabilities/ns/thing: ")
    assert "docs/migration-guide-2.8-to-3.0.0.md" in line and code == 1


def test_an_unparsable_item_does_not_stop_the_other_checks(project, run):
    bad = write_item(project, "2026-10-01-bad", {"title": "b", "stage": "request"})
    (bad / "item.yaml").write_text("title: [unclosed\n")
    write_item(project, "2026-10-01-a", {"title": "a", "stage": "request",
                                        "blocked-by": ["2026-10-01-nothing"]})
    code, out, _ = run(project)
    [unreadable] = about(out, "2026-10-01-bad/item.yaml")
    assert unreadable.startswith("error: ")
    assert about(out, "2026-10-01-nothing")
    assert code == 1


def test_a_dangling_relates_to_is_an_error(project, run):
    FsTaxonomyStore.open(project).add("Payment")
    meta = project / "docs" / "taxonomy" / "payment" / "meta.yaml"
    meta.write_text(meta.read_text().replace("relatesTo: []", "relatesTo: [invoice]"))
    code, out, _ = run(project)
    [line] = about(out, "invoice")
    assert line.startswith("error: ") and code == 1


def test_an_unresolvable_subject_is_an_error(project, run):
    FsCapabilitiesStore.open(project).add("ns/thing")
    meta = project / "docs" / "capabilities" / "ns" / "thing" / "meta.yaml"
    meta.write_text(meta.read_text() + "Subject: nosuch\n")
    code, out, _ = run(project)
    [line] = about(out, "nosuch")
    assert line.startswith("error: ") and code == 1


def test_a_finding_is_one_line_however_its_message_runs(project, run):
    (project / "docs" / "work" / "notes.yaml").write_text("a: [b\n")
    _, out, _ = run(project)
    [line] = [l for l in about(out, "notes.yaml") if l.startswith("error: ")]
    assert "line 1" in line


def test_the_count_is_on_stderr_and_a_clean_run_prints_nothing(project, run):
    code, out, err = run(project)
    assert (code, out) == (0, [])
    assert err.splitlines()[-1] == "0 errors, 0 warnings, 0 unresolved"
    write_item(project, "2026-10-01-a", {"title": "a", "stage": "request",
                                        "blocked-by": ["2026-10-01-nothing"]})
    code, out, err = run(project)
    assert err.splitlines()[-1] == "0 errors, 1 warning, 0 unresolved"
    assert not any("warning," in line for line in out)


def test_remote_in_filesystem_mode_is_a_usage_error(project, run):
    code, out, _ = run(project, "--remote")
    assert (code, out) == (2, [])


@pytest.mark.parametrize("argv", [["docs"], ["--no-recurse"]])
def test_the_removed_spellings(project, monkeypatch, argv):
    monkeypatch.chdir(project)
    with pytest.raises(SystemExit) as stop:
        main(["validate", *argv])
    assert stop.value.code == 2
