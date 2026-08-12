# Spec — Install the plugin's CLI from PyPI instead of its own clone

## Capability changes

Planned ledger deltas only; no records are written at this stage.

| Capability | Delta |
| --- | --- |
| `plugin/bootstrap-the-cli` (`cap-17ca61`) | **Reword.** "installs it from its own clone via pipx" → installs `tcw-cli` from PyPI. Add the new skip: no network / PyPI unreachable is now a case the automatic path cannot finish, and it prints. Status stays `Supported`. |
| `cli/install-from-pypi` (`cap-f118a5`) | **Reword.** The closing caveat — "if I use the plugin, it manages its own copy and I should not install this one as well" — becomes false: both routes now install the same distribution from the same source, into the same pipx venv. Replace it with the convergence. Status stays `Supported`. |
| `plugin/diagnose-the-install` (`cap-5d5b7a`) | **Reword.** "whether it matches the active plugin version" no longer holds under a floating install; the leftover-package sentence keeps its meaning. Status stays `Supported`. |

No new capabilities, no removals. No taxonomy delta — the `cli` Subject these
three already point at is unchanged, and this introduces no new term or Feature.

## Problem

`scripts/session_bootstrap.sh:93` runs `pipx install --force "$root"`, where
`$root` is the plugin's own cached clone. The plugin therefore has to *be* the
Python repo, and the CLI a user gets from the plugin is a locally-built copy that
never touches PyPI — even though `2026-08-11-publish-tcw-to-pypi-with-automated-releases`
now publishes `tcw-cli` there (0.20.1 is live; the release workflow is
`.github/workflows/release.yml`).

Three consequences:

1. **Two install routes produce two different artifacts.** A plugin user's `tcw`
   is built from a clone; a `pipx install tcw-cli` user's is the published wheel.
   They can differ, and `README.md:123-125` has to warn users away from doing
   both.
2. **The published artifact is not the one users exercise.** Nothing in the
   plugin path would catch a broken sdist, a missing `package-data` entry, or a
   release that failed to upload — the plugin never installs it.
3. **The plugin cannot shed its Python.** As long as the bootstrap installs from
   the clone, the AI-agent packaging and the Python source are welded together.
   Separating them (the request's ask #2) cannot start until the install source
   moves.

## Goals

- `session_bootstrap.sh` installs `tcw-cli` from PyPI, and only from PyPI.
- The CLI floats to the latest published `tcw-cli` rather than pinning to the
  plugin's version string.
- Existing plugin users migrate with no duplicate package and no manual step.
- Every guard the script has today survives: editable checkouts untouched,
  unidentifiable installs untouched, missing `pipx` silent, one printed line on
  failure, exit 0 on every path.
- Codex and Claude both keep working, through the same script.
- The docs and the three capability records stop describing a clone install.

## Non-goals

- **The repo split (ask #2).** The plugin keeps shipping the Python source; it
  just stops installing from it. Splitting the packaging into a second repo or a
  second manifest is a separate item, filed at closeout.
- **Any offline or air-gapped fallback.** Explicitly rejected by the requester
  during spec: PyPI is the only source. A session with no network and no prior
  install gets no `tcw`, and prints why. See Risks.
- **Publishing or CI** — the blocking item shipped that.
- **Version pinning between the plugin and the CLI.** Rejected in favor of
  floating; see Design.
- **Changing the hook wiring** (`hooks/hooks.json`) or the Codex entry point
  (the `tcw-plugin` skill running the same script).

## Design

### The script

Today's flow, with the changed steps marked:

| Step | `session_bootstrap.sh` | Change |
| --- | --- | --- |
| 1 | `[ -f "$root/tcw/__init__.py" ]` or exit (line 68-69) | **keep** — see "the version marker" below |
| 2 | sentinel `cmp` + `command -v tcw` → exit (71-78) | **keep** |
| 3 | provenance + editable guard → exit (80-85) | **keep, unchanged** |
| 4 | `command -v pipx` or exit (87-89) | **keep** |
| 5 | `pipx install --force "$root"` (91-101) | **change** to `pipx install --force tcw-cli`, and reword the failure line |

The whole change is one install target and one message. Steps 1–4 are the
guards, and none of them are about *where* the package comes from.

**Floating, not pinned.** `pipx install --force tcw-cli` resolves whatever is
newest. The consequence is deliberate and worth stating plainly: **the refresh
cadence is the plugin's, not PyPI's.** Step 2 short-circuits while the sentinel
matches the clone, so a new `tcw-cli` published between plugin updates is not
picked up until the next plugin update moves the clone. That is exactly today's
cadence — the CLI refreshes when the plugin refreshes — and it keeps the
steady-state cost at one `cmp` and one `command -v`, with no per-session network
call. A user who wants the newest CLI sooner runs `pipx upgrade tcw-cli`, which
now works because the install spec is a PyPI name rather than a local path.

**The version marker stays `tcw/__init__.py`.** Step 1 and step 2 read that file
purely as a change-detector for "the plugin moved", not as something to install
from. It is a proven marker, present in every plugin clone today, and swapping it
for `.claude-plugin/plugin.json` would trade that for an unverified one whose
failure mode is a silent `exit 0` with no CLI installed. The coupling is
cosmetic until the repo split, which is where it should be re-decided.

**The failure line** (line 99) currently reads `automatic install from $root
failed`. `$root` is no longer the source, and the most likely cause is now
network rather than a broken clone. It becomes one line naming PyPI and pointing
at the same diagnosis route.

### Migration

Verified, not assumed. In an isolated `PIPX_HOME`: `pipx install --force <local
clone>` then `pipx install --force tcw-cli` leaves **one** venv, `tcw-cli`, with
`pipx_metadata.json` → `main_package.package_or_url == "tcw-cli"`. pipx names the
venv from the distribution metadata, which is `tcw-cli` either way
(`pyproject.toml:6`), so the PyPI install replaces the clone install in place.

No migration step, no duplicate, nothing for a user to clean up. An existing
plugin user's first session after the update reinstalls in place because the
plugin update moves the clone and staleness the sentinel already detects.

The pre-rename `tcw` pipx package that `doctor.md:56-62` describes is unaffected
and stays inert clutter.

### Docs and capability records

| File | What changes |
| --- | --- |
| `README.md:118-128` | The "from its _own clone_ (via pipx)" paragraph, and the `**don't also pip install tcw-cli separately**` warning — which inverts: it is now the same package, so there is nothing to drift. Say a session needs network the first time and after a plugin update. |
| `README.md:143-152` | The "As a Python package" section stops being a peer route and becomes the same route. |
| `README.md:943` | "from the plugin's own clone (pipx)" in the doctor description. |
| `skills/tcw-plugin/SKILL.md:3-8` | `description`, `when_to_use`, and `compatibility` all say "from the plugin's own clone". |
| `skills/tcw-plugin/SKILL.md:61-86` | The install/repair section body. |
| `skills/tcw-plugin/references/setup.md` | Reframed throughout. Notably: the opening "don't also `pip install tcw-cli` separately" (1-6), step 2's description of what the script does (18-25), step 4's fallback ladder — `python3 -m pip install --user "<clone-root>"` becomes `--user tcw-cli` (29-38) — and step 6's drift warning, which no longer applies (44-45). Step 1 (resolving the clone root) still stands: the script still takes it. |
| `skills/tcw-plugin/references/doctor.md` | The mental model (3-8) — pipx no longer builds from the cache dir. Step 4's reconcile (33-48) rests on "installed source ≠ active cache clone", which under a floating PyPI install is no longer the question; the reconcile becomes "is `tcw` present and not ours-to-leave-alone". Step 6 (56-62) claims the leftover `tcw` package's "install spec is a local path" — still true of the leftover, but the surrounding contrast changes. |
| `docs/changelogs/upcoming.md` | Changed/Internal entries. |
| `docs/release-notes/upcoming.md` | Plain-language note: the plugin now installs the published CLI; first session after install/update needs network. |
| capability records | The three deltas in **Capability changes**. |

### Tests

`tests/test_session_bootstrap.py` already covers every branch with a recording
`pipx` stub and never invokes real pipx (file header, lines 4-7). One assertion
is source-specific:

- `tests/test_session_bootstrap.py:216` — `assert log.read_text().strip() ==
  f"install --force {root}"` → `"install --force tcw-cli"`.

Everything else — the steady-state, editable, unidentifiable, missing-pipx,
failed-install, and probe tests — is about guards that do not move, and must
keep passing untouched. That they still pass unmodified is itself the evidence
that the change is confined to the install target.

### Sibling sweep

Repo-wide, the sweep is for *other* places that install or describe installing
`tcw` from a local path:

- `scripts/session_bootstrap.sh:93` — the one install site.
- `skills/tcw-plugin/references/setup.md:36` — the documented fallback ladder,
  a second install site expressed as agent instructions.
- `skills/tcw-plugin/references/doctor.md:46` — `pipx install --force
  "<active-clone>"` as the direct fix, a third.

All three are in the table above. No other file in the repo runs or prescribes a
`pipx`/`pip` install of TCW (`.github/workflows/` installs the repo for testing
and building, which is correct and out of scope).

## Acceptance criteria

1. `scripts/session_bootstrap.sh` contains no `pipx install` whose target is
   `$root` or any path; the only install invocation is `pipx install --force
   tcw-cli`.
2. `tests/test_session_bootstrap.py` passes with exactly one assertion changed
   (line 216's expected pipx argv). Every other test in the file passes
   unmodified.
3. A run with a stub `pipx` and a stale sentinel records `install --force
   tcw-cli` and writes the sentinel from the clone's `tcw/__init__.py`.
4. A run against a real editable checkout still records no pipx invocation and
   writes no sentinel (`test_real_editable_checkout_is_left_alone`).
5. A run whose stub `pipx` exits non-zero prints exactly one line, that line
   names PyPI rather than `$root`, the sentinel is left stale, and the exit code
   is 0.
6. Steady state (sentinel matches, `tcw` on PATH) still invokes no pipx and
   prints nothing.
7. A `grep -rn 'own clone\|its own copy'` over `README.md` and
   `skills/tcw-plugin/` returns nothing describing where the CLI is installed
   from.
8. `skills/tcw-plugin/references/setup.md` and `doctor.md` prescribe
   `tcw-cli` — not a clone path — everywhere they tell the agent to install or
   force-install.
9. `tcw capabilities show plugin/bootstrap-the-cli` describes a PyPI install and
   names the no-network case; `cli/install-from-pypi` no longer says the plugin
   manages a separate copy.
10. The full suite passes (`pytest`), including `test_plugin_manifests.py` and
    `test_documented_cli_surface.py`.
11. `docs/changelogs/upcoming.md` and `docs/release-notes/upcoming.md` both carry
    an entry.

## Risks

**No network means no CLI.** Accepted by the requester, explicitly, over a
fallback. Session start becomes dependent on PyPI's availability for anyone
without an existing install: a fresh plugin install offline, or a plugin update
offline where the sentinel has gone stale. The failure is not silent — step 5
prints a line pointing at `/tcw-doctor` — but a machine that used to work
offline will not. `setup.md`'s manual ladder is the escape hatch and also
requires network.

**A plugin release can outrun its own PyPI release.** A user updating to plugin
`X` before the release workflow finishes uploading `tcw-cli X` installs the
previous version instead, silently, and the sentinel then records it as current
until the next plugin update. Floating chose this over the pinned alternative
(which would fail loudly instead). Mitigation is procedural: the release workflow
tags and publishes from the same commit, so the window is minutes.

**Skill/CLI version skew.** Floating means the skills in plugin `X` may drive a
`tcw-cli` newer than `X` if a user runs `pipx upgrade tcw-cli`. TCW's CLI surface
is additive in practice, but nothing enforces that. Low, and the alternative
(pinning) was rejected.

**Doctor's reconcile loses its comparison.** `doctor.md` step 4 currently
diagnoses "installed source ≠ active cache clone", which is the whole shape of
its repair. Under a floating PyPI install there is no such equality to test, and
the risk is that the rewrite leaves the doctor able to describe a problem it can
no longer fix. The rewrite has to give it a concrete new action
(`pipx install --force tcw-cli` / `pipx upgrade tcw-cli`), not just delete the
old one.

**Docs drift is the largest surface here.** The code change is ~4 lines; nine
documentation locations across four files, plus three capability records,
describe the old behavior in prose. The acceptance criteria include greps
precisely because a missed paragraph is the likely failure, not a broken script.

## Notes

- Scope and version policy were decided with the requester during this stage:
  ask #1 only (no repo split), PyPI as the sole source (no clone fallback,
  overriding the initially-suggested fallback), and float-to-latest rather than
  pinning. The request's four open questions are answered by that plus the
  Design section: offline is not supported, the repo is not split, the version
  floats, and the doctor diagnoses a PyPI install.
- The pipx migration behavior in **Design → Migration** was verified against real
  pipx in a throwaway `PIPX_HOME`, not recalled.
- `tcw-cli` on PyPI is at 0.20.1, matching the repo — checked against the PyPI
  JSON API during this stage.
