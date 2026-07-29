# Spec — Auto-install the tcw CLI on SessionStart via a plugin hook

## Capability changes

**Changed:** `plugin/bootstrap-the-cli` (`cap-17ca61`, currently `Supported`).

Its description is written entirely around the manual command
(`docs/capabilities/plugin/bootstrap-the-cli/description.md:1`: "As a user, I run
`/tcw-init` …"). After this item the user runs nothing: the CLI installs itself
at session start and re-installs itself when a plugin update moves the clone.
Recorded in this item's `capabilities.yaml` as `changed:`; the body is rewritten
at `complete`. Status stays `Supported` throughout — the capability exists both
before and after, only its mechanism changes.

Checked against the standing ledger for contradictions
(`tcw capabilities check` → `capabilities OK`):

- `plugin/diagnose-the-install` (`cap-5d5b7a`) — **unchanged.** `/tcw-doctor`
  remains the user-invoked diagnosis, and its user-facing promise is untouched.
  Only the reference document behind it changes.
- `plugin/install-as-a-plugin` (`cap-c830d4`) — **unchanged.** Its text names the
  marketplace/install commands only and never mentions `/tcw-init`, so it stays
  true. (The README's install *snippet* does change; the capability does not.)

No taxonomy delta: `Subject: cli` is already registered and no new Vocabulary or
Feature entry is introduced.

## Problem

Two manual steps stand between having the plugin and having a working `tcw`:

1. **First install.** `/tcw-init` (`commands/tcw-init.md`) routes the agent to
   `skills/tcw-plugin/references/setup.md`, which resolves the clone root and
   `pipx install`s it. Nothing runs it automatically, so a user who installs the
   plugin and starts working hits missing-`tcw` errors first.
2. **After every plugin update.** `${CLAUDE_PLUGIN_ROOT}` changes on each update,
   but the pipx venv still points at the abandoned version directory.
   `references/doctor.md:3-5` states this plainly — pipx builds from the cache
   dir and *"'No drift' is what this procedure enforces — it is not automatic."*
   The user only discovers the drift when a command misbehaves.

Both are mechanical reconciles that a machine can do, gated behind a human
remembering to ask.

## Goals

1. A `SessionStart` plugin hook installs `tcw` when absent and re-installs it when
   the plugin version under `${CLAUDE_PLUGIN_ROOT}` no longer matches what was
   installed.
2. The reconcile logic lives in **one executable script in the repo**, invoked
   both by the hook (Claude, automatically) and by the `tcw-plugin` skill
   (Codex, by instruction) — so the guarantee does not live in a Claude-only layer.
3. `/tcw-init` is deleted, along with its references in `README.md` and
   `skills/tcw-plugin/SKILL.md`.
4. In the steady state the hook costs one `diff` and adds nothing to context.

## Non-goals

- **The hook is not `/tcw-doctor`.** Shadowed installs, a stray separate
  `pip install tcw`, `sort -V` cache-version scanning, and Node/`tcw serve`
  diagnosis all stay in `references/doctor.md`. The hook handles absent-or-stale
  and nothing else.
- **No pipx bootstrap ladder in the script.** `references/setup.md:12-19` offers a
  fallback ladder when pipx is missing (`pip install --user pipx`, `pip --user`,
  a dedicated venv). Choosing among those is a judgment call about someone's
  Python environment and must not happen silently inside a session-start hook.
  The script skips silently; the ladder stays as agent prose.
  *(Corrected at `implement`: this originally read "reports 'pipx missing' and
  stops", contradicting the silent-skip rule this same spec sets out under
  Design — a status line on every session in every project is exactly the context
  tax the design argues against. Silence won. `references/setup.md` carries the
  compensating flow: run the script, verify `tcw --version`, and only if it is
  still missing check `command -v pipx` yourself and take the ladder.)*
- **The hook cannot replace `/tcw-doctor`'s repair.** *(Added at `implement`.)*
  The script skips when its sentinel matches and `tcw` is on PATH — but doctor
  exists for cases where both can hold while the install is still wrong (a
  shadowed install; a re-clone of the same version at a new path). Collapsing
  `doctor.md` to a bare "run the script" would make `/tcw-doctor` silently no-op
  on exactly those. Its step 4 re-checks `tcw`'s source afterwards and falls back
  to a direct `pipx install --force`.
- No change to how `tcw` is packaged, built, or published.
- Historical `docs/changelogs/v0.2.0.md`, `docs/changelogs/v0.9.0.md`, and
  `docs/release-notes/v0.2.0.md` mention `/tcw-init` as archive and are not edited.

## Design

### Install target stays pipx-global

`${CLAUDE_PLUGIN_DATA}` is the documented home for plugin-installed dependencies
and survives updates, which makes it superficially the right place for a venv.
It is rejected: every skill under both harnesses calls `tcw …` as a bare command
(`skills/tcw-work/SKILL.md:14`, `allowed-tools: Bash(tcw *)` in each skill's
frontmatter), so `tcw` must be on the user's PATH. pipx-global stays; the data
directory is used only for the sentinel.

### The sentinel

`${CLAUDE_PLUGIN_DATA}/installed-version` is a copy of the plugin clone's
`tcw/__init__.py`, written **only after a successful install**. Comparing files
rather than parsing `tcw --version` means:

- missing sentinel ⇒ never installed, or the last attempt failed ⇒ act;
- differing sentinel ⇒ a plugin update changed the clone ⇒ act;
- a failed install leaves the sentinel stale, so the next session retries
  automatically with no state to clean up.

`tcw/__init__.py` is the right file to watch because `__version__` is one of the
five strings a release bumps in lockstep (guarded by
`tests/test_plugin_manifests.py:33`), so it changes on every released update.

### `scripts/session_bootstrap.sh`

Takes the clone root as `$1`, defaulting to `${CLAUDE_PLUGIN_ROOT}`, and the
sentinel path as `$2`, defaulting to `${CLAUDE_PLUGIN_DATA}/installed-version`.
Explicit arguments are what let the `tcw-plugin` skill run it under Codex, where
neither variable is set. Order of checks, each exiting 0 and silently unless
noted:

1. **No clone root resolvable** → exit. (Nothing to install from.)
2. **Sentinel matches and `tcw` is on PATH** → exit. The steady-state path: one
   `command -v` and one `cmp`, no interpreter start.
   *(Corrected at `implement`: this was ordered after the editable check, which
   contradicted the Risks section's "no Python starts" promise — the editable
   probe runs `python3`. A dev checkout never has a matching sentinel, so moving
   it first changes cost, not semantics.)*
3. **Editable dev install detected** → exit. This is the guard
   `references/doctor.md:11-14` already mandates ("if `dir_info.editable == true`
   … report and don't touch it"), and it is not hypothetical: this repo's own
   checkout resolves `tcw` to a pyenv shim from `pip install -e .`, so without
   this guard the hook would force-install over the maintainer's dev setup on
   every session in this very repo.
   *(Corrected at `implement`: the probe must strip `""`/`"."`/cwd from
   `sys.path` before reading distribution metadata. A hook runs with the project
   as cwd, and a `tcw.egg-info` in a TCW checkout is found first and has no
   `direct_url.json` — so the guard as originally specified answered "not
   editable" here and would have force-installed over the dev setup.)*
   *(Corrected at `implement`, second pass: the probe must also run the
   interpreter named in the shebang of the `tcw` on PATH, not the `python3` on
   PATH. For a `pipx install -e` or an editable install into a venv those are
   different interpreters, and the PATH one raises `PackageNotFoundError` — read
   as "not editable", which force-installs over the checkout. The guard is
   therefore stated as its inverse: **only replace a `tcw` whose own interpreter
   reports a plain, non-editable install.** An install whose owner cannot be
   identified — a version manager's shim, whose shebang names `bash` — is left
   alone. That is why the original guard passed on this machine: `tcw` and
   `python3` are both pyenv shims backed by the same interpreter, a coincidence
   the probe never earned.)*
4. **`pipx` absent** → exit (see Non-goals).
5. Otherwise `pipx install --force "<clone-root>"`. On success, copy
   `tcw/__init__.py` to the sentinel and exit silently. On failure, leave the
   sentinel untouched and print one line naming the failure and `/tcw-doctor`.

### Why failures print to stdout and exit 0

Confirmed against the hooks reference: for `SessionStart`, stdout is *"added as
context that Claude can see and act on"*, whereas an exit-2 stderr *"renders in
the transcript as a hook error notice … Claude doesn't see it"*. So a failure
that should reach the agent must go to **stdout with exit 0** — the intuitive
`exit 2` would produce a notice the agent cannot act on. Every skip stays silent
precisely because stdout is context: a status line on every session, in every
project, would be a permanent context tax for no information.

`SessionStart` cannot block startup and its default command timeout is 600s, so a
slow first install delays nothing and cannot wedge a session.

### Wiring

`hooks/hooks.json` at the plugin root, shell form, quoting per the reference:

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [ { "type": "command", "command": "\"${CLAUDE_PLUGIN_ROOT}\"/scripts/session_bootstrap.sh" } ] }
    ]
  }
}
```

`.claude-plugin/plugin.json` gains `"hooks": "./hooks/hooks.json"`. The root
location is auto-discovered, but that manifest already lists `skills` and
`commands` explicitly, so an explicit key matches the file's convention and
removes the assumption flagged in the request.

### Documentation collapse

`references/setup.md` and `references/doctor.md` both become "run
`scripts/session_bootstrap.sh <clone-root>`", keeping only the judgment the
script deliberately does not encode — setup keeps the pipx ladder for the
"pipx missing" report; doctor keeps install-kind classification, the `sort -V`
cache scan, and Node diagnosis. This is what makes the behavior identical under
both harnesses rather than a Claude-only bonus.

## Acceptance criteria

1. `hooks/hooks.json` exists at the plugin root, registers exactly one
   `SessionStart` command hook, and plugin-manifest validation passes.
   *(Corrected at `implement`: `claude plugin validate .` was not runnable as
   written — with a `.claude-plugin/marketplace.json` present, the CLI validates
   the **marketplace** manifest and never looks at `plugin.json`. Exercising the
   `hooks` key requires an isolated plugin dir with no marketplace manifest.
   Verified there: passes, including `--strict`, and a deliberately bad path
   errors with `hooks[0]: Path not found`, so the key is recognized rather than
   silently tolerated.)*
2. `.claude-plugin/plugin.json` contains `"hooks": "./hooks/hooks.json"`.
3. `scripts/session_bootstrap.sh` is executable (mode 755, committed as such).
4. Run against a clone root whose `tcw/__init__.py` matches the sentinel, with
   `tcw` on PATH: exits 0, produces no output, and does not invoke pipx.
5. Run when the resolved `tcw` is an editable install: exits 0, produces no
   output, and does not invoke pipx — verifiable in this repo's own checkout.
6. Run with a sentinel that differs from the clone's `tcw/__init__.py`, in an
   environment where pipx is absent: exits 0, produces no output, and does not
   modify the sentinel.
7. After a simulated failing `pipx install`, the script exits 0, prints exactly
   one line naming `/tcw-doctor`, and the sentinel is unchanged (so the next run
   retries).
8. After a successful install, the sentinel is byte-identical to the clone's
   `tcw/__init__.py`, and an immediately following run takes the silent
   steady-state path.
9. `commands/tcw-init.md` is deleted, and `grep -rn "tcw-init"` over `README.md`,
   `skills/`, and `commands/` returns nothing.
   *(Corrected at `implement`: this originally included `docs/capabilities/` in
   the same grep, which contradicted this spec's own Capability changes section
   and plan Task 9 — both defer the `bootstrap-the-cli` description rewrite to
   `complete`. The capability body still names `/tcw-init` at review by design;
   criterion 11 is what covers it, at the stage that owns it.)*
10. `README.md`'s Claude install snippet no longer shows `/tcw-init` and states
    that the hook installs the CLI at the next session start; the Codex paragraph
    (`README.md:127-128`) names the `tcw-plugin` skill without referring to
    `/tcw-init`; the command inventory (`README.md:108`) drops it.
11. `docs/capabilities/plugin/bootstrap-the-cli/description.md` describes the
    automatic install, mentions no `/tcw-init`, and `tcw capabilities check`
    passes with the capability still `Supported`.
12. A test in `tests/test_plugin_manifests.py` asserts `hooks/hooks.json` parses,
    that the `hooks` key in `.claude-plugin/plugin.json` points at an existing
    file, and that the referenced hook command script exists and is executable.
13. The full suite passes.

## Risks

- **The hook force-installs over a dev checkout.** Highest-impact failure mode,
  and it would land on the maintainer first. Criterion 5 covers it directly, and
  the editable check is ordered before every other action for that reason.
- **Deleting a command may not propagate cleanly to existing installs.** A stale
  `/tcw-init` could linger in an installed plugin until reinstall. It would route
  to `references/setup.md`, which by then says "run the script" — so the worst
  case is a redundant but correct action, not a broken one. Confirm during
  implementation; if it lingers, note it in the release notes.
- **Sentinel and reality can diverge.** The sentinel records what the *script*
  installed. If the user later `pipx uninstall`s or shadows `tcw`, the sentinel
  still matches and the script skips — which is why the steady-state check also
  requires `tcw` on PATH (criterion 4), and why `/tcw-doctor` survives.
- **Every-session, every-project cost.** Mitigated to one `command -v` plus one
  `cmp` on the hot path; no Python starts, no pipx invocation.

## Notes

Grounded against the [plugins
reference](https://code.claude.com/docs/en/plugins-reference.md) and the [hooks
reference](https://code.claude.com/docs/en/hooks.md), both read during this stage:
`${CLAUDE_PLUGIN_ROOT}`/`${CLAUDE_PLUGIN_DATA}` semantics, the manifest-diff
pattern this design follows, `hooks/hooks.json` as a component location, and the
`SessionStart` stdout-as-context and exit-code behavior.

Assumption not verified here: that `claude plugin validate` accepts a `hooks` key
pointing at a file path (the reference's example manifest shows
`"hooks": "./config/hooks.json"`, so it is documented, but this plugin has never
shipped one). Criterion 1 forces it to be checked at implementation.
