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
| 5 | `pipx install --force "$root"` (91-101) | **change** to `pipx install --force tcw-cli`, and reword the failure line (99) and the file header (2) |

The whole change is one install target and two comments. Steps 1–4 are the
guards, and none of them are about *where* the package comes from.

**Floating, not pinned.** `pipx install --force tcw-cli` resolves whatever is
newest. The consequence is deliberate: **the refresh cadence is the plugin's,
not PyPI's.** Step 2 short-circuits while the sentinel matches the clone's
`tcw/__init__.py`, so a new `tcw-cli` published between plugin updates is not
picked up until the plugin's own version string changes. That is today's cadence
— the CLI refreshes when the plugin refreshes — and it keeps the steady-state
cost at one `cmp` and one `command -v`, with no per-session network call. A user
who wants the newest CLI sooner runs `pipx upgrade tcw-cli`, which now works
because the install spec is a PyPI name rather than a local path.

**What the sentinel is, precisely.** It is a *trigger token for a plugin-version
change* and nothing more. It must not be described — in the script's comments,
the docs, or the capability records — as evidence about the installed CLI:

- It compares file **contents**, not clone paths (`session_bootstrap.sh:74-75`).
  A plugin update whose `tcw/__init__.py` is byte-identical triggers nothing. In
  practice `cut_version.py` bumps `__version__` on every release, so a real
  plugin update always changes it; a cache move without a version bump does not,
  and does not need to.
- After a successful install it records the **clone's** version file
  (`session_bootstrap.sh:95-96`), never the version pipx actually resolved. Under
  a floating install those two can differ — most visibly in the release race in
  **Risks**, where the previous `tcw-cli` is installed and then marked current.

That asymmetry is accepted, not fixed here: correcting it means asking the fresh
install what version it is, which is a per-install interpreter start, and the
skew it would detect is one the user resolves with `pipx upgrade tcw-cli`. The
requirement this places on implementation is a wording one — the header comment
at `session_bootstrap.sh:2` and the comment at line 71 both currently say the
sentinel means "what we installed still matches the clone", which stops being
true and must be reworded to "the plugin has not changed since we last
installed".

**The version marker stays `tcw/__init__.py`.** Step 1 and step 2 read that file
purely as the change-detector above, not as something to install from. It is a
proven marker, present in every plugin clone today, and swapping it for
`.claude-plugin/plugin.json` would trade that for an unverified one whose failure
mode is a silent `exit 0` with no CLI installed. The coupling is cosmetic until
the repo split, which is where it should be re-decided.

**The failure line** (line 99) currently reads `automatic install from $root
failed`. `$root` is no longer the source, and the most likely cause is now
network rather than a broken clone. It becomes one line naming PyPI and pointing
at the same diagnosis route. It stays **one** line and does not attempt to
classify the failure (network vs. 404 vs. pipx internal) — that is what
`/tcw-doctor` is for, and the script is deliberately near-silent
(`session_bootstrap.sh:10-12`).

### Migration

Verified, not assumed, and reproducible without touching the developer's own
install:

```sh
export PIPX_HOME=$(mktemp -d) PIPX_BIN_DIR=$PIPX_HOME/bin
pipx install --force /path/to/TCW      # the clone install users have today
pipx install --force tcw-cli           # what the new bootstrap runs
pipx list --short                      # expect exactly: tcw-cli <version>
python3 -c "import json;print(json.load(open('$PIPX_HOME/venvs/tcw-cli/pipx_metadata.json'))['main_package']['package_or_url'])"
rm -rf $PIPX_HOME
```

Run during this stage: one venv, `tcw-cli`, and `package_or_url` flips from the
local path to `tcw-cli`. pipx names the venv from the distribution metadata,
which is `tcw-cli` for both the clone and the wheel (`pyproject.toml:6`), so the
PyPI install replaces the clone install in place.

This stays a **manual** check rather than a test. `tests/test_session_bootstrap.py`
forbids invoking real pipx by design (file header, lines 3-7); adding a real-pipx,
real-network case would break that rule and make the suite depend on PyPI. The
claim is about pipx's own venv-naming behavior, which the script does not
influence — re-running the block above at implement time is the proportionate
check.

No migration step, no duplicate, nothing for a user to clean up. An existing
plugin user's first session after the update reinstalls in place because the
plugin update moves the clone and staleness the sentinel already detects.

The pre-rename `tcw` pipx package that `doctor.md:56-62` describes is unaffected
and stays inert clutter.

### Docs and capability records

| File | What changes |
| --- | --- |
| `README.md:118-128` | The "from its _own clone_ (via pipx)" paragraph, and the `**don't also pip install tcw-cli separately**` warning — which inverts: it is now the same package, so there is nothing to drift. **State the offline regression here, in the install section** — the first session after installing or updating the plugin needs network — not only in the changelog. |
| `README.md:137` | The Codex paragraph: "it installs the `tcw` CLI from the plugin clone by running the same script Claude runs automatically." |
| `README.md:143-152` | The "As a Python package" section stops being a peer route and becomes the same route. |
| `README.md:943` | "from the plugin's own clone (pipx)" in the doctor description. |
| `commands/tcw-doctor.md` | **The fourth install site.** Its `description` frontmatter (line 2) promises "does it match the active plugin-cache version", which floating removes; the body runs the bootstrap against `<active-clone>` (line 9-11) and prescribes `pipx install --force "<active-clone>"` (line 13). Must track `doctor.md`, since the command is a thin router into it. |
| `scripts/session_bootstrap.sh:2` | The file header, "Install or refresh the `tcw` CLI from the plugin clone." |
| `skills/tcw-plugin/SKILL.md:3-8` | `description`, `when_to_use`, and `compatibility` all say "from the plugin's own clone". |
| `skills/tcw-plugin/SKILL.md:61-86` | The install/repair section body. |
| `skills/tcw-plugin/references/setup.md` | Reframed throughout. Notably: the opening "don't also `pip install tcw-cli` separately" (1-6), step 2's description of what the script does (18-25), step 4's fallback ladder — `python3 -m pip install --user "<clone-root>"` becomes `--user tcw-cli` (29-38) — and step 6's drift warning, which no longer applies (44-45). Step 1 (resolving the clone root) still stands: the script still takes it. |
| `skills/tcw-plugin/references/doctor.md` | The mental model (3-8) and steps 3-4 (33-48) — see the concrete rewrite below. Step 6 (56-62) claims the leftover pre-rename `tcw` package's "install spec is a local path" — still true of that leftover, but the surrounding contrast ("rather than from PyPI's unrelated `tcw` project") now sits next to a `tcw-cli` that *does* resolve from PyPI, so the sentence needs re-reading in the new context. |
| `docs/changelogs/upcoming.md` | Changed/Internal entries. |
| `docs/release-notes/upcoming.md` | Plain-language note: the plugin now installs the published CLI; first session after install/update needs network. |
| capability records | The three deltas in **Capability changes**. |

### What `/tcw-doctor` diagnoses instead

`doctor.md`'s repair is currently built on one comparison — installed source vs.
the active plugin-cache clone (steps 3-4, lines 33-48) — and floating deletes it.
Deleting it without a replacement would leave the doctor able to name a problem
it can no longer fix, so the replacement is specified here rather than left to
implementation:

- **Step 3 (active cache version) is dropped, not reworded.** The `sort -V` scan
  of sibling version dirs exists only to find the clone to compare against. There
  is no clone to compare against.
- **Step 4 becomes: is `tcw` present, and is it ours to touch?** The question
  changes from *does it match the clone* to *does it exist and is it a plain,
  non-editable install*. Steps 1-2 already answer the second half and are
  unchanged. Missing → run the bootstrap, then `pipx install --force tcw-cli` as
  the direct fix if it stayed silent. Present and plain → `pipx upgrade tcw-cli`
  is the refresh, and is the honest answer to a user whose CLI is behind.
- **Version skew is reported, not repaired.** The doctor already reports the
  installed version (step 7). It now reports it without claiming it should equal
  the plugin's, and names `pipx upgrade tcw-cli` as the way to move it. This is
  where the release-race skew in **Risks** becomes visible to a user.
- `commands/tcw-doctor.md` mirrors all of the above — it is a router into this
  file and its own `description` currently makes the version-match promise.

### Tests

`tests/test_session_bootstrap.py` already covers every branch with a recording
`pipx` stub and never invokes real pipx (file header, lines 3-7). **Exactly two**
assertions name the clone as the install target, and both must change:

- `tests/test_session_bootstrap.py:215` — `assert log.read_text().strip() ==
  f"install --force {root}"` → `"install --force tcw-cli"`.
- `tests/test_session_bootstrap.py:203` — `assert
  log.read_text().strip().endswith(str(root))`, in the failed-install test →
  assert it ends with `tcw-cli`.

Everything else — the steady-state, editable, unidentifiable, missing-pipx,
failed-install (its other four assertions), and probe tests — is about guards
that do not move, and must keep passing untouched. That they still pass
unmodified is itself the evidence that the change is confined to the install
target.

No new tests. The failed-install test already covers the whole
`pipx exits non-zero` path — one printed line, stale sentinel, exit 0 — and that
path does not branch on *why* pipx failed, so a network-timeout case and a
package-not-found case would exercise identical code. Likewise there is nothing
in the script that branches on CLI-vs-plugin version skew, so there is no skew
behavior to test.

### Sibling sweep

Repo-wide, the sweep is for *other* places that install `tcw` from a local path
or describe the plugin as installing from its own clone. Verified with
`grep -rn "own clone\|its own copy\|pipx install\|plugin clone\|active-clone"`
across the tree:

**Live install sites (all four must change):**

- `scripts/session_bootstrap.sh:93` — the executable one.
- `skills/tcw-plugin/references/setup.md:36` — the fallback ladder's
  `pip install --user "<clone-root>"`, an install site expressed as agent
  instructions.
- `skills/tcw-plugin/references/doctor.md:46` — `pipx install --force
  "<active-clone>"` as the direct fix.
- `commands/tcw-doctor.md:13` — the same fix, restated in the slash command.

**Live prose describing the old model:** `README.md:121,137,943`;
`skills/tcw-plugin/SKILL.md:3,4,8,77`; `setup.md:1,3,19`;
`scripts/session_bootstrap.sh:2`; the three capability records. All are in the
table above.

**Deliberately not touched:** `docs/changelogs/v*.md`, `docs/release-notes/v*.md`,
`docs/plan/phase-1-scaffold.md`, and completed `docs/work/` items describe what
was true when written — they are the archive, and rewriting them would be
falsifying it. `.github/workflows/` installs the repo to test and build it, which
is correct and out of scope. `tests/test_session_bootstrap.py`'s use of "clone"
in fixture docstrings (32, 171) still describes what those fixtures are.

## Acceptance criteria

1. `scripts/session_bootstrap.sh` contains no `pipx install` whose target is
   `$root` or any path; the only install invocation is `pipx install --force
   tcw-cli`.
2. `tests/test_session_bootstrap.py` passes with exactly **two** assertions
   changed — the expected pipx argv at line 215 and the `endswith(str(root))` at
   line 203. Every other assertion in the file, and every other test file, passes
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
7. `grep -rn 'own clone\|its own copy\|plugin clone\|clone-root\|active-clone' README.md
   commands/ skills/ scripts/` returns nothing that describes where the CLI is
   installed from or prescribes installing it. (The narrower `own clone` pattern
   alone would pass while `README.md:137`, `SKILL.md:77`, `setup.md:1`, and
   `session_bootstrap.sh:2` still say "from the plugin clone".)
8. `skills/tcw-plugin/references/setup.md`, `doctor.md`, and
   `commands/tcw-doctor.md` prescribe `tcw-cli` — not a clone path — everywhere
   they tell the agent to install, force-install, or upgrade.
9. `commands/tcw-doctor.md`'s `description` frontmatter no longer promises that
   `tcw` "match[es] the active plugin-cache version", and `doctor.md` no longer
   contains the `sort -V` active-cache-version scan.
10. All three declared capability deltas land:
    `tcw capabilities show plugin/bootstrap-the-cli` describes a PyPI install and
    names the no-network case; `cli/install-from-pypi` no longer says the plugin
    manages a separate copy; `plugin/diagnose-the-install` no longer says the
    doctor checks whether `tcw` matches the active plugin version.
11. `README.md`'s install section states, in the section itself, that the first
    session after installing or updating the plugin needs network — not only in
    the changelog.
12. The manual migration block in **Design → Migration** is re-run at implement
    time and reported in `outcome.md`: one venv, `package_or_url == "tcw-cli"`.
13. The full suite passes (`pytest`), including `test_plugin_manifests.py` and
    `test_documented_cli_surface.py`.
14. `docs/changelogs/upcoming.md` and `docs/release-notes/upcoming.md` each carry
    an entry **about this change** — naming the PyPI install source and the
    offline regression — not merely a non-empty entry.

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

**Doctor's reconcile loses its comparison.** `doctor.md` steps 3-4 are built on
"installed source ≠ active cache clone", which is the whole shape of its repair.
Under a floating PyPI install there is no such equality to test, and the risk is
a rewrite that leaves the doctor able to describe a problem it can no longer fix.
Mitigated by specifying the replacement in **Design → What `/tcw-doctor`
diagnoses instead** rather than deferring it to implementation.

**Docs drift is the largest surface here, and it is bigger than it looks.** The
code change is ~4 lines; four *live install sites* and roughly a dozen prose
locations across six files, plus three capability records, describe the old
behavior. The first draft of this spec missed `commands/tcw-doctor.md` — a whole
install site — and four "plugin clone" phrasings; both reviews caught it. The
acceptance criteria carry explicit grep patterns because a missed paragraph is
the likely failure here, not a broken script.

**Supply-chain surface.** Installing from PyPI at session start means a
compromised or hijacked `tcw-cli` release reaches every plugin user
automatically, where previously the code came from the already-trusted plugin
clone. Judged acceptable and out of scope to harden here: the blocking item
already publishes via GitHub Actions trusted publishing with no long-lived API
token (`README.md:1011`), and the plugin clone itself arrives over the same
trust-on-first-use path from GitHub. Flagged rather than solved.

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
- This spec was reviewed by `codex exec` and `bllm-review` after its first
  commit. **Accepted:** the second clone-target assertion at
  `test_session_bootstrap.py:203` (criterion 2 as first written would have failed
  a correct implementation); the missed `commands/tcw-doctor.md` install site;
  the too-narrow grep in criterion 7; the overclaiming sentinel wording; the
  missing acceptance criterion for the third capability delta; the vacuous
  changelog criterion; the undefined doctor replacement; stating the offline
  regression in `README.md` rather than only the changelog; the 216→215
  off-by-one. **Rejected, with reasons now recorded above:** adding real-pipx
  migration tests (violates the suite's no-real-pipx rule, adds a network
  dependency — kept as a manual check); classifying pipx failure modes in the
  printed line (the script is deliberately near-silent; the doctor diagnoses);
  separate tests for network vs. package-not-found and for version skew (neither
  is a branch in the script); a `pipx upgrade`-instead-of-`--force` migration
  path (`--force` is already today's behavior and nothing lives in that venv).
  **Narrowed:** the supply-chain concern became a Risks entry rather than
  in-scope hardening; "log the resolved version on a race" became a doctor
  reporting requirement rather than session-start output.
