"""A project with no tracker configured is untouched by this feature.

**Why this is not a comparison against a branch point.** The spec's first wording
asked for output byte-identical to the commit before this item. That is not
achievable, and the reason is documented in the fixture seeder itself
(`evals/seed_fixture.py`): two runs are deliberately not byte-identical, because
slugs are date-prefixed, capability ids are minted, `started` is a timestamp, and
commit hashes follow from those. Comparing output across two seedings would fail for
reasons that have nothing to do with trackers.

So the property is expressed three ways that *are* checkable, and the middle one is
the strongest:

1. Nothing tracker-shaped appears in the output, and every command still exits zero.
2. **The Jira client is never imported.** A board read cannot be paying any part of
   this feature's cost if the module that talks to Jira was never loaded. If someone
   later wires a tracker call into a listing, this fails immediately and by name.
3. Output is stable across consecutive runs, so the feature introduced no ordering
   or timing dependence into the commands it sits beside.
"""

from __future__ import annotations

import contextlib
import io
import pathlib
import subprocess
import sys

import pytest

from tcw.store.fs import FsWorkStore, init

COMMANDS = [
    ["work", "list"],
    ["work", "list", "--all"],
    ["validate"],
    ["work", "docs"],
    ["work", "lifecycle"],
]


@pytest.fixture()
def node(tmp_path, monkeypatch):
    """A node with one real work item and no `work.tracker` key."""
    root = tmp_path / "node"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    init(["work"], root, project_id="probe")
    store = FsWorkStore.open(root)
    item = store.create("An item that exists so show has a target")
    monkeypatch.chdir(root)
    return root, item.slug


def _run(argv):
    from tcw.cli import main
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(argv)
        except SystemExit as exit_:
            code = exit_.code or 0
    return code, out.getvalue(), err.getvalue()


# ── 1. nothing tracker-shaped, and nothing newly broken ──────────────────────


def test_the_store_reports_no_tracker_and_no_problems(node):
    root, _slug = node
    store = FsWorkStore.open(root)
    assert store.tracker_config() is None
    assert store.tracker_problems() == []


@pytest.mark.parametrize("argv", COMMANDS)
def test_each_command_still_succeeds(node, argv):
    _root, _slug = node
    code, out, err = _run(argv)
    assert code == 0, (argv, out, err)


@pytest.mark.parametrize("argv", COMMANDS)
def test_no_command_mentions_a_tracker(node, argv):
    _root, _slug = node
    _code, out, err = _run(argv)
    combined = (out + err).lower()
    for word in ("tracker", "jira", "claimable", "exclusive"):
        assert word not in combined, (argv, word, combined)


def test_show_still_succeeds_and_mentions_no_tracker(node):
    _root, slug = node
    code, out, err = _run(["work", "show", slug])
    assert code == 0, err
    assert "tracker" not in (out + err).lower()


# ── 2. the Jira client is never imported ─────────────────────────────────────


# The repository root, so a subprocess resolves `tcw` to this tree rather than to
# whatever editable install happens to be on the machine. Verified: a leading
# `sys.path` entry does win here.
REPO = pathlib.Path(__file__).resolve().parents[1]

_PROBE = """
import sys
sys.path.insert(0, {repo!r})
import io, contextlib
from tcw.cli import main
out, err = io.StringIO(), io.StringIO()
with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
    try:
        code = main({argv!r})
    except SystemExit as e:
        code = e.code or 0
loaded = sorted(n for n in sys.modules if n.startswith("tcw.tracker"))
print("EXIT", code)
print("LOADED", ",".join(loaded))
"""


@pytest.mark.parametrize("argv", COMMANDS)
def test_the_jira_client_is_never_imported(node, argv):
    """The strongest form of "unaffected": a listing cannot be paying any part of
    this feature's cost if the module that speaks to Jira was never loaded.

    **This runs in a subprocess, and it has to.** The first version ran in-process
    and passed vacuously — `tcw.work.cli` is already imported by the time the test
    body runs, so deleting entries from `sys.modules` and calling `main` again does
    not re-execute its module-scope imports. Hoisting the client import to module
    scope did not fail it, which is exactly the false confidence mutation testing
    exists to catch. A fresh interpreter is the only place the question is real.

    The imports are deferred inside the tracker command handlers so this holds. If a
    later change hoists one, or wires a tracker call into a board read, this fails
    and names the command that did it.
    """
    root, _slug = node
    script = _PROBE.format(repo=str(REPO), argv=argv)
    result = subprocess.run([sys.executable, "-c", script], cwd=root,
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    assert "EXIT 0" in result.stdout, result.stdout
    loaded = [line for line in result.stdout.splitlines() if line.startswith("LOADED")]
    assert loaded, result.stdout
    names = loaded[0].removeprefix("LOADED").strip()
    assert names == "", f"{argv} imported {names}"


# ── 3. output is stable across runs ──────────────────────────────────────────


@pytest.mark.parametrize("argv", COMMANDS)
def test_output_is_identical_across_consecutive_runs(node, argv):
    """Not a claim about any earlier commit — a claim that this feature introduced
    no ordering or timing dependence into the commands it sits beside."""
    _root, _slug = node
    first = _run(argv)
    second = _run(argv)
    assert first == second, argv
