"""The top-level handler (TCW-73 Design 1.3, 1.8, 4; AC 26).

An error line starts with the command's own words; a failure after something
was created names it on stdout exactly as success would; a reader that stops
reading ends the command quietly.
"""

import io
import os
import sys

import pytest

from tcw.cli import main
from tcw.errors import BackendError
from tcw.work.fs_backend import FsWorkBackend
from tests.work.projects import make_project


@pytest.fixture
def run(monkeypatch, capsys):
    def run(argv, cwd, stdin=""):
        monkeypatch.chdir(cwd)
        monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
        try:
            code = main(argv)
        except SystemExit as stop:
            code = stop.code
        captured = capsys.readouterr()
        return code, captured.out, captured.err
    return run


@pytest.fixture
def fx(tmp_path):
    return make_project(tmp_path, "fx", config={})


def test_an_error_line_starts_with_the_command_words(run, fx):
    code, out, err = run(["work", "show", "fx/no-such"], fx)
    assert code == 4 and out == ""
    assert err.startswith("tcw work show: ")
    assert not err.startswith("tcw: ")


def test_a_nested_command_names_every_word(run, fx):
    code, _, err = run(["work", "stage", "prompt", "nonsense"], fx)
    assert code == 2
    assert err.startswith("tcw work stage prompt: ")


def test_a_failure_after_creation_prints_the_name_then_the_error(run, fx, monkeypatch):
    def create(self, title, props, *, stage, request):
        (self.work_path / "2026-10-02-x").mkdir()
        raise BackendError("made it, then failed", name="fx/2026-10-02-x")
    monkeypatch.setattr(FsWorkBackend, "create", create)
    code, out, err = run(["work", "new", "x"], fx)
    assert (code, out) == (1, "fx/2026-10-02-x\n")
    assert err == "tcw work new: made it, then failed\n"


def test_a_failure_before_anything_exists_prints_nothing_on_stdout(run, fx, monkeypatch):
    def create(self, title, props, *, stage, request):
        raise BackendError("refused before writing")
    monkeypatch.setattr(FsWorkBackend, "create", create)
    code, out, _ = run(["work", "new", "x"], fx)
    assert (code, out) == (1, "")


def test_a_rename_that_fails_after_the_move_prints_the_new_slug(run, fx, monkeypatch):
    code, out, _ = run(["work", "new", "A b"], fx)
    first = out.strip()
    code, out, _ = run(["work", "new", "C d", "--blocked-by", first], fx)
    assert code == 0
    import tcw.work.fs_backend as fs_backend
    real = fs_backend.FsWorkBackend._write

    def failing(self, item, raw_stage):
        raise OSError("disk full")
    monkeypatch.setattr(fs_backend.FsWorkBackend, "_write", failing)
    code, out, err = run(["work", "rename", first, "other"], fx)
    monkeypatch.setattr(fs_backend.FsWorkBackend, "_write", real)
    new = first.rsplit("-a-b", 1)[0] + "-other"
    assert (code, out) == (1, new + "\n")
    assert "still name the old slug" in err


def test_an_abbreviated_option_is_not_accepted(run, fx):
    code, _, err = run(["work", "list", "--ta", "x"], fx)
    assert code == 2 and "--ta" in err


def test_a_closed_stdout_exits_quietly(run, fx, monkeypatch):
    run(["work", "new", "A b"], fx)

    def broken(*args, **kwargs):
        raise BrokenPipeError
    import tcw.work.cli as work_cli
    monkeypatch.setattr(work_cli, "_list", lambda args: broken())
    saved = os.dup(1)
    try:
        code, out, err = run(["work", "list"], fx)
    finally:
        os.dup2(saved, 1)
        os.close(saved)
    assert code == 1 and err == ""


@pytest.mark.parametrize("argv", [["projects", "list"],
                                  ["work", "procedure", "audit-backlog"]])
def test_a_reader_gone_before_short_output_exits_quietly(fx, argv):
    """Review fix C1: output shorter than the pipe buffer is only written when
    stdout is flushed, which used to happen at interpreter exit, outside the
    handler: "Exception ignored ... BrokenPipeError" and exit 120. The read end
    is closed before the command starts, so every write fails."""
    import subprocess
    read_end, write_end = os.pipe()
    os.close(read_end)
    try:
        done = subprocess.run([sys.executable, "-m", "tcw.cli", *argv], cwd=fx,
                              stdout=write_end, stderr=subprocess.PIPE,
                              stdin=subprocess.DEVNULL, timeout=60)
    finally:
        os.close(write_end)
    assert (done.returncode, done.stderr) == (1, b""), done.stderr.decode()


def test_a_create_rolled_back_names_each_file_removed(run, fx, monkeypatch):
    """Review fix N2: a create that fails after writing `item.yaml` removes
    its folder, naming each file removed and not the folder (Design 1.2)."""
    from tcw.work import fs_backend
    real = fs_backend._replace_file

    def failing(path, text):
        if path.name == "request.md":
            raise OSError("disk full")
        return real(path, text)
    monkeypatch.setattr(fs_backend, "_replace_file", failing)
    code, out, err = run(["work", "new", "A b"], fx, stdin="Need X\n")
    assert (code, out) == (1, ""), err
    removed = [line for line in err.splitlines() if line.startswith("removed ")]
    assert removed and all(line.endswith("/item.yaml") for line in removed), err
    assert not list((fx / "docs" / "work").glob("*-a-b"))
