# Fan the backlog audit out across every connected work root

## Origin

GitHub issue [#24](https://github.com/brocef/TCW/issues/24), filed 2026-08-28
by @brocef.

> ### Motivation
>
> `references/audit-backlog.md` describes the audit as a single-node procedure: start
> with `tcw work list --status backlog` for the node you happen to be standing in,
> fan out one subagent per item, then one inter-item pass. That is the right shape
> for a leaf project, but it silently under-covers a **multi-node workspace**.
>
> Concretely, in a workspace whose root `tcw-config.yaml` declares
> `connected-projects.children`:
>
> ```yaml
> id: proposit-app
> connected-projects:
>   children:
>     proposit-core:   proposit-core
>     proposit-shared: proposit-app/packages/shared
>     proposit-server: proposit-app/apps/server
>     proposit-mobile: proposit-app/apps/mobile
> ```
>
> running `/tcw-audit-work-backlog` at the root audits the root's 8 items and
> reports as if it were done. The four child nodes hold 92 more backlog items that
> the command never looked at. Nothing in the procedure or the output says so — the
> report reads as a complete audit of the workspace. That is exactly the failure the
> doc itself warns against elsewhere: "'audited, clean' and 'not audited' must not
> look the same."
>
> Worse, the doc's most valuable check is the one that most needs the other nodes:
>
> - **Wrong repository / node** — "the item belongs in another TCW node, or should be
>   split across nodes." You cannot judge whether an item is in the wrong home while
>   reading only one home.
> - **Duplicate or superseded** — cross-node duplication is the common case in a
>   federated workspace (a shared-layer item and a consumer item describing the same
>   fix), and a per-node inter-item agent structurally cannot see it.
> - **Blocked without a next action** — the doc says to look each blocker up with
>   `tcw work show <blocker>`, but real blockers here read
>   `blocked-by: external: proposit-core/2026-08-18-add-the-xor-operator-to-the-logic-engine`.
>   Resolving that reference requires the *other* node's store. Today the check
>   quietly degrades to "external blocker, cannot verify."
>
> The workaround is to hand-dispatch one agent per node and merge the reports
> yourself, re-deriving the batching, the return contract, and the reporting format
> in each dispatch prompt. That is the procedure's own job.
>
> ### Description
>
> Make the root-level audit node-aware, mirroring the fan-out the doc already
> prescribes one level up.
>
> 1. **Detect the roots.** When the invoking node's `tcw-config.yaml` declares
>    `connected-projects.children`, the audit's unit of work is the *set* of work
>    roots (the invoking node plus each child), not the invoking node alone.
> 2. **One auditor subagent per work root.** Each runs the existing two-checklist
>    procedure — per-item fan-out (batches of ≤ 8) then a per-node inter-item pass —
>    against its own node, read-only, and returns the doc's line format plus its
>    items' two-line summaries.
> 3. **One cross-node pass at the end**, consuming those summaries (not re-reading
>    the stores), for the three checks that only exist at workspace scope:
>    cross-node duplicates/supersession, misplaced items, and `external:` blockers
>    whose referent can now actually be looked up in the node it names — including
>    the case where the referent is already completed, which
>    [tcw external blockers don't auto-clear] leaves silently gating its dependents.
> 4. **Report per node, then the cross-node section**, and state the node roster that
>    was audited. Same severity scale, same "audited, clean" line-per-item rule.
> 5. **Keep the approval rule where it is** — the invoking session, which holds the
>    user relationship, approves; the node agents stay read-only.
>
> A smaller version of this would be worth having even without the fan-out: a single
> sentence in `audit-backlog.md` saying the procedure covers one node, and that a
> workspace with `connected-projects` needs it run per node. That alone removes the
> false-completeness reading.
>
> ### Benefits
>
> - The audit's coverage matches the user's mental model of "audit my backlog" in the
>   multi-repo workspaces TCW's `connected-projects` feature exists to serve.
> - Three checklist items the doc already specifies — wrong node, duplicates,
>   stale blockers — become answerable instead of structurally undecidable.
> - `external:` blockers get verified against the store that owns them, which is the
>   only place a "this blocker is already completed" finding can come from.
> - The batching rule, the two-line return contract, and the report format are
>   written once in the skill instead of re-derived in every hand-written dispatch.
>
> Axis: **work**.
>
