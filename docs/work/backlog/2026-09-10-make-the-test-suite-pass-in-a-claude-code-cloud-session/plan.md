# Plan — Make the test suite pass in a Claude Code cloud session

Five tasks. Tasks 1 and 2 are independent of tasks 3 and 4 and touch different
files, but task 1 carries the item's central finding — a test that passed
without measuring anything — so it goes first and its falsification is recorded
before anything else changes. Task 5 is the documentation block.

`python -m pytest` must be no worse at every task boundary, and the target is
zero failures by the end of task 4.

---

## Task 1 — the cleanup test measures cleanup

**Modifies** `tests/test_store_editor.py`.

**Falsify first, against the tree as it stands.** Before editing anything,
delete the `tmp.unlink(missing_ok=True)` line from `_atomic_write_all`
(`tcw/store/fs.py:1334`), run
`test_atomic_write_temp_cleanup_on_failure`, and record that it **passes**.
That is the evidence for criterion 4 and it is unobtainable afterwards. Restore
the line with `git checkout -- tcw/store/fs.py`.

Then rewrite the test at `tests/test_store_editor.py:967`. Drop both `os.chmod`
calls and the `try/finally`, and induce the failure with the file's own helper
so `mkstemp` has already succeeded and a temp exists:

```python
def test_atomic_write_temp_cleanup_on_failure(tmp_path, monkeypatch):
    """A staging failure leaves no temp behind.

    The failure is induced at `Path.write_text`, one statement after
    `mkstemp` — inducing it earlier (a read-only parent) means no temp is
    ever created, and the assertion below then holds whether or not the
    cleanup handler runs.
    """
    d = tmp_path / "subdir"
    d.mkdir()
    p = d / "data.yaml"
    _fail_writing(monkeypatch, "data.yaml")

    with pytest.raises(OSError):
        _atomic_write_all([(p, "content\n")])

    tmp_files = list(d.glob("*.tmp"))
    assert tmp_files == [], f"temp files left behind: {tmp_files}"
```

`_fail_writing` matches on name prefix and the temps are `data.yaml.*.tmp`, so
one call covers the staged write (`tests/test_store_editor.py:994-1008`). Its
default exception is `OSError(28)`, hence `pytest.raises(OSError)` rather than
`PermissionError` — the claim is about a failed write, not about which errno.

The test keeps its position; `_fail_writing` is defined below it and Python
binds it before any test runs.

**Proves it:** repeat the mutation from the top of this task against the
rewritten test and record that it now **fails**. Then, with the tree restored,
`pytest tests/test_store_editor.py` green, and `grep -n chmod` showing no hit
inside this test.

---

## Task 2 — the promote-failure test leaves permissions alone

**Modifies** `tests/test_store_editor.py`.

Rewrite `test_atomic_write_preserves_prior_on_failure`
(`tests/test_store_editor.py:946`) onto the `Path.replace` seam that
`test_atomic_write_all_promote_failure_is_the_recorded_ceiling` already uses at
line 1050. Keep the single-pair shape — that test fails on the *second* of two
promotes, so a first-promote failure is covered nowhere else:

```python
def test_atomic_write_preserves_prior_on_failure(tmp_path, monkeypatch):
    """If the replace step fails, the original file must remain readable."""
    d = tmp_path / "subdir"
    d.mkdir()
    p = d / "data.yaml"
    original = "key: value\n"
    p.write_text(original)

    def refuse(self, target):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(Path, "replace", refuse)

    with pytest.raises(PermissionError):
        _atomic_write_all([(p, "key: new_value\n")])

    assert p.read_text() == original
    assert list(d.glob("*.tmp")) == []
```

The added `*.tmp` assertion is not scope creep: patching `Path.replace` is what
makes the promote loop raise, and without it the test would not notice a temp
surviving the failure it just induced.

If `os` and `stat` become unused in the module after tasks 1 and 2, remove those
imports (`tests/test_store_editor.py:8-9`); if any other test still uses them,
leave them.

**Proves it:** change `_atomic_write_all` to write each target directly rather
than staging and promoting, confirm this test fails, and revert — criterion 5.
Then `pytest tests/test_store_editor.py` green.

---

## Task 3 — the scaffold test skips under root

**Modifies** `tests/test_scaffold.py`.

Add `import os` to the import block (`tests/test_scaffold.py:8-12`) and decorate
the test at line 319:

```python
@pytest.mark.skipif(
    os.geteuid() == 0,
    reason="root holds CAP_DAC_OVERRIDE, so the chmod that makes this target "
           "unwritable does not stop root writing to it",
)
def test_an_unwritable_target_reports_and_prints_no_path(item):
```

The reason names the cause rather than calling the test unreliable, matching
`tests/test_session_bootstrap.py:353-356`.

**Proves it:** `pytest tests/test_scaffold.py -rs` shows the test skipped with
that reason under uid 0, and the rest of the file green — criterion 6. The
non-root half of the criterion is verification, not a test; see below.

---

## Task 4 — the provisioner raises setuptools to the isolation-free floor

**Modifies** `scripts/remote_session_setup.sh`, `tests/test_remote_session_setup.py`.

Insert a new step between the current step 4 (the editable install, ending
`scripts/remote_session_setup.sh:82`) and the current step 5 (the PATH repair,
`scripts/remote_session_setup.sh:84`), and renumber the two comment headers
below it from `5.`/`6.` to `6.`/`7.`:

```sh
# 5. The build toolchain. tests/test_shipped_prompts.py builds a wheel with
#    --no-build-isolation, so whatever setuptools this interpreter has is what
#    builds it. `bdist_wheel` moved into setuptools at 70.1; below that the
#    build fails and the test reports a packaging defect that is not there.
#    Checked before upgrading, so an image already current is never written to
#    — which is what makes a `--force` run on a developer's machine safe.
if ! python3 -c 'import setuptools, sys
v = tuple(int(p) for p in setuptools.__version__.split(".")[:2])
sys.exit(0 if v >= (70, 1) else 1)' >/dev/null 2>&1; then
    if ! python3 -m pip install --upgrade "setuptools>=70.1" >/dev/null 2>&1 &&
        ! python3 -m pip install --upgrade "setuptools>=70.1" --break-system-packages >/dev/null 2>&1; then
        echo "tcw: could not raise setuptools to >=70.1 — tests/test_shipped_prompts.py cannot build its wheel in this session."
    fi
fi
```

An unparseable version string raises, exits non-zero, and is read as "below the
floor", so the bad case is a redundant upgrade rather than a skipped one.

Extend the stubbed `python3` (`tests/test_remote_session_setup.py:37-58`) with a
`-c` case returning `${STUB_SETUPTOOLS_RC:-0}` — 0 meaning "already at the
floor", which is what keeps every existing test's pip count unchanged. Add:

- `test_a_current_setuptools_is_not_upgraded` — default stub, assert no logged
  `pip install --upgrade` line.
- `test_an_old_setuptools_is_raised_to_the_floor` — `STUB_SETUPTOOLS_RC="1"`,
  assert one `pip install --upgrade "setuptools>=70.1"` line and a zero exit.
- `test_a_failing_setuptools_upgrade_reports_once_and_exits_zero` —
  `STUB_SETUPTOOLS_RC="1"` plus `STUB_PIP_RC="1"`, assert two upgrade attempts,
  the second carrying `--break-system-packages`, one printed line, exit 0.

`STUB_PIP_RC="1"` makes *every* pip call fail, so the third test's assertions
must filter on `pip install --upgrade` rather than counting all pip lines.

**Proves it:** criteria 8-11. `pytest tests/test_remote_session_setup.py` green
including `test_failing_pip_retries_once_then_reports`, which counts
`pip install -e` invocations and must still see exactly two — that is criterion
10, and it is the assertion this task is most likely to break.

---

## Documentation Sync

One block, after the code tasks, evaluated over the finished diff.

- **`README.md` — [Public-API], does not fire.** No public CLI surface and no
  user-facing behaviour changes. Everything here is contributor tooling; the
  published install path, `scripts/session_bootstrap.sh`, is untouched.
- **`docs/release-notes/upcoming.md` — [Public-API], does not fire.** Nothing a
  user of the released `tcw-cli` would notice.
- **`docs/changelogs/upcoming.md` — [Any-Code-Change], fires.** Under
  *Internal*: the two atomic-write tests induce failure at the write and replace
  seams instead of through directory permissions, which also repairs a cleanup
  assertion that held whether or not the cleanup ran; the scaffold
  unwritable-target test is skipped as root; and the remote session provisioner
  raises setuptools to 70.1 so the shipped-prompts wheel build works without
  build isolation.
- **`skills/<component>/SKILL.md` — [Skill-Driven-Component], does not fire.**
  No component's CLI surface, model, lifecycle, or guardrails changed. The
  skills describe `tcw`; none of them describes the test suite or the
  provisioner.

`tcw work docs` is the check that this list is complete; run it over the diff
rather than trusting this block.

---

## Verification

What the suite cannot check, to be done by hand before `submit`:

1. **The non-root half of criteria 2, 3 and 6.** Every assertion above runs as
   root in this session, which is the environment being fixed — so the claim
   that nothing was weakened for a normal developer is unproven by a green run
   here. Create an unprivileged user, give it a copy of the checkout it owns,
   and run the three affected files as that user. All three tests must **run**
   (not skip) and pass. If that cannot be arranged in this container, say so in
   the outcome rather than implying it was checked, and leave it for CI, which
   runs as a non-root user on `ubuntu-latest`.
2. **The provisioner against the real environment, once.** `bash -n` and the
   stubbed tests prove syntax and control flow, not that the upgrade works. Run
   `scripts/remote_session_setup.sh --force` in this container and confirm
   setuptools lands at or above 70.1 and `tcw --version` still answers.
3. **The whole suite, once, end to end.** Criterion 1 is the item's actual
   goal and no per-file run establishes it. Expect zero failures and one skip.
4. **`tcw validate` and `tcw capabilities check`** both exit 0 — criterion 12.

## Notes

- No blockers, and no dependency on either branch item. This touches
  `tests/` and `scripts/` only; nothing under `tcw/` changes, so the repository
  guide's rule against driving the lifecycle with the CLI mid-edit does not
  apply.
- Tasks 1 and 2 both edit `tests/test_store_editor.py` and are kept separate
  anyway: task 1 carries a mutation-test record that has to be taken before the
  file is touched, and burying it in a two-test commit would lose that ordering.
