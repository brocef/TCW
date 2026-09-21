# Plan: Warn when the loaded plugin skills are from a different version than the tcw CLI

Implements `spec.md` (committed in c27060ab). Implementation runs in
`.worktrees/<slug>` on `work/<slug>` after `tcw work start --worktree`. Run the
suite with bare `pytest` from the worktree root, as CI does
(`.github/workflows/*.yml` runs `pip install -e '.[dev]'` then `pytest`). No
file under `tcw/` changes, so the CLI stays safe to drive during this item.

No blockers. `2026-08-12-separate-the-agent-plugin-from-the-python-cli-source`
is related, not a blocker: this item is built to survive it (Task 2 stops
depending on `tcw/__init__.py`), and neither needs the other first.

## Remedy commands, verified 2026-09-21

Read from each tool's own `--help` on this machine (Claude Code CLI, Codex CLI
0.155.1):

| Need | Command | Evidence |
| --- | --- | --- |
| Update the plugin, Claude Code, user-wide install | `claude plugin update tcw@tcw` | `claude plugin update --help`: "Update a plugin to the latest version (restart required to apply)" |
| Same, install made for one project | `claude plugin update tcw@tcw --scope project` (or `--scope local`) | same help: `-s, --scope <scope>  Installation scope: user, project, local, managed (default: user)`. The reported case was a `project`-scope install (`~/.claude/plugins/installed_plugins.json`) |
| Update the plugin, Codex | `codex plugin marketplace upgrade tcw`, then `codex plugin add tcw@tcw` | `codex plugin marketplace upgrade --help`: "Refresh configured Git marketplace snapshots", takes an optional marketplace name; `codex plugin add --help`: installs `PLUGIN@MARKETPLACE` from a configured marketplace |
| Upgrade the CLI (pipx) | `pipx upgrade tcw-cli` | already the documented remedy, `skills/setup/references/install.md:39` |
| Match the CLI to older skills (pipx) | `pipx install --force tcw-cli==<skills version>` | pipx's standard version-pin form; `--force` is what the bootstrap already uses (`scripts/session_bootstrap.sh:102`) |

**Still unconfirmed, and said so in the message rather than hidden:** whether
Codex's `marketplace upgrade` alone moves the installed plugin, or the
`plugin add` step is also needed. On this machine the Codex plugin cache moved
to 2.5.0 (revision `7974ed30`, the v2.5.0 tag) while `config.toml`'s
`[marketplaces.tcw] last_revision` still reads an August commit, so the cache
is updated by a path the help text does not describe. The message gives both
commands; running `add` for an already-installed plugin is the documented
install path (`README.md:85-86`). Confirming it needs a real Codex update,
which changes the user's own install, so it is an opt-in step under
Verification, not something this plan runs.

## The warning text

Fixed here so tests can assert on it. `<cli>` and `<skills>` are the two
versions. First line, always:

```
tcw: the `tcw` CLI on your PATH is <cli>, but the tcw plugin skills loaded in this session are from <skills>. They come from different releases, so the skills may describe commands or behavior this CLI does not have, or lack ones it does.
```

Then, when the CLI is **newer**:

```
To bring them into line, update the plugin and restart the session:
  Claude Code: claude plugin update tcw@tcw   (add --scope project if you installed it for one project)
  Codex: codex plugin marketplace upgrade tcw, then codex plugin add tcw@tcw
Or, if you installed the CLI with pipx, match it to the skills instead: pipx install --force tcw-cli==<skills>
```

When the CLI is **older**:

```
To bring them into line, upgrade the CLI: pipx upgrade tcw-cli (for a development checkout, update the checkout instead).
If that does not reach <skills>, that release is not on PyPI yet; the warning will clear once it is.
```

Every line begins at column 0 except the two indented command lines. The
prefix `tcw: the \`tcw\` CLI on your PATH is` is what tests use to recognize the
message.

## Tasks

### Task 1: the check script, with its own tests

**Creates** `scripts/check_versions.sh` (mode 755) and
`tests/test_check_versions.py`.

Script behavior, in order:

1. `exec 2>/dev/null`: the script never writes to standard error (bash's own
   job-control notices included), so a hook transcript stays clean.
2. Plugin root: `root="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"`.
   Quote every use; the root may contain spaces.
3. Plugin version: the first match of `"version": "X.Y.Z"` in
   `$root/.claude-plugin/plugin.json`, else in `$root/.codex-plugin/plugin.json`,
   extracted with `sed -n` (the only `"version"` key in either manifest is the
   top-level one). No match: exit 0 silently.
4. `command -v tcw` fails: exit 0 silently.
5. _(Corrected during implement: the temporary file below made the check fall
   silent inside Codex's read-only sandbox, where `mktemp` fails. The output is
   captured with command substitution instead, with the deadline loop inside
   it, and step 7 parses both versions with the regular expression rather than
   here-strings, which bash 3.2 also backs with a temporary file. See
   `outcome.md`.)_ CLI version with a 3-second deadline, plain bash (macOS has no `timeout`):
   `set -m` so the background job gets its own process group; run
   `tcw --version </dev/null >"$tmp"` in the background, where `$tmp` comes from
   `mktemp` and is removed by an `EXIT` trap; poll `kill -0 "$pid"` every
   `sleep 0.1` for up to 30 rounds; if still running, `kill -TERM -- "-$pid"`
   (the whole group, so a wrapper's child dies too), then exit 0 silently. If
   `set -m` misbehaves on either platform, fall back to `pkill -P "$pid"`
   followed by `kill "$pid"`; criterion 7's test decides which is kept.
6. Parse `tcw X.Y.Z` from the first line with `[[ … =~ ^tcw\ ([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]`
   (bash 3.2 supports `=~`; keep the pattern in a variable). No match, or a
   non-zero exit from `tcw`: exit 0 silently.
7. Equal: exit 0 silently. Otherwise compare major, minor, patch as integers
   and print the first line plus the "newer" or "older" block above. Exit 0.

The script calls no `python`, `python3`, `jq` or `timeout`, and uses nothing
newer than bash 3.2.

Tests (each runs the script as `["/bin/bash", str(script)]` with
`PATH=<tmp bin>:/usr/bin:/bin`, a stub `tcw` written like
`tests/test_session_bootstrap.py`'s `_stub`, and a temporary plugin folder
holding a copy of the script under `scripts/` plus a minimal
`.claude-plugin/plugin.json` of the form `{"name": "tcw", "version": "…"}`):

- `test_matching_versions_print_nothing`: 2.4.0 / 2.4.0 → empty stdout, exit 0.
  (Criterion 1.)
- `test_cli_newer`: plugin 2.4.0, stub 2.5.0 → exit 0; stdout starts with the
  prefix, contains `2.5.0`, `2.4.0`, `claude plugin update tcw@tcw`, and not
  `pipx upgrade`. (Criterion 2.)
- `test_cli_older`: plugin 2.4.0, stub 2.3.0 → contains both versions and
  `pipx upgrade tcw-cli`, not `claude plugin update`. (Criterion 3.)
- `test_patch_only_mismatch_in_both_directions`, parametrized: plugin 2.4.0 /
  stub 2.4.1 gives the newer block; plugin 2.4.1 / stub 2.4.0 gives the older
  block. (Criterion 4.)
- `test_comparison_is_numeric`: plugin 2.9.0, stub 2.10.0 → newer block.
  (Criterion 5.)
- `test_cannot_tell_means_silent`, parametrized over: no `tcw` on PATH; stub
  `exit 3`; stub printing `something else`; plugin folder with no manifest;
  manifest with no version → empty stdout, exit 0. (Criterion 6.)
- `test_a_hanging_cli_is_abandoned_silently`: stub is
  `#!/bin/sh` + `sleep 37.4`. Assert the run takes under 4 seconds, stdout and
  stderr are empty, exit 0, and afterwards (after a 0.5-second grace)
  `pgrep -f "sleep 37.4"` finds nothing. (Criterion 7.)
- `test_codex_manifest_alone_is_enough`: only `.codex-plugin/plugin.json` →
  criterion 2's warning. (Criterion 8.)
- `test_root_is_found_from_the_script_location`: plugin folder at
  `tmp_path / "plugin root with space"`, run with no argument and
  `cwd=tmp_path / "elsewhere"` → reads that folder's manifest (a mismatch
  warns). (Criterion 9.)
- `test_the_real_manifests_parse`: with the repository root as the argument and
  a stub printing `tcw <tcw.__version__>`, nothing is printed; with a stub one
  patch higher, the warning names `tcw.__version__` as the skills version. This
  proves the `sed` extraction works on the shipped manifest layout, not only on
  the test's minimal one.
- `test_script_uses_no_forbidden_tools`: the script text matches none of
  `\bpython3?\b`, `\bjq\b`, `\btimeout\b` outside comments. (Criterion 10.)

Mutation checks before trusting the tests (per `CLAUDE.md`, "Measuring the
skill layer"): swap the numeric comparison for a string comparison and see
`test_comparison_is_numeric` fail; drop the process-group kill and see the
hanging test fail on the `pgrep` assertion; break the `sed` pattern and see
`test_the_real_manifests_parse` fail.

**Proves:** criteria 1-10. Suite green: nothing else references the script yet.

### Task 2: run the check from the SessionStart bootstrap

**Modifies** `scripts/session_bootstrap.sh` and `tests/test_session_bootstrap.py`.

Script changes:

1. Replace the step 1 guard (line 72) with two:
   - `[ -n "$root" ] || exit 0` (unchanged meaning for "no plugin root").
   - Register the check to run on every later exit:
     `trap 'if [ -f "$root/scripts/check_versions.sh" ]; then bash "$root/scripts/check_versions.sh" "$root" 2>/dev/null; fi' EXIT`.
     An `EXIT` trap covers every existing `exit 0` (steps 2, 3, 4 and the end)
     without touching them, and runs after the install attempt on the install
     path. It calls `bash` explicitly, so the executable bit does not matter.
     The `-f` test keeps a plugin copy without the script (every existing test
     fixture) silent.
   - `[ -f "$root/tcw/__init__.py" ] || exit 0`: the install logic still needs
     its marker, but this exit now fires the trap, so a manifest-only plugin
     still gets the check.
2. Rewrite the header comment (lines 12-14): every path exits 0; a failed
   install prints one line, and a CLI/plugin version difference prints the
   check's warning; both go to standard output because SessionStart adds
   standard output to the agent's context.

The script keeps exactly one `<<'PY'` heredoc, which
`tests/test_session_bootstrap.py::_editable_probe` requires.

Tests: add a helper `_plugin(tmp_path, version, with_marker=True)` that builds
a root holding `tcw/__init__.py` (when asked), `.claude-plugin/plugin.json`, and
a copy of the real `scripts/check_versions.sh`. New tests, each with plugin
2.4.0 and a stub `tcw` printing `tcw 2.5.0` unless stated:

- `test_manifest_only_root_still_warns`: no `tcw/__init__.py` → warning, exit
  0, pipx never called.
- `test_steady_state_warns_on_a_mismatch` and
  `test_steady_state_is_silent_when_versions_match` (stub 2.4.0).
- `test_unidentifiable_tcw_warns_and_is_left_alone`: stub shebang
  `#!/usr/bin/env bash` → warning, pipx never called, sentinel not written.
- `test_editable_checkout_warns_and_is_left_alone`: owning interpreter stub
  answers "editable" (as in `test_editable_install_is_left_alone`) → warning,
  pipx never called.
- `test_missing_pipx_warns`: stale sentinel, no pipx → warning, sentinel
  unchanged.
- `test_successful_install_is_compared_after_the_install`: a stub `pipx` that
  rewrites the `tcw` stub to print `tcw 2.4.0` → stdout empty, pipx called once
  with `install --force tcw-cli`, sentinel written.
- `test_failed_install_prints_both_lines`: stub `pipx` exits 1 → stdout holds
  the existing `pipx install tcw-cli` failure line first, then the warning;
  stderr empty; sentinel unchanged.
- `test_check_runs_without_the_executable_bit`: `chmod 644` the copied check
  script → steady-state case still warns.

Existing tests: all fixture tests keep passing unchanged, because `_clone`
roots hold no check script. `test_real_editable_checkout_is_left_alone` runs
against the repository itself with the real PATH, so its `assert r.stdout == ""`
changes to: every stdout line belongs to the version warning (the first starts
with the prefix) or stdout is empty. That keeps the test meaningful on a
maintainer machine whose editable CLI differs from the checkout's manifest,
while still failing on any install output.

`tests/test_plugin_manifests.py::test_hooks_manifest_wires_one_executable_session_start_script`
is not touched and must still pass (still one SessionStart command).

Mutation checks: remove the trap and see the steady-state, editable and
manifest-only tests fail; move the trap registration below the
`tcw/__init__.py` exit and see only `test_manifest_only_root_still_warns` fail;
drop the explicit `bash` and see the executable-bit test fail.

**Proves:** criteria 11 and 12, and the header-comment part of 14. This is the
riskiest change (it edits the script every Claude session runs), so it comes
after Task 1's script already has its own tests.

### Task 3: the version-check line in every skill

**Modifies** all 17 `skills/*/SKILL.md`: `capabilities`,
`commands-drive-work-to-completion`, `commands-pause-work`,
`commands-plan-work`, `commands-process-inbox`, `commands-verify-work`,
`configure`, `documentation-sync`, `extras-autonomous-work`, `extras-report`,
`extras-triage-issues`, `post-mortem`, `setup`, `taxonomy`, `work-create`,
`work-stage`, `work`. **Adds to** `tests/test_check_versions.py`.

The line, identical in every file, is the first line after the frontmatter's
closing `---` (before the existing blank line, so each body grows by exactly
one line):

```
**Version check.** Under Claude Code, skip this: the session-start hook already ran it. Under any other harness, once per session before your first `tcw` command, run `bash "<plugin>/scripts/check_versions.sh"`, where `<plugin>` is two folders above the folder holding this `SKILL.md`, and pass on anything it prints to the user.
```

Constraints this placement respects, checked in the current tree:

- `skills/work/SKILL.md`'s body is 59 lines against
  `tests/test_skill_lifecycle_parity.py`'s `SKILL_LINE_BUDGET = 60`; one added
  line lands exactly on the budget. Do not add a blank line before it.
  (`setup` and `configure` are at 32 and 31 lines, same budget.)
- The line contains no `` !` `` and no `$ARGUMENTS`, so the routing skills'
  "no Claude-only mechanism" test still passes, and `work-stage`'s first
  injected command is still its validation line.
- It names no `setup/references/` or `configure/references/` path
  (`tests/test_skill_path_pointers.py`).

Test: `test_every_skill_starts_with_the_version_check`, parametrized over every
`skills/*/SKILL.md`: the first line after the closing `---` equals the constant
above. Also assert the set of skills found is 17, so a skill added later
without the line fails loudly rather than being unparametrized. Mutation check:
delete the line from one skill and see exactly that case fail.

**Proves:** criterion 13.

### Task 4: capability ledger

**Creates** `docs/capabilities/plugin/warn-when-skills-and-cli-versions-differ/`
(via `tcw capabilities add plugin/warn-when-skills-and-cli-versions-differ
"Warn when skills and CLI versions differ" --status Missing`, run from the
worktree root, then `tcw capabilities set … --field Subject=cli,skill`), with
the description drafted in `spec.md`. **Modifies**
`docs/capabilities/plugin/bootstrap-the-cli/description.md`: replace "so the
command never goes stale behind the skills that drive it" with a clause saying
the installed CLI can still differ from the plugin, and that the session then
warns (naming the new capability's behavior). **Creates** the item's
`capabilities.yaml`:

```yaml
new:
    - plugin/warn-when-skills-and-cli-versions-differ
changed:
    - plugin/bootstrap-the-cli
```

Add `skills/extras-report` under `changed:` only if its capability description
names what the bug template's Environment block asks for; leave it out
otherwise. The status flips to `Supported` at completion, as the capabilities
skill prescribes.

**Proves:** criterion 15 (ledger half). Check: `tcw capabilities check` passes
and `tcw capabilities show plugin/warn-when-skills-and-cli-versions-differ`
prints the entry.

### Task 5: Documentation Sync

One pass over the finished diff. Every entry `tcw work stage prompt plan`
printed, evaluated:

| Entry | Fires? | Task |
| --- | --- | --- |
| `README.md` (Public-API) | **Yes**: user-facing session behavior changes | In the plugin install section (after the Claude paragraph ending at line 80, and in the Codex paragraph at 89-90), add one sentence each: the session warns when the CLI and the plugin come from different releases, and says how to line them up; under Codex the skills ask the agent to run the check. Leave the "Codex has no session-start hook" sentence as is (spec Non-goals). |
| `docs/guide/jira.md` (Tracker-Change) | No: no tracker behavior changes | none |
| `docs/guide/<topic>.md` (Guide-Topic-Change) | No: no guide covers installing the plugin or CLI (`docs/guide/` holds configuration, jira, linking-and-validation, multi-repo, taxonomy-and-capabilities, web-viewer, work; none mentions pipx, the bootstrap or plugin versions) | none |
| `docs/release-notes/upcoming.md` (Public-API) | **Yes** | Plain-language entry: your agent now tells you when the `tcw` command and the plugin's skills come from different releases, and what to run; it never stops work. |
| `docs/changelogs/upcoming.md` (Any-Code-Change) | **Yes** | Under `### Added`: `scripts/check_versions.sh`, the bootstrap's `EXIT` trap and its independence from `tcw/__init__.py`, the per-skill line, and the tests. Under `### Changed`: `install.md`, the `extras-report` template. |
| `skills/<component>/SKILL.md` (Skill-Driven-Component) | **Yes** | Task 3 covers all 17. Also: `skills/setup/references/install.md:39-41` gets a sentence that a difference is allowed but the session now warns about it, pointing at the warning's own advice; `skills/extras-report/SKILL.md` bug skeleton (line 78) gains `- tcw plugin version: <the plugin version your agent loaded, e.g. from its plugin list>` directly under the `tcw version` line. |
| `skills/configure/references/<document>.md` (Configuration-Key-Change) | No: no configuration key is added or changed | none |

The two `upcoming.md` files are also being edited by the other items batched
for v2.5.1; rebase before committing and keep their entries intact.

**Proves:** criteria 14 and 15 (changelog half). `pytest` stays green,
including `tests/test_documented_cli_surface.py`, which parses every `tcw …`
invocation in the Markdown touched here.

## Verification

What the suite cannot check, done at the verify stage and recorded in
`outcome.md` with the transcript lines (criterion 16):

1. **Claude, real hook.** From a scratch folder, put a stub `tcw` printing
   `tcw 0.0.1` first on PATH and start
   `claude -p "Say exactly what the session-start context told you about tcw versions." --plugin-dir <worktree>`.
   Pass: the answer repeats the mismatch warning. `--plugin-dir` is required so
   the session loads this checkout's plugin, not the installed marketplace copy.
2. **Codex, skill instruction.** Same stub and scratch folder;
   `codex exec -c sandbox_mode=read-only --disable shell_snapshot -o <file> "Use the tcw work skill to list the work items here." < /dev/null`,
   with the worktree's plugin installed for Codex, or with the skill text
   supplied if installing it would touch the user's Codex setup (ask first).
   Pass: the transcript shows `bash …/scripts/check_versions.sh` run and the
   warning relayed. A Codex session that does not act on the line is recorded
   as a finding, not retried until it does. If the Codex hook also fired
   (see spec Notes), record that too.
3. **Opt-in, with the user's consent only:** confirm whether
   `codex plugin marketplace upgrade tcw` alone updates the installed plugin or
   `codex plugin add tcw@tcw` is also needed, and trim the message if one
   command suffices. This changes the user's own Codex install, so it is not
   run without asking.
4. **Timing.** Run the bootstrap's steady-state path ten times on this machine
   with matching versions and record the median added time (expected about 0.2
   seconds, bounded by the 3-second deadline).

## Acceptance criteria coverage

| Criterion | Task |
| --- | --- |
| 1-10 (script behavior) | 1 |
| 11, 12 (bootstrap paths, explicit `bash`, one hook) | 2 |
| 13 (line in every skill) | 3 |
| 14 (`install.md`, header comment, `extras-report`) | 2 (comment), 5 |
| 15 (ledger, changelogs) | 4, 5 |
| 16 (manual delivery check) | Verification |

## Notes

- The 3-second deadline is a judgment call: `tcw --version` took about 0.2
  seconds here, and a first run after an install can be slower while Python
  compiles its cache files. The spec accepts a missed warning over a stalled
  session start.
- `tcw` alone in backticks inside the skill line is not a `tcw` invocation, so
  `tests/test_documented_cli_surface.py` should not match it; if it does, the
  test names the problem and the line can say "the tcw CLI" instead.

## Decision taken on the plan (2026-09-21, autonomous run)

- **The opt-in Codex upgrade confirmation at verify is skipped.** It would change the
  user's own Codex install, and the user is not present to consent. The message keeps
  both Codex commands, and outcome.md records that it is unverified whether
  `codex plugin marketplace upgrade tcw` alone updates the installed plugin.
