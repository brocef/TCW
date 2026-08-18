"""The three intake commands against a real, inherited file descriptor.

These shell out rather than calling `main([...])` in-process, because the bug is
about the descriptor a *child* inherits, and an in-process call cannot reproduce
a parent holding the write end of a pipe open.
"""

import os
import subprocess
import time

import pytest

TIMEOUT = "0.4"                 # the bound these tests run the CLI with
DEADLINE = 30                   # hang tripwire only — not a performance assertion


def _env():
    e = dict(os.environ)
    e["TCW_STDIN_TIMEOUT"] = TIMEOUT
    return e


def _run(root, argv, **kw):
    return subprocess.run(["tcw", *argv], cwd=root, capture_output=True,
                          text=True, timeout=DEADLINE, env=_env(), **kw)


@pytest.fixture
def node(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for k, v in (("user.email", "t@t.t"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(tmp_path), "config", k, v], check=True)
    r = _run(tmp_path, ["init", "--id", "stdin-probe"], stdin=subprocess.DEVNULL)
    assert r.returncode == 0, r.stderr
    return tmp_path


def _held_open_pipe():
    """A read end whose writer never closes — what a wrapper process leaves."""
    return os.pipe()


# -- arm A: the hang, across all three commands ------------------------------

@pytest.mark.parametrize("argv, made", [
    (["work", "new", "arm a"], "docs/work/backlog"),
    (["taxonomy", "add", "ArmA"], "docs/taxonomy"),
    (["capabilities", "add", "work/arm-a"], "docs/capabilities"),
])
def test_an_inherited_open_stdin_does_not_hang(node, argv, made):
    r, w = _held_open_pipe()
    try:
        start = time.monotonic()
        result = _run(node, argv, stdin=r)       # would hang forever before
        elapsed = time.monotonic() - start
    finally:
        os.close(r)
        os.close(w)
    assert result.returncode == 0, result.stderr
    assert elapsed < DEADLINE
    assert "no piped input" in result.stderr
    assert (node / made).exists()


def test_the_warning_never_reaches_stdout(node):
    """`slug=$(tcw work new …)` must still capture only the slug."""
    r, w = _held_open_pipe()
    try:
        result = _run(node, ["work", "new", "quiet stdout"], stdin=r)
    finally:
        os.close(r)
        os.close(w)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("quiet-stdout")   # the slug, alone
    assert "no piped input" in result.stderr                # warning went to stderr
    assert "no piped input" not in result.stdout


# -- arm B: closed stdin, unchanged ------------------------------------------

def test_closed_stdin_is_silent(node):
    result = _run(node, ["work", "new", "arm b"], stdin=subprocess.DEVNULL)
    assert result.returncode == 0, result.stderr
    assert "no piped input" not in result.stderr


# -- arm C: piped intake, unchanged ------------------------------------------

def test_piped_intake_still_lands_verbatim(node):
    result = _run(node, ["work", "new", "arm c"], input="raw intake body\n")
    assert result.returncode == 0, result.stderr
    slug = result.stdout.strip()
    intake = node / "docs" / "work" / "backlog" / slug / "intake.md"
    assert intake.read_text(encoding="utf-8") == "raw intake body\n"
    assert "no piped input" not in result.stderr


def test_a_positional_description_short_circuits_past_stdin(node):
    """`args.description or read_piped_stdin()` — a description given on the
    command line means stdin is never touched, so a held-open descriptor cannot
    even delay it. `description` is positional, not a flag."""
    r, w = _held_open_pipe()
    try:
        result = _run(node, ["taxonomy", "add", "Flagged",
                             "given on the command line"], stdin=r)
    finally:
        os.close(r)
        os.close(w)
    assert result.returncode == 0, result.stderr
    assert "no piped input" not in result.stderr


# -- the truncation arm ------------------------------------------------------

def test_a_stalled_producer_is_refused_and_creates_nothing(node):
    """Bytes arrive, then the writer stalls. Storing the fragment as `intake`
    would break the capability's own promise that it lands verbatim."""
    r, w = _held_open_pipe()
    try:
        proc = subprocess.Popen(["tcw", "work", "new", "arm d"], cwd=node,
                                stdin=r, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, env=_env())
        os.write(w, b"half a document")       # ...and never an EOF
        out, err = proc.communicate(timeout=DEADLINE)
    finally:
        os.close(r)
        os.close(w)
    assert proc.returncode == 1, (out, err)
    assert "truncated intake" in err
    assert "TCW_STDIN_TIMEOUT" in err
    assert out == ""                          # nothing on stdout on failure
    listing = _run(node, ["work", "list"], stdin=subprocess.DEVNULL).stdout
    assert "arm d" not in listing             # and no item was created


# -- lifecycle hooks must not inherit stdin either ---------------------------

def test_a_command_hook_does_not_inherit_stdin(node):
    """A hook reading stdin would otherwise consume the parent's piped intake,
    or stall to the full hook timeout waiting on a pipe nobody will close.

    Run as a subprocess with a held-open descriptor: an in-process test inherits
    pytest's `/dev/null`, hits EOF at once, and would pass either way.
    """
    import yaml
    cfg = node / "tcw-config.yaml"
    conf = yaml.safe_load(cfg.read_text()) or {}
    conf.setdefault("work", {})["lifecycle"] = {
        "timeout": 5,                       # pre-fix, `cat` stalls out to here
        "transitions": {"start": {"pre": [{"command": "cat"}]}},
    }
    cfg.write_text(yaml.safe_dump(conf, sort_keys=False))

    slug = _run(node, ["work", "new", "hooked"],
                stdin=subprocess.DEVNULL).stdout.strip()

    r, w = _held_open_pipe()
    try:
        start = time.monotonic()
        result = _run(node, ["work", "start", slug], stdin=r)
        elapsed = time.monotonic() - start
    finally:
        os.close(r)
        os.close(w)

    assert result.returncode == 0, result.stderr
    assert "timeout" not in result.stderr
    assert elapsed < 5, "the hook waited on inherited stdin"
