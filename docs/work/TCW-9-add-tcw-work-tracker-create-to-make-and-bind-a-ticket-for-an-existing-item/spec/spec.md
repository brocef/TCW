# Spec — Make and bind a ticket for a work item, on demand and on filing

## Capability changes

**New — 2**, seeded `Missing` at planning and flipped at completion:

- `work/create-a-ticket-for-an-existing-item` — `tcw work tracker create`, one
  item or many, idempotent, with a dry run.
- `work/file-work-with-its-ticket` — an item filed with `tcw work new` (or
  `tcw work inbox accept` of a raw entry) gets its ticket as part of being filed,
  under a setting that is off by default.

**Changed — 1:**

- `work/require-tracker-backed-work` — strict mode's description says
  `tcw work new` and `tcw work inbox accept` "refuse and point me at
  `tcw work tracker import <ticket>`". That stays true, but it is now one of
  *three* arrangements rather than the only alternative to doing nothing, and
  the description has to say which one wins when both settings are on.

Both new capabilities keep `Feature: external-work-tracker`, the Feature the
six existing tracker capabilities already use. No taxonomy entry changes.

## Problem

**The tracker integration only runs one way.** `tcw work tracker import` creates
an item from a ticket and `tcw work tracker link` binds an item to a ticket that
must already exist — `link`'s own help says the ticket "is read — which is how a
key that does not exist is refused — and not written to". Nothing creates a
ticket for an item. The subcommand list is
`{list,show,import,link,claim,release,unlink,sync}`; there is no `create`.

So a project that files work in TCW can never get that work into its tracker
without leaving TCW to do it.

**This repository proved it at its own expense on 2026-09-20.** The board held
53 open items and **zero** tracker bindings — no `tracker.yaml` anywhere — while
the TCW Jira project held one ticket. Closing that gap meant a script against
Jira's REST API that created each issue, read its available transitions, moved
it out of the workflow's initial status, ran `tcw work tracker link`, logged each
created key before binding so an interrupted run could resume, and skipped items
that already had a binding. GitHub #43 reports the same thing at four times the
size: 116 of 125 open items across six nodes.

Every step of that script is information TCW already holds. Every adopting team
writes it again.

**Two specific hazards, both now demonstrated rather than predicted.**

1. **A created ticket lands where the inbox looks.** A new Jira issue enters the
   workflow's initial status — `Triage` in this project — and
   `work.tracker.inbox-query` here is `project = TCW AND status = Triage`. A
   ticket created and left there comes back through `tcw work inbox` as
   untriaged inbound work, offering to create a **second** item for the one that
   just created it. The backfill avoided this only because it moved every ticket
   `Accept` → `To Do` before binding.

2. **There is no configured status for a backlog item's ticket.**
   `TRACKER_STATUS_KEYS = ("active", "review", "completed", "discarded")`
   (`tcw/store/base.py:1141`) and `statuses` refuses any other key
   (`tcw/store/base.py:1360-1361`, `"{where}.{key}: unknown key"`), while
   `WORK_STATUSES` (`tcw/store/base.py:814`) includes `backlog`. So the one
   status almost every created ticket starts in is the one the configuration
   cannot name. The backfill hard-coded `To Do`.

**And a command nobody runs reproduces the gap.** This is why the request was
amended on 2026-09-20 rather than filed separately: a manual `create` fixes a
backlog once, and the next fifty items drift out again. Filing should produce
the ticket.

### Sweep

Repo-wide, for the same shape of one-directional gap:

1. `tcw work tracker` has no `create` (subcommand list above) — the reported gap.
2. `statuses` cannot name `backlog` — above. It is the same defect wearing a
   different hat: the configuration models a bound ticket's *later* life and not
   its beginning.
3. **Strict mode is the existing answer and points the other way.**
   `tcw/work/cli.py:422-426` makes `tcw work new` refuse under
   `work.tracker.strict` and send the user to `tcw work tracker import`. The
   capability `work/require-tracker-backed-work` says the same of
   `tcw work inbox accept` for a raw entry. So TCW already has an opinion about
   items without tickets — "refuse to file" — and this item adds the opposite
   one. They must be reconciled, not stacked.
4. `tcw/work/cli.py:422` exempts epics from strict mode (`and not args.epic`).
   Whatever this spec decides for epics has to be stated against that, not
   inherited from it silently.
5. No other axis has this problem: taxonomy and capabilities have no external
   mirror to push to.

## Goals

1. A command creates a ticket for an existing item and binds it — one item, or
   many — with a dry run, and is safe to re-run.
2. A created ticket is never left in a status the inbox query would select.
3. Filing an item can create its ticket, under a setting that is **off by
   default**, so this backlog's drift cannot recur silently.
4. A tracker that does not answer never costs someone their work item.
5. How this sits beside `work.tracker.strict` is decided and written down.

## Non-goals

- **Writing item properties into ticket fields** beyond what creation needs —
  GitHub #37, tracked in
  `2026-09-15-write-work-item-properties-to-mapped-tracker-fields`. That item's
  own notes keep it separate, and this spec does not widen into it.
- **Backfilling closed items.** `completed` and `discarded` items, and the 218
  graveyard tombstones, get no tickets. A ticket created only to be closed is
  noise.
- **Changing `import`, `link`, `claim`, `release`, `unlink`.** They keep their
  current behaviour exactly.
- **A second tracker provider.** `TRACKER_PROVIDERS = ("jira-cloud",)` stays a
  one-value enum; this adds no provider abstraction beyond what creation needs.
- **Deciding claim exclusivity from a workflow definition** — a separate item.

## Design

Seven rules. The numbering is what the Coverage table crosses.

**Rule 1 — one operation, two callers.** Creating-and-binding is a single
operation in the tracker layer. `tcw work tracker create` is one caller; the
filing path (Rule 5) is the other. Neither reimplements it, and the automatic
path must be unable to do anything the explicit command cannot.

**Rule 2 — what the ticket is made from.** Summary from the item's title.
Description from its request, or its intake when there is no request, converted
to the tracker's format. Issue type, parent and any project-specific fields come
from configuration under a new `work.tracker.create` block, which joins
`TRACKER_KEYS` (`tcw/store/base.py:1114`) and is inherited like the rest of the
block. The reporter's proposed defaults — Epic for an item with children, Bug
for an item tagged `bug`, Task otherwise — are a starting point the plan may
keep, but each is a **configured rule**, not a literal in the code, because a
project's issue types are its own.

**Rule 3 — where the ticket lands, and the refusal that makes it safe.**
`statuses` gains `backlog` as a legal key (`TRACKER_STATUS_KEYS`), so a project
can say where a not-yet-started item's ticket belongs.

After creating, the operation moves the ticket to the status mapped for
`backlog`, applying the transition the workflow offers **to that destination** —
the backfill needed `Accept` to reach `To Do`, and the transition's name is not
the target's name. **Corrected during implementation:** an earlier draft of this
paragraph said the operation "walks the workflow's transitions", which reads as
a multi-hop search. Neither this nor `sync` does that. Both take a single hop
chosen by where it lands (`assess_move`, `tcw/tracker/sync.py:205`), treat a
ticket already in the target as nothing to do, and refuse rather than guess when
the workflow offers more than one way in.

**If no status is mapped for the item's status, creation refuses and creates
nothing.** This is the rule that makes hazard 1 unreachable rather than merely
unlikely: a project that has not said where backlog tickets go gets a refusal
naming `work.tracker.statuses.backlog`, not a ticket sitting in the inbox query.
Fail-closed matches how the rest of this configuration behaves.

**Rule 4 — re-running is safe, and interruption is survivable.** An item that
already has a binding is skipped, never given a second ticket. The created key
is recorded before the binding is attempted, so an interruption between the two
resumes by linking rather than by creating a duplicate. `--dry-run` reports what
would be created and writes nothing, locally or in the tracker.

**Rule 5 — filing can create the ticket.** A new setting under
`work.tracker.create` — **default off** — makes item creation call Rule 1. The
verbs it applies to are exactly the ones strict mode already gates, because they
are the ones that bring an item into being:

- `tcw work new` (`tcw/work/cli.py:418-426`);
- `tcw work inbox accept` of a **raw** entry — accepting a *ticket key* is
  already `import`, which produces a bound item and needs nothing.

**Epics are included, and that is a deliberate departure.** Strict mode exempts
them (`tcw/work/cli.py:422`, `and not args.epic`) because it cannot demand a
claimed ticket for a container nobody works directly. Creation has no such
problem, and an epic on the board with no ticket is a hole in the tracker's
picture of the work. The spec states this rather than inheriting the exemption
by accident.

**Corrected in review:** this originally said an epic with no ticket "breaks
parent links for its children". It does not, because there are no parent links
to break — TCW sets no parent or epic link in the tracker and `create_issue`
takes no parent. The conclusion stands; the reason given for it did not, and it
had been repeated into the command's help text and the user guide.

**Rule 6 — a tracker that does not answer costs nothing.** `tcw work new` works
today with no network and no credentials, and keeps doing so. When creation is
enabled and the tracker cannot be reached, **the item is still created**, the
ticket is recorded as owed, and the command says so.

**Corrected during implementation:** this rule said `tcw work tracker sync`
would settle it later, and it does not. `sync` retries a status change for an
item that *already has* a ticket, and its whole implementation is about a
binding; an item owing a ticket has none. `tcw work tracker create`, with or
without `--all`, is what settles the debt. `sync` asked about such an item now
says so and names that command. Correspondingly, the owed record is a sibling
key in the same sidecar read by the same code path rather than a reuse of the
sync record, which only exists for a bound item.

The alternative — refusing to file — is rejected: it converts a tracker outage
into lost thinking, and the inbox exists precisely so an idea can be captured
before anything else is possible.

**Rule 7 — strict mode wins, and both together is allowed.**

**Corrected after implementation, in review:** the rest of this rule was wrong,
and the code it cites disproves it. `_new` refuses under strict mode only
`and not args.epic`, and creation-on-filing covers epics deliberately, so a
project can mean "tasks come from tickets, epics filed here get theirs made".
Rejecting the pair also made `tracker_config` fail closed on the whole block,
disabling `import`, `link`, `sync` and `claim`. The validation error is gone and
criterion 14 is inverted. The original text follows, for the record.

`strict` answers "may work proceed without a claimed ticket". The new setting
answers "does filing produce a ticket". They are different questions, so
`strict` keeps its current meaning and refusal path unchanged.

But they cannot both be satisfied: strict refuses `tcw work new` outright
(`tcw/work/cli.py:422-426`), so a project with both set would never reach
creation. Rather than let one silently shadow the other, `tcw validate` reports
the combination as a configuration problem, naming both keys. Three arrangements
remain expressible and each is honest:

| `strict` | create-on-filing | `tcw work new` |
| --- | --- | --- |
| off | off | files, no ticket — today's default, how this backlog drifted |
| off | **on** | files, and the ticket follows |
| on | off | refuses; ticket first, via `import` |
| on | on | epics file and get a ticket; everything else is refused |

## Abstraction litmus test

> Could a non-filesystem store implement this operation, even if less elegantly?

**Creating a ticket is not a store operation at all, and that is the point.**
The work store holds items; the tracker is a separate collaborator that
`tcw/tracker/` talks to. Rule 1's operation lives there, beside `import` and
`link`, and the store is only asked for the item and to write the binding
sidecar — both things it already does for `link`.

So the litmus applies to what this adds to the *store* interface, which is
nothing. The store gains no method that only a filesystem could honour; a
hypothetical `JiraWorkStore` would be the odd case here, not the normal one,
because for it the item and the ticket are the same object and creation is
already implied.

**Rule 3's status mapping is the one thing that could have gone wrong.** Naming
a *transition* would have been provider-specific and unreachable for a tracker
without workflows. It names a **status**, and lets the provider say which of the
routes it offers lands there — the same rule `sync` already follows, for the
same reason.

**Harness compatibility.** Every mechanism here is in the `tcw` CLI, which
behaves identically under Claude and Codex. Nothing is carried by a skill, a
hook or injected context. The skills that mention the tracker (`work`,
`configure`) gain documentation, not behaviour.

## Acceptance criteria

1. `tcw work tracker create <slug>` creates a ticket, binds the item, and the
   item's `tracker.yaml` names the created key. `tcw work list` shows
   `ticket: <key>` for it.
2. The created ticket is **not** in any status `work.tracker.inbox-query`
   selects. Checked by running the configured inbox query after creation and
   asserting the new key is absent from its results.
3. With no `statuses.backlog` entry, `tcw work tracker create` exits non-zero,
   names `work.tracker.statuses.backlog`, creates no ticket, and writes no
   binding. **Corrected during implementation:** this said
   `work.tracker.statuses.<status>`, which implied the refusal depends on the
   item's own status. It does not. A created ticket is always placed at the
   backlog status whatever the item's status is (Rule 3 below says so), so the
   only entry creation can be missing is `backlog`, and that is the only key the
   refusal can name. Verified by querying the tracker for issues created
   during the run: there are none.
4. `statuses.backlog` is accepted by `tcw validate` where it is refused today
   (`tcw/store/base.py:1360-1361`), and an unknown key is still refused.
5. Running `tcw work tracker create <slug>` twice creates one ticket. The second
   run reports the existing binding and exits zero.
6. An interruption between creating and binding resumes by linking: with a
   recorded key whose item has no binding, the next run binds that key and
   creates nothing.
7. `--dry-run` reports what would be created, creates no ticket, and writes no
   binding. Verified against the tracker, not only against the local tree.
8. `tcw work tracker create --all` creates tickets for every unbound open item
   and skips bound ones, in one run.
9. With creation-on-filing **off** (the default), `tcw work new` behaves exactly
   as it does today: no ticket, no binding, no tracker call. Asserted with no
   credentials in the environment.
10. With it **on**, `tcw work new "<title>"` produces an item **and** a bound
    ticket, and the ticket obeys criteria 2 and 3.
11. With it on and the tracker unreachable, `tcw work new` still creates the
    item, exits zero, says the ticket is owed, and records it. A later
    `tcw work tracker create` creates and binds the ticket.
    (**Corrected in review** — it originally named `tcw work tracker sync`,
    the same mistake as Rule 6 and caught later, because correcting the rule
    did not correct the criterion that repeated it. `sync` is about a binding;
    an item owing a ticket has none.)
12. With it on, `tcw work inbox accept` of a raw entry creates a bound item;
    accepting a ticket key still goes through `import` and is unchanged.
13. With it on, `tcw work new --epic` creates a bound ticket, unlike strict
    mode's exemption.
14. `strict: true` together with creation-on-filing validates, and a filed epic
    still gets its Epic-typed ticket while a filed task is still refused.
    (**Corrected in review** — it originally required `tcw validate` to report
    the pair as a problem. See Rule 7.)
15. `strict: true` alone still refuses `tcw work new` with today's message
    pointing at `tcw work tracker import` — asserted by the absence of any new
    wording, so this item cannot quietly change that path.
16. `pytest` passes and `tcw validate` on this repository exits 0.

### Coverage

Criteria against the seven design rules. `n/a` carries the reason.

| # | R1 one op | R2 content | R3 status/refusal | R4 idempotent | R5 on filing | R6 owed | R7 strict |
| - | --------- | ---------- | ----------------- | ------------- | ------------ | ------- | --------- |
| 1 | ✓ | ✓ | ✓ | n/a — first run | n/a — explicit verb | n/a — tracker answers | n/a |
| 2 | n/a | n/a | ✓ the hazard itself | n/a | n/a | n/a | n/a |
| 3 | n/a | n/a | ✓ the refusal | n/a | n/a | n/a | n/a |
| 4 | n/a | n/a | ✓ the config key | n/a | n/a | n/a | n/a |
| 5 | n/a | n/a | n/a | ✓ | n/a | n/a | n/a |
| 6 | n/a | n/a | n/a | ✓ resumption | n/a | n/a | n/a |
| 7 | n/a | ✓ reports content | ✓ reports target | ✓ writes nothing | n/a | n/a | n/a |
| 8 | ✓ same op per item | n/a | n/a | ✓ skips bound | n/a | n/a | n/a |
| 9 | n/a | n/a | n/a | n/a | ✓ the default | n/a | n/a |
| 10 | ✓ same op | ✓ | ✓ | n/a | ✓ | n/a | n/a |
| 11 | n/a | n/a | n/a | ✓ sync must not double-create | ✓ | ✓ | n/a |
| 12 | ✓ | n/a | n/a | n/a | ✓ the second verb | n/a | n/a |
| 13 | n/a | n/a | n/a | n/a | ✓ epics | n/a | ✓ departs from the exemption |
| 14 | n/a | n/a | n/a | n/a | ✓ | n/a | ✓ |
| 15 | n/a | n/a | n/a | n/a | n/a | n/a | ✓ unchanged |
| 16 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

Criterion 15 is written as the absence of a change, deliberately: strict mode's
refusal is existing behaviour this item could break without any test noticing,
because every other criterion here is about the new paths.

## Risks

- **This is two landings in one item.** Rules 1–4 are the command; Rules 5–7 are
  the automatic layer and cannot be built first. The plan must sequence them so
  the suite is green between them. If sequencing them turns out to need two
  separate plans, decompose rather than ship a plan nobody can follow — the
  request was folded deliberately, but folding the *request* does not oblige a
  single landing.
- **Idempotency is the expensive thing to get wrong.** A `--all` run that
  double-creates leaves duplicate tickets in a shared tracker, which is not
  undoable from TCW. Criteria 5, 6 and 8 exist for it, and criterion 11 extends
  it to the owed path — where the same item could be created by `sync` and by a
  retried filing.
- **Creation-on-filing changes what a failed command costs.** Today
  `tcw work new` either files or does not. With Rule 6 it can half-succeed: item
  filed, ticket owed. That state must be visible — an item whose ticket is owed
  should be distinguishable on the board, not just in a sidecar nobody opens.
- **The status-mapping refusal will annoy existing users.** Anyone who sets
  `statuses` today has no `backlog` entry, so their first `tracker create` will
  refuse. That is the correct trade against silently feeding the inbox query,
  but it must be in the release notes, not discovered.
- **Issue-type and parent rules are where provider assumptions hide.** Epic /
  Bug / Task are Jira's defaults, not every tracker's. Keeping them configured
  (Rule 2) is what stops the one-provider enum becoming a one-provider design.

## Notes

- The request's four questions are answered here: Rule 6 (unreachable tracker),
  Rule 5 (which verbs), Rule 7 (strict), Rule 3 (initial-status trap).
- The 2026-09-20 backfill is evidence, not design. Its `--sync-status` asymmetry
  — backlog tickets left unassigned, the active item claimed and assigned — is
  behaviour Rule 1's operation should derive from the item's status rather than
  leave to a flag, and the plan should name a task for it.
- GitHub #43 stays open until this ships, per the request and this project's
  rule that an issue is answered after publication.
