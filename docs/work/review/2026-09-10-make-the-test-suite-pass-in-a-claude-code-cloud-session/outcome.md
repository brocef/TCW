# Outcome — Make the test suite pass in a Claude Code cloud session

The suite passes in a Claude Code cloud session. All twelve acceptance criteria
were checked against commands run in this session; the evidence is quoted below
rather than summarized.

## What shipped

### Task 1 — the cleanup test measures cleanup — `2679824`

Falsified first, as the plan required, and the result is the item's central
finding. With `tmp.unlink(missing_ok=True)` deleted from `_atomic_write_all`,
the **existing** `test_atomic_write_temp_cleanup_on_failure` passed:

```
1 passed in 0.09s
```

That run had to be made as an unprivileged user, which the plan did not
anticipate — see *What the plan got wrong* below.

`tests/test_store_editor.py:967` now induces the failure at `Path.write_text`
through the file's own `_fail_writing`, one statement after `mkstemp`, so a temp
exists when the handler runs. Against the same mutation the rewrite fails:

```
tests/test_store_editor.py:986: AssertionError
FAILED tests/test_store_editor.py::test_atomic_write_temp_cleanup_on_failure
```

Criteria 3 and 4. `_atomic_write_all` is unchanged; the mutation was reverted
with `git checkout --` both times and the working tree confirmed clean.

### Task 2 — the promote-failure test leaves permissions alone — `6741a40`

`tests/test_store_editor.py:946` patches `Path.replace`, the seam
`test_atomic_write_all_promote_failure_is_the_recorded_ceiling` already used,
and keeps its single-pair shape. A `*.tmp` assertion was added because patching
the promote step is what makes the loop raise, and without it the test would not
notice a temp surviving the failure it just induced.

Criterion 5, against an `_atomic_write_all` mutated to write each target
directly instead of staging and promoting:

```
tests/test_store_editor.py:965: Failed
FAILED tests/test_store_editor.py::test_atomic_write_preserves_prior_on_failure
```

`os` and `stat` stayed imported: `test_atomic_write_all_keeps_the_targets_mode`
(`tests/test_store_editor.py:1597-1601`) still uses both, legitimately — it
asserts mode preservation rather than inducing a failure. The plan allowed for
this.

### Task 3 — the scaffold test skips under root — `1c2c699`

Criterion 6, first half:

```
SKIPPED [1] tests/test_scaffold.py:320: root holds CAP_DAC_OVERRIDE, so the
chmod below does not make the target unwritable and the command succeeds
44 passed, 1 skipped in 13.34s
```

### Task 4 — the provisioner raises setuptools to the floor — `d84eb62`

A new step 5 in `scripts/remote_session_setup.sh`, with steps 5 and 6
renumbered to 6 and 7. The floor check was verified against real interpreters,
not only the stub, and its boundary matches the build boundary exactly:

| setuptools | floor check | isolation-free build |
| ---------- | ----------- | -------------------- |
| 68.1.2     | below       | `AttributeError: install_layout` |
| 70.0.0     | below       | `invalid command 'bdist_wheel'` |
| 70.1.0     | at/above    | `Successfully built tcw-cli` |
| 84.0.0     | at/above    | `Successfully built tcw-cli` |

Three new tests cover criteria 9 and 11; criterion 10 is
`test_failing_pip_retries_once_then_reports`, which still counts exactly two
`pip install -e` invocations. `bash -n` passes and the script stays executable
(criterion 8). `tests/test_remote_session_setup.py`: 23 passed.

### Documentation — `4e11925`

One entry of four fired. `docs/changelogs/upcoming.md` gained an `## Internal`
section. `README.md` and `docs/release-notes/upcoming.md` did not fire — no
public CLI surface or user-facing behaviour changed, and the published install
path `scripts/session_bootstrap.sh` is untouched. `skills/<component>/SKILL.md`
did not fire — no component's CLI surface, model, lifecycle, or guardrails
changed.

## Test result

Criterion 1, the whole suite, in this cloud session as root:

```
SKIPPED [1] tests/test_scaffold.py:320: root holds CAP_DAC_OVERRIDE, ...
2528 passed, 1 skipped in 393.24s (0:06:33)
```

Before this item: `4 failed, 2522 passed`. The arithmetic closes — the four
failures now pass, three provisioner tests were added, and one test is skipped
under root.

Criteria 2, 3 and 6, second half — the same files run as an unprivileged user
on a copy of the tree, where the scaffold test **runs** rather than skipping:

```
190 passed in 16.09s
```

Criterion 12:

```
capabilities OK
validate OK
```

Verification step 2, the provisioner against the real environment: it printed
nothing (its success condition), setuptools moved 68.1.2 → 84.0.0, `tcw
--version` still answers `tcw 2.0.2`, and `tests/test_shipped_prompts.py` went
from failing to `32 passed`.

## What the plan and spec got wrong

Three things, none of which changed the design.

**The falsification in task 1 could not be done as root, and the plan said to
do it there.** The plan opened with "delete the unlink, run the test, record
that it passes". As root the test already fails for the permission reason, so
that run proved nothing — the first attempt returned `FAILED` and was
uninformative. The evidence required an unprivileged user, which the plan had
scheduled only as a closing verification step. A non-root account was added to
the container and the mutated tree copied to a directory it owns, which is how
the run was obtained. The spec's criterion 4 was right about *what* to prove and
the plan was wrong about *where*.

**Three existing provisioner tests index the call log positionally, and the plan
did not see it.** `test_remote_session_installs_package_then_plugin`,
`test_installed_checkout_skips_pip_but_still_ensures_the_plugin` and
`test_a_missing_claude_still_installs_the_package` assert on `log[0]`, `log[1]`
and a whole-list equality, so inserting any step shifts them. The plan predicted
only criterion 10 — the `pip install -e` count — and that one never broke. The
three were repaired by filtering the new check out of the log through a
`_calls` helper rather than by shifting indices, so the next step added to that
script does not break them again. Applied to the fourth positional test as well,
which had not broken, rather than leaving one sibling fragile.

**The floor check had to become a single line.** The stub `python3` logs
`"$*"`, so a multi-line `-c` script was recorded as three separate log entries
and broke a whole-list assertion. Written as one line assigned to a shell
variable instead.

## Notes

- A fourth correction was to a test written in this item, not to the plan: the
  new `test_a_failing_setuptools_upgrade_reports_once_and_exits_zero` filtered
  stdout on the string `setuptools`, which also matched pytest's temporary
  directory — it is named after the test, and the test's name contains that
  word. It now matches `could not raise setuptools`.
- The skip in task 3 means a regression in the scaffold write-failure path would
  be invisible in every cloud session and caught only in CI. The spec accepted
  this and the risk stands; restoring that coverage needs a differently-induced
  failure and is its own item, deliberately not opened here.
- Reproducing the non-root runs needs an account this container does not ship
  with. One was added (`useradd`) and the tree copied to a directory it owns,
  because the checkout and the editable install both belong to root. The account
  is a session-local artifact of the container, not a repository change, and it
  disappears with the container.
- `70.1` remains an empirical floor, established on this interpreter by the
  table above rather than read from a changelog. The script's comment names
  `bdist_wheel` as the reason so the next reader can re-derive it.
