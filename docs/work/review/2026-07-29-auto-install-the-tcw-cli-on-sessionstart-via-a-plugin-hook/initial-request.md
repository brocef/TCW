# Auto-install the tcw CLI on SessionStart via a plugin hook

## Product changes

Installing and repairing the `tcw` CLI stops being something the user has to
ask for. Today a user runs `/tcw-init` after installing the plugin, and runs
`/tcw-doctor` whenever a plugin update leaves the pipx install pointing at an
abandoned version directory. Both are manual, and the stale case is invisible
until something fails — the user finds out that `tcw` is behind by hitting a
command that no longer behaves as the skills describe.

The request: make the install happen on its own, at session start, for both the
first install and the after-an-update reconcile. `/tcw-init` is to be **retired
and deleted** — with the hook doing the initial install there is nothing left
for it to do. `/tcw-doctor` stays, as the manual escape hatch for the cases the
hook deliberately does not touch.

This rewrites the existing capability `plugin/bootstrap-the-cli`, whose current
description is written entirely around the user invoking `/tcw-init`.

## Technical changes

Requested approach: a `SessionStart` hook in the plugin, per the [plugins
reference](https://code.claude.com/docs/en/plugins-reference.md). Two documented
environment variables make this viable, and their properties are what the design
rests on:

- `${CLAUDE_PLUGIN_ROOT}` — the plugin's install directory. It *changes on every
  plugin update*, which is precisely the drift `/tcw-doctor` exists to repair,
  and it is also the pipx source the install needs.
- `${CLAUDE_PLUGIN_DATA}` — a directory that *survives* plugin updates. It gives
  the hook somewhere to stash a sentinel copy of the plugin's version file, so
  "has the plugin changed under us?" is a `diff`, not a version-string parse.

The reconcile therefore fires when `tcw` is absent **or** the sentinel differs
from the bundled version file, and the sentinel is written only after a
successful install so a failure retries next session.

The logic is to live in **one script in the repo**, not inline in the hook JSON.
That is a harness-compatibility requirement, not a style preference: a Codex user
gets no hooks, so if the logic lives in the hook it is a Claude-only guarantee.
With it in a script, `skills/tcw-plugin/references/setup.md` and `doctor.md`
collapse to "run this script", a Codex agent runs the same code by instruction,
and Claude simply gets it fired automatically. One implementation, two harnesses.

Three behaviors the hook must get right, all confirmed against a real machine
during this discussion:

1. **Never disturb an editable dev install.** This repo's own checkout resolves
   `tcw` to a pyenv shim from `pip install -e .`. `doctor.md` step 2 already says
   to leave those alone; a hook that force-installs over one would break the
   maintainer's setup on every session in this very repo.
2. **Tolerate a missing pipx.** `pipx` is not on PATH in every shell (it was not
   in the shell used here). The hook must exit quietly rather than print an error
   at every session start, in every project.
3. **Surface real failures, stay silent otherwise.** Skips — editable install,
   no pipx, nothing to do — say nothing. A pipx run that actually fails prints one
   line, which `SessionStart` injects as context so the agent can surface it and
   point at `/tcw-doctor`.

## Meta changes

Deleting `/tcw-init` reaches further than the command file. Known referencing
surfaces: `README.md` (the install snippet and the command inventory),
`skills/tcw-plugin/SKILL.md`, and the `plugin/bootstrap-the-cli` capability.
Historical changelogs and release notes mentioning it are archive and must not be
rewritten.

The README install sequence changes shape: today it ends with a command the user
runs; afterwards the plugin install is followed by a session restart, because a
hook installed mid-session does not fire until the next session begins.

## Notes

**Constraints**

- The hook must be cheap in the steady state. It runs at the start of every
  session in every project, not only in TCW ones.
- `tcw` must stay a bare command on PATH — every skill under both harnesses calls
  `tcw …` directly. This rules out installing into a `${CLAUDE_PLUGIN_DATA}` venv
  even though that directory is otherwise a natural fit; the pipx-global install
  stays.

**Out of scope**

- The hook is not `/tcw-doctor`. Shadowed installs, a stray separate
  `pip install tcw`, and Node/`tcw serve` diagnosis stay with the doctor
  procedure. Do not let the hook grow into it.
- No change to how `tcw` itself is packaged or published.

**Assumptions to confirm at spec**

- That a `hooks/hooks.json` is auto-discovered from the plugin root with no
  `plugin.json` change — the reference lists it as a component location, but this
  plugin ships no hooks today, so it is unverified here.
- That deleting a command file is a clean removal for existing installs, rather
  than something that leaves a stale `/tcw-init` behind until reinstall.
