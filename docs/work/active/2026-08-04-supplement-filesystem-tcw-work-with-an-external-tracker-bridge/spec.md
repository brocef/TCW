# Spec — Supplement filesystem TCW work with an external tracker bridge

This is an **epic** spec. It fixes the initiative's boundaries, the child items
that build it, and their order. Implementation detail belongs in each child's own
spec, and every design question this document defers is named as deferred rather
than left silent.

## Capability changes

Planned deltas only; nothing is written to the ledger here. Three new
capabilities, one per delivering child, and two existing ones changed. No
capability is removed.

| Capability | Delta | Child |
| ---------- | ----- | ----- |
| `work/inspect-external-tracker-work` | new, seeded `Missing` | C1 |
| `work/manage-external-tracker-intake` | new, seeded `Missing` | C2 |
| `work/synchronize-external-tracker-work` | new, seeded `Missing` | C3 |
| `work/require-tracker-backed-work` | new, seeded `Missing` | C4 |
| `work/read-a-work-item` | changed | C5 |
| `work/open-a-work-item` | changed | C5 |

The request named two capabilities. This spec names four, because the request's
`work/synchronize-external-tracker-work` bundled two things the decomposition
separates: pushing lifecycle state outward (C3) and refusing local work that no
ticket authorizes (C4). A single capability spanning both would be `Missing`
until the last of five children landed, which tells a ledger reader nothing for
most of the initiative's life.

`work/manage-the-work-inbox` is **not** changed, per the request: a permissive
filesystem inbox and an authoritative external tracker are distinct intake
sources, and the inbox capability's text (`tcw capabilities show
work/manage-the-work-inbox`) describes only the former.

Each capability needs a taxonomy Feature before it can be written, because
`tcw capabilities set` refuses a `Feature` reference that does not resolve. No
suitable Feature exists — of the nine Features `tcw taxonomy list` prints, none is
about an external tracker. An `external-work-tracker` Feature is therefore
registered by the **epic's** coordination plan, before any child is created,
because all four capabilities name the same one and none of them can be written
until it resolves. That ordering is load-bearing, not cosmetic.

**A seeded capability cannot be withdrawn.** `tcw capabilities` has `add`, `set`
and `reset` but no `rm` verb, so a capability seeded for a child that is later
dropped ends as `Status: Omitted` rather than disappearing. This matters because
the plan contemplates rescoping C3 through C5. The taxonomy Feature *can* be
removed (`tcw taxonomy rm`); the capability records cannot.

## Problem

TCW's work store is a folder tree in Git, and an item's status is *where it
lives* rather than a stored field (`tcw/store/base.py:1862`). A status change is
realized by moving the folder, and the filesystem adapter commits that move
itself. This is the property the methodology is built on and it stays.

Its limit is coordination between people who do not share a working copy. Three
specifics, each checked:

1. **A claim is not visible until it is pushed, and pushing is not guaranteed.**
   `start` refuses a second claimant through `AlreadyClaimed`
   (`tcw/store/base.py:1851`, raised at `tcw/store/base.py:2679`), but that
   check reads the local tree. The store's own publication triad is explicit
   that a store may not publish at all: `publishes` defaults to `False`
   "so a new adapter cannot leak writes by omission"
   (`tcw/store/base.py:2021`), and `publish` "raises to report that the write
   did **not** become visible" (`tcw/store/base.py:2035`). Two people on two
   clones can therefore both read `backlog`, both move the folder, and both be
   correct locally.
2. **There is no intake surface for someone without the repository.** The inbox
   is a folder in the work store and `inbox_accept` consumes an entry from it
   (`tcw/store/fs.py:5608`, `tcw/store/fs.py:5620`). Filing a request means
   having a checkout and commit access.
3. **Nothing records that a TCW item answers an external ticket.** The bounded
   sidecar registry holds exactly `capabilities.yaml` and `rollup.md`
   (`tcw/store/base.py:1790`), and `WorkItem` carries no external reference
   field (`tcw/store/base.py:1862`). A ticket key in a title is prose.

The store layer already anticipates a tracker: the comment on the publication
triad says a tracker-backed store "answers `True` and implements both methods as
no-ops — a tracker write is published by definition", and calls that "a
legitimate implementation, not a stub" (`tcw/store/base.py:2013`). What is
missing is not room in the model. It is the bridge.

## Goals

The request's seven goals are adopted unchanged, with one restatement.

1. Two people or agents cannot independently claim the same tracker ticket
   **when the tracker's workflow can express that**, and TCW refuses to promise it
   when the workflow cannot. Restated 2026-09-12 after the claim experiment
   (`jira-claim-experiment.md`) showed the property belongs to the user's workflow
   configuration rather than to Jira. A guarantee TCW cannot keep is worse than a
   refusal it can explain.
2. Someone without a checkout can file and discuss a request in product
   language.
3. An assigned ticket can be imported into one or more repository-local TCW
   items without losing its product prose or its origin.
4. Tracker status and concise progress links stay current as the TCW lifecycle
   advances.
5. A project may refuse local work that no assigned, claimed ticket authorizes.
6. Jira Cloud works. **Restated:** the request asked for a provider-neutral
   contract with Jira as the first of several providers. This initiative builds
   Jira directly behind a narrow seam and extracts an interface when a second
   provider exists. See `## Notes` — this is a deliberate departure from the
   request, decided 2026-09-12, not an oversight.
7. A project with no tracker configured behaves exactly as it does today.

## Non-goals

Everything the request listed as a non-goal for the first delivery stands, and is
not repeated here. Added by this spec:

- **A provider abstraction with one implementation.** No abstract provider base
  class, no registry of providers, no deterministic fake provider. Tests fake the
  HTTP layer instead.
- **A new runtime dependency.** `pyproject.toml:12` declares `PyYAML>=6` and
  nothing else, and `jsonschema` is explicitly test-only. The Jira client uses
  `urllib.request` from the standard library.
- **A `JiraWorkStore`.** That remains
  `2026-06-19-remote-adapter-jiraworkstore`, and this initiative does not
  advance it.
- **Capability-metadata synchronization.** That remains
  `2026-06-19-tracker-sync-for-capabilities`.
- **Re-solving concurrency-safe claims for callers sharing one local store.** The
  request points at a `2026-06-22-concurrency-safe-work-claims-…` item as the
  narrower fallback. **That work completed on 2026-08-12** (commit `b4f3c256`)
  and what it shipped is live: `start` claims through an atomic rename into
  `.claiming/` (`tcw/store/fs.py:3722`) and stamps `owner` and `started`. The
  local-claim problem is solved, and this initiative builds on it rather than
  duplicating it. What it must *not* do is treat the two claims as one; see
  `## Design`, the identity decision.

  An earlier draft of this spec said the item was "not on this board, so the
  cross-reference is stale". That was wrong, and how it was wrong is worth
  recording: `.gitignore:29` excludes `docs/work/completed/*`, so **no resolved
  item is visible to `tcw work list --all` in any checkout**. A missing row is not
  evidence that work was never done.

## Design — child boundaries and ordering

Five children, each an `--initiative` child of this epic, each with its own
`initial-request.md`, `spec.md` and `plan.md`. Ordering is recorded as
`--blocked-by`, because `--initiative` carries no dependency relation and
children with a required order would otherwise all read as workable at once.

### The identity decision belongs to the epic

**There are now two claims and two identities, and this spec settles how they
relate rather than letting three children each guess.**

- The **local** claim is the atomic rename into `.claiming/`
  (`tcw/store/fs.py:3722`), and its identity is `WorkItem.owner`, taken from
  `--owner`, then `TCW_WORK_OWNER`, then the Git email (`tcw/work/cli.py:785`).
- The **tracker** claim is the configured ready-to-in-progress transition, and
  its identity is whoever the configured credentials authenticate as.

The rules, binding on C2, C4 and C5:

1. `tracker import` does **not** set `owner`. Importing binds a ticket to a
   backlog item; it does not start work. `owner` is still set by `start`, as it
   is for every other item, and an imported item that nobody has started has no
   owner. Setting it at import would make the board claim someone is working on
   something they have not begun.
2. The binding records the tracker identity that won the claim. That is a
   separate field from `owner` and never overwrites it.
3. In strict mode, C4 verifies the **tracker** identity: that the ticket is still
   assigned to whoever the local credentials authenticate as. It does not compare
   that identity to `owner`, because the two namespaces are not comparable — a
   Git email and a Jira account id are different things, and mapping them is a
   directory problem this initiative is not solving.
4. A second developer who pulls a linked backlog item and runs `start` gets the
   local claim and no tracker claim. Their next linked mutation is refused in
   strict mode because the ticket is not assigned to them. That refusal is
   correct and must name both facts: the item is theirs locally, the ticket is
   not.
5. Criterion 2's "names the current assignee" means the **tracker** assignee.

This is a decision, not a preference, and a child that needs to depart from it
returns here rather than deciding locally.

### C1 — Configure a tracker and read its tickets

The foundation, and useful alone: a developer can see their assigned tickets
without leaving the terminal.

- Parse a `work.tracker` block from the node sentinel (`tcw-config.yaml`,
  `tcw/store/project.py:21`). Read credentials only from environment variables
  the config names; never store a secret in the repository.
- Expose the parsed block through a `WorkStore` method, following the existing
  pattern for config-derived facts — `documentation()`
  (`tcw/store/base.py:2266`), `lifecycle_policy()` (`tcw/store/base.py:2277`),
  `registered_tags()` (`tcw/store/base.py:2286`).
- A Jira Cloud client over `urllib.request`: resolve the authenticated user,
  run the configured JQL, fetch one issue, discover workflow transitions.
- Distinguish authentication, permission, validation, not-found, rate-limit and
  transient-network failures as separate, named outcomes. This taxonomy is built
  here because every later child depends on telling "your token is wrong" from
  "the ticket moved".
- Commands: `tcw work tracker list`, `tcw work tracker show <ticket>`. Both
  read-only. `tracker` is a nested subcommand group beside the existing `inbox`,
  `tags`, `tombstone` and `stage` groups (`tcw/work/cli.py:1846`,
  `tcw/work/cli.py:1879`, `tcw/work/cli.py:1968`).
- Malformed tracker configuration fails closed through `tcw validate`
  (`tcw/validate.py:93`) without breaking ordinary board reads.
- **Reports whether a ticket's claim transition is exclusive**, from the
  transitions the ticket itself offers. Answerable only for a ticket already in the
  status the claim leads to; otherwise reported as not determined. Costs one field
  on a call `tracker show` already makes, needs no permission beyond viewing the
  issue, and works on team-managed and company-managed projects alike.
- **Does not** read a project's workflow definition, and makes no network call from
  `tcw validate`. Both moved to C4 — see that child's boundary. Revised 2026-09-12
  after review; C1's own spec records why in full.

Blocked by: nothing.

### C2 — Claim a ticket and bind it to a work item

The first delivery completes here. C1 and C2 together are the scope agreed on
2026-09-12.

- Add `tracker.yaml` to `WORK_SIDECARS` (`tcw/store/base.py:1790`) with
  `yaml_mapping` validation. This buys revision-protected read and write
  (`tcw/store/fs.py:6314`), participation in the item's modified timestamp
  (`tcw/store/fs.py:4173`), and a `serve` read endpoint, at no cost.
- The binding: schema version, provider id, ticket reference and stable URL, TCW
  project id, part id, claimed remote identity. No credentials.
- The idempotency key is `(TCW project id, provider id, ticket reference, part
  id)`, `part` defaulting to `default`. Re-running an import with the same key
  returns the existing item; a different `--part` deliberately creates another.
- `tcw work tracker import <ticket> [--part <id>] [--title <title>]`: claim the
  ticket, then create the local item. **The claim is a read-modify-verify
  sequence, not a single write**, because the experiment showed a transition's
  response carries no contention signal: read the issue and require it in the
  configured ready state and unassigned or already assigned to the authenticated
  identity; apply the claim transition and the assignment; re-read and require the
  issue in the claimed state assigned to that identity. Contention is detected
  from that final read, never from the transition's status code — a rejected
  transition returns `HTTP 400` with "Transition id 'N' is not valid for this
  issue", which is the same response an operator gets for a misconfigured
  transition id, and the two must not be conflated.
- The ticket's product prose is snapshotted into the item's `intake`, not its
  request — `create` takes them as separate arguments precisely so an adapter can
  tell them apart (`tcw/store/base.py:2047`), and `BODY_ORDER`
  (`tcw/store/base.py:1786`) makes the intake the fallback body. The `request`
  stage still has to run.
- `tcw work tracker link <slug> <ticket> [--part <id>]` binds an existing item;
  it refuses a second primary binding. `tcw work tracker unlink <slug> --reason
  <text>` is an audited repair and records the reason.
- Failure windows: a successful remote claim followed by a failed local create
  leaves the ticket claimed, and re-running the import detects the same-identity
  claim and completes the binding rather than failing.

Blocked by: C1.

### C3 — Synchronize the lifecycle outward

- A deterministic outbound event recorded with the local transition, the local
  transition committed, immediate delivery attempted, and `tcw work tracker sync
  [<slug> | --all]` retrying until the remote target is observed. A temporary
  outage must never undo a local transition that already happened — the store
  already has a type for exactly this shape of news, `TransitionCommitError`
  ("the item **did move**", `tcw/store/base.py:1815`) and its `PublicationError`
  subclass (`tcw/store/base.py:1827`).
- Mapping: bindings key on the *move*, so the existing `TRANSITION_IDS`
  (`tcw/store/base.py:770`) are the mapping keys, and `complete --resolution
  done` firing `complete` while `--resolution wontfix` fires `discard` is
  behavior to reuse, not to reinvent.
- Delivery state is derived from the observed remote state plus deterministic
  event ids, so a successful delivery needs no second cleanup commit.
- Only stable links and short summaries go outward. No `spec.md`, `plan.md`,
  `outcome.md`, capability prose, diffs or code references.
- Reports remote drift; never follows it automatically.
- **Surfaces its own state.** `tcw work show` and `tcw work list` gain the
  current / pending / conflicting indicator here, moved from C5, because this is
  the child that creates those states.

Blocked by: C2.

### C4 — Refuse work no ticket authorizes

- Strict mode gates `work new` and `work start` for unlinked items, verifies
  remote assignment and state before a linked mutation, and refuses the
  destructive `drop` (`tcw/store/base.py:2812`) for a linked item in favour of a
  preserved discard resolution.
- **Owns the `strict` configuration key**, which no earlier child accepts, and
  introduces it together with the gates that honour it. A half-honoured flag would
  tell a user their work is gated when it is not.
- **Owns the authoritative workflow-shape verdict**, moved here from C1 on
  2026-09-12. Reading a project's workflow definition decides, before any ticket
  exists, whether the claim transition can exclude a second claimant.
  `POST /rest/api/3/workflows` with `projectAndIssueTypes` was measured answering
  it in one call, and the verdict logic was measured correct on both fixtures. It
  lives here because this is where the consumer is, and because it brings three
  problems C1 could not carry: it needs a project identifier no configuration key
  holds, it may require site-administrator permission, and a severity tier
  `tcw validate` does not have (`tcw/validate.py:220`, `tcw/cli.py:447`).
  **C4 must settle the permission question with a non-admin token before designing
  around the route**, and must not put the call on any lifecycle-transition path:
  `tcw validate` is a `pre` hook on `complete` in this repository's own config
  (`tcw-config.yaml:65`), and a `pre` failure means the store is not touched
  (`tcw/work/hooks.py:115`), so a network call there makes completing an item
  depend on Jira being reachable.
- Drift blocks a strict-mode mutation: the conflict is recorded and reported, and
  local artifacts are preserved for explicit reconciliation.
- No bypass flag. Changing strictness is a reviewable `tcw-config.yaml` edit.

Blocked by: C3, because the drift check is C3's.

### C5 — Surface the binding

**Narrowed after review.** An earlier draft gave C5 "whether the remote state is
current, pending or conflicting" while also declaring it independent of C3. Those
cannot both hold: *pending* is derived from C3's delivery state and *conflicting*
from C3's drift report, so after C2 alone two of the three states have no
producer. C5 is now the binding's **identity** only, and the sync-state indicator
moves to C3, which owns the state and should surface what it creates.

- `tcw work show` and `tcw work list` name the provider, the ticket, its link,
  and whether the item is bound or unbound. Nothing about delivery or drift.
- `tcw work show --json` is a **closed, versioned document**: `WORK_ITEM_SCHEMA`
  sets `additionalProperties: false` and requires every declared property
  (`tcw/work/projection.py:102`), and
  `test_the_schema_declares_exactly_the_model_plus_two`
  (`tests/test_projection.py:113`) pins the properties to `WorkItem`'s fields.
  Surfacing tracker state there is one of exactly two choices — a `WorkItem`
  field, which flows into the document automatically and forces the matching
  schema entry in the same change, or a `SCHEMA_VERSION` bump. C5's spec picks
  one and says why. It is not a free-form addition.
- The web app displays the binding and does not mutate it. Note that C2, not C5,
  is where this is won or lost — see Risk 1.

Blocked by: C2. Genuinely independent of C3 and C4 now that the sync-state
indicator has moved to C3, and it must not be chained to them — a false blocker
is a lie the tool enforces.

### Ordering summary

```
C1 ──> C2 ──> C3 ──> C4
              └────> (C5 blocked by C2 only)
```

## Abstraction litmus test

Every operation this initiative adds or changes, with a verdict.

| Operation | Verdict | Why |
| --------- | ------- | --- |
| Read the node's tracker configuration | **store interface** | A config-derived fact about the node, exactly like `documentation()`, `lifecycle_policy()` and `registered_tags()`. Any adapter can answer it. |
| Read and write the `tracker.yaml` binding | **model** | `read_sidecar`/`write_sidecar` are already abstract (`tcw/store/base.py:2451`). The registry gains an entry; the interface gains nothing. |
| The binding's content — ticket reference, URL, identity, part id, event ids | **model** | Portable data. A tracker-backed store would hold the same facts in its own fields. |
| List / show / claim a ticket, apply a remote event | **neither — a new module beside the store** | These are operations on the *tracker*, not on the work store. Putting them behind `WorkStore` would make every adapter owe a tracker implementation, which is wrong: a store's job is to hold items. A coordinator composes the tracker client with the configured store, and no tracker network call goes inside `FsWorkStore`. |
| Claim, assignment, external reference, remote transition, conflict | **model concepts** | Portable. Every one of them has an analogue in any tracker. |
| JQL, Jira REST paths, transition-id discovery, environment variable names, HTTP status mapping | **adapter private detail** | Jira-shaped. None of it appears in a signature outside the Jira module. |
| Surfacing tracker state in the JSON projection | **model** | A `WorkItem` field or a schema version bump; both are model-level and neither is filesystem-specific. |
| Strict-mode gates on `new`, `start`, `drop` | **model** | Policy over abstract transitions, expressed against `TRANSITION_IDS`. |

No operation in this initiative is a filesystem trick. The one thing that reads
like a filesystem convenience — a sidecar file — is already an abstract named
resource with a bounded registry, which is why it is the right place for the
binding.

## Acceptance criteria

For the initiative as a whole. Each child's own spec carries the criteria for its
own code; these are the ones that only make sense across children.

1. With no `work.tracker` block in `tcw-config.yaml`, every existing `tcw work`
   command produces byte-identical output and the same exit code as it does on
   the commit before C1. Demonstrated by the existing suite passing unchanged,
   with no test edited to accommodate the bridge.
2. Two concurrent `tcw work tracker import` runs against one ticket produce
   exactly one local work item. The loser creates no item, exits non-zero, and
   its message names the current assignee and workflow state.
3. Running `tcw work tracker import <ticket>` twice with the same `--part`
   produces one item and reports the second run as already bound. Running it
   twice with different `--part` values produces two items, each with its own
   binding.
4. A claim that succeeds remotely and then fails locally leaves the ticket
   claimed, and a re-run of the same command completes the binding rather than
   reporting a conflict.
5. A local lifecycle transition whose outbound delivery fails leaves the item in
   its new status, exits non-zero, and says the local move happened and the
   tracker is pending. A later `tcw work tracker sync` reaches the tracker
   without a second local transition.
6. A tracker event already applied remotely is reported as delivered, and
   produces no duplicate comment or transition.
7. With strict mode on and a ticket reassigned away from the authenticated
   identity, the next linked mutation is refused, the refusal names the
   conflict, and no artifact is deleted or rewritten.
8. No secret appears in any tracked file, any sidecar, or any command's stdout
   or stderr. Checked by a test that sets a sentinel token value and greps the
   whole work store plus captured output for it.
9. `tcw validate` exits non-zero on a strict tracker configuration missing a
   required claim or terminal mapping, names the missing key, and still lets
   `tcw work list` and `tcw work show` run. It also exits non-zero when the
   configured claim transition is available from the state it lands in, and the
   message says the workflow cannot exclude a second claimant. Checked against a
   project using Jira's default simplified workflow, which fails this check.
10. `tcw work show --json` validates against `WORK_ITEM_SCHEMA` for a bound item
    and for an unbound one, and `test_the_schema_declares_exactly_the_model_plus_two`
    passes without being edited to allow an undeclared property.
11. **No code path treats the binding as proof that a claim was made.** A
    hand-written `tracker.yaml` naming a ticket nobody claimed does not let a
    strict-mode mutation through: the mutation re-reads the ticket's assignee and
    workflow state from the tracker and refuses on the tracker's answer, not on
    the sidecar's. Checked by writing a binding by hand for an unclaimed ticket
    and confirming the next linked mutation is refused.

    The earlier wording of this criterion asked that the binding "cannot be
    forged through a write surface that does not go through the claim path". That
    is unachievable and was the wrong thing to ask: the binding is a file in the
    user's own repository, so anyone who can run `tcw` can edit it in a text
    editor. The defensible property is not that the file cannot be written, it is
    that writing it buys nothing.
12. Every capability in the `## Capability changes` table reads its final status,
    and the taxonomy `external-work-tracker` Feature resolves, before this epic
    completes. `tcw capabilities check` and `tcw validate` both exit zero.

### Coverage

The Design section numbers five children, so the axes are C1 to C5. A cell names
the child that discharges the criterion, or `n/a` with what makes it so. An epic
criterion is discharged by a child's tests, not by the epic's own — the epic
writes no code.

| # | C1 | C2 | C3 | C4 | C5 |
| - | -- | -- | -- | -- | -- |
| 1 | yes | yes | yes | yes | yes |
| 2 | n/a — no claim exists until C2 | yes | n/a | n/a | n/a |
| 3 | n/a — the idempotency key is C2's | yes | n/a | n/a | n/a |
| 4 | n/a | yes | n/a | n/a | n/a |
| 5 | n/a | n/a | yes | n/a | n/a |
| 6 | n/a | n/a | yes | n/a | n/a |
| 7 | n/a | n/a | n/a | yes | n/a |
| 8 | yes — credentials are read here | yes | yes | yes | n/a — C5 adds no credential path |
| 9 | yes | n/a | yes — adds the transition mappings | yes — adds the strict requirement | n/a |
| 10 | n/a | n/a | n/a | n/a | yes |
| 11 | n/a | yes | n/a | n/a | n/a |
| 12 | yes | yes | yes | yes | yes |

Criterion 1 spans every child because every child can break it, and a single
child's suite cannot prove it stayed true after the next one landed. It is
therefore re-checked at each child's completion, not once.

## Risks

1. **Registering the sidecar puts an edit button on the binding, two children
   before C5 says the web app is read-only.** `PUT
   /api/work/<slug>/sidecars/<name>` accepts any name in `WORK_SIDECARS` and
   calls `write_sidecar` with no further gate (`tcw/serve/__init__.py:1281`). The
   only request validation is Content-Type plus a loopback-origin check
   (`_validate_mutating_request`), which is cross-site protection, not
   authorization. The `generated` marker is *reported* to the client
   (`tcw/serve/__init__.py:646`) and refuses nothing on the server, and the built
   client renders an edit button for every sidecar not marked generated.

   Two things follow, and C2's plan must carry both because C2 is where the
   registry entry lands:

   - **Mark `tracker.yaml` `generated: "yes"`.** That removes the button for
     free, and `rollup.md` is the in-repo precedent with the matching comment
     that "edit surfaces must not offer to write it"
     (`tcw/store/base.py:1795`). So C2's "at no cost" claim about reusing the
     sidecar machinery is not quite true; this is the cost.
   - **Do not try to make the file unforgeable.** See criterion 11. The
     server-side refusal for generated sidecars is a real pre-existing gap that
     also affects `rollup.md`, and it should be filed separately rather than
     absorbed here.
2. **Nothing yet names a network timeout, and the default is to block forever.**
   `urllib.request.urlopen` takes a `timeout` argument, and with none supplied it
   falls back to the global socket default, which is unset
   (`socket.getdefaulttimeout()` returns `None`). A tracker that accepts a
   connection and never answers would hang `tcw work tracker list` — and, once C3
   lands, a lifecycle transition — with no way out but a signal. C1 sets an
   explicit timeout on every request and C1's spec states the value; this is a
   requirement, not an implementation detail, because the alternative is a CLI
   that stops responding.

3. **A Jira client on `urllib.request` is more code than `requests`.** Retries,
   pagination, timeouts and error mapping all get written by hand. The mitigation
   is that the client stays small because the operation set is small; the
   alternative — a first runtime dependency — changes what installing `tcw`
   means for every user, which is a worse trade.
4. **Deciding against a provider abstraction may prove wrong.** If a second
   provider is wanted sooner than expected, the seam has to be widened after the
   fact. Accepted: extracting an interface from one working implementation is
   ordinary work, and guessing the interface from zero is how the wrong one gets
   built.
5. **C5 touches a closed schema.** A careless addition either fails the pinning
   test or forces a `SCHEMA_VERSION` bump that every consumer of `--json` sees.
   Mitigated by making the choice explicit in C5's spec rather than in code
   review.
6. **Strict mode can lock a project out of its own backlog.** Enabling it before
   existing open items are linked blocks their next mutation by design. The
   request already says so; C4 must make the refusal name the fix.
7. **The epic spans a lot of calendar time.** Jira's REST surface, and the
   simultaneous-transition behavior the claim depends on, can change between C1
   and C4. Mitigated by keeping the claim's conflict handling in one place and
   by C1's error taxonomy being explicit rather than incidental.

## Notes

**Deviation from the request, decided 2026-09-12.** The request's goal 6 asks to
"remain provider-neutral at the coordination boundary and ship Jira Cloud as the
first provider", and its `## Provider-neutral architecture` section specifies a
nine-operation provider contract plus a deterministic fake provider. This spec
builds Jira directly behind a narrow seam and defers the interface until a second
provider exists. The reasoning: an interface with one implementation is a guess
about the second one, and the testing benefit the fake provider was carrying is
available by faking the HTTP layer instead. The abstract-spine litmus test is
unaffected — it governs the *store* model, and the verdict table above holds a
tracker client outside `WorkStore` either way. This was the user's decision in
the planning session, recorded here rather than applied quietly. Everything else
in the request stands as filed.

**That assumption was tested on 2026-09-12, and it is false as stated.** See
`jira-claim-experiment.md`. Jira's default simplified workflow offers every
transition from every state, so the claim transition applied twice returns `204`
both times and two simultaneous claims both succeed. Whether serialization happens
is beside the point: the second request is a legitimate no-op, not a loser. The
design consequence is already folded into C1 (verify the workflow can exclude) and
C2 (claim by read-modify-verify), and goal 1 is restated as conditional. What
remains untested is a **conforming** workflow — one where the claim transition is
unreachable from its destination — and C2 must build one in the `TCWTEST` fixture
and rerun the experiment before freezing.

**This epic is `type: epic` by a hand-written field.** No CLI verb promotes an
existing item, and the gap is filed as
`docs/work/inbox/no-cli-verb-promotes-an-existing-item-to-an-epic.md`.
