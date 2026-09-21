# Outcome: Warn when the loaded plugin skills are from a different version than the tcw CLI

Built in the worktree on `work/2026-09-21-warn-when-the-loaded-plugin-skills-are-from-a-different-version-than-the-tcw-cli`,
with a private virtual environment pinned to the worktree. No file under `tcw/`
changed.

## What shipped, task by task

| Task | Commit | What |
| --- | --- | --- |
| 1 | `340ee2fe` | `scripts/check_versions.sh` and `tests/test_check_versions.py`: reads the plugin manifest's version, asks `tcw --version` with a 3-second deadline, and prints both versions and the fix when they differ. Always exits 0; silent when they match or it cannot tell. |
| 2 | `dc15f420` | `scripts/session_bootstrap.sh` registers an `EXIT` trap once the plugin root is known, so the check runs after any install attempt and on every early exit, including a plugin root with no `tcw/__init__.py`. It is called through `bash`. Header comment rewritten. Ten new cases in `tests/test_session_bootstrap.py`. |
| 3 | `9cd0b3b8` | All 17 `skills/*/SKILL.md` open with the version-check line for agents outside Claude Code; a test requires it. Also fixed `test_an_explicit_root_wins`, which passed without testing anything (see below). |
| 4 | `fe28ee51` | New capability `plugin/warn-when-skills-and-cli-versions-differ` (`cap-76bee2`, `Missing` until completion); `plugin/bootstrap-the-cli` no longer claims the CLI "never goes stale behind the skills"; `skills/extras-report` mentions the plugin version. Item `capabilities.yaml` lists one new and two changed. `tcw capabilities check` → `capabilities OK`. |
| 5 | `412ca837` | Documentation Sync: README (Claude and Codex install paragraphs), `skills/setup/references/install.md`, the `extras-report` bug template and its "grab the versions" step, `docs/changelogs/upcoming.md`, `docs/release-notes/upcoming.md`. |
| fix | `87e321c0` | The check wrote a temporary file, so it fell silent inside Codex's read-only sandbox. Found by the manual Codex run (criterion 16); fixed and covered by two new tests. |
| docs | (this commit) | `plan.md` corrected for the change above; changelog says the check writes no file; this `outcome.md`. |

Documentation entries not updated, with the reason: `docs/guide/jira.md` (no
tracker change), `docs/guide/<topic>.md` (no guide covers installing the plugin
or the CLI), `skills/configure/references/` (no configuration key changed).

## Test result

Full suite, run without a git identity as CI runs it
(`GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null pytest -q -p no:cacheprovider`
from the worktree root):

`3934 passed in 1167.02s (0:19:27)`, exit status 0, at `87e321c0` (the commits after it change only Markdown).

## Mutation checks

Every new test was watched go red for the reason it names, by breaking the code
it covers and restoring it afterwards:

- String comparison instead of numeric → only `test_comparison_is_numeric` failed.
- Killing only the `tcw` process instead of its process group → only
  `test_a_hanging_cli_is_abandoned_silently` failed (the stub's `sleep` child
  survived). Removing the deadline → the same test failed, after the 37-second
  stub finished.
- Breaking the manifest pattern → the eight warning tests, including
  `test_the_real_manifests_parse`, failed.
- Ignoring the `tcw` exit status → only `test_cannot_tell_means_silent[tcw fails]` failed.
- Ignoring the root argument → `test_an_explicit_root_wins` failed (after the fix below).
- Reintroducing `mktemp` (the original code) → both
  `test_works_where_no_file_can_be_written` cases failed with empty output.
- Bootstrap: removing the trap → the seven warning cases failed; moving it below
  the `tcw/__init__.py` exit → only `test_manifest_only_root_still_warns` failed;
  calling the script without `bash` → only
  `test_check_runs_without_the_executable_bit` failed; running the check at trap
  registration instead of on exit → `test_successful_install_is_compared_after_the_install`
  and `test_failed_install_prints_both_lines` failed.
- Removing the line from `skills/configure/SKILL.md` → only
  `test_every_skill_starts_with_the_version_check[configure]` failed.

## Criterion 16: delivery, checked by hand

All runs from a scratch folder outside the repository, with a stub `tcw`
printing `tcw 0.0.1` first on PATH. The worktree's HEAD and status were the same
before and after each run.

**Claude** (`claude -p … --plugin-dir <worktree> --max-turns 2`, asked to repeat
any tcw-version message from its session-start context without running tools).
The answer, verbatim:

```
tcw: the `tcw` CLI on your PATH is 0.0.1, but the tcw plugin skills loaded in this session are from 2.5.0. They come from different releases, so the skills may describe commands or behavior this CLI does not have, or lack ones it does.
To bring them into line, upgrade the CLI: pipx upgrade tcw-cli (for a development checkout, update the checkout instead).
If that does not reach 2.5.0, that release is not on PyPI yet; the warning will clear once it is.
```

The hook's warning reaches the agent's context.

**Codex** (`codex -C <scratch> exec --skip-git-repo-check --disable shell_snapshot -c sandbox_mode=read-only -o <file> "Read the skill file <…>/skills/work/SKILL.md and follow it to show me the tcw work board for this folder. …" < /dev/null`;
the session header read `sandbox: read-only`). The user's installed Codex
plugin and configuration were not touched, so the skill was pointed at by path.

- **Run 1 (code from `9cd0b3b8`):** Codex ran
  `bash ".../scripts/check_versions.sh"` on its own, before any `tcw`
  command, and reported "Printed nothing; exit status 0". That silence was
  wrong. Reproduced with `codex sandbox -c sandbox_mode=read-only`:
  `mktemp: mkstemp failed … Operation not permitted`. Fixed in `87e321c0`.
- **Run 2 (after the fix):** Codex again ran the check first. This time its
  shell's startup files put the real `tcw` (2.5.0) ahead of the stub, which
  matched the plugin's 2.5.0, so silence was correct. The run shows the PATH an
  agent's shell ends up with is not always the one it was started with.
- **Run 3 (after the fix, mismatch independent of PATH):** the skill was read
  from a copy of the plugin whose manifests say 9.9.9. Codex ran the check
  first and relayed:

  ```
  tcw: the `tcw` CLI on your PATH is 0.0.1, but the tcw plugin skills loaded in this session are from 9.9.9. They come from different releases, ...
  To bring them into line, upgrade the CLI: pipx upgrade tcw-cli (for a development checkout, update the checkout instead).
  If that does not reach 9.9.9, that release is not on PyPI yet; the warning will clear once it is.
  ```

So in all three Codex runs the agent acted on the line unprompted. That is
three runs of one model on one task, not a guarantee (spec, Risks).

**Timing** (Verification step 4): ten runs of the bootstrap's steady-state
path with matching versions on this machine, median 0.12 seconds in total,
0.11 seconds of it the check.

## What the plan or spec got wrong

- **The plan's temporary file broke the check under Codex.** Plan Task 1 step 5
  captured `tcw --version` into a `mktemp` file, and step 7 split versions with
  here-strings, which bash 3.2 also backs with a temporary file. Codex's
  read-only sandbox refuses every file write, so the check exited silently: the
  exact false silence goal 5 exists to avoid, on the one harness the skill line
  is for. Fixed with command substitution and regular-expression parsing;
  `plan.md` now carries a correction note. Neither spec nor plan considered that
  the Codex path runs inside a sandbox.
- **A test in the plan's list passed without testing anything.**
  `test_an_explicit_root_wins` wrote its manifest on one line
  (`{"version": "2.5.0"}`), which the manifest pattern does not match (it
  expects the key at the start of a line, as the shipped manifests have it), so
  the check was silent for the wrong reason. It now uses a real multi-line
  manifest and also asserts the warning without the argument. The pattern's
  line-start requirement is kept: the shipped manifests are multi-line, and
  `test_the_real_manifests_parse` guards that.
- **Stubbing an owning interpreter behaves differently on macOS.** The
  bootstrap tests' stand-in interpreter is a shell script. Linux runs a script
  named as another script's interpreter; macOS does not, and runs the `tcw`
  stub's own body with `sh` instead. `_owned_tcw` answers `--version` both ways;
  its docstring says why.
- **`test_real_editable_checkout_is_left_alone`** had to accept the warning as
  its only output, as the plan foresaw.

## Deferred or unverified

- **Unverified: whether `codex plugin marketplace upgrade tcw` alone updates the
  installed plugin**, or `codex plugin add tcw@tcw` is also needed. Skipped by
  the decision recorded at the end of `plan.md`, because checking it changes the
  user's own Codex install. The message gives both commands.
- **Not checked: whether Codex runs the plugin's SessionStart hook** (spec
  Notes). Run 3 used a plugin copy that Codex had not installed, so its hook
  could not fire.
- **`docs/release-notes/upcoming.md` says v2.5.1 changes "Nothing else"** beyond
  v2.5.0. This item's entry is added under "Also in this release", which makes
  that sentence untrue. It belongs to the release as a whole and to other items
  in the batch, so it is left for whoever merges them.

## Notes

- During implementation `pkill -f "pytest -q -p no:cacheprovider"` was run to
  stop this item's own stale suite run. That pattern would also have matched a
  suite another agent was running with the same flags at that moment.
- **Folded in at verify (review findings).** The deadline was not a real
  ceiling: after TERM the command substitution kept waiting on the output pipe,
  so a `tcw` that ignores TERM held up session start for as long as it ran
  (reproduced at 8.5 seconds). The check now sends KILL to the same process
  group 0.2 seconds after TERM. The hanging test is parametrized with a stub
  that ignores TERM, and both cases now track the stub's own PIDs rather than
  matching process names; removing the KILL line makes the TERM case wait the
  stub's full 37 seconds. The bootstrap's steady-state comment no longer says no
  interpreter starts, and the release note no longer says "the one command".
- **Second deadline gap, also folded in at verify.** A `tcw` that prints its
  version and exits while a background child keeps the output pipe open made
  the check wait for that child (20 seconds in the verifier's reproduction).
  After the polling loop the check now always sends KILL to the process group,
  ignoring the error when the group is already empty.
  `test_a_child_left_holding_the_output_does_not_delay_the_warning` failed
  before the fix (waited 37.2 seconds) and passes after it. The verifier's
  stand-ins now take 3.6 seconds (ignores TERM; silent) and 0.2 seconds (child
  left behind; warns).

## Autonomous decisions

Taken in an autonomous run; each consulted Codex (read-only) and an Opus subagent.

- **Put the check outside the CLI, as a plugin script?** Codex: sound, because an older CLI rejects new arguments. Opus: sound, because argparse's exit 2 would turn a warning into a block, and an environment variable misses the older-CLI case. Chose a plugin-side script.
- **Warn on a patch-only difference?** Codex: yes. Opus: yes. Chose yes.
- **Add the instruction to all 17 skills?** Codex: all. Opus: all. Chose all.
- **(Plan) An opt-in check at verify that `codex plugin marketplace upgrade tcw` alone updates an installed plugin.** No advisor. Skipped by the coordinating session, because it changes the user's own Codex install without their consent. Recorded as unverified.
- **Code review** (adversarial-code-reviewer): NOT DONE on one finding. The 3-second limit was not a real ceiling for a `tcw` that ignores TERM. It also flagged a stale bootstrap comment and a release-note wording error. All three were fixed in 10ac237f. The verifier found a second gap, a child left holding the output, fixed in 34aba83b. Nothing rejected.
- **Verify** (tcw:verifier): accept. Criteria 1–14 and 16 are met. Criterion 15, the capability status Missing → Supported, is set at verify in the same commit as this section, as the ledgerless item did.
- **Hands-on QA** by the coordinating session: with a stand-in `tcw` printing 2.4.0 the script warned with the upgrade advice. With 2.5.0 it was silent. With a stand-in that ignores TERM and sleeps 8 seconds it gave up silently at 3.5 seconds and left no process behind. Exit 0 in every case.
