# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Removed — the post-completion version offer

- **`tcw/work/prompts/verify.md`** — step 9 ("After `complete`, **offer** a
  version cut…") deleted. The stage now ends at step 8, the post-mortem offer.
  `tests/fixtures/prompt_fallback/unconfigured.json` re-baselined for the
  `verify` entry only; every other stage's recorded stdout is byte-identical.
- **`skills/work/references/lifecycle/stage-verify.md`** — item 5, the option
  menu and its routing to the `documentation-sync` procedure, deleted. Nothing
  renumbers; it was the last item.
- **`DEFAULT_DOD`** (`tcw/store/base.py`) — `"version offered"` dropped; the
  tuple is now four items. The adjacent comment about tuple order driving the
  stage-letter string belongs to `WORK_ARTIFACTS`, not to this tuple, so
  `tcw work list` output is unaffected. Mirrored in
  `web/client/src/ui/content-views.tsx` (the completion dialog's fallback
  checklist), `tests/test_serve_write.py`, and this repo's `docs/work/dod.yaml`.
- **`skills/documentation-sync/SKILL.md`** — the `After complete` lifecycle row
  removed; the table is two rows and the skill is described as invoked at two
  lifecycle points, not three.

## Changed — a version cut is now only ever user-initiated

- **`tcw/work/procedures/documentation-sync.md`** — `## When to offer version
  and changelog options` replaced by `## When the user asks to cut a version`.
  The four-option menu and every instruction to present it are gone. Retained,
  re-framed: the `unpushed-version.sh` gate with unchanged exit codes (`0`
  foldable · `1` not · `2` remote unreachable), the fold-vs-fresh-bump judgment,
  the bar on rewriting a published tag, and the deferral to the project's own
  version-cut process before the manual ritual. Changelog upkeep is stated as
  the end-of-`implement` documentation gate's job, not a version cut's.
- **`tcw work docs` rationale** (`tcw/work/cli.py`,
  `skills/work/references/commands.md`) — rewritten rather than trimmed. The
  verb was justified by the gate's third, non-stage invocation point; that point
  is gone but the verb is still the read-only accessor the `documentation-sync`
  skill calls before any stage prompt resolves and the web app reads.
- **`skills/documentation-sync/references/cut-version.md`** and
  **`scripts/unpushed-version.sh`** — cross-references repointed at the renamed
  section; the script's behavior and exit codes are unchanged.
- **`tcw/work/procedures/unattended-work.md`** — the `Version choice` row
  reworded to `Version cut`: not the run's to make, since nobody is present to
  ask. The `upcoming.md` accumulation instruction is kept; it appears nowhere
  else in that table.
- Docs: `README.md`, `docs/guide/work.md` (both DoD listings and the
  "those five are the defaults" prose), `skills/work/references/transitions.md`,
  `skills/configure/references/work.md`,
  `skills/commands-drive-work-to-completion/SKILL.md`, and four capability
  descriptions under `docs/capabilities/`.

## Added

- **`work.tracker.inbox-query`** — optional JQL, `TrackerConfig.inbox_query`
  (`""` when absent; blank or non-string is a problem and fails the block closed).
  In `TRACKER_KEYS`; inherits through `merge_tracker_blocks` unchanged.
- **`tcw work inbox list` tracker section** — with `inbox-query` set, output is
  `raw intake:` then `tracker tickets:` (`  KEY | status | assignee | summary`,
  `  (none)`); on `TrackerError` raw intake still prints, `  (not listed)`, exit 1.
  Without it, output is byte-identical to before; a tracker block with problems adds
  one stderr line. The search is `JiraClient.search(inbox_query)`, in the CLI —
  `WorkStore.inbox_list` is unchanged.
- **`inbox show|accept --ticket`**, and **`inbox accept --part`** (refused, consuming
  nothing, when the ref resolves to a raw entry). A lone `inbox-query: null` is
  reported as `expected a non-empty string, got NoneType`.
- **`InboxEntryNotFound(ValueError)`** in `tcw/store/base.py`, raised by
  `FsWorkStore` for no such inbox entry; ambiguity stays a plain `ValueError`.

- **Procedures** — non-stage instruction text a project may replace.
  `PROCEDURE_IDS` (`tcw/store/base.py`): `unattended-work`, `triage-issues`,
  `documentation-sync`, `post-mortem`, `create-work`, `audit-backlog`,
  `consolidate-plans`, `decompose`, `delegation`, `search`. Defaults ship as
  `tcw/work/procedures/<id>.md` (package data), verbatim copies of the matching
  skill body or `skills/work/references/procedures/*.md`;
  `tests/test_shipped_procedures.py` fails if a copy and its source diverge.
  `load_builtins()` returns them as `Builtins.procedures`, refusing a missing or
  empty file like a stage prompt (shared `_load_texts`).
- **`work.procedures`** config: `parse_procedures()` (pure), one plain binding
  list per id with `PROMPT_KINDS`, parsed by `_parse_binding_list` with role
  `procedure`; an empty list is refused. `LifecyclePolicy.procedures` /
  `.procedure(id)`, filled by `FsWorkStore.lifecycle_policy()`; problems and
  `file:` checks reported through `lifecycle_problems()`.
- **`resolve_procedure()`** (`tcw/work/resolve.py`): the `builtin` floor and
  composition of `resolve_prompts`; `generate:` hooks see role `procedure`.
- **`tcw work procedure prompt <id> [ref] [--no-exec]`**: no bookend, no status
  note, no harness check. When every binding was skipped by its `when:`, a note
  goes to stderr (exit 0, empty stdout).

- `test_skill_frontmatter_name_matches_its_directory` and
  `test_agent_frontmatter_name_matches_its_file`
  (`tests/test_plugin_manifests.py`) assert a declared `name` equals the
  directory or file it sits in. The existing frontmatter test checked only that
  `name` was _present_, so a directory rename that left its frontmatter behind
  passed the whole suite.
- `test_no_shipped_name_repeats_the_plugin_id` asserts no skill directory or
  agent stem begins with the plugin id plus `-`, reading the id from
  `.claude-plugin/plugin.json` rather than hardcoding it, so the rule survives a
  plugin rename and refuses the prefix returning one skill at a time.
- `DELETED_NAMES` (`tests/test_skill_lifecycle_parity.py`) gains the 17 distinct
  old names, and `LIVE_ROUTES` gains `agents`, `.agents`, `hooks`, `scripts`,
  `tcw`, `evals` and `tcw-config.yaml` — every surface that ships or runs and can
  name a skill, none previously in the guard's reach.
- `work.tracker.transitions` accepts `submit`, `rework`, `complete` and `discard`
  alongside `claim`, naming the transition each move applies. `discard` takes one
  name or one per discard resolution, and may be partial. A named transition that
  the ticket does not offer, that matches more than one offered transition, or that
  leads to a status other than the mapped one is refused before anything is sent.
  Validation is shape-only, as for `statuses`.
- `tcw work tracker link --sync-status`: for an item past `backlog`, records a
  `pending`/`claim: owed` sync record and delivers it at once — the claim, then one
  transition straight to the item's mapped status when offered, otherwise one per
  mapped status, re-reading between hops, and writes `catch-up: true` on the binding.
  Forward-only: no claim transition is applied to a ticket already past `active`
  (one assigned to the caller carries on from where it is — refused if resolved, and
  under strict mode, when it is on the `active` status itself, only if the claim would
  be exclusive; any other is refused), a
  ticket past its item is refused, and a resolved ticket is never moved. Refused for
  an item somebody else started. What does not arrive stays recorded for `tracker
  sync`, which resumes a walk the claim finished but a later hop did not, and aims at
  the item's current status rather than the recorded move's. Only a `catch-up`
  binding is walked through more than one status; every other delivery, including
  an owed claim from a failed `start`, is followed by one transition as before.
- A shared rung in the ladder (two local statuses mapped to one tracker status) is
  named for the higher local status, so its hop uses that move's named transition.
- A plain `link` of an item past `backlog` changes nothing in the tracker. When the
  ticket's status differs from the item's mapped one, it warns and writes
  `status-synced: false` on the binding (not part of `--json`). While that note
  stands, a move refused only because the ticket's status is out of its window is
  `held` with the `--sync-status` repair instead of `conflicting`, and records
  nothing; another holder, an unclaimed ticket whose status is in step, and
  transition-name refusals stay `conflicting`. Strict mode's refusal names the same
  repair. The note clears once a delivery — or a checking `sync` — finds the ticket
  where its item says.
- **`tcw work stage validate [words…]`** (`tcw/work/cli.py`): reports whether a
  `work-stage` invocation's arguments are ones `tcw work stage prompt` would
  accept — a known stage id, no item for `inbox`, otherwise an optional
  reference resolving to exactly one item; status is not judged. Valid: no
  output, exit 0. Invalid: a Markdown usage error plus the reason on stdout,
  exit 1 (`_resolve`'s stderr message is captured into the reason). Under a
  harness other than Claude Code, a notice that injected commands must be run
  by hand is printed first, even when valid.
- **`tcw/harness.py`**: `ancestor_programs()` walks the process's ancestors via
  `ps`, falling back to `/proc`, and never raises; `detect()` returns the
  nearest `claude`/`codex` ancestor's harness, else `other` when
  `CODEX_THREAD_ID`, `CODEX_SANDBOX` or `CODEX_SESSION_ID` is set, else
  `claude`.
- **`skills/README.md`**: the two rules deciding whether a project may replace
  what a shipped skill says — Rule 2 (a document with no procedure of its own
  has nothing to override), checked first, then Rule 1 (TCW owns the shape of
  what is produced, the project owns the conduct) — why a project cannot add a
  procedure id of its own, and a verdict with a reason for every `SKILL.md`,
  every file under a skill's `references/`, and every `agents/*.md`.
- **`dynamic_skill: true|false`** in the frontmatter of all sixteen
  `skills/*/SKILL.md`, as a top-level key with a trailing comment pointing at
  `../README.md`. Read by people only; neither harness acts on it. `true` for
  `extras-autonomous-work`, `extras-triage-issues`,
  `documentation-sync`, `post-mortem`, `work-create` and
  `work-stage`; `false` for the rest. No skill body changed.
- **`tests/test_dynamic_skill_marker.py`**: fails when a shipped skill,
  reference document or agent has no verdict row (or more than one), when a row
  names no shipped file, when a skill lacks `dynamic_skill` or its comment, or
  when the value disagrees with the row's verdict.
- **`tcw work edit --type {epic,""}`** and a `type` keyword on
  `WorkStore.update_work`. `WorkStore.check_type_change(item, new_type)`
  (`tcw/store/base.py`) validates against `WORK_TYPES` and refuses `epic` → `""`
  while `initiative_children()` is non-empty (any status) or
  `incomplete_graph_note()` is non-empty. `_edit` runs it before the blocker
  writes, so a refused type change writes nothing; under `tracker_strict()` any
  `--type` is refused via `_strict_says_no`. The web app's field whitelist still
  excludes `type`. New `tests/test_edit_type.py`; strict case in
  `tests/test_tracker_strict.py`.

- **`tcw work tracker claim <slug> [--take-over]`** and **`release <slug>
  [--force]`** — ownership as its own operation. Sets/clears `WorkItem.owner` via
  `WorkStore.set_field` and assigns/unassigns the bound ticket. No transition and
  no status change on either side. The local half is guarded before it is written
  (an unbound item, or one whose ticket is unassigned, has no assignee to check)
  and written last, so a failed tracker half never leaves the two disagreeing; the
  write is committed, as `start --take-over` commits its own.

- **`tcw/tracker/ownership.py`** — `assert_ownership(client, ticket, *, assertion,
  take_over)` and `drop_ownership(client, ticket, *, force)`, returning
  `OwnershipOutcome`. Exclusivity is assign-then-read-back; `intake.claim` is
  untouched and unused here, because it reads the transition name from
  `config.claim_transition` directly and can only ever apply the start transition.
  The read-back distinguishes three answers, not two: the caller holds it, another
  account holds it, or nobody does — the last reports that the ticket was
  unassigned mid-claim rather than naming a holder who does not exist.

- **`work.tracker.exclusive-claim-transition`** — optional top-level key,
  `TrackerConfig.exclusive_claim_transition` (`""` when absent; present-but-blank
  or non-string is a problem and fails the block closed). In `TRACKER_KEYS`;
  inherits through `merge_tracker_blocks` unchanged. Applied before the assignment
  when set, which moves the ticket.

## Changed

- **`complete` refuses a `--worktree` item whose folder in the worktree holds
  uncommitted changes**, before the merge-back, since the merge carries only commits and
  the judgments above read working files. `uncommitted_paths` (`tcw/store/fs.py`) reads
  `git status --porcelain -z --untracked-files=all`, includes untracked entries (unlike
  `_has_committable_changes`) and consumes a rename's source record. Not skipped by
  `--force`, which overrides whether shipping is allowed rather than what it carries, and
  it therefore precedes the Definition-of-Done checklist. An external `work.path` store is
  exempt: both checkouts share it, detected by comparing the two stores' resolved roots. A
  staged `tracker.yaml` gets a second line naming `tcw work tracker sync` *after*
  committing, because a sync with nothing owed writes nothing and leaves the file staged.

- **Inbox ref resolution**: `inbox show`/`accept` ask the store first and, only on
  `InboxEntryNotFound` with `inbox-query` declared, read the ref as a ticket
  (`_inbox_can_try_ticket`). A ref that is neither names both (`_not_a_ticket`).
  `inbox accept <ticket>` calls `_tracker_import(..., label="inbox accept",
  not_found=...)`, which makes no extra ticket read; `_tracker_client`, `_print_refusal`
  and `_tracker_import` now take the full verb as their label. `_ticket_row` and
  `_print_ticket` are shared with `tracker list`/`show`, whose output is unchanged.
- **Strict mode**: `inbox accept` is refused for a raw entry only; a ticket goes
  through `tracker import`'s own strict claim check.

- `resolve_prompts` delegates to a private `_compose()` shared with
  `resolve_procedure`; stage resolution is unchanged.
- **Every shipped skill and agent name drops the `tcw-` prefix.** The plugin id
  already qualifies a skill at the point of use (`/tcw:<skill>` under Claude,
  `$tcw:<skill>` under Codex), so the prefix was a second copy of information the
  namespace had already supplied. Breaking: the old names do not resolve, and
  neither harness has a skill-alias mechanism to soften it.
    - 15 skill directories under `skills/`, each with its `SKILL.md` frontmatter
      `name`: `tcw-work` → `work`, `tcw-work-stage` → `work-stage`,
      `tcw-work-create` → `work-create`, `tcw-capabilities` → `capabilities`,
      `tcw-taxonomy` → `taxonomy`, `tcw-setup` → `setup`, `tcw-configure` →
      `configure`, `tcw-post-mortem` → `post-mortem`, the four `tcw-commands-*`
      and the three `tcw-extras-*` to `commands-*` and `extras-*`.
      `documentation-sync` is unchanged; it never carried the prefix.
    - 3 agent files under `agents/`, each with its frontmatter `name`:
      `tcw-backlog-auditor` → `backlog-auditor`, `tcw-verifier` → `verifier`,
      `tcw-post-mortem` → `post-mortem`. No manifest lists them — the Claude
      manifest carries no `agents` key and the directory is auto-loaded — so only
      the files and their references changed.
- **15 taxonomy Feature slugs** lose the prefix (`tcw-work-skill` → `work-skill`,
  …). Display names are deliberately untouched: `TCW Work Skill` stays, matching
  `documentation-sync-skill`, which already paired a `TCW …` display name with an
  unprefixed slug. `relatesTo` and `vocabulary` are carried over verbatim, with
  `work-create-skill`'s reference to `work-skill` re-pointed.
- **15 capability paths** under `docs/capabilities/skills/` lose the prefix, each
  keeping its name, `Status`, `Subject`, `Planning doc` and body, and pointing at
  its renamed `Feature`.
- `tcw-config.yaml`'s `Configuration-Key-Change` documentation entry path is now
  `skills/configure/references/<document>.md`. This is the only place the rename
  changed configuration rather than prose.
- Live references followed throughout: the 16 `SKILL.md` bodies and everything
  under `skills/*/references/`, `README.md`, `docs/guide/`, `docs/lifecycle/`,
  `.codex-plugin/plugin.json`'s `longDescription` (which now also backticks
  every skill name), `evals/` (`coverage.py`'s
  `EXCLUSIONS`/`PARTIAL` keys, `evals.json`, `grade.py`, `assets/gen_requirement.py`),
  `scripts/session_bootstrap.sh`, `tcw/work/templates.py`'s docstring, and `tests/`.
  Where a bare new name would read as an ordinary word — `work`, `setup`,
  `capabilities` in a skill `description`, `when_to_use` or a
  `REQUIRED SUB-SKILL` line — it is written as "the `<name>` skill".
- `skills/work-stage/SKILL.md` injects
  `` tcw work stage validate -- $stage $item 2>/dev/null || true `` ahead of its
  heading. `2>/dev/null` keeps an older `tcw` without the verb silent; named
  arguments rather than `$ARGUMENTS`, because extra words reaching the shell
  unquoted could make the line exit non-zero and cancel the skill load.
- `skills/work/SKILL.md` and `references/commands.md` no longer link or name
  the `references/lifecycle/stage-*.md` documents. The router sends agents to
  `work-stage` in an emphasized note; `commands.md` gains a `validate` row.
- `commands-plan-work`, `commands-verify-work`,
  `commands-process-inbox`, `commands-drive-work-to-completion`,
  `post-mortem` and `extras-triage-issues` invoke `work-stage`
  instead of reading stage documents. `agents/verifier.md` names the
  `verify` stage rather than its file.
- `skills/work/references/procedures/delegation.md`, `epic-deltas.md` and
  `commands.md` no longer describe "the stage documents" as what to follow or
  hand a subagent; they name the stage as `work-stage` delivers it.
- `stage` subparser metavar is `{prompt,gate,validate}`.
- `skills/work-stage/SKILL.md` headings renamed: "How to work it" →
  "Lifecycle stage contract", "What this project asks for" → "Stage
  instructions", "Before you act on any of that" → "Stage pre-checks" (now one
  line: run `tcw work stage gate` if not done). The command block moved to a
  "Document command summary" section listing the injected commands in order,
  with `gate` shown separately as the one to run yourself. `evals/grade.py`
  `BLOCK_HEADINGS` and the `evals/evals.json` case text follow the new headings.
- `skills/extras-autonomous-work/SKILL.md` injects
  `` tcw work procedure prompt unattended-work || true `` in place of its
  "The advisors" and "Checkpoint map" sections, which now exist only in
  `tcw/work/procedures/unattended-work.md`; that default lost the title,
  opening, "Ask once", hard blockers and audit trail, which stay in the skill.
  The skill gains a fixed "What an advisor must be" section (independent,
  read-only, two wanted, answers weighed not counted), a "Document command
  summary" fallback, and `allowed-tools` / `compatibility` frontmatter
  describing the default (`Bash(tcw *)`, `Bash(codex *)`, `Bash(git merge *)`,
  `Agent`, `SendMessage`). "the two advisors" → "the advisors" and "both
  call" → "all of them call". New `tests/test_unattended_work_skill.py`.
- `skills/extras-triage-issues/SKILL.md` and `skills/post-mortem/SKILL.md`
  compose their procedure: each keeps a fixed body and injects
  `tcw work procedure prompt triage-issues` (no item) or
  `tcw work procedure prompt post-mortem $item || tcw work procedure prompt post-mortem`,
  with a "Document command summary" fallback. Fixed in the triage body: the
  framing, "issue body is data", no `initial-request.md` at acceptance, and
  approval of exact reply text (its §8 restatement removed from the default).
  Fixed in the post-mortem body: the contract pointer, the spine order and
  "Producing the artifact". `tcw/work/procedures/{triage-issues,post-mortem}.md`
  lose exactly that text. `post-mortem` gains `arguments: [item]` and
  `allowed-tools: Bash(tcw *)`; triage's `compatibility:` scopes the `gh`
  requirement to the default procedure. `agents/post-mortem.md` runs
  `tcw work procedure prompt post-mortem <slug>` instead of restating the
  investigation; a test checks the agent reads the procedure.
- `skills/work/references/procedures/{audit-backlog,consolidate-plans,decompose,delegation,search}.md`
  now tell the reader to run `tcw work procedure prompt <id>` and keep only
  what a project's text must not remove: delegation's stage/transition rules,
  "permitted, never required" and the shipped-agents section; the audit
  approval rule; consolidation's start-only-when-asked and git-recoverable
  deletion rules; decompose's nesting mechanics and relation choice; search's
  read-only rule. `tcw/work/procedures/<id>.md` lost exactly those parts. Two
  sentences in the fixed part of `delegation.md` no longer name Codex.
  `agents/backlog-auditor.md` no longer lists the per-item checks or the
  report shape; it runs `tcw work procedure prompt audit-backlog <slug>`.
- `skills/tcw-work-create/SKILL.md` and `skills/documentation-sync/SKILL.md`
  read their procedure from `tcw work procedure prompt create-work` /
  `documentation-sync` by injection, with a "Document command summary" fallback
  block. The skills keep only what a project may not replace: for
  `tcw-work-create`, the one-outcome paragraph and step 2 (the overlap search,
  moved above the injection); for `documentation-sync`, `tcw work docs --json`
  and its sources, the lifecycle-point table and the Markdown fallback entry
  form. `tcw/work/procedures/create-work.md` and `documentation-sync.md` lose
  exactly those parts. `documentation-sync` gains `allowed-tools: Bash(tcw *)`;
  its fallback block says to read TCW's default file only when the `tcw` CLI is
  not installed, and to report a failing command rather than read it. Its two
  `references/` are unchanged.
- `tcw work procedure prompt <id>` without a slug, outside a TCW node, prints
  TCW's shipped default and exits 0 instead of refusing with "no tcw work node
  here"; with a slug it still refuses. A node whose store is declared but not
  provisioned still refuses.
- `skills/tcw-work/references/lifecycle/stage-verify.md` reaches the version cut
  through `tcw work procedure prompt documentation-sync` instead of naming
  `documentation-sync`'s `references/cut-version.md` directly, so a project's
  replacement is followed.
- `skills/setup/references/install.md` gives the Codex install command,
  `bash "<plugin>/scripts/session_bootstrap.sh" "<plugin>"`, and says where `<plugin>`
  is and why the sentinel argument can be omitted. `skills/work-stage/SKILL.md` and
  `skills/documentation-sync/SKILL.md` define `<plugin>` in their manual fallbacks.
- Capability ledger: `work/run-a-lifecycle-stage` no longer describes the
  `work-stage` skill (moved to `skills/work-stage`); the issue-closing rules live
  only in `work/complete-a-work-item`, linked from `skills/extras-triage-issues`.
- **Behaviour change:** `FsTaxonomyStore.remove` refuses a term with any
  subdirectory under its folder, or one another local term's `relatesTo` or
  `vocabulary` resolves to (compared by folder identity, self-references ignored),
  and a local spelling not in `_local_slugs()`. It no longer cascades through
  `git rm -rf`. `relators()` and the CLI's post-removal warning are removed; its
  leaf-name match flagged unrelated terms. `TaxonomyStore.remove` documents the
  contract.

- **`JiraClient.assign`** takes `str | None`; `None` unassigns
  (`{"accountId": null}`). A project forbidding unassigned issues answers 400,
  surfacing as `TrackerRequestInvalid`, which `drop_ownership` reports rather than
  raises.

- **`_started_by_someone_else` → `_held_by_someone_else`** (`tcw/work/cli.py`),
  and its wording from "started by" to "held by" at all three call sites
  (`cli.py` guard, `sync --all` skip line, `tcw/tracker/sync.py` strict-mode hint):
  an item can now carry an owner while sitting in `backlog`, never started. The
  take-over remedy is a parameter rather than hardcoded to `start --take-over`.

## Fixed

- **`complete` judges a `--worktree` item from its branch's copy.** With the store
  inside the checkout the worktree holds its own copy, so `submit`, `rework`, blocker
  edits and tracker records made during the work are committed on the branch while the
  primary checkout's copy stays as `start` left it. `_complete` read that stale copy for
  every judgment it makes before `merge_worktree`. It now opens a second store —
  `_branch_copy` (`tcw/work/cli.py`) over `worktree_node_root` (`tcw/store/fs.py`), the
  node's own directory *inside* the worktree, not the worktree top, since `git worktree
  add` checks out the whole repository and `resolve_store` never searches upward — and
  uses it for the blocker check and the strict tracker refusal. `authorize` and
  `binding_refusal` (`tcw/tracker/sync.py`) and `_strict_refusal` take a keyword-only
  `own=` for the item's own binding, status and owner; `_siblings` and the tracker
  configuration still come from the primary store. Unreadable worktree (gone, not a
  store, malformed config on the branch, item absent) falls back to the primary copy
  with one line on stderr; `ValueError`, `OSError` and `MultipleMatch` are all caught,
  the last because it is not a `ValueError`.
- **The skipped-verify message now requires both copies to read `active`.** Either copy
  alone is wrong: `submit` inside the worktree leaves the primary at `active`, and
  `submit` from the primary checkout leaves the branch copy at `active`
  (`tests/test_recursion.py`, `tests/test_tracker_sync.py` drive the second).

- A discard moves a ticket nobody is assigned; every other move still refuses one,
  and a ticket assigned to another account is still never moved. The post-transition
  read-back no longer demands the ticket be assigned to the caller for resolved work,
  which had turned a successful unassigned discard into `did not reach 'Won't Do': it
  is in 'Won't Do'`, and the progress comment for such a discard is posted rather
  than skipped.
- Drift is judged against the whole path from where the ticket was left to the move's
  target, so a hand move to an intermediate mapped status is accepted instead of
  reported as drift. The path is walked toward the target rather than derived by
  inverting the status mapping, which is ambiguous when `completed` and `discarded`
  map to one name.
- `tcw work tracker sync <slug>` exits 1 when the named item was started by somebody
  else and still carries a sync or comment record, naming it and `TCW_WORK_OWNER`;
  with nothing recorded, and under `--all`, it still exits 0. Strict
  mode's refusal names the owner to run as, so its "run sync" advice can no longer
  end in a silent success.
- Messages distinguish an unassigned ticket from one somebody else holds.
- `skills/documentation-sync/SKILL.md` cited steps 4, 6 and 9 of the stage
  documents; they are steps 1, 3 and 5.
- `docs/guide/taxonomy-and-capabilities.md`'s examples refused when run in order:
  `Permission -p admin` and `--vocab user` named terms nothing had added, and
  `Subject=invoice,billing` a term that did not exist. The block now adds `Admin`
  and `User` first and uses `Subject=invoice,user`. In `docs/guide/work.md`,
  `--tags bug,cli` named a tag the block never registered; `tags add` now
  registers `cli` too.
- `PUT /api/work/<slug>/sidecars/<name>` wrote a `generated` sidecar
  (`rollup.md`, `tracker.yaml`) although the client hides its edit control. It now
  returns 409 naming the owning command, in every mode. `WORK_SIDECARS`'
  `generated` value is that command instead of `"yes"`; the strict-mode-only
  `tracker.yaml` branch of `_strict_refuses` and its call in the route are removed.

## Removed

- `skills/work/references/lifecycle/default/README.md`, which pointed at
  `tcw/work/prompts/*.md` — files that ship with the Python package, not the
  plugin.

## Internal

- Two comments in `tcw/store/fs.py` cited README text that does not exist; they
  now cite `docs/guide/work.md` and `docs/guide/multi-repo.md`.
- The frontmatter parse in `tests/test_plugin_manifests.py` is extracted to
  `_frontmatter` and shared by all three frontmatter tests.
- The Codex description guard (`_names_missing_from`) matches a skill name only
  when backticked, and only in `longDescription`. It matched a whole token
  across the whole manifest, which the prefix made safe: without it `work`,
  `taxonomy` and `capabilities` are ordinary words, found in "framework", "work
  item" and the manifest's keywords, so any of them could be dropped from the
  enumeration with the suite green. Its self-test is renamed
  `test_a_shared_name_or_plain_word_cannot_stand_in_for_a_skill_name` and
  checks both collisions on live names.
- Capability ids are regenerated. The CLI has no rename verb on either axis, so
  each entry was re-created with `add` + `set` and the old one removed with
  `rm`; an id does not survive that. Nothing in this repository reads them, but
  a project that inherits this ledger keys an override by the upstream id, so an
  override of one of these 15 entries no longer matches it. Taxonomy
  Features carry no id — the slug is their identity — so they lose nothing.
  A `tcw capabilities mv` / `tcw taxonomy mv` would have made the migration two
  loops of one command and is filed as follow-up work.
- `ladder_steps`/`ladder`/`forward_from` in `tcw/tracker/sync.py` express the mapped
  statuses as an ordered ladder, used both for the drift window and for the walk.
  `MOVE_ONTO` (the inverse of `MOVE_STATUS`) is shared by the walk and `link`.
- `transitions` keys other than `claim` are unknown to 2.3.0 and earlier, which
  reject the whole tracker block when one is set.
  `assess_move` takes the move it is serving and the transition named for it.
- `tests/tracker_fake.py` records applied transition ids and gains the `AMBIGUOUS`,
  `STRICT_LADDER` and `BROKEN_LADDER` workflows.
- `tests/test_skill_lifecycle_parity.py`: the router test now asserts that
  nothing in `work` outside `references/lifecycle/` names a stage document,
  the orphan check exempts `references/lifecycle/`, and new tests require the
  bold `work-stage` note and the validation line as the stage skill's first
  injected command. New `tests/test_harness.py` and
  `tests/test_stage_validate.py`. `tests/test_eval_grading.py` checks that the
  grader's block headings appear in the stage skill.
- `tests/test_shipped_procedures.py`: every converted source keeps its
  `SOURCES` row wrapped in `Composes`. For those, `test_each_default_is_todays_text`
  checks that a skill injects `tcw work procedure prompt <id>` and names it in
  its "Document command summary", or that a reference document names it, and
  that no paragraph of the default (whitespace-normalized, 40 characters or
  more, headings excluded) survives in the source. New
  `test_the_backlog_auditor_reads_the_procedure` and
  `test_the_post_mortem_agent_reads_the_procedure`.

- **`tests/tracker_fake.py` validates the assignee.** It previously wrote any
  value and answered 204, and reads `""` as unassigned — so an unassignment sent
  as `""` passed every test and would have 400d against real Jira. Only `None` or
  a registered account id is accepted now.
