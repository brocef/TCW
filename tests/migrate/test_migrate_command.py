"""`tcw migrate` as a command: its form, which project it runs in, and the
checks it is spared (TCW-116 Design 1.1, 1.2, 1.5, 8.1; criteria 1-3).

Every run is in-process (`tests/objectcli.py`'s `tcw`), so a test can patch
what a run calls; standard output is checked empty in every case.
"""

from __future__ import annotations

from pathlib import Path

from tcw.errors import NO_PROJECT
from tcw.project_files import legacy_message
from tests.objectcli import tcw  # noqa: F401  (a fixture)
from tests.projectfiles import write_config


def _three_x(root: Path, text: str = "id: app\n") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "tcw-config.yaml").write_text(text, encoding="utf-8")
    return root


def test_help_shows_the_two_flags_and_no_argument(tcw, tmp_path):
    done = tcw(["migrate", "--help"], tmp_path)
    assert done.code == 0
    usage = done.out.split("\n\n")[0]
    assert "[--dry-run]" in usage and "[--no-jira]" in usage
    assert usage.split("migrate", 1)[1].split() == ["[-h]", "[--dry-run]", "[--no-jira]"]


def test_an_argument_is_a_usage_error(tcw, tmp_path):
    done = tcw(["migrate", "x"], _three_x(tmp_path / "app"))
    assert done.code == 2
    assert done.out == ""


def test_outside_any_project_it_exits_1_with_the_common_message(tcw, tmp_path):
    done = tcw(["migrate", "--dry-run"], tmp_path)
    assert done.code == 1
    assert NO_PROJECT in done.err
    assert done.out == ""


def test_a_3x_project_is_not_refused_while_other_commands_are(tcw, tmp_path):
    app = _three_x(tmp_path / "app")
    done = tcw(["migrate", "--dry-run"], app)
    assert done.code == 0, done.err
    assert done.out == ""
    assert legacy_message(app.resolve()) not in done.err
    refused = tcw(["work", "list"], app)
    assert refused.code == 1
    assert legacy_message(app.resolve()) in refused.err


def test_dash_c_into_a_3x_project_runs_as_if_started_there(tcw, tmp_path):
    app = _three_x(tmp_path / "app")
    here = tmp_path / "here"
    write_config(here, "id: here\n")
    direct = tcw(["migrate", "--dry-run"], app)
    through = tcw(["-C", str(app), "migrate", "--dry-run"], here)
    assert (through.code, through.err, through.out) == (direct.code, direct.err, direct.out)


def test_a_configuration_problem_does_not_refuse_it(tcw, tmp_path):
    app = tmp_path / "app"
    write_config(app, "id: app\nwork:\n  no_such_key: 1\n")
    assert tcw(["work", "list"], app).code == 1
    done = tcw(["migrate", "--dry-run"], app)
    assert done.code == 0, done.err
    assert done.out == ""


# ── Step 10: the planned files checked, the check after the run, the summary ──

import yaml  # noqa: E402

from tests.migrate import fixtures  # noqa: E402
from tests.migrate.fixtures import build_f_single, snapshot  # noqa: E402

NOT_CHECKED_WORK = ("work store not checked after the run (--no-jira): run 'tcw validate' "
                    "to check it")
KNOWN_AFTER = ("tcw validate's findings on the converted project are known only after "
               "a real run")


def a12(done) -> list[str]:
    return [line for line in done.err.splitlines() if line.startswith("  A12 ")]


def test_b3_a_planned_configuration_4_0_refuses(tcw, tmp_path):
    root = _three_x(tmp_path / "app", "id: app\nwork:\n  stages:\n    spec:\n"
                                      "      status: 5\n")
    before = snapshot(root, times=False)
    for argv in (["migrate", "--dry-run"], ["migrate"]):
        done = tcw(argv, root)
        assert done.code == 3, done.err
        assert ("  B3 .tcw/tcw-config.yaml: TCW 4 would refuse the file as planned: "
                "work.stages.spec.status: 'status' maps a stage to a Jira status and is "
                "only read with `backend: jira`") in done.err
    assert snapshot(root, times=False) == before


def test_b3_a_planned_state_file_4_0_refuses(tcw, tmp_path, monkeypatch):
    from tcw import object_folders
    root = _three_x(tmp_path / "app")
    (root / "docs/taxonomy/invoice").mkdir(parents=True)
    (root / "docs/taxonomy/invoice/meta.yaml").write_text("name: Invoice\n")
    real = object_folders.parse_state_text

    def refusing(text, file):
        if str(file).endswith("invoice/tcw-taxonomy.yaml"):
            return None, "made to refuse"
        return real(text, file)
    monkeypatch.setattr(object_folders, "parse_state_text", refusing)
    before = snapshot(root, times=False)
    done = tcw(["migrate"], root)
    assert done.code == 3, done.err
    assert ("  B3 docs/taxonomy/invoice/tcw-taxonomy.yaml: TCW 4 would refuse the file "
            "as planned: made to refuse") in done.err
    assert snapshot(root, times=False) == before


def test_a12_lists_what_tcw_validate_finds_and_no_report_predicts(tcw, tmp_path, monkeypatch):
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG")
    import os
    root = build_f_single(tmp_path / "app", backend="files",
                          config_home=Path(os.environ["XDG_CONFIG_HOME"]))
    dry = tcw(["migrate", "--dry-run"], root)
    assert a12(dry) == [] and KNOWN_AFTER in dry.err.splitlines()
    done = tcw(["migrate"], root)
    assert done.code == 0, done.err
    assert a12(done) == [f"  A12 {where}: {text}" for where, text in fixtures.F_SINGLE_A12]
    # `tcw validate` then gives exactly the A reports the run gave: A1, A5, A12.
    found = tcw(["validate"], root)
    lines = found.out.splitlines()
    assert len(lines) == 3
    assert any("is not its folder's name" in line for line in lines)           # A1
    assert any("not_tags" in line for line in lines)                          # A5
    assert any(fixtures.F_SINGLE_A12[0][1] in line for line in lines)           # A12


def test_a_finding_of_another_kind_in_a_reported_file_is_not_absorbed(tcw, tmp_path):
    root = build_f_single(tmp_path / "app", backend="files")
    meta = root / "docs/capabilities/cli/v/meta.yaml"
    meta.write_text(meta.read_text() + "Roles: 5\n")
    done = tcw(["migrate"], root)
    assert done.code == 0, done.err
    assert any(line.startswith("  A2 docs/capabilities/cli/v/resources/meta.yaml")
               for line in done.err.splitlines())
    assert any(line.startswith("  A12 docs/capabilities/cli/v: Roles")
               for line in a12(done)), done.err


def test_the_summary_counts_the_changes(tcw, tmp_path):
    root = build_f_single(tmp_path / "app", backend="files")
    dry = tcw(["migrate", "--dry-run"], root)
    said = dry.err.splitlines()
    written = len({line.split(" ")[2].rstrip(":") for line in said
                   if line.startswith("would write ")})
    moved = sum(line.startswith("would move ") for line in said)
    deleted = sum(line.startswith("would delete ") for line in said)
    assert (f"would change: {written} files written, {moved} moved, {deleted} deleted; "
            f"0 tickets edited") in said
    done = tcw(["migrate"], root)
    assert (f"changed: {written} files written, {moved} moved, {deleted} deleted; "
            f"0 tickets edited") in done.err.splitlines()


def test_no_jira_leaves_the_work_store_out_of_the_check_after(tcw, tmp_path, monkeypatch):
    import tcw.validate as checks
    real = checks.validate
    seen = []

    def spy(*args, **kwargs):
        seen.append(kwargs.get("work", True))
        return real(*args, **kwargs)
    monkeypatch.setattr(checks, "validate", spy)
    jira = tcw(["migrate", "--no-jira"], build_f_single(tmp_path / "jira"))
    assert jira.code == 0, jira.err
    assert seen == [False]
    assert jira.err.splitlines()[-1] == NOT_CHECKED_WORK
    assert a12(jira) == [f"  A12 {where}: {text}" for where, text in fixtures.F_SINGLE_A12]
    seen.clear()
    files = tcw(["migrate", "--no-jira"], build_f_single(tmp_path / "files", backend="files"))
    assert files.code == 0, files.err
    assert seen == [True] and NOT_CHECKED_WORK not in files.err


def test_validate_without_the_work_store_changes_nothing_else(tmp_path, tcw):
    from tcw.validate import validate
    root = build_f_single(tmp_path / "app", backend="files")
    assert tcw(["migrate", "--no-jira"], root).code == 0
    item = root / "docs/work/2026-10-01-a/tcw-work-item.yaml"
    item.write_text(item.read_text() + "parent: 5\n")
    full = validate(root)
    without = validate(root, work=False)
    assert without == [f for f in full if "docs/work" not in f.where]
    assert len(full) > len(without)
