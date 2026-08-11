# Spec: make the TCW marketplace syncable from the claude.ai web app

> Revised after adversarial review by `codex exec` and `bllm-review`. The
> review log and what was accepted, narrowed, or rejected is in `## Notes`.

## Capability changes

```yaml
changed:
    - plugin/install-as-a-plugin
```

No new capabilities. `plugin/install-as-a-plugin` (`cap-c830d4`) reads
**Supported** and its body is:

> As a user, I add the tcw marketplace and run `/plugin install tcw` (Claude
> Code) or `codex plugin add tcw@tcw` (Codex) to install the tcw skills as a
> plugin.

It names both harnesses but not the two ways to reach the marketplace inside
Claude — the CLI and the web/desktop plugin directory. The first works; the
second does not. That silence is what let the break go unnoticed.

At completion the body gains a clause distinguishing them. **Gated on AC-7**: if
the web UI still refuses after this work, the wording stays as it is. A ledger
that claims more than was verified is worse than one that claims less.

No taxonomy delta. `tcw taxonomy search plugin` and `… marketplace` both return
nothing; the capability carries `Subject: cli` and no `Feature`. Registering a
plugin-distribution Feature is a real gap but not this item's — see Non-goals.

## Problem

Adding `brocef/TCW` as a marketplace from <https://claude.ai/code> fails with
"Marketplace sync failed. Check the repository URL and try again", while
`claude plugin marketplace add` succeeds against the same repo. The web path
syncs server-side through a validator stricter than the CLI's, and the UI never
shows the reason. Full evidence is in `initial-request.md`.

### What the evidence supports, and how strongly

Two different grades of inference are in play, and the spec is only as good as
the weaker one:

**Grade A — cleared by a positive control.** A trait carried by a marketplace
that syncs from the web cannot be what blocks TCW. `source: "./"`, shipping
`hooks/`, a hook entry without `matcher`, shipping `agents/`, shipping
`commands/`, `license`/`metadata` in skill frontmatter, undocumented skill
frontmatter keys generally, and file symlinks are all cleared this way — by
`obra/superpowers` (added successfully in the same UI), `ponytail`, or the
285-plugin `anthropics/claude-plugins-official` catalog. These hold regardless
of anything else in this spec.

**Grade B — inferred from a second failure.** `brocef/skill-cefailures` fails
with the *same generic string*, which is not proof of the *same cause*: the
whole problem with that string is that distinct server-side failures collapse
into it. Treating the two failures as one cause is an **assumption**. It is what
retires `when_to_use`/`compatibility` as suspects, and it is what makes the
candidate list below "two" rather than "several".

Under that assumption, the differences shared by both failures and absent from
the working control are:

| | `description` | `owner` contact | plugin `author` | self-symlink |
| --- | --- | --- | --- | --- |
| superpowers — works | yes | `email` | yes | no |
| skill-cefailures — fails | no | name only | no | yes |
| TCW — fails | no | name only | no | yes |

A third possibility is unresolved and unresolvable from inside this repository:
both failures are repositories the user owns and the success is not, so an
uninstalled Claude GitHub App would explain everything. The user has deferred
that probe.

### This item does not identify the cause, and does not pretend to

Both candidates are changed at once. If AC-7 passes, that does not tell us which
one mattered; if AC-7 fails, it disproves neither, because ownership stays
confounded. **Identification is an explicit non-goal.** What this item is: two
independently justified cleanups — a symlink that costs more than it buys, and
manifest metadata that is simply absent — with web sync as a hoped-for outcome
rather than a diagnosed fix. Staging them into two one-variable experiments was
considered and rejected: it would cost the user a second manual web test to
learn something no goal here depends on.

### Ground truth, with references

- `.claude-plugin/marketplace.json` — keys `name`, `owner`, `plugins`. No
  top-level `description`; `owner` is `{"name": "Brian Cefali"}`; the plugin
  entry has `description`, `name`, `source`, `version` and no `author`.
  `claude plugin validate .` passes with exactly one warning, and it is the
  missing `description`.
- `.claude-plugin/plugin.json` — has `author` (name only) and `keywords`; no
  `homepage`, `repository`, or `license`. Its Codex twin
  `.codex-plugin/plugin.json` carries `homepage` and `repository`. Two manifests
  for one artifact that disagree about where it lives.
- `.agents/plugins/marketplace.json:11` — `{"source": "local", "path":
  "./plugins/tcw"}`; no `description` on the marketplace or its plugin entry.
- `plugins/tcw` — mode `120000`, target `..`. The only other tracked symlink is
  `CLAUDE.md → AGENTS.md`, a file, shared with marketplaces that sync fine.
- What the symlink actually costs, stated precisely: **one** real workaround —
  `pyproject.toml:31` `norecursedirs = ["plugins", …]` with its explaining
  comment at `:28-29`; **one** redundant line — `pyproject.toml:22`
  `exclude = ["plugins*"]`, already implied by `include = ["tcw*"]` at `:21`;
  and **one** docstring clause — the third of three reasons for `git ls-files`
  at `tests/test_documented_cli_surface.py:44-56`. (An earlier draft called all
  three "recursion defenses"; only the first is.)
- `tests/test_plugin_manifests.py:95-98` (`test_symlink_points_at_repo_root`)
  pins the symlink's existence.

### The symlink is not load-bearing — measured

Run against `codex-cli 0.147.0`, each in an isolated `CODEX_HOME` against a git
clone of the working tree:

```bash
export CODEX_HOME=$(mktemp -d)
codex plugin marketplace add <clone>     # local path source
codex plugin add tcw@tcw
```

| Layout | `marketplace add` | `plugin add` | cache size | top-level entries |
| --- | --- | --- | --- | --- |
| symlink + `"path": "./plugins/tcw"` | ok | ok, `0.18.2` | 29M | 34 |
| **no symlink + `"path": "."`** | ok | ok, `0.18.2`, 8 skills | 29M | 34 |

Identical. Codex resolves `"."` against the marketplace root, and — because the
symlink also resolved to the repo root — vendors exactly the same tree either
way. `"."` does not widen what Codex ingests; the wide ingest is pre-existing
and out of scope.

**Migration, also measured.** With a plugin already installed from the old
layout, mutating the marketplace to the new one leaves it `installed, enabled
0.18.2` with its path re-resolved to the root, no cache clearing. This is
structural, not luck: the manifest and the tree change in the **same commit**, so
a stale snapshot holds the old manifest *and* the old tree (consistent), and a
refreshed one holds both new. No mixed state exists.

## Goals

1. Remove `plugins/tcw` and everything that exists only because of it, without
   regressing Codex packaging.
2. Bring `.claude-plugin/marketplace.json` to the metadata shape of marketplaces
   known to sync from the web, and close the same gaps where they repeat.
3. `claude plugin validate .` at zero warnings.
4. Regression tests that fail if the symlink or the metadata gaps return.

## Non-goals

- **Identifying which change fixed it** (above).
- **Fixing `brocef/skill-cefailures`.** Separate repo; it was the diagnostic
  twin. Follow-up if the fix generalizes.
- **Removing `when_to_use` / `compatibility`.** Retired as suspects under the
  Grade-B assumption, and legitimate Agentskills fields Codex reads. Removing
  them would trade a first-class target's fidelity for a guess.
- **The ownership probe.** Deferred by the user to "if I get desperate". It
  stays the designated fallback.
- **Narrowing what Codex vendors.** Pre-existing, unchanged by this work.
- **Registering a taxonomy Feature for plugin distribution.**
- **Any CLI, skill, or command surface change.** Nothing here touches `tcw`
  behavior, so no `skills/<component>/SKILL.md` update is triggered.

## Design

Decisions only; sequencing and exact edits belong to `plan.md`.

**D1 — the repo contains no symlink that resolves to its own ancestor.**
`plugins/tcw` goes. Codex packaging addresses the plugin root-relatively
instead, which the measurement above shows is equivalent. Everything that named
the symlink as its reason is revisited: the `norecursedirs` entry and its
comment, the redundant `packages.find` exclude, and the stale docstring clause.
`tests/test_documented_cli_surface.py` keeps `git ls-files` — its other two
reasons stand on their own and the implementation does not change.

**D2 — the Claude marketplace manifest carries the metadata its peers carry.**
Top-level `description`; `owner.email` (`brocef@users.noreply.github.com`, the
address on this repo's commits — see Notes); a per-plugin `author`; `category`
matching the `"Developer Tools"` already in `.codex-plugin/plugin.json`; and
`keywords` mirroring `.claude-plugin/plugin.json`. `owner.name` is **kept** — the
schema requires it, and dropping it would fail the validation this item exists
to pass. Every field added is a documented schema field, so AC-3 is what
confirms none of them offends the validator.

**D3 — manifests describing one artifact agree about it.** The defect is "a
manifest under-describes the artifact"; swept repo-wide it recurs three times.
`.claude-plugin/plugin.json` gains `homepage`, `repository`, and `license` to
match its Codex twin; `.agents/plugins/marketplace.json` gains descriptions at
both levels. `license` is Apache-2.0, matching `LICENSE` and the six `SKILL.md`
files that already declare it. `.agents/plugins/marketplace.json` keeps **no**
version field — `tests/test_plugin_manifests.py:47` enforces that.

**D4 — the shape is pinned by tests.** In `tests/test_plugin_manifests.py`:
the symlink test is replaced by its inverse, asserting the *class* (no tracked
path is a symlink resolving to an ancestor of itself) rather than the instance,
so a future `plugins/<x> → ..` cannot reappear; a completeness test covers the
marketplace metadata from D2; a test asserts the `.agents` plugin source path
resolves to an existing directory, so `"."` cannot rot; and a consistency test
asserts `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` agree on
`homepage`, `repository`, and `license`. These pin the shape we believe is
required — they cannot verify server-side sync. That is AC-7, manual by
necessity.

**D5 — documentation.** Per `CLAUDE.md`'s Documentation Sync:
`docs/changelogs/upcoming.md` [Any-Code-Change] gets the full technical entry
unconditionally. `docs/release-notes/upcoming.md` [Public-API] is **gated on
AC-7 exactly as the capability edit is** — a user-facing note saying the plugin
can be added from the web directory is the same unverified claim the Risks
section forbids. If AC-7 fails, the release note is omitted and the changelog
records the cleanup without the claim. `README.md` needs no change: the install
commands at `README.md:100-131` are unaffected. Re-evaluate at implementation
rather than forcing an edit. No migration note is needed — the no-mixed-state
result above makes it noise.

## Acceptance criteria

1. `git ls-tree -r HEAD | awk '$1=="120000"'` lists `CLAUDE.md` and nothing else.
2. From a scratch clone of the working tree and an empty `CODEX_HOME`:
   ```bash
   git clone . /tmp/tcw-ac2 && export CODEX_HOME=$(mktemp -d)
   codex plugin marketplace add /tmp/tcw-ac2   # → "Added marketplace `tcw`"
   codex plugin add tcw@tcw                    # → "Added plugin `tcw`"
   ls "$CODEX_HOME"/plugins/cache/tcw/tcw/*/skills | wc -l   # → 8
   ```
   The installed version must equal the version in `pyproject.toml`, read
   rather than hard-coded.
3. `claude plugin validate .` exits 0 with **zero** warnings (today: one).
4. `CLAUDE_CONFIG_DIR=$(mktemp -d) claude plugin marketplace add
   https://github.com/brocef/TCW` reports success.
5. `pytest tests/` passes, including D4's four test changes, and
   `test_plugin_manifests.py` still confirms the 5 version fields agree and the
   agents marketplace carries no version.
6. `grep -rn "plugins/tcw" --include='*.py' --include='*.toml' --include='*.json' .`
   returns nothing outside `docs/changelogs/` (archival history stays).
7. **Manual, user-only, and the verdict on the diagnosis:** at
   <https://claude.ai/code>, with any prior `tcw` marketplace entry removed
   first, adding `brocef/TCW` completes without "Marketplace sync failed" and
   the `tcw` plugin becomes listable in the directory. Requires the user's own
   logged-in account; no agent can run it.

AC-1..6 are the deliverable and are all automatable. AC-7 decides whether the
diagnosis was right, and passing AC-1..6 says nothing about it.

## Risks

- **The diagnosis may be wrong.** The ownership confound is unresolved. If
  claude.ai resolves own-account repos through an uninstalled GitHub App, every
  change here lands correctly and AC-7 still fails. _Mitigation:_ each change is
  justified independently of the diagnosis. A failed AC-7 hands the fork probe a
  clean baseline with one variable left.
- **AC-7 failing must not be papered over.** On failure: no capability body
  edit, no release note, `verify` records it plainly, and the fork probe becomes
  the follow-up item. Recording "fixed" on AC-1..6 alone would be a false ledger
  entry — and the changelog/release-note split in D5 exists to make that
  impossible by omission.
- **Grade-B inference could be wrong.** If the two repos fail for different
  reasons, the candidate list is incomplete and `when_to_use`/`compatibility`
  are not actually retired. Cost of being wrong is bounded: AC-7 fails, and the
  suspects return to the table.
- **Removing `norecursedirs`/`exclude` entries** could surface latent breakage if
  anything under `plugins/` ever returns. Nothing does — the directory is
  removed — and both lines are trivially restorable.
- **Over-fitting to one control.** The metadata design copies `superpowers`;
  `ponytail` corroborates `description` and `owner` contact only. Nothing proves
  `author`/`category`/`keywords` are required. They are added as harmless
  completeness, not as diagnosed fixes.

## Notes

- **Assumption, flagged for the user.** "Use my github email … as my email
  instead of my name" is read as *add the commit email as the contact field,
  keep `owner.name`*, because the schema requires `name` and dropping it would
  fail AC-3. Say so if the intent was to replace the name string outright.
- The address is `brocef@users.noreply.github.com`. It is on this repo's commits
  but not literally all of them — three carry `noreply@anthropic.com`. An
  earlier draft claimed "all 1034 commits", which was wrong on both the count
  and the "all".
- All `codex` measurements used git clones in a scratch directory with isolated
  `CODEX_HOME`s; the user's real `~/.codex` was never touched.
- `.claude/settings.local.json` carries a stale `Bash(ln -s .. plugins/tcw)`
  permission entry. Untracked and machine-local, so out of scope — noted so it
  is not mistaken for a missed dependent.

### Review log

`codex exec` (7 findings) and `bllm-review` (5) reviewed the first draft.

**Accepted:** the D5 release-note gating inconsistency (codex 3 — the worst
finding, and load-bearing); three factual errors (codex 5 — the capability
wording *does* name harnesses, the commit-count claim, the "three recursion
defenses" overclaim, all verified against the repo before accepting); AC-2 and
AC-7 not being third-party reproducible (codex 4); the experiment lacking
commands and captured output (codex 6); plan-level mechanics in Design (codex 7
— Design is now decisions-only); a manifest-consistency test for the two
`plugin.json` files (bllm 3).

**Narrowed rather than conceded:** codex 1 said `skill-cefailures` clears
nothing. Partly right — the Grade A/B split now distinguishes rows cleared by
positive controls, which hold independently, from the one inference that rests
on both failures sharing a cause. Codex 2 (changing two variables at once) is
answered by stating identification as a non-goal rather than by staging the
work.

**Rejected with reason:** bllm 1 (`"."` might widen what Codex ingests) —
measured identical, 29M and 34 entries either way, because the symlink resolved
to the same root. bllm 5 (no upgrade-path criterion) — measured; the manifest
and tree change in one commit so no mixed state exists, which also **downgraded
a risk in the first draft** that had overstated the same thing. bllm 4 (assert
`plugins/` is gone) — redundant with D4's class assertion, and an empty
directory is not tracked by git anyway. bllm 2 (validator might reject the new
fields) — every added field is a documented schema field and AC-3 covers it.
