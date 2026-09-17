# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

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

## Changed

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

## Fixed

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
