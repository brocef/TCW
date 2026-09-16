# Spec — Compose documentation-sync and tcw-work-create from project bindings

Child 6 of
`2026-09-16-make-every-procedural-skill-in-tcw-overridable-by-the-project-that-uses-it`.
Written against `main` at `a0a9d75f`, which carries children 1 and 2.

## Capability changes

Planned ledger deltas only. Both entries exist
(`tcw capabilities show skills/documentation-sync` → `cap-301436`,
`skills/tcw-work-create` → `cap-43570a`).

```yaml
changed:
    - skills/documentation-sync # its procedure text now comes from `tcw work procedure prompt documentation-sync`
    - skills/tcw-work-create # its procedure text now comes from `tcw work procedure prompt create-work`
```

What either skill does for a project that configures nothing is unchanged.

## Problem

1. **Both skills still ship their procedure as fixed prose.** Child 2 added the
   ids `documentation-sync` and `create-work` (`tcw/store/base.py:939`) and
   copied each skill body verbatim into `tcw/work/procedures/<id>.md`, but
   `skills/documentation-sync/SKILL.md` and `skills/tcw-work-create/SKILL.md`
   still carry the text themselves. A project writing
   `work.procedures.documentation-sync` today changes what
   `tcw work procedure prompt` prints and nothing an agent reading the skill
   sees. `skills/README.md:98-103` marks both overridable; the conversion is
   what makes that verdict true.
2. **`tests/test_shipped_procedures.py:21-32` pins each default to its skill
   body.** Once the skill body is split, the `documentation-sync` and
   `create-work` rows compare against a file that no longer holds the default.
3. **Both skills mix TCW's rules with conduct.**
   - `tcw-work-create` states board rules — one idea gives exactly one outcome,
     look before `tcw work new`, a duplicate splits history
     (`SKILL.md:14-17`); search the board and inbox through `find-overlap.md`
     (`:62-67`). `skills/README.md:102-103` says those stay fixed.
   - `documentation-sync` opens with where the entries come from:
     `tcw work docs --json` and its `source` values (`SKILL.md:9-16`), the
     lifecycle points that invoke the skill (`:18-26`) and the Markdown fallback
     form of an entry (`:28-51`). Those are TCW's configuration surface and the
     stage contracts in `skills/tcw-work/references/lifecycle/stage-*.md`, not
     conduct.
4. **documentation-sync has two overridable references but one id.**
   `skills/README.md:99-100` classifies `references/cut-version.md` and
   `references/release-notes-and-changelogs.md` overridable. Child 2 shipped
   only `documentation-sync`, and a child may not add ids.
5. **documentation-sync is used outside TCW nodes, and the verb is not.**
   `SKILL.md:16` supports a project that is not a TCW node. Run there,
   `tcw work procedure prompt documentation-sync` exits 1 with
   "no tcw work node here" (`tcw/work/cli.py:1572-1574` → `_store()`), checked
   in an empty directory. A plain `` !`… || true` `` would leave such a reader
   with no procedure at all.
6. **Injection needs permission.** Claude Code runs `` !`cmd` `` only for
   commands the skill's `allowed-tools` grants. `tcw-work-create` already
   declares `Bash(tcw *)` (`SKILL.md:5`); `documentation-sync` declares no
   `allowed-tools` (`SKILL.md:1-5`).

## Goals

1. Each converted `SKILL.md` keeps its frontmatter, holds only the fixed text,
   injects its procedure with `` !`tcw work procedure prompt <id> …` `` and ends
   with a manual fallback block naming the command, as
   `skills/tcw-work-stage/SKILL.md:38-58` does.
2. A reader in a checkout with nothing configured gets today's words: fixed
   body plus command output equals the pre-conversion body, except for
   differences the outcome names and explains.
3. The board rules in `tcw-work-create` and the configuration surface in
   `documentation-sync` cannot be switched off by a `work.procedures` binding.
4. Nothing that invokes `documentation-sync` breaks: `AGENTS.md:132`, the
   `plan`/`implement` stage contracts (`stage-plan.md`, `stage-implement.md`,
   guarded by `tests/test_documentation_sync_wiring.py:69-78`),
   `stage-verify.md:35` and a project that is not a TCW node.

## Non-goals

- **Converting `skills/tcw-work-create/references/find-overlap.md`.** Fixed
  (`skills/README.md:103`); it stays byte-for-byte.
- **A second procedure id** for either documentation-sync reference. That is a
  mechanism change (see Design, and Risks).
- **Changing `tcw work docs`, `work.documentation`, or anything under `tcw/`
  other than `tcw/work/procedures/*.md`.**
- **Serving the version-cut instructions from `tcw-config.yaml`.**
  `2026-08-18-serve-version-cut-instructions-from-tcw-config-yaml-instead-of-the-agent-guide`
  is in `backlog` (`tcw work show`, 2026-09-16): it has not landed, so there is
  no configuration to reuse and none is added here.
- **Editing `skills/tcw-work/references/lifecycle/stage-verify.md`**, which
  names `cut-version.md` directly; not this child's file.
- **Changing `dynamic_skill` or any verdict.**
- **Live sessions** under Claude or Codex, and eval arms
  (`evals/evals.json:787`, `tests/test_eval_grading.py:203`) — deferred to
  verify.

## Design

### `tcw-work-create`

Fixed body, in this order:

1. Frontmatter unchanged.
2. `# Turning an idea into a work item` and its opening paragraph (today
   `:12-17`) — one outcome, look first, no duplicate.
3. `## 2. Find overlap` (today `:62-67`), moved up so it sits in the fixed part.
   The whole section moves rather than splitting its one permissive sentence
   about dispatching a subagent.
4. `` !`tcw work procedure prompt create-work || true` ``.
5. The fallback block.

`tcw/work/procedures/create-work.md` loses exactly those two pieces: the title
and paragraph, and the step 2 section. It keeps `How it runs`, steps 0, 1, 3, 4
and 5. Cross-references such as "step 2's `blocks` lines" still resolve, since
the fixed step 2 is in the same skill the reader has open.

Kept in the default, as conduct: the modes, step 0 (which checkout to run in —
a git workflow, which Rule 1 names as conduct), step 3's mode columns and its
precedence among matches, step 4's questions and commit, and step 5's report
lines. "Closed items are never the deciding match" is also stated by the fixed
`find-overlap.md` ("It is never a match"), so replacing step 3 cannot remove it.

No slug is passed: the skill files new work, not work on one item.

### `documentation-sync`

Fixed body: frontmatter, then today's `:7-51` — the title, the
`tcw work docs --json` paragraph and its sources, the lifecycle-point table and
the one-pass paragraph, and "The Documentation Sync Section — the fallback
form". Then the injection, then the fallback block.

The default loses exactly those lines and keeps `## Evaluating Triggers`
through `## Common Mistakes` (today `:53-137`).

**The references stay where they are, unchanged, and are not folded in.** With
one id, the unit a project can replace is the whole procedure, and the default
is the only text that tells a reader to open either reference ("Companion
references", "When to offer version and changelog options"). A project that
replaces `documentation-sync` without `builtin: true` therefore also stops its
agents reading them; one that keeps `builtin: true` and adds a `blob:` can
redirect a single step ("cut versions with X instead of
`references/cut-version.md`"). Folding them in was rejected: it would load
about 265 more lines on every invocation where today they load on demand
(`SKILL.md:92-94` says that is the point), make the reader's text differ from
today's, and still not let a project replace one reference without restating
the rest. Finer control needs a second id, which is reported rather than added.

**Injection with a fallback to TCW's own text.** The injected command is

```sh
tcw work procedure prompt documentation-sync 2>/dev/null || cat "${CLAUDE_PLUGIN_ROOT}/tcw/work/procedures/documentation-sync.md" || true
```

The plugin source is the repository root (`.claude-plugin/marketplace.json`,
`"source": "./"`), so the shipped default is in the plugin. Outside a TCW node,
or with no CLI installed, the reader gets TCW's default, which is what a node
with nothing configured gets anyway. The fallback block names both commands.

**`allowed-tools: Bash(tcw *), Bash(cat *)`** is added to documentation-sync's
frontmatter, the same pair `tcw-work-stage` declares, so the injection is
permitted.

### The drift test

The `documentation-sync` and `create-work` rows leave `SOURCES`: there is no
second copy left to drift from. They move to a `CONVERTED` map (id → skill
path). The coverage test accepts the union of both maps, and a new
parametrized test asserts for each converted skill that it injects
`tcw work procedure prompt <id>`, names that command in a fenced fallback
block, and does not repeat the default's text (its first line of prose is
absent from the skill body). The other eight rows are untouched.

### Storage abstraction

Nothing here is a store operation. The skill reads TCW's own shipped file and
calls a CLI verb that already resolves node configuration; the litmus test is
not engaged.

### Harness

The procedure text reaches Claude by injection and Codex through the fallback
block, which is the only carrier on Codex. `docs/lifecycle/harness.md`'s rule is
met because the text itself comes from the CLI; the `cat` fallback is packaging
the plugin already relies on (`skills/tcw-work-stage/SKILL.md:27`).

## Acceptance criteria

1. In the worktree with nothing configured, for each id, the text of the fixed
   body (after frontmatter) with the `` !`…` `` line replaced by
   `tcw work procedure prompt <id>` output, diffed against
   `git show main:<skill path>` after frontmatter, differs only by: the
   fallback block, and for `tcw-work-create` the moved step 2 section. The
   frontmatter is compared separately and differs only by documentation-sync's
   added `allowed-tools`. The outcome shows the diff.
2. `grep -niE '\b(codex|opus|sonnet|haiku|sendmessage|adversarial-code-reviewer)\b'`
   over `skills/documentation-sync/SKILL.md` and `skills/tcw-work-create/SKILL.md`
   prints nothing (epic criterion 8).
3. Each of those two files contains a fenced block naming
   `tcw work procedure prompt <its id>` under a manual-fallback heading (epic
   criterion 11).
4. `skills/tcw-work-create/SKILL.md` contains `references/find-overlap.md` and
   "Exactly one outcome comes out"; `tcw/work/procedures/create-work.md` contains
   neither.
5. `skills/documentation-sync/SKILL.md` contains `tcw work docs --json` and the
   "## The Documentation Sync Section" heading;
   `tcw/work/procedures/documentation-sync.md` contains neither.
6. From a directory that is not a TCW node, the documentation-sync injection
   command (with `CLAUDE_PLUGIN_ROOT` set to the worktree) prints the default
   and exits 0.
7. `git diff main -- skills/tcw-work-create/references/find-overlap.md skills/documentation-sync/references`
   is empty.
8. `tests/test_shipped_procedures.py`, `tests/test_documentation_sync_wiring.py`,
   `tests/test_dynamic_skill_marker.py`, `tests/test_plugin_manifests.py` and
   `tests/test_skill_lifecycle_parity.py` pass; bare `pytest` passes once at
   the end.
9. The item's `capabilities.yaml` carries both `changed:` entries and
   `tcw capabilities check` exits 0.

## Risks

- **A broken project configuration falls back silently.** Inside a node whose
  `work.procedures.documentation-sync` fails to resolve (for example, a
  `generate:` script that errors), `2>/dev/null ||` serves TCW's text instead
  of the refusal. Accepted so a non-TCW project is not told to run `tcw init`;
  `tcw validate` still reports the shape errors. The proper fix is for the
  verb to print the builtin text outside a node — a mechanism change, reported.
- **`stage-verify.md:35` bypasses an override.** It names
  `references/cut-version.md` directly, so a project that replaced
  documentation-sync's version-cut guidance is still pointed at TCW's. Belongs
  with the version-cut item.
- **A dangling-looking pointer.** `references/cut-version.md:4` says see
  "`SKILL.md` → When to offer version and changelog options", a section that now
  arrives by injection. A Claude reader still finds it in the loaded skill; a
  Codex reader finds it in the command output. Left unchanged so the references
  stay today's text.
- **Sibling merge conflict in `tests/test_shipped_procedures.py`.** Children
  3–5 each change a row in the same map and likely the same coverage test.
  The change here is kept to row moves and one additive test.
- **Converting changes what an eval observes.** An arm checking that the agent
  read `tcw-work-create/SKILL.md` still passes; one checking for procedure
  wording in that file would not. Not run here.

## Notes

- `tcw work stage gate spec` refused: "'spec' is not legal for an item in
  'active'; it runs in backlog". The requester chose to plan inside the
  worktree; the prompt was followed anyway.
- Line numbers above are from the worktree at `a0a9d75f`.
- Assumption, not verified: Claude Code refuses `` !`cmd` `` in a skill whose
  `allowed-tools` does not grant the command. Stated in Claude Code's
  documentation for commands; not exercised here (live checks deferred).

## Decisions for the requester to confirm

1. documentation-sync's references stay as unchanged files reached through the
   default, not folded into it and not given their own id.
2. documentation-sync falls back to `cat` of the shipped default when the verb
   fails, with stderr suppressed.
3. `allowed-tools: Bash(tcw *), Bash(cat *)` added to documentation-sync.
4. tcw-work-create's fixed part is the opening paragraph plus the whole of
   step 2, moved above the injected procedure; step 0, step 3's precedence and
   step 5's report lines stay overridable.
5. The drift test gets a `CONVERTED` map instead of rows that point at a split
   source.
