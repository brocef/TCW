# Provision the tcw plugin and CLI automatically in Claude Code remote sessions — Specification

## Capability changes

None. No capability record is added, retired, or moved, and no taxonomy term
changes. The existing `plugin/install-as-a-plugin` and `plugin/bootstrap-the-cli`
capabilities describe what a **TCW user** gets from the published plugin; this
item provisions **this repository's own contributor environment** in a Claude
Code remote container, which is development tooling rather than a shipped
capability. `cli/install-from-pypi` is untouched: nothing here changes how the
published CLI is installed for anyone.

## Problem

A Claude Code remote session that opens this repository starts with neither the
plugin nor the `tcw` CLI, and both are needed before any work can be tracked —
`CLAUDE.md` requires every change to go through `tcw work`, which is exactly the
command that is missing.

Two independent gaps produce that state:

1. **The plugin is declared but nothing can install it.** `.claude/settings.json:2-5`
   enables `tcw@tcw`, but a plugin id is `plugin@marketplace` and the repository
   declares no marketplace anywhere — the settings schema's
   `extraKnownMarketplaces` key is absent from the file. An enabled plugin whose
   marketplace is unknown cannot be resolved, so the session starts with none of
   the eight skills, ten commands, or two agents the plugin ships
   (`.claude-plugin/plugin.json:20-21`).

2. **The plugin's own CLI bootstrap deliberately declines to act here.**
   `scripts/session_bootstrap.sh` is a SessionStart hook (`hooks/hooks.json:2-9`)
   that installs `tcw-cli` from PyPI with pipx, and `scripts/session_bootstrap.sh:95`
   exits 0 when pipx is absent, on the stated ground that choosing a Python
   environment should not happen unasked at session start. A stock remote
   container has no pipx, so the hook silently no-ops — and it is silent by
   design, so nothing reports the absence either. That gate is correct for the
   published plugin on a user's machine and simply does not deliver a `tcw` here.

Even if pipx were bootstrapped, `session_bootstrap.sh:101` installs the
**published** distribution, currently 0.21.1 on PyPI against this tree's 1.0.3
(`pyproject.toml:7`, `tcw/__init__.py:1`). A contributor session would then be
running a CLI nine minor versions behind the source it is editing. What a
checkout needs is what CI provisions: `pip install -e '.[dev]'`
(`.github/workflows/test.yml:36`).

## Goals

- A Claude Code remote session opening this repository provisions, at session
  start and with no human step: the `tcw` CLI from **this checkout**, its `dev`
  extras so `pytest` runs, and the `tcw` plugin from **this checkout**.
- Provisioning is idempotent, non-interactive, and never fails a session: any
  step that cannot complete prints one line the agent can read and exits 0.
- Provisioning leaves the working tree clean — no tracked file is modified as a
  side effect of a session starting.
- The plugin's own `session_bootstrap.sh` keeps working unchanged, and the two
  mechanisms do not fight over the `tcw` on PATH in either order.
- The logic is a plain script a human or a Codex agent can run by hand; the
  Claude hook is only the thing that calls it.

## Non-goals

- Changing anything about how the **published** plugin or `tcw-cli` installs for
  users: `scripts/session_bootstrap.sh`, the `tcw-plugin` skill, `/tcw-doctor`,
  and the PyPI packaging are all out of scope.
- Provisioning the Node/pnpm toolchain (`pnpm install`, prettier, eslint,
  vitest, playwright). The request named the plugin and the Python package;
  `.github/workflows/test.yml` needs no Node either.
- Provisioning local (non-remote) sessions automatically. The script is
  runnable by hand anywhere, but session-start behavior is gated to remote.
- Bootstrapping pipx, or installing the published `tcw-cli`, in a session on
  this repository.
- Repairing a plugin copy that goes stale mid-container after the branch changes
  the plugin payload; `claude plugin update tcw@tcw` and `/tcw-doctor` already
  cover that.

## Design

### One script, called by one hook

`scripts/remote_session_setup.sh` holds all of the logic; `.claude/settings.json`
gains a `SessionStart` hook that runs it. This split is what
`docs/lifecycle/harness.md` asks for: the hook is a Claude-only convenience, and
nothing is *only* reachable through it — `scripts/remote_session_setup.sh --force`
does the same work under Codex, in a local shell, or in a session where the hook
never fired. Nothing here is a TCW requirement carried by a Claude-only
mechanism, because nothing here ships to TCW users at all.

The script mirrors the contract `scripts/session_bootstrap.sh` already
establishes for this repository's SessionStart scripts: **every path exits 0**,
and only a failure prints, on **stdout**, because SessionStart stdout is added to
the agent's context while stderr is not.

### What it does, in order

1. **Gate.** Exit 0 unless `CLAUDE_CODE_REMOTE` is `true` or `--force` was
   passed. Session start is the only automatic caller, and only remotely.
2. **Python package.** `python3 -m pip install -e ".[dev]"` from
   `$CLAUDE_PROJECT_DIR`, skipped when a guard shows the checkout is already the
   importable `tcw` and the dev extras import. The guard strips the cwd from
   `sys.path` before importing, for the reason `session_bootstrap.sh:38-46`
   documents: a session's cwd is this repository, so an unstripped path proves
   nothing about what is installed.
3. **PATH repair.** If `tcw` is still not on PATH after a successful install but
   a `tcw` exists in the user base's `bin`, append that directory to PATH via
   `$CLAUDE_ENV_FILE` when the harness provides one.
4. **Plugin.** `claude plugin marketplace add "$CLAUDE_PROJECT_DIR"` then
   `claude plugin install tcw@tcw -y`, both at the default **user** scope. Both
   commands are idempotent and report the already-done case as success.

### Why the checkout, for both halves

The marketplace source is the checkout, not `brocef/TCW`, for the same reason
the Python install is editable: a session that edits `skills/` should be running
those skills, not `main`'s. It also needs no network. The cost is that the
installed copy is a snapshot taken at install time — declared a non-goal above.

### Interaction with the plugin's own bootstrap

Both hooks fire at session start in an unspecified order, and either order is
safe. If `session_bootstrap.sh` runs first, it finds no pipx and no-ops
(`scripts/session_bootstrap.sh:95`). If it runs after, it finds a `tcw` whose
interpreter reports an **editable** install and returns before the pipx gate
(`scripts/session_bootstrap.sh:88-90`) — the developer-checkout guard it already
has, doing exactly the job it was written for.

### Scope of the sweep

A repo-wide sweep for the sibling defect — "a session-start mechanism that
silently does nothing" — found one other SessionStart script,
`scripts/session_bootstrap.sh`, whose silence is deliberate and specified
(`scripts/session_bootstrap.sh:16-18`), and no other. `.github/workflows/`
provisions explicitly and fails loudly. Nothing else in the tree installs
anything at start-up.

## Acceptance criteria

- `scripts/remote_session_setup.sh` exists, is executable, and `bash -n` parses
  it.
- With `CLAUDE_CODE_REMOTE` unset and no arguments, the script exits 0 having
  run neither `python3` nor `claude` (assertable with stub executables on PATH).
- With `CLAUDE_CODE_REMOTE=true`, the script runs `python3 -m pip install -e`
  against `$CLAUDE_PROJECT_DIR` and both `claude plugin` commands, and exits 0.
- `--force` produces that same behavior with `CLAUDE_CODE_REMOTE` unset.
- No invocation ever passes `--scope project` or `--scope local` to a `claude
  plugin` command, so no tracked file changes; `git status --porcelain` is empty
  after a run in a clean checkout.
- A failing `pip` and a missing `claude` each produce exactly one stdout line
  and exit status 0.
- When the guard reports the checkout already installed with its dev extras, the
  run performs no pip install.
- `.claude/settings.json` registers the script as a `SessionStart` hook, parses
  as JSON, and still enables `tcw@tcw`.
- `pytest tests/test_remote_session_setup.py` passes, and the existing
  `tests/test_session_bootstrap.py` still passes unchanged.
- After a real run in a remote container: `tcw --version` prints the version in
  `tcw/__init__.py`, `python3 -c "import pytest"` succeeds, and `claude plugin
  list` shows `tcw@tcw` enabled.

## Risks

- **A hook that runs on every session start is a per-session cost.** Mitigated
  by the already-installed guard and by both `claude plugin` commands returning
  early when there is nothing to do; the steady-state run is a few seconds.
- **`pip install` into a container's system interpreter.** Acceptable because
  the container is disposable and single-purpose; on an image that marks its
  interpreter externally managed the install would fail, so the script retries
  once with `--break-system-packages` before reporting failure.
- **A plugin installed at session start may not be live until the next
  session.** Plugin loading happens during start-up, so the first session that
  provisions a fresh container may see the CLI but not the skills. Remote
  container state is cached after the hook completes, so subsequent sessions
  start with it already installed. This is a latency property, not a failure,
  and the script says nothing misleading about it.
- **The checkout-sourced marketplace pins an absolute path in *user* settings**
  (`~/.claude/settings.json`), which is per-container and disposable. Nothing
  machine-specific is committed to the repository.

## Notes

- Assumption, tested only in print mode: declaring `extraKnownMarketplaces` in
  project settings does **not** by itself install an enabled plugin — a headless
  `claude -p` run in this checkout with both keys declared left
  `~/.claude/plugins/installed_plugins.json` empty. Interactive start-up may
  well install it; the design does not depend on either answer, since the script
  installs explicitly.
- Assumption, from the request rather than the code: "the Python package" means
  this checkout, not the published `tcw-cli`. The evidence in **Problem** is what
  decided it; flipping the decision is a one-line change to the script.
