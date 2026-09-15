# Plan — Drop the `tcw-` prefix from the plugin's skill and agent names

Thirteen tasks: one guard that can land first, eight rename tasks, one store task,
one pair of guards that can only land last, and a documentation block.

The shape is set by which guards are green when. **8b** (a name matches its directory)
passes on the tree today — all fifteen skills already agree — so it lands **first** and
is a real net under every rename that follows. **8c** (a name does not repeat the
plugin id) and **8a** (the old names appear in no live route) are both false until the
renames are done, so they land **last**. The middle is mechanical and each task is one
skill family, complete: directory, frontmatter, and every live reference to it.

Riskiest task is **10**, the taxonomy and capability rename: it is the only one driving
store commands rather than editing files, the only one whose failure mode is a command
that reports success while leaving `check` red, and the only one with no test coverage
to catch a mistake. It is placed after every skill rename, so the names it writes are
already final, and it is alone in its commit.

---

## What every rename task does

Tasks 2–9 share one shape. Each names its own files; this is the procedure they share,
written once so the tasks do not repeat it.

1. `git mv skills/<old> skills/<new>` (or `git mv agents/<old>.md agents/<new>.md`), so
   `references/` subtrees follow and history survives.
2. Set the frontmatter `name:` in the moved `SKILL.md` / agent file to the new
   directory or file basename.
3. Replace every occurrence of the old name in **live** files with the new one. The
   substitution is on the **full old name** (`tcw-work`, not `tcw-`), matched as a whole
   name so a longer name containing it is not caught — `tcw-work` must not rewrite
   `tcw-work-stage`, and `tcw-work-skill` is task 10's, not this one's.
4. Leave untouched: everything under `docs/changelogs/v*.md`,
   `docs/release-notes/v*.md`, `docs/plan/`, `docs/migration-guide-*.md`, and
   `docs/work/` outside this item's own folder (spec rule 7); the `DELETED_NAMES` tuple
   in `tests/test_skill_lifecycle_parity.py`, which records retired names on purpose;
   and every token in spec rule 6's table.
5. Run `python -m pytest` and `tcw validate`. Commit.

**The live files a rename typically reaches**, so none is forgotten: the fifteen
`SKILL.md` bodies and everything under `skills/*/references/`; `README.md`;
`docs/guide/work.md`; `docs/guide/taxonomy-and-capabilities.md`;
`docs/lifecycle/implementation.md`; `.codex-plugin/plugin.json`'s `longDescription`;
`tcw-config.yaml`; `evals/coverage.py`, `evals/evals.json`, `evals/grade.py`,
`evals/assets/gen_requirement.py`; `scripts/session_bootstrap.sh`;
`tcw/work/templates.py`; `tests/**`; `tests/cli/scenarios/11-scaffold-and-artifact-templates.md`;
and the bodies under `docs/capabilities/**`.

**One deliberate intermediate staleness.** A capability body at
`docs/capabilities/skills/tcw-work/description.md` is rewritten by step 3 while the
folder it sits in is still called `tcw-work` — the folder is task 10's to rename. No
test reads those bodies for skill names and `tcw capabilities check` validates refs
rather than prose, so the boundary stays green; it is called out here so a reviewer
reads it as sequencing rather than as a miss.

---

## Task 1 — Guard 8b: a name matches the thing it names

**Modifies** `tests/test_plugin_manifests.py`

1. Add `test_skill_frontmatter_name_matches_its_directory`, parametrized over the
   existing `sorted((REPO / "skills").glob("*/SKILL.md"))` used at `:130`, asserting
   the parsed frontmatter `name` equals `skill.parent.name`.
2. Add `test_agent_frontmatter_name_matches_its_file`, parametrized over
   `sorted((REPO / "agents").glob("*.md"))`, asserting frontmatter `name` equals
   `agent.stem`. Reuse the frontmatter parse already written at `:136-146` rather than
   writing a second one.
3. Write the docstrings to say what the gap was: `:131` checks `name` and `description`
   are *present*, never that `name` agrees with the path, which is what lets a
   directory rename land half-done.

**Proves** criterion 2 and the 8b half of criterion 4.

**Mutation check, before trusting it.** Temporarily set
`skills/documentation-sync/SKILL.md`'s `name:` to `documentation_sync`; confirm only
the new skill test fails and that the message names the file. Temporarily set
`agents/tcw-verifier.md`'s `name:` to `verifier`; confirm only the new agent test
fails. Revert both. Record in `outcome.md` what each failure said.

Green on the unrenamed tree — this is the whole point of its position.

---

## Task 2 — `tcw-work` → `work`

**Renames** `skills/tcw-work/` → `skills/work/`
**Modifies** `skills/work/SKILL.md` frontmatter, and every live file naming `tcw-work`

The largest of the renames — `tcw-work` is named in more live files than any other
name, including the seven stage documents and the `default/` set under
`skills/work/references/lifecycle/`, the five under
`skills/work/references/procedures/`, `tcw/work/templates.py:7`
(`skills/tcw-work/references/lifecycle/stage-*.md` in a docstring), and
`tests/test_skill_lifecycle_parity.py:26-27`, which hold `skills/tcw-work/SKILL.md`
and `skills/tcw-work/references` as module constants.

Per **What every rename task does**, with one extra care: match `tcw-work` as a whole
name. `tcw-work-stage` (task 3) and `tcw-work-skill` (task 10) both begin with it and
must not be rewritten here.

**Proves** part of criteria 1, 2, 8, 9, 12.

---

## Task 3 — `tcw-work-stage` → `work-stage`

**Renames** `skills/tcw-work-stage/` → `skills/work-stage/`
**Modifies** its frontmatter, and every live file naming `tcw-work-stage`

Reaches `tests/test_skill_lifecycle_parity.py:315` (`STAGE_SKILL`), `:352`, `:422`;
`evals/coverage.py:53` (a `PARTIAL` key); `evals/evals.json`, where eight cases carry
`"invokes": "tcw-work-stage"`; and `evals/assets/gen_requirement.py:35`.

Separate from task 2 because the whole-name rule makes them independent, and because
`PARTIAL`'s key is a different kind of reference from a path constant.

**Proves** part of criteria 1, 2, 8, 9, 12, 13, 14.

---

## Task 4 — `tcw-capabilities` → `capabilities`, `tcw-taxonomy` → `taxonomy`

**Renames** `skills/tcw-capabilities/` → `skills/capabilities/`,
`skills/tcw-taxonomy/` → `skills/taxonomy/`
**Modifies** both frontmatters, and every live file naming either

The two remaining axis-driver skills, together because they cross-reference each other
in their own `SKILL.md` headers ("The taxonomy axis is tcw-taxonomy, the work axis is
tcw-work") and in `README.md`'s skill table. Reaches
`tests/test_skill_lifecycle_parity.py:487-492`, which reads
`skills/tcw-taxonomy/SKILL.md` and asserts what its description must not say, and
`tests/test_skill_flow.py`, whose module docstring names both.

**Proves** part of criteria 1, 2, 8, 9, 12.

---

## Task 5 — `tcw-setup` → `setup`, `tcw-configure` → `configure`

**Renames** `skills/tcw-setup/` → `skills/setup/`,
`skills/tcw-configure/` → `skills/configure/`
**Modifies** both frontmatters, `tcw-config.yaml:40`, and every live file naming either

These two move together because two guards bind them as a pair:
`tests/test_skill_lifecycle_parity.py:433`'s
`ROUTING_SKILLS = {"tcw-configure": "tcw-setup", "tcw-setup": "tcw-configure"}`, which
asserts each routes to the other and nothing else, and
`tests/test_skill_path_pointers.py:17`, parametrized over both. Renaming one alone
leaves a guard asserting a route to a directory that no longer exists.

This is the one task that changes **configuration rather than prose**:
`tcw-config.yaml:40` reads `path: skills/tcw-configure/references/<document>.md` and
becomes `path: skills/configure/references/<document>.md`. The same file's
`Skill-Driven-Component` description (`:31-39`) names `tcw-work`, `tcw-capabilities`
and `tcw-configure` in prose; task 2 and task 4 will already have taken the first two,
so take `tcw-configure` here. Also reaches `scripts/session_bootstrap.sh:9` and `:45`,
which name the `tcw-setup` skill (and must leave `tcw-cli` on `:50`, `:60`, `:102`,
`:108` alone), and `evals/coverage.py:58` and `:61` (`PARTIAL` keys for both).

Run `tcw validate` explicitly after this task: it is the only one that edits
`tcw-config.yaml`'s structure rather than its prose.

**Proves** part of criteria 1, 2, 7, 8, 9, 12, 13, and the `tcw-config.yaml` half of 15.

---

## Task 6 — `tcw-post-mortem` → `post-mortem` (the skill)

**Renames** `skills/tcw-post-mortem/` → `skills/post-mortem/`
**Modifies** its frontmatter, and every live file naming `tcw-post-mortem`

Alone, and before task 9, because `tcw-post-mortem` is the name of **both** a skill and
an agent. Until task 9 runs, `agents/tcw-post-mortem.md` still declares
`name: tcw-post-mortem`, so the two are briefly distinguishable and the substitution in
this task must not touch the agent file or the references that mean the agent —
`README.md:624` describes the agent, not the skill. `evals/evals.json:373` names
`tcw-post-mortem` in a case `note` discussing which skill is in play; that is the
skill, and it changes.

**Proves** part of criteria 1, 2, 8, 9, 12, 14.

---

## Task 7 — the four `tcw-commands-*` skills

**Renames** `skills/tcw-commands-plan-work/` → `skills/commands-plan-work/`,
`skills/tcw-commands-drive-work-to-completion/` → `skills/commands-drive-work-to-completion/`,
`skills/tcw-commands-verify-work/` → `skills/commands-verify-work/`,
`skills/tcw-commands-process-inbox/` → `skills/commands-process-inbox/`
**Modifies** the four frontmatters, and every live file naming any of them

One task because `evals/coverage.py:40-45` builds all four `EXCLUSIONS` keys from a
single comprehension over a tuple of the four names — splitting them would edit that
one expression four times. `README.md:588`, `:626-627` and `.codex-plugin/plugin.json`
enumerate all four together for the same reason.

**Proves** part of criteria 1, 2, 8, 9, 12, 13.

---

## Task 8 — the three `tcw-extras-*` skills

**Renames** `skills/tcw-extras-autonomous-work/` → `skills/extras-autonomous-work/`,
`skills/tcw-extras-triage-issues/` → `skills/extras-triage-issues/`,
`skills/tcw-extras-report/` → `skills/extras-report/`
**Modifies** the three frontmatters, and every live file naming any of them

One task for the same reason as task 7: `README.md:601`, `:605-607` and `:627-629`
present them as one family, and `evals/coverage.py:35` holds the
`tcw-extras-autonomous-work` exclusion beside them.

Care: `DELETED_NAMES` already contains the bare `autonomous-work`, and its whole-name
matching means `extras-autonomous-work` does not trip it (the character before
`autonomous-work` is `-`). Do not "fix" that entry.

**Proves** part of criteria 1, 2, 8, 9, 12, 13.

---

## Task 9 — the three agents

**Renames** `agents/tcw-backlog-auditor.md` → `agents/backlog-auditor.md`,
`agents/tcw-verifier.md` → `agents/verifier.md`,
`agents/tcw-post-mortem.md` → `agents/post-mortem.md`
**Modifies** the three frontmatters, and every live file naming any of them —
principally `README.md:624` and the skills that dispatch to them
(`skills/work/references/procedures/delegation.md`,
`skills/work/references/procedures/audit-backlog.md`, `skills/post-mortem/SKILL.md`,
`skills/commands-verify-work/SKILL.md`)

No manifest lists them: `.claude-plugin/plugin.json` carries no `agents` key and Claude
auto-loads the directory, which `tests/test_plugin_manifests.py`'s
`test_claude_agents_key_is_md_files_not_a_directory` records. Confirm that test still
passes rather than assuming it.

After this task no `tcw:tcw-…` address exists anywhere in the plugin.

**Proves** criterion 3, part of 8 and 9.

---

## Task 10 — the taxonomy Features and the capability entries

**Creates** `docs/taxonomy/<new>-skill/` ×14, `docs/capabilities/skills/<new>/` ×14
**Removes** `docs/taxonomy/tcw-*-skill/` ×14, `docs/capabilities/skills/tcw-*/` ×14
**Modifies** nothing by hand that a command can write

Driven entirely through `tcw taxonomy` and `tcw capabilities`. Three passes, in this
order — the order is what keeps `check` green, because a Feature removed while a
capability still points at it leaves `tcw taxonomy check` failing after a command that
reported success.

**Pass A — add the 14 new Features.** For each old Feature under `docs/taxonomy/`:

```
tcw taxonomy add "<display name from old meta.yaml>" --kind feature \
    -s <old-slug minus tcw-> [--vocab <ref> ...one per entry in the old vocabulary list] \
    < docs/taxonomy/<old-slug>/description.md
```

The display `name` is carried over **unchanged** — `TCW Work Skill` stays
`TCW Work Skill` — matching `documentation-sync-skill`, which already pairs a `TCW …`
display name with an unprefixed slug. Then copy `relatesTo` from the old `meta.yaml`
into the new one by hand (e.g. `work-skill` keeps `relatesTo: [work-inbox]`); the
`tcw-taxonomy` skill names hand-editing `relatesTo` as the route for that field, since
no command writes it. Run `tcw taxonomy check` at the end of the pass.

**Pass B — move the 14 capabilities.** For each, in this order:

```
tcw capabilities add skills/<new> "<name from old meta.yaml>"
# copy the old description.md body across, and rewrite the skill names it quotes
tcw capabilities set skills/<new> --status Supported \
    --field Feature=<new>-skill --field Subject=skill \
    --field "Planning doc=<value from old meta.yaml>"
tcw capabilities rm skills/<old>
```

Metadata goes through `set` and deletion through `rm` — `skills/capabilities/SKILL.md`
forbids hand-editing either. The `description.md` body has no command that writes it,
so it is authored directly; that is the one file here edited by hand, and the
prohibition does not cover it. `skills/documentation-sync` is not touched.
Run `tcw capabilities check` at the end of the pass.

**Pass C — remove the 14 old Features.** `tcw taxonomy rm <old-slug>` each, then
`tcw taxonomy check`. Run `check` after **each** removal, not once at the end:
`tcw taxonomy rm` only warns on a dangling `relatesTo`
(`docs/work/inbox/tcw-taxonomy-rm-deletes-nested-terms-without-a-word.md`), so running
it per removal is what makes a mistake attributable to the command that caused it. All
14 are flat top-level entries, verified with `find docs/taxonomy -maxdepth 2 -type d`,
so the same command's silent nested-delete cannot bite.

**Proves** criteria 5, 6, 7, and the ledger half of the Capability changes section.

**Verification the suite cannot do.** No test asserts the content of the taxonomy or
the ledger, so this task is checked by command output and by eye:
`tcw taxonomy list | grep -- -skill` shows 15 entries, none prefixed;
`tcw capabilities list | grep '^\[Supported\]\s*skills/'` shows 15, none prefixed; and
`tcw capabilities show skills/work` reproduces the old entry's name, status, subject
and planning-doc value with a `Feature: work-skill`. Diff the old and new
`description.md` for one entry to confirm nothing but the skill names changed.

---

## Task 11 — Guards 8a and 8c: the old names are gone and cannot return

**Modifies** `tests/test_skill_lifecycle_parity.py`, `tests/test_plugin_manifests.py`

**8a.** Append the 17 old names to `DELETED_NAMES` (`:503`) — `tcw-work`,
`tcw-work-stage`, `tcw-capabilities`, `tcw-taxonomy`, `tcw-setup`, `tcw-configure`,
`tcw-post-mortem`, the four `tcw-commands-*`, the three `tcw-extras-*`, and
`tcw-backlog-auditor`, `tcw-verifier` (the agents; `tcw-post-mortem` covers both, and
is listed once). Extend `LIVE_ROUTES` (`:514`) with `"agents"` and `"tcw-config.yaml"`.
Checked already: neither carries an existing `DELETED_NAMES` entry, so widening the
routes introduces no pre-existing failure. Leave `evals/` and `tests/` out — both
legitimately quote retired names, this tuple among them.

**8c.** Add `test_no_shipped_name_repeats_the_plugin_id` to
`tests/test_plugin_manifests.py`: read `name` from `.claude-plugin/plugin.json` rather
than hardcoding `"tcw"`, then assert no `skills/*/SKILL.md` directory name and no
`agents/*.md` stem starts with `f"{plugin_id}-"`. Stated as the general rule so it
survives a plugin rename and refuses the prefix creeping back one skill at a time.

Both land here rather than earlier because both are **false until tasks 2–9 are done**.

**Proves** criteria 9 and the 8a/8c halves of 4.

**Mutation checks.** For 8a, temporarily reintroduce `tcw-work` into `README.md` and
confirm the failure names both the token and the file; separately reintroduce it into
`tcw-config.yaml` and confirm the widened `LIVE_ROUTES` is what catches it. For 8c,
temporarily `git mv skills/work skills/tcw-work` (frontmatter with it, so 8b stays
green and only 8c speaks) and confirm the failure names the skill. Revert each, and
record what each failure said in `outcome.md`.

Then run the two checks the suite does not cover:
`python -m evals.run_evals --axis a --dry-run` resolves every arm with no unresolved
skill name (criterion 14), and a one-time grep for the 17 old names across the tree —
excluding the rule-7 paths and the `DELETED_NAMES` tuple itself — returns nothing
(the grep half of criterion 9).

---

## Task 12 — Confirm the exclusions held

**Modifies** nothing

A verification task with no edits, run on the finished tree before documentation.
Re-measure every token in spec rule 6's table the way the spec measured it — whole-word,
excluding `.git/`, `eval-runs/`, `tcw_cli.egg-info/` and `work/` — and confirm each
count is unchanged: `tcw-config` 441, `tcw-cli` 95, `tcw-unhosted` 14, `tcw-inert` 11,
`tcw-event` 9, `tcw-project-badge` 8, `tcw-sr-only` 5, `tcw-ref` 4,
`tcw-sidecar-token` 3, `tcw-serve` 3, `tcw-storage-folders` 2. Then confirm
`git diff --stat` against the pre-change tree touches nothing under
`docs/changelogs/v*.md`, `docs/release-notes/v*.md`, `docs/plan/`,
`docs/migration-guide-0.21.X-to-1.0.0.md`, or `docs/work/` outside this item's folder.

A mismatch here means a substitution was applied by prefix rather than by name, and is
a defect to fix, not a count to update.

**Proves** criteria 10 and 11.

---

## Task 13 — Documentation Sync

**Modifies** `README.md`, `docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`,
`skills/*/SKILL.md`, `skills/configure/references/<document>.md`

One pass over the finished diff, evaluating each of this project's five documentation
entries. All five fire.

- **`README.md` — Public-API.** Already rewritten name-by-name by tasks 2–9; this pass
  re-reads `:587-629` whole, since the skill table, the "three axis drivers / four
  `tcw-commands-*` / three `tcw-extras-*`" sentence at `:587-589`, the extras table and
  the agents paragraph at `:624-629` were each edited by a different task and want to
  read as one voice. Check the prose that *describes* the families still says
  `commands-*` and `extras-*` correctly now the `tcw-` is gone.
- **`docs/release-notes/upcoming.md` — Public-API.** The breaking change, in plain
  language: what the names were, what they are, and that the old ones stop resolving.
  Give the full old → new mapping for all 17 (criterion 16) — this is the only place a
  user whose muscle memory has stopped working will look. Mention that projects naming
  TCW skills in their own `AGENTS.md` prose will want to update it, and that nothing in
  a `tcw-config.yaml` breaks, since no lifecycle `skill:` binding named one.
- **`docs/changelogs/upcoming.md` — Any-Code-Change.** Technical, grouped. *Changed*:
  the 14 skill names, the 3 agent names, the 14 taxonomy Feature slugs, the 14
  capability paths, and `tcw-config.yaml`'s `Configuration-Key-Change` entry path.
  *Added*: the three guards. Name the regenerated capability ids as a consequence.
- **`skills/<component>/SKILL.md` — Skill-Driven-Component.** No component's CLI
  surface, model, lifecycle or guardrails changed, so no skill needs new *content*.
  What this pass checks is that the bodies tasks 2–9 rewrote still route correctly to
  each other by their new names — every `REQUIRED SUB-SKILL:` line, every
  `references/` pointer, and the cross-axis headers in
  `skills/work/SKILL.md`, `skills/capabilities/SKILL.md` and `skills/taxonomy/SKILL.md`.
- **`skills/configure/references/<document>.md` — Configuration-Key-Change.** Fires
  because `tcw-config.yaml`'s documentation-entry `path` value changed in task 5.
  Update the document that explains documentation entries so its worked example matches
  what this repository now declares, and check the other `references/` documents for
  examples quoting a `skills/tcw-…` path.

Then `tcw work docs 2026-09-15-drop-the-tcw-prefix-from-the-plugin-s-skill-and-agent-names`
and confirm every trigger is addressed (criterion 15).

**Proves** criteria 15 and 16.

---

## Verification

What the suite cannot check, gathered so none of it is left to the end:

- **The three mutation checks** (tasks 1 and 11). pytest can prove an assertion passes;
  only breaking what it observes proves it would have caught the thing it claims to.
  Each is reverted immediately and its failure text recorded in `outcome.md`.
- **The taxonomy and ledger end state** (task 10). No test reads either store's
  contents, so `tcw taxonomy list`, `tcw capabilities list`, `tcw capabilities show`
  and `tcw ... check` are the whole verification, plus a by-eye diff of one migrated
  `description.md`.
- **The eval harness** (task 11). `python -m evals.run_evals --axis a --dry-run`
  resolves every arm and spawns nothing. A missed name in `evals/evals.json` would
  otherwise surface as a skill that "was not invoked" in a **paid** run, which reads
  exactly like a genuine finding. No graded run is needed or planned here.
- **The exclusion counts and the untouched history** (task 12).
- **What cannot be verified in this repository at all:** that Claude and Codex resolve
  the renamed skills. Both read `SKILL.md` frontmatter and the directory name, and both
  are changed together, but nothing here exercises either host. The first real check is
  invoking `/tcw:work` in a session with the local plugin loaded
  (`--plugin-dir /home/user/TCW`, as `evals/run_evals.py` does); say so at verification
  rather than implying the suite covered it.

## Notes

- **Follow-up to file at completion, per the spec's Notes:** `tcw capabilities mv` /
  `tcw taxonomy mv`. Task 10 is the second time a rename has had to be done as
  `add` + `rm`, and it is the only task in this plan with no test coverage and a
  by-hand body copy. A rename verb passes the abstraction litmus test — re-keying an
  entry is something a tracker-backed store can do — and would have made task 10 two
  loops of one command. Not folded in: it changes the CLI surface and needs its own
  spec.
- **Version cut.** This is a breaking change to every skill entry point. Per
  `AGENTS.md`, write the `upcoming.md` entries (task 13) *before* any
  `scripts/cut_version.py` run, and batch the cut across a run of items rather than
  cutting for this one alone — that decision is the user's at closeout, not this plan's.
- **Not a blocker, but adjacent:** the three subagents have no capability in the ledger
  (`tcw capabilities list` returns nothing for them), so task 9 renames something the
  ledger never described. Recorded as a pre-existing gap in the spec's Non-goals; this
  plan does not close it.
