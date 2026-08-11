# Make the TCW marketplace syncable from the claude.ai web app

## Origin

Reported by the user on 2026-08-11. Adding TCW as a plugin marketplace from the
web app at <https://claude.ai/code> fails, with either `brocef/TCW` or the full
`https://github.com/brocef/TCW` URL:

> Marketplace sync failed. Check the repository URL and try again.

The same flow, in the same session, adds `obra/superpowers` without complaint.
The user's question was literally "what is TCW missing?" and the request is to
fix whatever that turns out to be, plus any adjacent change that is cheap and
cannot hurt (their example: the marketplace `description` the validator already
warns about).

## Problem

The CLI path works and the web path does not, for the same repository:

```
$ CLAUDE_CONFIG_DIR=<clean> claude plugin marketplace add https://github.com/brocef/TCW
Cloning repository (timeout: 120s): https://github.com/brocef/TCW.git
Clone complete, validating marketplace…
✔ Successfully added marketplace: tcw (declared in user settings)

$ claude plugin validate .
⚠ Found 1 warning:
  ❯ description: No marketplace description provided.
✔ Validation passed with warnings
```

These are two different code paths, not one. The web/Cowork flow syncs
**server-side** through Anthropic's marketplace service, which runs a stricter
content validator than the CLI and collapses every distinct failure into the one
generic string above. The specific server-side reason is returned in a
`status: failed_content` payload that the UI never shows — see References.

**The user cannot read that payload.** They are adding the plugin in a browser,
not in Claude Desktop, so `~/Library/Logs/Claude/claude.ai-web.log` — where the
detail is otherwise recoverable — does not exist for them. Every finding below
is therefore inferred by differential comparison against marketplaces whose web
sync status is known, not read from an error message.

### A second repository fails identically

`brocef/skill-cefailures` was added in the same web UI as a discriminating probe
and failed the same way. That matters because it is a near-twin of TCW on the
axes that were under suspicion, and a stranger on the others:

- **shares** with TCW: the `plugins/<name> → ..` self-symlink, the
  `.agents/plugins/marketplace.json` + `.codex-plugin/` dual packaging, a
  tracked `.claude/settings.json`, `source: "./"`, and the same manifest
  metadata shape
- **does not share**: no `hooks/`, no `agents/`, and skills carrying only
  `name` + `description` — no `when_to_use`, no `compatibility`

So the cause is something the two failures share, and it is not skill
frontmatter, hooks, or agents.

### What the comparison rules out

Each row is cleared by a marketplace that carries the trait and is known to
work — either added successfully in this same web UI, or present in the official
`anthropics/claude-plugins-official` catalog (285 plugins).

| Ruled out                            | Cleared by                                                       |
| ------------------------------------ | ---------------------------------------------------------------- |
| Repo private / not anonymously readable | public; unauthenticated `raw.githubusercontent.com` fetch works |
| Invalid or missing manifest           | `claude plugin validate .` passes; CLI add succeeds                |
| `$schema` present / absent            | official marketplace has one, superpowers does not — both fine     |
| `source: "./"`                        | superpowers, ponytail, supabase all use it                         |
| Shipping `hooks/` at all              | superpowers ships a SessionStart hook (and uses undocumented `shell`/`async`); TCW's uses only `type`/`command` |
| Hook entry without `matcher`          | ponytail's `SubagentStart`/`UserPromptSubmit` omit it              |
| Shipping `agents/`                    | 27 of 255 official-catalog plugins ship agents                     |
| Shipping `commands/`                  | ubiquitous in the official catalog                                 |
| Skill frontmatter `license`/`metadata` | supabase (official catalog) uses both                             |
| Undocumented skill frontmatter keys   | ponytail ships `homepage` and `argument-hint` in SKILL.md          |
| `when_to_use` / `compatibility`       | `skill-cefailures` has neither and fails anyway                    |
| File symlinks                         | superpowers (`AGENTS.md`), supabase (`CLAUDE.md`)                  |

### What survives

Differences shared by **both** failing repos and absent from the confirmed-working
one:

| | `description` | `owner` contact | plugin `author` | self-symlink | `.claude/` tracked |
| --- | --- | --- | --- | --- | --- |
| superpowers — **works** | yes | `email` | yes | no | no |
| skill-cefailures — **fails** | no | name only | no | yes | yes |
| TCW — **fails** | no | name only | no | yes | yes |

Two candidate stories, not yet separated:

1. **Marketplace metadata.** The manifest omits the top-level `description`, the
   `owner` has no `email`/`url`, and the plugin entry has no `author`. A
   server-side validator treating any of these as required — where the CLI only
   warns — fits the evidence exactly.
2. **The `plugins/tcw → ..` self-symlink.** With `source: "./"` the plugin root
   *contains a directory symlink back to itself*, so any component scan that
   follows symlinks sees `plugins/tcw/plugins/tcw/…` without end. This repo has
   already had to defend against precisely that recursion three times —
   `norecursedirs` and a `packages.find` exclude in `pyproject.toml`
   (`docs/changelogs/v0.2.0.md`), and a switch from `rglob` to `git ls-files` in
   `tests/test_documented_cli_surface.py` (`docs/changelogs/v0.18.0.md`). Local
   tooling could be configured around it; a server-side scanner cannot be.

### The unresolved confound

Both failures are repositories **the user owns**; the success belongs to someone
else. If claude.ai resolves own-account repositories through the Claude GitHub
App rather than anonymously, every `brocef/*` marketplace fails on install
scope alone and nothing in this repository is at fault. There is a known class
of issues in this area (References).

This is separable with one action the user can take: fork `obra/superpowers` to
`brocef/superpowers` and add `brocef/superpowers` in the same web UI. Identical
content, different owner.

- **it works** → ownership is cleared and the cause is in this repository
- **it fails** → nothing here is wrong; the fix is a GitHub App install, and this
  item shrinks to recording that

**This probe had not been run when the request was written.** The spec should
not assume its outcome.

## Product changes

`README.md` documents installing TCW as a plugin. That path is currently broken
for anyone using Claude on the web or in the desktop app — they can only install
via the CLI. Restoring it is the point of the item. Whether anything else about
the documented install story changes is the spec's call.

## Technical changes

Not decided — the spec's job. The candidates are the manifest metadata fields,
the self-symlink, or neither (if the confound above explains it).

## Meta changes

The abstraction litmus test does not apply: this is plugin packaging, not a
store operation. The **harness-compatibility** rule does, and bites hard —
whatever changes must keep the Codex/Agentskills path working. Two specifics:

- `.agents/plugins/marketplace.json` addresses the plugin as
  `{"source": "local", "path": "./plugins/tcw"}`, which is what the self-symlink
  exists to satisfy. Removing the symlink without re-homing that path breaks
  Codex packaging to fix Claude.
- `tests/test_plugin_manifests.py:98` asserts the symlink resolves to the repo
  root, so removing it is a deliberate, test-visible decision rather than a
  quiet deletion.

## Open for the spec

- **Run the ownership probe first**, or accept the ambiguity and fix the
  in-repo candidates blind? They are cheap and harmless either way, but the
  probe decides whether this item is real work or a note.
- **If the symlink has to go**, how does `.agents/plugins/marketplace.json`
  address the plugin instead — a `path` of `"."`, a different source kind, or a
  genuine subdirectory layout? This is the only expensive question in the item.
- **Which cheap improvements are in scope.** Raised but not settled with the
  user: top-level marketplace `description` (the one validator warning),
  `owner.email`/`url`, per-plugin `author`, `category`/`keywords` on the
  marketplace entry, and `homepage`/`repository`/`license` in
  `.claude-plugin/plugin.json` (`.codex-plugin/plugin.json` already carries
  homepage and repository, so the Claude manifest is the odd one out).
- **How to pin the fix.** `tests/test_plugin_manifests.py` is the natural home,
  but it can only assert the shape we believe is required — it cannot verify
  server-side sync. Decide what an honest regression test asserts.
- **Whether `when_to_use` / `compatibility` stay.** They are now cleared as the
  cause. They are also legitimate Agentskills fields that Codex reads, so the
  default should be to keep them; recorded here only so a later reader does not
  re-open it.

## Notes

- Explicitly **out of scope**: fixing `brocef/skill-cefailures`. It is a separate
  repository and served here only as the diagnostic twin. If the fix generalizes,
  applying it there is follow-up work, not this item.
- The user was asked what to clarify and for reference material; they redirected
  to running the `skill-cefailures` probe, whose result is recorded above. The
  References below are what this session gathered, not material the requester
  supplied.
- Everything in "What survives" is differential inference. If the real
  server-side error ever becomes readable — via Claude Desktop's
  `claude.ai-web.log`, or by reading the sync response in browser devtools — it
  names the cause directly and supersedes all of it.

## References

- <https://github.com/DietrichGebert/ponytail/issues/582> — the same generic UI
  error traced to a `status: failed_content` server-side rejection over a single
  undocumented hook field; establishes that the web validator is stricter than
  the CLI and that the UI hides the reason.
- <https://github.com/anthropics/claude-code/issues/61271> — documents the
  generic string masking a specific server-side payload, and that the sync runs
  from an unauthenticated server-side session.
- <https://github.com/anthropics/claude-code/issues/56844> — "Claude GitHub App
  is not installed on this repository"; the class of failure behind the
  ownership confound.
- <https://code.claude.com/docs/en/plugin-marketplaces> — the marketplace schema;
  required vs optional fields for the manifest and the `owner` block.
- `~/.claude/plugins/marketplaces/` and
  `~/.claude/plugins/plugin-catalog-cache.json` — the local control corpus
  (superpowers, ponytail, skill-cefailures, supabase) and the official
  285-plugin catalog with per-plugin component listings, which is what most of
  the "ruled out" table is evidenced against.
- `docs/changelogs/v0.2.0.md` and `docs/changelogs/v0.18.0.md` — why the
  self-symlink exists and the three separate recursion defenses it has already
  required.
