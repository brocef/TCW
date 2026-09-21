# Spec: Warn when the loaded plugin skills are from a different version than the tcw CLI

## Capability changes

Planned ledger changes only; nothing is written to the ledger at this stage.

- **Add** `plugin/warn-when-skills-and-cli-versions-differ` (status `Missing`
  now, `Supported` at completion; subjects `cli`, `skill`). Draft wording:
  _"As a user, when the `tcw` CLI on my PATH and the tcw plugin skills my agent
  loaded come from different releases, I am told so in the session: which
  version each one is, and the command that brings them into line. The warning
  never stops my work. Under Claude it appears when the session starts; under
  Codex the skills tell the agent to run the same check."_
- **Modify** `cap-17ca61` (`plugin/bootstrap-the-cli`). Its description claims
  the automatic install means _"the command never goes stale behind the skills
  that drive it"_. That is not true: the install takes whatever PyPI's newest
  `tcw-cli` is (`scripts/session_bootstrap.sh:102`), which can be newer or older
  than the plugin, and the script deliberately leaves a `tcw` it did not install
  alone (`scripts/session_bootstrap.sh:86-91`). Reword that clause to say the
  versions can still differ and that the new warning reports it.

## Problem

The `tcw` CLI and the plugin skills are released together from this repository
under one version string (the five version-bearing files listed in `CLAUDE.md`),
but they reach a user's machine by two separate routes: the skills through the
agent's plugin system, the CLI through PyPI (or a developer's own install). The
two routes drift apart and nothing notices, so an agent follows instructions
written for a CLI it is not running.

What the code does today:

- The only version comparison anywhere is the SessionStart hook's install
  trigger. `hooks/hooks.json:8` runs `scripts/session_bootstrap.sh`, which reads
  the plugin's version marker (`$root/tcw/__init__.py`) and compares it
  byte-for-byte with a copy saved after its last install (the "sentinel",
  lines 80-84). It never asks the CLI what version it is. When it does install,
  it installs the newest `tcw-cli` on PyPI (line 102), not the plugin's version.
- It exits at step 1, before anything else, when there is no plugin root or no
  `$root/tcw/__init__.py` (line 72). That file disappears from the plugin once
  `2026-08-12-separate-the-agent-plugin-from-the-python-cli-source` lands.
- It skips, printing nothing, whenever the `tcw` on PATH is not one it can
  identify as a plain pipx-style install (line 89), is a developer's editable
  checkout (line 90), or `pipx` is missing (line 95).
- The setup skill says outright that the CLI "floats, and it is not required to
  equal the plugin's version" (`skills/setup/references/install.md:39-41`).
- Codex is documented as having no session-start hook
  (`skills/setup/references/install.md:9-10`, `README.md:89`), so under Codex
  nothing runs at all unless the agent is told to.
- `tcw --version` prints `tcw X.Y.Z` (`tcw/cli.py:469`) and has done so in
  every release, so any CLI, old or new, can answer the question.

The reported case (proposit-app, 2026-09-21): the CLI was 2.5.0 and the
Claude plugin loaded for that project was 2.4.0 (confirmed on this machine:
`~/.claude/plugins/installed_plugins.json` records `tcw@tcw` for
`/Users/brian/Projects/Proposit-App` at install path `.../cache/tcw/tcw/2.4.0`).
PyPI's newest `tcw-cli` is 2.4.0, so the 2.5.0 CLI was not a PyPI install at
all: the `tcw` on PATH is a pyenv shim (`#!/usr/bin/env bash`) resolving to
`~/.pyenv/versions/3.14.6/bin/tcw`, which is exactly the kind of `tcw` the
bootstrap leaves alone without a word. The skills described 2.4.0 behavior; the
CLI had 2.5.0's. Nothing said so.

## Goals

1. When the version of the loaded plugin and the version `tcw --version`
   reports differ, the agent is told, in one short message: both versions, which
   side is behind, and the command that brings them into line. The message
   describes the difference as the two coming from different releases, which
   may mean the skills describe behavior the CLI lacks. It does not claim they
   are incompatible: many releases change neither side's contract.
2. **Warn only** (the requester's decision, 2026-09-21): no path of the check
   blocks, fails, or changes a session's outcome. It always exits 0.
3. It reaches **Claude and Codex** users. Under Claude it runs at session start
   with no agent action. Under Codex, and any harness where the hook does not
   run, the skills themselves tell the agent to run it.
4. It still works when the CLI is the **older** side, including a CLI from
   before this change.
5. Silent when the versions match, and silent when it cannot find out (no `tcw`
   on PATH, unreadable output, a `tcw --version` that does not answer in time,
   unreadable plugin manifest). A missing or broken CLI is the setup skill's
   job, and a false alarm every session is worse than no warning.
6. It never slows session start by more than a fixed, short limit, however the
   CLI behaves.

## Non-goals

- **Blocking or refusing on a mismatch.** Ruled out by the requester.
- **Changing what the bootstrap installs.** Pinning the install to the plugin's
  own version (`pipx install tcw-cli==<plugin version>`) would remove one source
  of drift, but it changes install behavior, and it would fail outright whenever
  the plugin is ahead of PyPI, as it is today with 2.5.0. Not this item.
- **Covering skills from releases that predate this change.** The check ships
  with the skills, so a user still on 2.4.0 skills gets no warning until their
  plugin carries the check. Nothing can fix that: the CLI cannot tell which
  skills an agent loaded (see Design).
- **Detecting how the CLI was installed** (pipx, editable checkout, pyenv) to
  tailor the advice. The message states its advice conditionally instead ("if
  you installed it with pipx…").
- **Revisiting the "Codex has no hook" claims** in `README.md`,
  `skills/setup/SKILL.md` and `install.md`. See Notes: there is evidence recent
  Codex runs plugin hooks, but confirming it and rewriting that guidance is a
  separate item.
- **The plugin/CLI split** itself. This item must keep working after it lands,
  which is why the check reads the plugin manifest and runs independently of
  `tcw/__init__.py`, but it does none of that work.

## Design

### Where the comparison lives, and why not in the CLI (settled)

Settled after review by Codex and an Opus reviewer: the comparison ships **with
the skills**, as a small script in the plugin (proposed
`scripts/check_versions.sh`; the plan may name it differently). It reads the
plugin's own version from the plugin manifest and asks the CLI with
`tcw --version`, which every release answers.

The alternatives each fail the case that matters most, a CLI older than the
skills:

- **A check inside the CLI** does not exist in a CLI that predates it, so it
  says nothing exactly when the CLI is behind.
- **A new CLI flag the skills pass their version to** (for example
  `tcw work stage validate --skills-version …`) is worse than silent against an
  older CLI: argparse rejects the unknown option with exit status 2, so the
  command the skill was actually running fails too.
- **An environment variable the skills set for the CLI** is ignored by an older
  CLI, so again nothing is reported when the CLI is behind.
- **The CLI searching the harnesses' plugin caches** answers the wrong
  question: this machine's Claude cache holds thirteen tcw versions side by
  side, and which one is loaded is decided per project in
  `installed_plugins.json`. Guessing from harness-internal files breaks
  silently whenever a harness changes its layout.

This is a deliberate exception to `docs/lifecycle/harness.md:16` ("anything
that must be guaranteed belongs in the `tcw` CLI"). The warning is not a
guarantee (goal 2), the CLI is the one component that cannot perform it, and
both harnesses still get it (goal 3). The script is plain `bash`, like
`session_bootstrap.sh`, and behaves the same under both; only what triggers it
differs.

### The check script

- **Plugin root**: an optional first argument; otherwise the folder above the
  script's own folder, resolved from the script's path so the working directory
  does not matter and paths containing spaces work. It needs no harness
  variable.
- **Plugin version**: the top-level `"version"` in `.claude-plugin/plugin.json`
  in the plugin root, falling back to `.codex-plugin/plugin.json`. Both exist in
  the Claude and the Codex install of the plugin (checked:
  `~/.claude/plugins/cache/tcw/tcw/2.4.0/` and
  `~/.codex/plugins/cache/tcw/tcw/2.5.0/` both hold both folders), and
  `tests/test_plugin_manifests.py` already keeps them equal to the other three
  version-bearing files. Not `tcw/__init__.py`, which the split item removes
  from the plugin.
- **CLI version**: `tcw --version`, expected to print `tcw X.Y.Z`.
- **Time limit**: `tcw --version` gets a fixed deadline (a few seconds; the
  plan picks the number). macOS ships no `timeout` command, so the deadline is
  built in plain `bash`: run the command in the background, and stop it if it
  has not finished when the deadline passes. On timeout the check is silent and
  exits 0, and it leaves no process running behind it.
- **Comparison**: numeric, part by part (so 2.10.0 is newer than 2.9.0), only
  to pick which advice to print. **Any difference in `X.Y.Z` warns, patch
  included** (settled): patch releases change skills too, and skipping them
  would hide exactly the drift this item exists to report.
- **Output**: to standard output, because a SessionStart hook's standard output
  is what reaches the agent's context (`scripts/session_bootstrap.sh:12-14`
  records this). Exit status 0 on every path.
- **No dependencies** beyond `bash` and standard command-line tools: no `jq`,
  no `timeout`, and no `python3` from PATH (the bootstrap explains at lines
  23-28 why the PATH `python3` is the wrong interpreter to ask anything). It
  must run under macOS's `/bin/bash` 3.2 as well as Linux.

The message, in outline (the plan settles exact text):

> tcw: the `tcw` CLI on your PATH is **2.5.0**, but the tcw plugin skills
> loaded in this session are from **2.4.0**. They come from different releases,
> so the skills may describe commands or behavior this CLI does not have, or
> lack ones it does.

followed by one of two remedies:

- **CLI newer than the skills**: update the plugin. As the alternative, if the
  CLI was installed with pipx, reinstall it at the skills' version.
- **CLI older than the skills**: upgrade the CLI if it was installed with pipx;
  a development checkout needs updating in place. If the upgrade cannot reach
  the skills' version, that release is not on PyPI yet.

The exact commands (`claude plugin update tcw@tcw` and whether a project-scoped
install needs a scope option; the Codex update path; the pipx lines) are
**to be verified at plan time** before any of them is written into the
message. See Notes.

### Trigger under Claude: the SessionStart hook

`session_bootstrap.sh` runs the check as `bash "$root/scripts/check_versions.sh"
"$root"`, calling `bash` explicitly so a lost executable bit cannot silently
disable it. It runs on **every path where the plugin root is known**, whether
or not `$root/tcw/__init__.py` exists:

- The step 1 exit at line 72 is split: "no plugin root" still exits silently,
  but "plugin root without `tcw/__init__.py`" skips only the install logic and
  still runs the check.
- On the install paths, the check runs **after** the install attempt, so it
  compares against the CLI as it now is, on success and on failure alike.
- On the early exits (step 2 steady state, step 3 "not ours to replace" and
  editable checkout, step 4 no `pipx`), it runs before exiting.
- The existing install protections are unchanged: the check only reads, never
  installs, and nothing about when or over what the bootstrap installs changes.

It is called from the bootstrap rather than added as a second hook entry,
because separate hook entries for one event are not guaranteed to run in order,
and `tests/test_plugin_manifests.py:205-222` asserts exactly one SessionStart
command.

Cost: one `tcw --version` per session start (about 0.2 seconds on this
machine), capped by the deadline, where the steady-state path today starts no
interpreter at all.

### Trigger under Codex and any other harness: the skills (settled)

Every `skills/*/SKILL.md`, all seventeen (settled), gets the same short
instruction, following the precedent at `skills/work-stage/SKILL.md:13-15` (a
line only non-Claude harnesses act on): _under any harness other than Claude
Code, once per session before running any `tcw` command, run
`bash "<plugin>/scripts/check_versions.sh"` and relay any warning it prints to
the user, where `<plugin>` is `<the folder holding this SKILL.md>/../..`._
Under Claude the hook has already run it, so the line says Claude should skip
it; no `` !`…` `` injection is used, which would repeat the hook's warning.

All seventeen rather than a subset, because any one of them may be the only tcw
skill a Codex session loads (the reported case went through `capabilities`,
`work-stage` and a command skill). A test fails when a shipped `SKILL.md` lacks
the instruction.

### What is and is not verified about delivery

The text being present in a skill is not the same as an agent running it, and
pytest can only prove the former. So:

- **Verified automatically:** the script's behavior (criteria 1-10), the
  bootstrap running it on every path (criterion 11), and the instruction being
  present in every skill (criterion 13).
- **Verified once, by hand, at the verify stage** (criterion 16): one Claude
  session and one Codex session, each started against a copy of this checkout's
  plugin with a mismatched stub `tcw` on PATH, and the transcript checked for
  the warning reaching the agent. Under Claude this confirms hook output reaches
  context; under Codex it confirms an agent that loads a tcw skill acts on the
  instruction. The eval harness under `evals/` (CLAUDE.md, "Measuring the skill
  layer") is the right instrument for a repeatable measurement, but it spawns
  only `claude` (`evals/run_evals.py:100`), so it cannot measure the Codex path;
  adding a Codex arm is out of scope.
- **Not verified:** that every Codex agent, in every session, runs the
  instruction. It is a request to a model, accepted as such under the warn-only
  decision.

### Sibling sweep

Searched the whole repository for other places where the two versions meet or
are described (`tcw --version`, `__version__`, `CLAUDE_PLUGIN_ROOT`,
`session_bootstrap`, "floats"). Findings, each handled here:

- `skills/setup/references/install.md:39-41` says the floating CLI "is not
  required to equal the plugin's version". It is still allowed, but it now
  warns; the paragraph must say so.
- `scripts/session_bootstrap.sh:12-14`, the header comment, says "only a failed
  install prints". After this change a version mismatch prints too; update the
  comment.
- `cap-17ca61` overclaims (see Capability changes).
- `skills/extras-report/SKILL.md:78`: the bug template's Environment block
  asks for `tcw --version` but not the plugin version, so a mismatch is
  invisible in the reports that would reveal it. Add a plugin-version line.
- `skills/work-stage/SKILL.md:27` reads the stage contract from the plugin
  while line 31 asks the CLI for the stage instructions: the two halves of one
  stage come from the two sides that can differ. The general warning covers
  it; no separate change.
- `session_bootstrap.sh:102` installs PyPI's newest rather than the plugin's
  version: a source of drift, left alone (Non-goals).

### Abstraction litmus test

No store operation is added or changed. The check reads plugin files and runs
the CLI; nothing touches items, statuses or references.

## Acceptance criteria

Unless it says otherwise, each is checked with a stub `tcw` on PATH (a script
printing a chosen `--version` line) and a temporary plugin folder holding a
manifest, and the check is run as `/bin/bash <script>`.

1. Plugin manifest `2.4.0`, stub prints `tcw 2.4.0`: the check prints nothing
   and exits 0.
2. Plugin `2.4.0`, stub prints `tcw 2.5.0`: exits 0; one message containing
   both `2.5.0` and `2.4.0` and the "update the plugin" advice, and not the
   "upgrade the CLI" advice.
3. Plugin `2.4.0`, stub prints `tcw 2.3.0`: exits 0; the message contains both
   versions and the "upgrade the CLI" advice, and not the "update the plugin"
   advice.
4. Patch-only, both directions: plugin `2.4.0` with stub `tcw 2.4.1` gives the
   "CLI newer" message; plugin `2.4.1` with stub `tcw 2.4.0` gives the
   "CLI older" message.
5. Plugin `2.9.0`, stub prints `tcw 2.10.0`: the "CLI newer" message (numeric
   comparison, not text comparison).
6. No `tcw` on PATH; a stub that exits non-zero; a stub printing
   `something else`; a plugin folder with no readable manifest: each prints
   nothing and exits 0.
7. A stub that sleeps far longer than the deadline: the check returns within
   the deadline plus one second, prints nothing, exits 0, and no stub process
   is still running afterwards.
8. Only `.codex-plugin/plugin.json` present (no `.claude-plugin/`): the plugin
   version is still read, and criterion 2's setup still warns.
9. Run with no arguments, from an unrelated working directory, as a copy of the
   script inside a plugin folder whose path contains a space: it reads that
   folder's manifest (its root is the folder above the script's own).
10. The check script contains no call to `python`, `python3`, `jq` or
    `timeout`.
11. `session_bootstrap.sh`, with a plugin root whose manifest says `2.4.0` and
    a stub `tcw 2.5.0`, prints the mismatch message and exits 0 on each path:
    - a manifest-only plugin root with **no** `tcw/__init__.py`;
    - the steady-state path (sentinel matches);
    - the "not ours to replace" path (a stub with a non-Python shebang);
    - the editable-checkout path (line 90);
    - the no-`pipx` path;
    - a successful install, where a stub `pipx` replaces the stub `tcw` with one
      printing `tcw 2.4.0`: nothing is printed, which proves the comparison saw
      the CLI after the install;
    - a failed install (stub `pipx` exits non-zero): the existing failure line
      and the mismatch message both appear.
    With a matching stub it prints nothing on the steady-state path. On every
    path, whether `pipx install` is called and whether the sentinel is written
    are the same as before this change.
12. The bootstrap invokes the check through `bash` explicitly: with the
    executable bit removed from the check script, criterion 11's steady-state
    case still warns. `hooks/hooks.json` still declares exactly one
    SessionStart command, and the existing tests in
    `tests/test_plugin_manifests.py` and `tests/test_session_bootstrap.py` pass,
    changed only where they asserted the bootstrap's output was empty.
13. Every `skills/*/SKILL.md` contains the version-check instruction, naming
    the script as `<plugin>/scripts/check_versions.sh` with `<plugin>` defined
    as two folders above the `SKILL.md`; a test enforces it and fails when one
    file's instruction is removed.
14. `skills/setup/references/install.md` names the warning and what to do
    about it; `scripts/session_bootstrap.sh`'s header comment no longer says
    only a failed install prints; the `extras-report` bug skeleton asks for the
    tcw plugin version alongside `tcw --version`.
15. Capability ledger: the new capability exists with status `Supported`, and
    `cap-17ca61` no longer says the CLI "never goes stale behind the skills".
    `docs/changelogs/upcoming.md` and `docs/release-notes/upcoming.md` carry an
    entry for the warning.
16. Manual delivery check, recorded in `outcome.md` with the transcript lines:
    one Claude session (plugin from this checkout via `--plugin-dir`) and one
    Codex session, each with a mismatched stub `tcw` first on PATH, show the
    warning reaching the agent. If the Codex session does not act on the
    instruction, that is recorded as a finding, not hidden.

## Risks

- **Codex agents may skip the instruction.** Under Codex the trigger is text an
  agent is asked to act on, not something that runs by itself. Accepted under
  the warn-only decision; criterion 16 measures it once, and the hook (if Codex
  runs it, see Notes) is a second chance.
- **Repeated noise for maintainers.** A TCW developer whose checkout is ahead
  of the installed plugin sees the warning every session. It is true, and the
  remedy works; accepted.
- **Session-start cost.** One extra interpreter start (about 0.2 seconds) per
  session on the steady-state path, never more than the deadline.
- **Wrong remedy command.** A wrong command in the message would send the user
  down a dead end, so the plan must verify each one before the text is fixed.
- **Advice when PyPI lags the plugin.** Today (plugin 2.5.0, PyPI 2.4.0) a pipx
  user on updated skills would be told to upgrade to a version that does not
  exist yet. The message says so explicitly rather than implying the upgrade
  will work.
- **The deadline kills a slow but healthy CLI.** On a very slow machine the
  first `tcw --version` could exceed the limit; the cost is a missed warning
  for that session, never a false one.

## Notes

- **Assumption, not verified: recent Codex may run the plugin's SessionStart
  hook.** `~/.codex/config.toml` on this machine records a
  `hooks.state."tcw@tcw:hooks/hooks.json:session_start:0:0"` trust entry, and
  the Codex 0.155.1 binary contains the strings `CLAUDE_PLUGIN_ROOT` and
  `PLUGIN_ROOT` next to its hooks code. If so, the check reaches Codex users
  through the hook too, once they trust it. Whether Codex passes a hook's plain
  standard output to the agent (it validates session-start JSON output) is
  unknown. The design does not depend on it: the skill instruction is the Codex
  path either way.
- **To verify at plan time:** the plugin-update command for a project-scoped
  Claude install (`claude plugin update tcw@tcw`, which reports "restart
  required to apply", may need a scope option) and the Codex equivalent
  (`codex plugin marketplace upgrade` refreshes the marketplace snapshot;
  whether the installed plugin then updates, or needs `codex plugin add
  tcw@tcw` again, is unconfirmed). This machine's Codex cache has moved from
  2.4.0 to 2.5.0 during this item's life, so the update path does exist; the
  exact command is what is unconfirmed.
- Blocks v2.5.1 with the other four items filed from the proposit-app reports
  (`initial-request.md`).
