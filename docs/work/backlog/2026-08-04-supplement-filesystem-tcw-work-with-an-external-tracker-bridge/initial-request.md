# Supplement filesystem TCW work with an external tracker bridge

## Capability changes

Future specification should introduce an `external-work-tracker` taxonomy
Feature associated with the existing `work-item`, `cli`, and `reference`
vocabulary, then declare these capabilities as `Missing` and link them back to
this item:

- `work/manage-external-tracker-intake` — list, inspect, atomically claim, and
  import assigned tracker tickets as filesystem-backed TCW work.
- `work/synchronize-external-tracker-work` — enforce tracker-backed assignment
  and synchronize lifecycle state, branches, and concise progress summaries.

Do not change `work/manage-the-work-inbox`: the permissive filesystem inbox and
an authoritative external tracker are distinct intake sources.

This request records those future deltas only. Creating the backlog item does
not create or alter taxonomy or capability entries.

## Problem

TCW's filesystem methodology keeps technical planning, code, capability changes,
and lifecycle evidence together in Git. That is valuable and should remain the
default. Its limitation is coordination across people or agents working from
different clones: a backlog-to-active folder move in one checkout is not a
shared, idempotent assignment claim in every other checkout.

The current convention is to commit a status transition on trunk and push it
when repository policy permits. That is neither an atomic cross-user claim nor a
good intake surface for non-developers. Two workers can select the same stale
backlog state before either sees the other's commit.

An external tracker such as Jira already provides a shared service, identities,
assignees, permissions, workflow transitions, and a product-facing ticket
surface. It should supplement the filesystem work store rather than replace it:

- the tracker owns product intake, assignment, and high-level coordination;
- Git retains detailed TCW lifecycle artifacts and technical truth;
- a strong machine-readable association joins the two; and
- the CLI coordinates claims and synchronization across the boundary.

This is different from a full `JiraWorkStore`. The filesystem `WorkStore`
continues to own the TCW item and every lifecycle artifact.

## Goals

1. Prevent two users or agents from independently claiming the same configured
   tracker ticket.
2. Let non-developers create and discuss requests in product language without
   requiring repository or TCW knowledge.
3. Import an assigned ticket into one or more repository-local TCW items without
   losing the ticket's product prose or origin.
4. Keep tracker status and concise progress links current as the TCW lifecycle
   advances.
5. Allow strict projects to prohibit work unrelated to the authenticated user's
   assigned and claimed tickets.
6. Remain provider-neutral at the coordination boundary and ship Jira Cloud as
   the first provider.
7. Preserve normal filesystem-only behavior when no tracker is configured.

## Intended workflow

1. Product or another non-developer creates one or more tracker tickets and
   assigns them through the tracker's normal workflow while they remain in a
   configured ready/backlog state.
2. A developer or agent polls the configured tracker through `tcw work tracker
   list` and inspects a candidate with `tracker show`.
3. `tracker import` verifies that the ticket is assigned to the authenticated
   tracker identity and atomically transitions it from ready to claimed/in
   progress.
4. TCW creates a local backlog item, records the ticket binding, and snapshots
   the ticket's product content into `initial-request.md` with attribution and a
   stable origin link.
5. The ordinary TCW request, specification, plan, implementation, verification,
   and completion lifecycle proceeds in Git. Existing `start --worktree` creates
   code branches/worktrees as it does today.
6. Mapped lifecycle events update the tracker with status plus concise work,
   branch, and review links. Technical artifacts are not copied into tracker
   prose.
7. Completion or discard applies the configured terminal tracker transition.
   Failed non-claim synchronization remains retryable through `tracker sync`.

## Authority and consistency model

### Split authority

- **Tracker authoritative:** ticket existence, assignee, claim state, and
  product-facing coordination status.
- **Filesystem TCW authoritative:** work-item decomposition, lifecycle artifacts,
  capability deltas, implementation details, review evidence, and code state.
- **No bidirectional free-for-all:** remote edits do not silently rewrite or
  discard local TCW work, and local technical prose does not overwrite product
  tickets.

### Claims are the hard gate

Claim/import must succeed remotely before the local item is created or linked.
The provider-neutral contract must expose an atomic claim capability; strict mode
must reject providers that only offer last-writer-wins assignment updates.

For Jira Cloud, use a configured ready-to-in-progress workflow transition as the
claim boundary. Jira Cloud serializes simultaneous transition requests on one
issue and reports the loser as a conflict; translate that result into a clear
"already claimed" diagnostic rather than retrying it as a transient failure.

Reference:
<https://developer.atlassian.com/cloud/jira/platform/change-notice-update-in-simultaneous-transitions-issue-api/>

### Later synchronization is durable and retryable

After claim/import, a temporary tracker outage must not undo a valid local
lifecycle transition. Record a deterministic outbound event with the local
transition, commit the local transition, attempt immediate delivery, and let
`tracker sync` retry until the remote target is observed. Providers must treat
an already-applied event as success.

The binding's event history should be append-only and bounded by lifecycle
transitions. Delivery/pending state should be derived from the current remote
state and deterministic event IDs so successful delivery does not require a
second cleanup commit for every TCW transition.

### Remote drift blocks strict-mode mutations

Before a linked lifecycle mutation, strict mode reads the current ticket. If it
has been reassigned, canceled, deleted, or moved to an incompatible state, TCW
must record/report the conflict and refuse the mutation. It must not
automatically discard or rewrite local work.

The operator resolves the authoritative state in the tracker or uses the normal
TCW lifecycle to reconcile local intent, then reruns `tracker sync`. There is no
convenience bypass flag: changing strictness requires an explicit, reviewable
`tcw-config.yaml` edit.

## Provider-neutral architecture

Introduce a tracker bridge beside `WorkStore`, not a remote `WorkStore`
implementation. A coordinator composes the configured tracker provider with the
existing store; tracker network calls do not belong inside `FsWorkStore`.

The provider contract should cover:

- validate provider configuration and credentials;
- identify the authenticated remote user;
- list configured candidate tickets;
- fetch a ticket and its revision/state;
- atomically claim a ticket or return a typed contention result;
- inspect current assignee and workflow state;
- apply an idempotent mapped lifecycle event; and
- generate a stable ticket locator for presentation.

Provider-neutral data should include ticket reference, title, product body,
assignee identity, workflow state, revision when available, URL, and bounded
attachment/link metadata. Jira-specific field IDs, transition IDs, JQL, and
authentication stay in the Jira provider/configuration.

The abstract-spine litmus test still applies. Claim, assignment, external
reference, transition, query, and conflict are portable concepts. JQL, Jira REST
paths, environment variable names, and Jira transition discovery are adapter
details.

## Strong association and cardinality

Add `tracker.yaml` to the bounded `WORK_SIDECARS` registry. The existing
`WorkStore.read_sidecar`/`write_sidecar` surface then keeps the association
portable and revision-protected without adding Jira behavior to `WorkStore`.

The sidecar should contain no credentials and should use a versioned mapping with
at least:

- provider ID;
- ticket reference and stable URL;
- TCW project ID;
- decomposition part ID;
- claimed remote identity; and
- deterministic lifecycle events containing event ID, local transition/status,
  resolution when applicable, target tracker event, and concise summary/link
  payload.

Each TCW item has one primary tracker ticket. One ticket may coordinate multiple
TCW items across repositories, or multiple explicitly named parts within one
repository. The idempotency key is:

`(TCW project ID, provider ID, ticket reference, part ID)`

`part` defaults to `default`. Repeating an import with the same key returns the
existing item; a distinct `--part api`, `--part web`, or similar value deliberately
creates another associated item. Many-to-many primary associations are out of
scope.

Imported titles default to `<TICKET> — <summary>`, so the external key appears in
the date-prefixed TCW slug and therefore in the existing `work/<slug>` branch.
`--title` may provide a better technical decomposition title without weakening
the sidecar association.

## Proposed CLI surface

```text
tcw work tracker list
tcw work tracker show <ticket>
tcw work tracker import <ticket> [--part <id>] [--title <title>]
tcw work tracker link <slug> <ticket> [--part <id>]
tcw work tracker unlink <slug> --reason <text>
tcw work tracker sync [<slug> | --all]
```

- `list` uses the provider's configured candidate query and defaults to work
  assigned to the authenticated identity.
- `show` presents product content, assignee, workflow state, and claimability
  without mutation.
- `import` claims then creates the bound backlog item. It accepts the useful
  creation metadata supported by `work new` where needed, while ticket content
  supplies the default title/body.
- `link` migrates an existing backlog item after verifying or acquiring the
  ticket claim. It refuses a second primary binding.
- `unlink` is an audited repair operation. It records the required reason; in
  strict mode the now-unlinked item cannot mutate until relinked.
- `sync` retries safe outbound events and reports remote drift. It never
  auto-follows an incompatible remote change.

Strict mode also changes existing behavior:

- unlinked `work new` and `work start` are refused;
- linked mutations verify remote assignment/state before proceeding;
- a linked backlog item cannot be destructively dropped, because that would
  erase its association and audit history—use a preserved discard resolution;
- unconfigured projects behave exactly as they do today.

`work show` and `work list` should surface the provider/ticket and whether the
remote state is current, pending, or conflicting. The local web application is
read-only for this tracker metadata in the first delivery; it does not gain
tracker mutation controls.

## Configuration

Use the existing node sentinel rather than creating another config file. The
shape should remain provider-neutral while allowing provider-specific settings,
for example:

```yaml
work:
  tracker:
    provider: jira-cloud
    strict: true
    base-url: https://example.atlassian.net
    candidate-query: project = ENG AND assignee = currentUser() AND status = Backlog
    credentials:
      email-env: TCW_JIRA_EMAIL
      token-env: TCW_JIRA_API_TOKEN
    transitions:
      claim: Start Progress
      submit: Ready for Review
      rework: Reopen
      complete: Done
      discard:
        duplicate: Duplicate
        superseded: Superseded
        wontfix: Won't Do
```

The exact parser belongs in the future spec, but these decisions are fixed:

- secrets are read from named environment variables and never written to the
  repository or tracker sidecar;
- claim and terminal mappings are required in strict mode;
- submit/rework mappings are optional because tracker workflows need not mirror
  every TCW status;
- all supported discard resolutions need an explicit mapping or a configured
  shared discard transition; and
- invalid strict configuration fails closed through `tcw validate` and tracker
  commands without breaking ordinary filesystem board reads.

## Lifecycle mapping

- Tracker ready/backlog -> `tracker import` claim -> tracker in progress plus
  local TCW backlog. "In progress" externally means assigned/claimed; local
  request/spec/plan work may still occur in backlog.
- TCW `start` -> tracker remains in progress unless a distinct mapping exists;
  publish the branch/work link when `--worktree` creates it.
- TCW `submit` -> optional tracker review transition.
- TCW `rework` -> optional transition back to in progress.
- TCW `complete --resolution done` -> required terminal completion transition.
- TCW discard resolutions -> their configured terminal transitions and concise
  reason summaries.

Only stable links and short summaries are written back. Do not copy
`spec.md`, `plan.md`, `outcome.md`, `refined-outcome.md`, capability prose, diffs,
or code references automatically. A ticket author may include code references
manually, but the bridge preserves the product/developer knowledge boundary.

## Jira Cloud first provider

The first concrete provider targets Jira Cloud REST v3. Use an email and API
token supplied through configured environment-variable names; OAuth 2.0 and Jira
Data Center are follow-ups.

The provider must:

- resolve the current user and verify ticket assignment;
- execute configured JQL without embedding project policy in the generic core;
- discover/validate configured workflow transitions;
- translate simultaneous-transition conflict into the generic claim-conflict
  result;
- combine transition fields and the concise link/comment payload where Jira's
  transition operation permits it;
- use stable ticket keys/URLs in the binding; and
- distinguish authentication, permission, validation, contention, not-found,
  rate-limit, and transient-network failures.

Reference for Jira issue and transition operations:
<https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/>

## Failure and recovery scenarios

- **Two claimers race:** one remote transition wins; the loser creates no local
  item and receives the current assignee/state.
- **Claim succeeds, local creation fails:** the ticket remains claimed. Retrying
  the same import detects that it is claimed by the same identity and safely
  creates or returns the idempotent local binding.
- **Local transition succeeds, tracker is unavailable:** local work remains in
  its correct status with a durable event; the command exits non-zero with a
  clear "local moved, tracker pending" result; `sync` retries.
- **Remote already reflects the event:** treat delivery as successful and do not
  duplicate comments or transitions.
- **Ticket reassigned/canceled/deleted:** strict mode blocks the next mutation and
  preserves local artifacts for explicit reconciliation.
- **Binding manually duplicated or malformed:** `tcw validate` and `work check`
  fail closed and name the conflicting items/keys.
- **Credentials absent:** tracker commands fail clearly without affecting
  filesystem-only reads or mutations when strict mode is disabled.
- **Existing items when strict mode is enabled:** link open items before enabling
  strict mode; otherwise their next mutation is intentionally blocked.

## Testing expectations for future implementation

1. Provider-contract tests with a deterministic fake provider for list, show,
   claim, conflict, drift, event application, and idempotency.
2. CLI/store tests for `tracker.yaml` validation and revision protection,
   idempotent import, multiple repositories/parts, link/unlink repair, strict
   gates, and unchanged unconfigured behavior.
3. Race tests proving only one claim/import creates local work.
4. Failure-window tests for remote-claim/local-create interruption and
   local-transition/remote-delivery interruption.
5. Lifecycle tests for start, submit, rework, done, every discard resolution,
   branch-link publication, pending state, retry, and incompatible remote drift.
6. Mocked Jira Cloud REST tests for authentication, JQL, assignment checks,
   transition discovery, conflict responses, status/comment payloads, pagination,
   permissions, rate limits, and network failures.
7. Configuration tests proving malformed strict mappings fail closed and secrets
   never appear in tracked state or diagnostic output.
8. An opt-in Jira Cloud smoke test skipped when credentials are absent; no live
   Jira dependency in the normal test suite.
9. Full repository checks: pytest, `tcw taxonomy check`,
   `tcw capabilities check`, `tcw validate`, build/package consistency where
   affected, and `git diff --check`.

## Documentation expectations for future implementation

All four repository Documentation Sync triggers are expected to fire:

- `README.md` — public CLI, configuration, workflow, guarantees, and recovery.
- `docs/release-notes/upcoming.md` — plain-language tracker-backed assignment and
  visibility.
- `docs/changelogs/upcoming.md` — provider contract, Jira adapter, sidecar,
  synchronization, and strict enforcement.
- `skills/tcw-work/SKILL.md` or a gated reference — tracker intake, claim,
  lifecycle synchronization, drift handling, and the distinction from the local
  inbox and full store adapters.

The future plan must schedule these updates as one documentation pass after the
implementation and tests settle.

## Non-goals for the first delivery

- Replacing `FsWorkStore`, `TaxonomyStore`, or `CapabilitiesStore`.
- Jira Data Center or Server support.
- OAuth, interactive login, or token persistence.
- GitHub, GitLab, Linear, or other concrete providers beyond the generic
  contract and Jira Cloud.
- Multiple primary tickets per TCW item.
- Mirroring technical lifecycle artifacts into tracker fields/comments.
- Webhooks, a daemon, scheduled background polling, or tracker mutation from
  `tcw serve`.
- Automatically following remote cancellation/reassignment into local status
  changes.
- Backfilling every historical work item.
- Making the existing capability `Tracker` field part of work assignment; that
  is the separate capability tracker-sync concern.
- Solving shared-filesystem atomic rename/owner stamping; that remains the
  narrower filesystem-claims item.

## Relationship to adjacent backlog work

- `2026-06-19-remote-adapter-jiraworkstore` now tracks the theoretical **full
  external TCW store adapters** concept. This bridge does not implement it.
- `2026-06-22-concurrency-safe-work-claims-for-multi-agent-repos-configurable-work-path-atomic-owner-stamp`
  now tracks only concurrency-safe filesystem claims for callers sharing one
  local store. It remains a lower-priority fallback and neither blocks nor
  implements this bridge.
- `2026-06-19-tracker-sync-for-capabilities` remains capability metadata sync,
  not work assignment.
- `2026-06-19-remote-extends-for-taxonomy` remains remote source resolution for
  filesystem-backed taxonomy federation, not a remote taxonomy store.

## Delivery and release boundary

This item remains in backlog until separately specified and planned. Creating or
refining this request does not authorize `tcw work start`, implementation,
capability/taxonomy writes, public documentation changes, a release, or a version
bump. Those occur only through the normal TCW lifecycle with explicit acceptance.
