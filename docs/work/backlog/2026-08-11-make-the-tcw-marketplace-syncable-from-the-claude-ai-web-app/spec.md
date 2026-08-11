# Spec: make the TCW marketplace syncable from the claude.ai web app

## Capability changes

```yaml
changed:
    - plugin/install-as-a-plugin
```

No new capabilities. `plugin/install-as-a-plugin` (`cap-c830d4`) reads
**Supported** today and its body says "As a user, I add the tcw marketplace and
run `/plugin install tcw` (Claude Code) or `codex plugin add tcw@tcw` (Codex)".
That is true through the CLI and false through the web/desktop plugin directory,
and the wording names no harness — which is how the break went unnoticed.

At completion, the body gains an explicit clause that the marketplace can be
added from the CLI **or** the web/desktop plugin directory. **That edit is gated
on AC-7 actually passing** (see Risks): if the web UI still refuses after this
work, the honest ledger state is the current wording, not a stronger claim.

No taxonomy delta. `tcw taxonomy search plugin` and `… marketplace` both return
nothing, and the capability carries `Subject: cli` with no `Feature`. Registering
a plugin-distribution Feature is defensible but is not this item's problem —
see Non-goals.

## Problem

`initial-request.md` has the full evidence. In brief: adding `brocef/TCW` as a
marketplace from <https://claude.ai/code> fails with "Marketplace sync failed.
Check the repository URL and try again", while `claude plugin marketplace add`
succeeds against the same repo. The web path syncs server-side through a
validator stricter than the CLI's, and the UI never shows the actual reason.

`brocef/skill-cefailures` fails identically. That cleared skill frontmatter,
hooks, and agents as causes, and left exactly two in-repo candidates — both
shared by the two failing repos and absent from `obra/superpowers`, which the
user added successfully in the same UI:

1. the marketplace manifest omits `description`, `owner` contact, and per-plugin
   `author`
2. `plugins/tcw → ..` is a **self-referential directory symlink** inside a plugin
   whose `source` is `"./"`

A third possibility — that claude.ai resolves the user's own repositories through
a GitHub App that is not installed — is unresolved and cannot be settled from
inside this repository. The user has deferred that probe.

### What is actually true today, with references

- `.claude-plugin/marketplace.json` — keys are `name`, `owner`, `plugins`. No
  top-level `description`; `owner` is `{"name": "Brian Cefali"}` with no contact
  field; the single plugin entry has `description`, `name`, `source`, `version`
  and no `author`. `claude plugin validate .` passes with exactly one warning,
  and it is the missing `description`.
- `.claude-plugin/plugin.json` — has `author` (name only) and `keywords`, but no
  `homepage`, `repository`, or `license`. Its Codex twin
  `.codex-plugin/plugin.json` **does** carry `homepage` and `repository`. The two
  manifests describe the same artifact and disagree about it.
- `.agents/plugins/marketplace.json:11` — addresses the plugin as
  `{"source": "local", "path": "./plugins/tcw"}`, and has no `description` on
  either the marketplace or its plugin entry.
- `plugins/tcw` — mode `120000`, target `..`. The only other symlink tracked in
  the repo is `CLAUDE.md → AGENTS.md`, which is a file and is shared with
  marketplaces that sync fine.
- The symlink has cost three separate recursion defenses:
  `pyproject.toml:22` (`exclude = ["plugins*"]`), `pyproject.toml:28-31`
  (`norecursedirs` with its explaining comment), and the `git ls-files` rationale
  at `tests/test_documented_cli_surface.py:44-56`.
- `tests/test_plugin_manifests.py:95-98` (`test_symlink_points_at_repo_root`)
  pins the symlink's existence, so removing it is a deliberate, test-visible act.

### The symlink is not load-bearing — measured, not assumed

The one expensive question in `initial-request.md` was whether Codex packaging
needs `plugins/tcw`. It does not. Both layouts were run against `codex-cli
0.147.0` in an isolated `CODEX_HOME`:

| Layout                                                | `marketplace add` | `plugin add tcw@tcw`   |
| ----------------------------------------------------- | ----------------- | ---------------------- |
| symlink + `"path": "./plugins/tcw"` (today)           | ok                | —                      |
| **no symlink + `"path": "."`**                        | ok                | ok, `0.18.2`, 8 skills |

Codex resolves `"."` against the marketplace root and installs every skill. The
symlink's entire remaining purpose is served by one character.

## Goals

1. Remove `plugins/tcw` and every workaround that exists only because of it,
   without regressing Codex packaging.
2. Bring `.claude-plugin/marketplace.json` up to the metadata shape of
   marketplaces known to sync from the web, and close the same gaps wherever
   they repeat in the other three manifests.
3. Get `claude plugin validate .` to zero warnings.
4. Leave a regression test that fails if either the symlink or the metadata gaps
   come back.

## Non-goals

- **Fixing `brocef/skill-cefailures`.** Separate repository; it served as the
  diagnostic twin. Applying whatever works there is follow-up.
- **Removing `when_to_use` / `compatibility` from skill frontmatter.** Cleared as
  the cause — `skill-cefailures` has neither and fails anyway — and they are
  legitimate Agentskills fields that Codex reads. Removing them would trade a
  first-class target's fidelity for nothing.
- **The ownership probe** (fork `obra/superpowers` to the user's account). The
  user has explicitly deferred it to "if I get desperate". It stays the
  designated fallback, not a task here.
- **Registering a taxonomy Feature for plugin distribution.** Real gap, wrong
  item; the capability's `Subject: cli` stays as-is.
- **Restructuring the repo so the plugin genuinely lives in a subdirectory.** The
  `"path": "."` result makes it unnecessary.
- **Changing any CLI surface, skill, or command.** Nothing here touches `tcw`
  behavior, so no `skills/<component>/SKILL.md` update is triggered.

## Design

### D1 — delete the self-symlink

`git rm plugins/tcw`, and change `.agents/plugins/marketplace.json:11` to
`"path": "."`. Then remove the workarounds that named it as their reason:

- `pyproject.toml:22` — drop `"plugins*"` from `packages.find.exclude`.
- `pyproject.toml:28-31` — drop `"plugins"` from `norecursedirs` and the comment
  above it that exists to explain it. The remaining entries (`.venv`, `build`,
  `dist`, `*.egg-info`) are unrelated and stay.
- `tests/test_documented_cli_surface.py:44-56` — the docstring gives three
  reasons for `git ls-files` over `rglob`; the third is the symlink. Delete that
  clause. **Do not change the implementation** — the other two reasons
  (`.gitignore` supplies junk exclusions, `--others` keeps new drafts in scope)
  are independently sufficient, and `git ls-files` remains the right call.

### D2 — marketplace manifest metadata

`.claude-plugin/marketplace.json` gains:

- top-level `description` — the one thing the validator warns about
- `owner.email` — `brocef@users.noreply.github.com`, the address on all 1034
  commits in this repo
- a per-plugin `author` block carrying the same name and email
- `category` on the plugin entry, matching the `"Developer Tools"` already
  declared in `.codex-plugin/plugin.json`
- `keywords` on the plugin entry, mirroring the six already in
  `.claude-plugin/plugin.json`

`owner.name` is **kept**. The marketplace schema lists it as required, and
dropping it would fail the validation this item exists to pass.

### D3 — close the sibling gaps in the other manifests

The defect is "a manifest under-describes the artifact". Swept repo-wide, it
appears three more times:

- `.claude-plugin/plugin.json` gains `homepage`, `repository`, and `license`,
  matching `.codex-plugin/plugin.json`. Two manifests for one artifact should not
  disagree about where it lives.
- `.agents/plugins/marketplace.json` gains a top-level `description` and a
  `description` on its plugin entry.
- `LICENSE` is Apache-2.0 and six `SKILL.md` files already declare
  `license: Apache-2.0`; the `license` fields above use the same SPDX string.

`.agents/plugins/marketplace.json` still carries **no** version field —
`tests/test_plugin_manifests.py:47` enforces that and it stays true.

### D4 — regression tests

In `tests/test_plugin_manifests.py`:

- **Replace** `test_symlink_points_at_repo_root` with its inverse: no tracked
  path in the repo is a symlink that resolves to an ancestor of itself. Asserting
  "`plugins/tcw` does not exist" would only pin this one instance; asserting the
  *class* is what stops a future `plugins/<x> → ..` reappearing.
- **Add** a manifest-completeness test: `.claude-plugin/marketplace.json` has a
  non-empty top-level `description`, an `owner` with both `name` and `email`, and
  a plugin entry with an `author`.
- **Add** an assertion that `.agents/plugins/marketplace.json`'s plugin `source`
  path resolves to an existing directory, so the `"."` change cannot silently rot.

These pin the shape we believe is required. They **cannot** verify server-side
sync — that is AC-7, and it is manual by necessity.

### D5 — documentation

Per the Documentation Sync section of `CLAUDE.md`:

- `docs/changelogs/upcoming.md` [Any-Code-Change] — Changed/Removed/Internal
  entries for the symlink removal, the manifest metadata, and the test changes.
- `docs/release-notes/upcoming.md` [Public-API] — plain-language note that the
  plugin can be added from the web/desktop directory, and that Codex users on a
  pinned snapshot should re-run `codex plugin marketplace upgrade`.
- `README.md` [Public-API] — **no change expected.** The install commands at
  `README.md:100-131` are unaffected; the `codex plugin marketplace add
  brocef/TCW --ref main` line stays correct. Re-evaluate at implementation, do
  not force an edit.
- `skills/<component>/SKILL.md` — not triggered; no component's CLI surface,
  model, lifecycle, or guardrails change.

## Acceptance criteria

1. `git ls-tree -r HEAD | awk '$1=="120000"'` lists `CLAUDE.md` and nothing else.
2. From a clean `CODEX_HOME` against the working tree: `codex plugin marketplace
   add <repo>` succeeds, then `codex plugin add tcw@tcw` installs version
   `0.18.2` with all 8 skills present in the plugin cache.
3. `claude plugin validate .` exits 0 with **zero** warnings (today: one).
4. From a clean `CLAUDE_CONFIG_DIR`: `claude plugin marketplace add
   https://github.com/brocef/TCW` still reports success.
5. `pytest tests/` passes, including the three test changes in D4, and
   `tests/test_plugin_manifests.py` still confirms the 5 version fields agree and
   the agents marketplace carries no version.
6. `grep -rn "plugins/tcw" --include='*.py' --include='*.toml' --include='*.json'
   .` returns nothing outside `docs/changelogs/` (archival history stays).
7. **Manual, and the one that decides the item:** adding `brocef/TCW` at
   <https://claude.ai/code> succeeds. Only the user can run it.

AC-7 cannot be automated and cannot be run by the implementing agent. AC-1
through AC-6 are the deliverable; AC-7 is the verdict on the diagnosis.

## Risks

- **The diagnosis may be wrong.** The unresolved confound is that both failing
  repos are the user's own, and the working one is not. If claude.ai resolves
  own-account repos through an uninstalled GitHub App, every change here lands
  correctly and AC-7 still fails. _Mitigation:_ each change is independently
  justified — the symlink has cost three workarounds and buys nothing now, and
  the metadata gaps are real regardless. If AC-7 fails, the item is not wasted;
  it hands the fork probe a clean baseline with one variable left.
- **AC-7 failing must not be papered over.** If it fails, the capability body
  edit in `## Capability changes` does **not** happen, `verify` records the
  outcome honestly, and the fork probe becomes the follow-up item. Recording
  "fixed" on the strength of AC-1..6 alone would be a false ledger entry.
- **Codex consumers pinned to the old path.** Anyone with an existing Codex
  marketplace snapshot resolves the plugin at `<root>/plugins/tcw`; after this
  lands that path is gone until `codex plugin marketplace upgrade` re-resolves.
  Cheap to absorb, but it belongs in the release notes (D5).
- **Deleting `norecursedirs`/`exclude` entries could surface latent breakage** if
  anything else under `plugins/` ever appears. Nothing does today — `plugins/`
  contains only the symlink and is removed entirely — but the entries are cheap
  to restore if a real `plugins/` package is ever added.
- **Low risk of over-fitting to superpowers.** The metadata design copies a
  single known-good marketplace. `ponytail` corroborates `description` +
  `owner` contact; neither carries proof that `author`/`category`/`keywords` are
  required. They are added as harmless completeness, not as diagnosed fixes.

## Notes

- **Assumption, flagged for the user.** "Use my github email … as my email
  instead of my name" is read as *add the commit email as the contact field*,
  keeping `owner.name` because the schema requires it. If the intent was to
  replace the name string with the email, say so — it is a one-line change, but
  it would fail `claude plugin validate` if `name` were dropped outright.
- The `codex` measurement used a git clone of the working tree in a scratch
  directory with an isolated `CODEX_HOME`; the user's real `~/.codex` was not
  touched.
- `.claude/settings.local.json` carries a stale
  `Bash(ln -s .. plugins/tcw)` permission entry. Untracked and machine-local, so
  out of scope — noted only so it is not mistaken for a missed dependent.
