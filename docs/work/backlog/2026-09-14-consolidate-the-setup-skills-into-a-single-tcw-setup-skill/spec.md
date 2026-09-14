# Spec — Give every TCW skill a taxonomy Feature and exactly one capability

> **About this spec**
>
> - **Where it came from.** The requester split this item's original scope in
>   three on 2026-09-14 (`initial-request.md`, revision note 16):
>   - the eval checks went to
>     `2026-09-14-make-eval-checks-measure-what-the-agent-did-…`;
>   - the skill restructure went to
>     `2026-09-14-restructure-tcw-s-skills-setup-and-configure-skills-command-and-extras-skills-and-no-slash-commands`;
>   - this item keeps the taxonomy Features and one capability per skill.
> - **History.** The earlier, larger spec and plan remain in git history (commit
>   `9fbaa25a`). This version is carved from them, with the round-three review
>   findings applied.
> - **Blocked by** the skill restructure item, because the skills this item
>   describes must exist first, and by
>   `2026-09-14-delete-a-capability-with-tcw-capabilities-rm`, because this item
>   deletes nine capabilities.

## Capability changes

Planned ledger and taxonomy changes only. Nothing is written at this stage.

**Order when writing:**

1. The vocabulary term.
2. The Features. `tcw taxonomy add` refuses a Feature naming vocabulary that isn't
   registered (`skills/tcw-taxonomy/SKILL.md:57-67`).
3. The capabilities, with their `Feature`. `set` refuses a `Feature` that doesn't
   resolve (`skills/tcw-capabilities/SKILL.md:55-63`).
4. Deleting the capabilities they replace, in the same commit as each successor.

### Taxonomy

**New Vocabulary — `skill`.** "An agent skill: a document an agent loads to learn
how to do one kind of task. The TCW plugin ships some, and a project can bind its
own to lifecycle stages."

- It is deliberately general, because `configurable-work-lifecycle` already uses
  "agent skills" to mean a project's own skills.
- No term named `skill` exists today.

**Fifteen new Features, one per top-level skill.**

- **Slugs.** Each slug is the skill's directory name plus `-skill`, set with `-s`.
  Without `-s`, "TCW Initialization Skill" would get the slug
  `tcw-initialization-skill`.
- **Vocabulary.** Each Feature names `skill` plus every existing term it operates
  on; `--vocab` can be repeated.
- **Related Features.** Where a Feature overlaps an existing one, it gets a
  `relatesTo` link, followed by `tcw taxonomy check`. This is the taxonomy skill's
  documented hand edit (`:116`).
- **Descriptions.** A description names the interaction area only, never behavior
  (`:76-78`).

| Skill | Feature path | Feature name | Vocabulary | `relatesTo` |
| --- | --- | --- | --- | --- |
| `tcw-setup` | `tcw-setup-skill` | TCW Initialization Skill | `skill`, `cli`, `node`, `store` | `provisioned-component-stores` |
| `tcw-configure` | `tcw-configure-skill` | TCW Configuration Skill | `skill`, `node`, `store`, `work-item/lifecycle-hook`, `work-item/definition-of-done` | `configurable-work-lifecycle`, `configurable-component-store-location`, `external-work-tracker`, `connected-project-registry` |
| `tcw-work` | `tcw-work-skill` | TCW Work Skill | `skill`, `work-item`, `work-item/transition` | `work-inbox` |
| `tcw-taxonomy` | `tcw-taxonomy-skill` | TCW Taxonomy Skill | `skill`, `vocabulary`, `feature` | `taxonomy-feature-registry` |
| `tcw-capabilities` | `tcw-capabilities-skill` | TCW Capabilities Skill | `skill`, `capability` | `capability-feature-association` |
| `documentation-sync` | `documentation-sync-skill` | TCW Documentation Sync Skill | `skill`, `work-item/lifecycle-stage` | — |
| `tcw-work-stage` | `tcw-work-stage-skill` | TCW Work Stage Skill | `skill`, `work-item/lifecycle-stage` | `configurable-work-lifecycle` |
| `tcw-extras-triage-issues` | `tcw-extras-triage-issues-skill` | TCW Extras Issue Triage Skill | `skill`, `work-item/intake` | `work-inbox` |
| `tcw-post-mortem` | `tcw-post-mortem-skill` | TCW Post-Mortem Skill | `skill`, `work-item/lifecycle-stage` | — |
| `tcw-extras-autonomous-work` | `tcw-extras-autonomous-work-skill` | TCW Extras Autonomous Work Skill | `skill`, `work-item` | — |
| `tcw-extras-report` | `tcw-extras-report-skill` | TCW Extras Report Skill | `skill` | — |
| `tcw-commands-plan-work` | `tcw-commands-plan-work-skill` | TCW Plan Work Command Skill | `skill`, `work-item`, `work-item/lifecycle-stage` | — |
| `tcw-commands-drive-work-to-completion` | `tcw-commands-drive-work-to-completion-skill` | TCW Drive Work to Completion Command Skill | `skill`, `work-item`, `work-item/lifecycle-stage`, `work-item/transition` | — |
| `tcw-commands-verify-work` | `tcw-commands-verify-work-skill` | TCW Verify Work Command Skill | `skill`, `work-item/lifecycle-stage`, `work-item/transition` | — |
| `tcw-commands-process-inbox` | `tcw-commands-process-inbox-skill` | TCW Process Inbox Command Skill | `skill`, `work-item/intake` | `work-inbox` |

### Capabilities

```yaml
new:
    - skills/tcw-setup
    - skills/tcw-configure
    - skills/tcw-work
    - skills/tcw-taxonomy
    - skills/tcw-capabilities
    - skills/documentation-sync
    - skills/tcw-work-stage
    - skills/tcw-post-mortem
    - skills/tcw-commands-plan-work
    - skills/tcw-commands-drive-work-to-completion
    - skills/tcw-commands-verify-work
    - skills/tcw-commands-process-inbox
    - skills/tcw-extras-autonomous-work
    - skills/tcw-extras-triage-issues
    - skills/tcw-extras-report
changed:
    - work/complete-a-work-item
# plus the nine deletions below, recorded in the form that
# 2026-09-14-delete-a-capability-with-tcw-capabilities-rm defines. A deleted path
# cannot sit under `changed:`, because the completion gate refuses a path that
# does not resolve.
```

**New: one capability per skill, under `skills/`.**

- **Path:** `skills/<skill-directory>`.
- **Name:** the requester's form, "Offer a skill dedicated to instructing agents how
  to …". For example, `skills/tcw-setup` is "Offer a skill dedicated to instructing
  agents how to set up TCW where it does not work yet".
- **Body:** the ledger's own form, "As a user or agent, I …", written in the
  capability's `description.md`. `tcw capabilities add` takes only a path and a
  name.
- **Fields:** `Feature` is the skill's Feature path; `Subject` is `skill`.
- **Status:** all fifteen are created `Supported`. Every skill ships once the
  restructure item has landed, and the completion gate fails only a `new:` path
  still `Missing` (`tcw/work/recursion.py:58-61`).
- **Removed names.** No body uses a removed command or skill name:
  - `tcw-plugin`
  - any `/tcw-…` slash command
  - `tcw-work-stage-<stage>`
  - `autonomous-work`, `tcw-triage-issues`, `tcw-report`

  Where a folded body said "run `/tcw-audit-work-backlog`", the successor says
  "ask the `tcw-work` skill".

**Deleted and folded in.** A capability is folded into a skill's capability only
when that skill is its main subject (revision note 12). Its behavior moves into the
successor's body, and the old entry is deleted with `tcw capabilities rm <path>`
in the same commit.

| Deleted capability | Folded into |
| --- | --- |
| `plugin/work-lifecycle` | split: planning goes to `skills/tcw-commands-plan-work`; driving through closeout, including bounded stage documents, goes to `skills/tcw-commands-drive-work-to-completion` |
| `work/consolidate-plans` | `skills/tcw-work` |
| `work/search-the-work-items` | `skills/tcw-work` |
| `work/audit-work-backlog` | `skills/tcw-work` |
| `plugin/report-an-issue-upstream` | `skills/tcw-extras-report` |
| `plugin/run-a-post-mortem` | `skills/tcw-post-mortem` |
| `plugin/triage-github-issues` | `skills/tcw-extras-triage-issues` |
| `taxonomy/bootstrap-the-taxonomy` | `skills/tcw-setup` |
| `capabilities/bootstrap-the-capabilities` | `skills/tcw-setup` |

**Changed:** `work/complete-a-work-item`. Line 20 of its description links
`tcw://C/plugin/triage-github-issues`. That link becomes
`tcw://C/skills/tcw-extras-triage-issues`, in the same commit as the deletion.

**Handled by the restructure item, not here:**
- `plugin/bootstrap-the-cli`: its wording is updated there, and its main subject is
  the install hook, so it gets no `Feature`.
- `work/run-a-lifecycle-stage`: its per-stage paragraph is reworded there.

**Not touched:** these capabilities describe CLI or configuration-file behavior,
not a skill:
- `work/configure-the-work-lifecycle`
- `work/declare-which-documents-track-which-changes`
- `work/read-the-documentation-gate-for-a-change`
- `work/customize-the-definition-of-done`
- `plugin/install-as-a-plugin`

## Problem

- **No taxonomy entry describes a skill.** There is no `skill` term and no Feature
  for any skill (`tcw taxonomy search skill` finds only
  `configurable-work-lifecycle`).
- **Skill capabilities are scattered.** The capabilities that describe what a user
  does through a skill sit in four namespaces (`plugin/`, `work/`, `taxonomy/`,
  `capabilities/`) and point at no Feature.
- **Coverage is uneven.** Some skills have several such capabilities
  (`tcw-work`'s procedures have three), and others have none
  (`autonomous-work`, `documentation-sync`, `tcw-work-stage`).

## Goals

1. Every top-level skill has exactly one taxonomy Feature and exactly one
   capability, linked to each other.
2. Every capability whose main subject is a skill is that skill's capability. No
   second capability describes the same skill.
3. Nothing a deleted capability described is lost; it lives in its successor's
   body.

## Non-goals

- Changing any skill, command, eval, or configuration. That is the restructure item
  and the eval-checks item.
- Moving any capability not listed above.
- Adding `tcw capabilities rm`. That is its own item.

## Design

### D1 — Taxonomy

- `tcw taxonomy add "Skill" -s skill "<definition above>"`.
- One `tcw taxonomy add "<name>" --kind feature -s <slug> --vocab <term> …` per
  table row. The description names the interaction area in one sentence, with no
  behavior.
- `relatesTo` links are written in each Feature's `meta.yaml` as the table gives,
  the taxonomy skill's documented hand edit (`skills/tcw-taxonomy/SKILL.md:116`).
  Then run `tcw taxonomy check`.

### D2 — Capabilities, grouped so no commit lacks a successor

Each group is one commit. It writes the successors (add, set, body) and deletes
what they replace:

1. `skills/tcw-work`, `skills/tcw-commands-plan-work`, and
   `skills/tcw-commands-drive-work-to-completion`. Fold in
   `work/consolidate-plans`, `work/search-the-work-items`, `work/audit-work-backlog`
   and the split `plugin/work-lifecycle`, then delete those four.
2. `skills/tcw-extras-report`, `skills/tcw-post-mortem`, and
   `skills/tcw-extras-triage-issues`. Fold in and delete
   `plugin/report-an-issue-upstream`, `plugin/run-a-post-mortem` and
   `plugin/triage-github-issues`, and fix `work/complete-a-work-item`'s link.
3. `skills/tcw-setup`. Fold in and delete the two bootstrap capabilities.
4. The remaining eight, which delete nothing: `skills/tcw-configure`,
   `skills/tcw-taxonomy`, `skills/tcw-capabilities`, `skills/documentation-sync`,
   `skills/tcw-work-stage`, `skills/tcw-commands-verify-work`,
   `skills/tcw-commands-process-inbox`, `skills/tcw-extras-autonomous-work`.

**`capabilities.yaml`** for this item is written in the **last** commit (after
group 4). Every `new:` path then exists, and every recorded deletion has happened.
Only the completion gate reads it (`tcw/work/recursion.py:36-68`), so writing it
last removes the window in which it names paths that don't exist yet.

### D3 — Related items

- `2026-09-01-fan-the-backlog-audit-out-across-every-connected-work-root` edits the
  audit procedure whose capability this item deletes. A note on it says its
  capability delta should name `skills/tcw-work`.

### Abstraction and harness checks

- **Abstraction:** every write uses `tcw taxonomy add`, `tcw capabilities add`,
  `set` or `rm`, or edits body text and `relatesTo`, the documented hand edits.
- **Harness:** nothing here is agent-facing.

## Acceptance criteria

1. **The vocabulary term.** `tcw taxonomy show skill` exits 0.
2. **Every Feature.** For every row of the Taxonomy table,
   `tcw taxonomy show <Feature path>`:
   - exits 0;
   - prints `kind: Feature`;
   - prints a `vocabulary:` line containing every term in that row.
3. **Every link.** Each `relatesTo` link in the table appears in that Feature's
   `meta.yaml`, and `tcw taxonomy check` exits 0.
4. **Every skill has its capability.** For every directory `<s>` under `skills/`,
   `tcw capabilities show skills/<s>`:
   - exits 0;
   - prints `**Status:** Supported`;
   - prints `**Feature:** <s>-skill`.
5. **Deleted capabilities are gone.** `tcw capabilities show <path>` exits non-zero
   for each of the nine deleted paths.
6. **One capability per skill.** No capability outside `skills/` has a `Feature`
   ending in `-skill`, and none lists a skill as its `Subject`.
7. **The moved link.** `docs/capabilities/work/complete-a-work-item/description.md`
   contains `tcw://C/skills/tcw-extras-triage-issues`, and no file under
   `docs/capabilities/` contains `tcw://C/plugin/triage-github-issues`.
8. **No removed names.** This command prints nothing:

   ```sh
   git grep -nP 'tcw-plugin|/tcw-[a-z-]+|tcw-work-stage-(request|spec|plan|implement|verify)|(?<![-\w])autonomous-work|(?<![-\w])tcw-triage-issues|(?<![-\w])tcw-report' -- docs/capabilities docs/taxonomy
   ```
9. **Nothing lost.** For each deleted capability, every behavior its body described
   at `<base>` is described in its successor. This is checked by reading, and the
   result is recorded in `outcome.md`.
10. **Everything validates.**
    - `tcw capabilities check` prints `capabilities OK`;
    - `tcw validate` exits 0;
    - bare `pytest` passes.

## Risks

- **The deletion form is not decided yet.** It depends on
  `2026-09-14-delete-a-capability-with-tcw-capabilities-rm`. If that item records
  deletions some other way than a `capabilities.yaml` key, D2's closing commit
  follows it.
- **Folding makes long bodies.** `skills/tcw-work` absorbs three procedures'
  capabilities. AC 9 is a reading check and cannot be automated.
- **Names may be wrong.** The fourteen Feature names beyond the requester's two are
  proposals. They become stable IDs, and changing them later touches every
  capability linked to them.
- **AC 6 depends on a naming convention.** It assumes no existing Feature slug ends
  in `-skill`. Check that at the start of implementation.
