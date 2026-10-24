"""Carrying out a plan, stopping, and finishing it by running again (TCW-116
Design 2.4-2.8; plan Step 3).

Every plan here is written by hand, before any conversion exists, so the
riskiest part of the command is tested alone: the order of the writes, the
progress record, what a re-run finds done, and blocker B17.
"""

from __future__ import annotations

import errno
import io
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from tcw.migrate import cli, execute, progress, report
from tcw.migrate.model import ABSENT, Delete, Move, Plan, Write, digest
from tests.move_stops import Fixture, every_stop

META = "name: X\nStatus: Supported\n"
STATE = "tcw-version: 4.0.0\nname: X\nStatus: Supported\n"
CONFIG_3X = "id: app\n"
CONFIG_4 = "tcw-version: 4.0.0\nid: app\n"


@dataclass
class Ran:
    code: int
    out: str
    err: str


def three_x(root: Path) -> Path:
    """A small tree for the hand-made plan below to convert."""
    files = {"tcw-config.yaml": CONFIG_3X,
             "docs/capabilities/ov/meta.yaml": "name: Login\n",
             "docs/capabilities/ov/description.md": "Logs in.\n",
             "docs/capabilities/x/meta.yaml": META,
             "docs/capabilities/x/camera.md": "The camera.\n"}
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text)
    return root


def hand_plan(root: Path) -> Plan:
    """Eight steps, one of each kind Design 2.4 orders, read from `root`."""
    def now(rel: str) -> str:
        return digest((root / rel).read_bytes())
    caps = "docs/capabilities"
    return Plan("app", "jira", steps=[
        Write(".tcw/tcw-migration.yaml", "A", ABSENT, "tcw-version: 4.0.0\nmoved: {}\n",
              ("C10",)),
        Write(".tcw/.gitignore", "A", ABSENT, "/tcw-migration-progress.yaml\n", ("C1",)),
        Move(f"{caps}/ov", f"{caps}/auth", "B",
             (("description.md", now(f"{caps}/ov/description.md")),
              ("meta.yaml", now(f"{caps}/ov/meta.yaml"))), ("C14",)),
        Move(f"{caps}/x/camera.md", f"{caps}/x/resources/camera.md", "B",
             (("", now(f"{caps}/x/camera.md")),), ("C13",)),
        Write(f"{caps}/x/tcw-capability.yaml", "C", ABSENT, STATE, ("C9",),
              ((f"{caps}/x/meta.yaml", now(f"{caps}/x/meta.yaml")),)),
        Delete(f"{caps}/x/meta.yaml", "C", now(f"{caps}/x/meta.yaml"),
               f"{caps}/x/tcw-capability.yaml", digest(STATE), ("C9",)),
        Write(".tcw/tcw-config.yaml", "D", ABSENT, CONFIG_4, ("C1",)),
        Delete("tcw-config.yaml", "E", now("tcw-config.yaml"), ".tcw/tcw-config.yaml",
               digest(CONFIG_4), ("C1",)),
    ])


@pytest.fixture
def run(capsys):
    """One run: `plan` applied when there is no progress record, else the
    record followed, as `tcw migrate` does."""
    def go(root: Path, plan: Plan | None = None, *, dry_run: bool = False) -> Ran:
        capsys.readouterr()
        if not (root / progress.PROGRESS).exists() and plan is not None and not dry_run:
            code = cli.apply_plan(plan, root)
        else:
            code = cli.run(root, dry_run=dry_run, no_jira=True)
        out, err = capsys.readouterr()
        return Ran(code, out, err)
    return go


def tree(root: Path) -> dict:
    found = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        found[rel] = path.read_bytes() if path.is_file() else "<folder>"
    return found


def finished(tmp_path: Path) -> dict:
    root = three_x(tmp_path / "clean")
    assert execute.apply(hand_plan(root), root, lambda step: None) is None
    return tree(root)


def test_every_step_is_done_in_order_and_the_progress_record_comes_and_goes(tmp_path,
                                                                            monkeypatch):
    root = three_x(tmp_path / "app")
    plan = hand_plan(root)
    seen = []

    def said(step):
        seen.append((report.step_line(step), (root / progress.PROGRESS).exists()))
    execute.apply(plan, root, said)
    assert [line for line, _ in seen] == [report.step_line(s) for s in plan.steps]
    # The record and its ignore line before the progress record; every
    # later step with the progress record there.
    assert [there for _, there in seen] == [False, False] + [True] * 6
    assert not (root / progress.PROGRESS).exists()
    assert not (root / "tcw-config.yaml").exists()
    assert (root / "docs/capabilities/auth/meta.yaml").read_text() == "name: Login\n"
    assert (root / "docs/capabilities/x/resources/camera.md").read_text() == "The camera.\n"
    assert (root / "docs/capabilities/x/tcw-capability.yaml").read_text() == STATE
    assert not (root / "docs/capabilities/x/meta.yaml").exists()


def test_every_stop_is_finished_by_running_again(tmp_path, run):
    made = []

    def make() -> Fixture:
        root = three_x(tmp_path / f"run-{len(made)}")
        made.append(hand_plan(root))
        return Fixture(root)

    def command(fixture: Fixture) -> Ran:
        return run(fixture.root, made[-1])

    total = every_stop(pytest.MonkeyPatch.context, make, command,
                       stopped_says=(report.RUN_AGAIN, report.DO_NOT_SAVE))
    # Eight steps, the progress record's write and deletion, and the folders
    # `.tcw/` and `resources/` made.
    assert total == 12


def stop_at(root: Path, plan: Plan, monkeypatch, stopped_before: int) -> None:
    """Run `plan` with the step at index `stopped_before` failing."""
    real = execute._perform
    calls = []

    def perform(step, at):
        calls.append(step)
        if plan.steps.index(step) == stopped_before:
            raise OSError(errno.EIO, "made to fail")
        return real(step, at)
    monkeypatch.setattr(execute, "_perform", perform)
    with pytest.raises(execute.MigrateStopped):
        execute.apply(plan, root, lambda step: None)
    monkeypatch.setattr(execute, "_perform", real)


def test_a_file_changed_after_a_stop_is_b17(tmp_path, monkeypatch, run):
    """Stopped before a state file is written (P8), its 3.x file changed by
    hand: B17 naming it, and nothing more written."""
    root = three_x(tmp_path / "app")
    plan = hand_plan(root)
    stop_at(root, plan, monkeypatch, stopped_before=4)
    (root / "docs/capabilities/x/meta.yaml").write_text("name: Changed\n")
    before = tree(root)
    again = run(root)
    assert again.code == 3
    assert again.out == ""
    assert ("B17 docs/capabilities/x/meta.yaml: is not as "
            ".tcw/tcw-migration-progress.yaml recorded it; "
            "docs/capabilities/x/tcw-capability.yaml was planned from it") in again.err
    assert ("restore it as it was, or restore the project from version control, delete "
            ".tcw/tcw-migration-progress.yaml, and run 'tcw migrate' again") in again.err
    assert tree(root) == before


def test_a_file_to_write_changed_after_a_stop_is_b17_and_nothing_more_is_written(
        tmp_path, monkeypatch, run):
    root = three_x(tmp_path / "app")
    plan = hand_plan(root)
    stop_at(root, plan, monkeypatch, stopped_before=6)        # before the configuration
    (root / ".tcw/tcw-config.yaml").write_text("tcw-version: 4.0.0\nid: mine\n")
    before = tree(root)
    again = run(root)
    assert again.code == 3
    assert "B17 .tcw/tcw-config.yaml: is not as .tcw/tcw-migration-progress.yaml " \
           "recorded it" in again.err
    assert tree(root) == before


def test_a_deletion_checks_its_own_file_m3(tmp_path, monkeypatch, run):
    """Stopped after the 4.0 state file is written (P7); the 3.x file then
    edited by hand: the next run refuses, and the edit survives."""
    root = three_x(tmp_path / "app")
    plan = hand_plan(root)
    stop_at(root, plan, monkeypatch, stopped_before=5)        # the deletion
    assert (root / "docs/capabilities/x/tcw-capability.yaml").read_text() == STATE
    (root / "docs/capabilities/x/meta.yaml").write_text(META + "Feature: f\n")
    again = run(root)
    assert again.code == 3
    assert "B17 docs/capabilities/x/meta.yaml" in again.err
    assert (root / "docs/capabilities/x/meta.yaml").read_text() == META + "Feature: f\n"


def test_a_deletion_waits_for_its_4_0_file(tmp_path):
    (tmp_path / "meta.yaml").write_text(META)
    (tmp_path / "tcw-capability.yaml").write_text(STATE + "Feature: hand\n")
    step = Delete("meta.yaml", "C", digest(META), "tcw-capability.yaml", digest(STATE))
    assert execute.state(step, tmp_path) == execute.CHANGED
    (tmp_path / "tcw-capability.yaml").write_text(STATE)
    assert execute.state(step, tmp_path) == execute.TODO
    (tmp_path / "meta.yaml").unlink()
    assert execute.state(step, tmp_path) == execute.DONE


def test_a_move_across_filesystems_is_refused_and_finished_by_hand(tmp_path, monkeypatch,
                                                                   run):
    expected = finished(tmp_path)
    root = three_x(tmp_path / "app")
    plan = hand_plan(root)
    real = os.rename

    def rename(a, b, *rest, **kw):
        if str(a).endswith("ov"):
            raise OSError(errno.EXDEV, "Invalid cross-device link")
        return real(a, b, *rest, **kw)
    monkeypatch.setattr(os, "rename", rename)
    stopped = run(root, plan)
    assert stopped.code == 1
    assert execute.cross_device_message("docs/capabilities/ov", "docs/capabilities/auth") \
        in stopped.err
    assert report.RUN_AGAIN in stopped.err
    assert not (root / "docs/capabilities/auth").exists()      # nothing copied
    assert (root / "docs/capabilities/ov/meta.yaml").is_file()
    again = run(root)
    assert again.code == 1                                     # still on two filesystems
    monkeypatch.setattr(os, "rename", real)
    real(root / "docs/capabilities/ov", root / "docs/capabilities/auth")
    done = run(root)
    assert done.code == 0, done.err
    assert tree(root) == expected


def test_a_permission_error_says_to_run_again(tmp_path, monkeypatch, run):
    root = three_x(tmp_path / "app")
    plan = hand_plan(root)
    real = execute.fs._atomic_write_all

    def refuse(pairs):
        if any(str(p).endswith("tcw-capability.yaml") for p, _ in pairs):
            raise PermissionError(errno.EACCES, "Permission denied", str(pairs[0][0]))
        return real(pairs)
    monkeypatch.setattr(execute.fs, "_atomic_write_all", refuse)
    stopped = run(root, plan)
    assert stopped.code == 1
    assert "stopped: [Errno 13] Permission denied" in stopped.err
    assert stopped.err.splitlines()[-2:] == [report.RUN_AGAIN, report.DO_NOT_SAVE]
    assert "not done:\n  write docs/capabilities/x/tcw-capability.yaml: C9" in stopped.err


def test_the_stopped_lines_are_exact():
    assert report.RUN_AGAIN == "run 'tcw migrate' again to finish"
    assert report.DO_NOT_SAVE == ("do not save these files in version control until "
                                  "'tcw migrate' finishes")


def test_a_write_that_does_not_read_back_stops_before_its_old_file_goes(tmp_path,
                                                                        monkeypatch, run):
    root = three_x(tmp_path / "app")
    plan = hand_plan(root)
    real = execute.read_text
    monkeypatch.setattr(execute, "read_text",
                        lambda path: "other" if path.name == "tcw-capability.yaml"
                        else real(path))
    stopped = run(root, plan)
    assert stopped.code == 1
    assert "does not read back as it was written" in stopped.err
    assert (root / "docs/capabilities/x/meta.yaml").read_text() == META


def test_a_dry_run_with_a_progress_record_lists_what_is_left(tmp_path, monkeypatch, run):
    root = three_x(tmp_path / "app")
    plan = hand_plan(root)
    stop_at(root, plan, monkeypatch, stopped_before=6)
    before = tree(root)
    dry = run(root, dry_run=True)
    assert dry.code == 0
    assert [line for line in dry.err.splitlines()      # less the summary (Steps 9, 10)
            if line.startswith(("would write", "would move", "would delete"))] == [
        "would write .tcw/tcw-config.yaml: C1", "would delete tcw-config.yaml: C1"]
    assert tree(root) == before


def test_the_record_keeps_the_project_and_its_backend(tmp_path):
    plan = hand_plan(three_x(tmp_path))
    (tmp_path / ".tcw").mkdir()
    (tmp_path / progress.PROGRESS).write_text(progress.dump(plan))
    record = progress.load(tmp_path)
    assert (record.project, record.work_backend) == ("app", "jira")
    assert record.steps == plan.steps


@pytest.mark.parametrize("drop", ["project", "work-backend", "steps"])
def test_a_record_without_a_field_is_b17(tmp_path, run, drop):
    plan = hand_plan(three_x(tmp_path))
    data = yaml.safe_load(progress.dump(plan))
    del data[drop]
    (tmp_path / ".tcw").mkdir()
    (tmp_path / progress.PROGRESS).write_text(yaml.safe_dump(data))
    refused = run(tmp_path)
    assert refused.code == 3
    assert f"B17 {progress.PROGRESS}: is not a progress record tcw migrate wrote" \
        in refused.err


def test_the_record_round_trips_any_text_exactly(tmp_path):
    text = "﻿id: app  \r\nname: a\r\n\ttab\n  \n"
    plan = Plan("app", "filesystem", steps=[Write("f.yaml", "C", ABSENT, text)])
    (tmp_path / ".tcw").mkdir()
    (tmp_path / progress.PROGRESS).write_text(progress.dump(plan), newline="")
    assert progress.load(tmp_path).steps[0].text == text
    execute.follow(progress.load(tmp_path).steps, tmp_path, lambda step: None)
    assert (tmp_path / "f.yaml").read_bytes() == text.encode("utf-8")
