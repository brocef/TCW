# Working from Jira

A TCW project can name the Jira Cloud site its team works from. It can then read
tickets, take a ticket as a work item, record that an existing item and a ticket
are the same work, and keep a ticket's status in step as its item moves through
the lifecycle.

```sh
tcw work tracker list                       # tickets the configured query selects
tcw work tracker show ENG-482               # one ticket, and whether it is yours to take
tcw work tracker import ENG-482             # take the ticket and get a work item for it
tcw work tracker link <slug> ENG-482        # record that an item and a ticket are the same work
tcw work tracker unlink <slug> --reason "wrong ticket"
tcw work tracker sync --all                 # retry tickets that did not follow their items
```

Two things hold whatever you configure:

- **A project with no `tracker` block behaves exactly as it would without this
  feature.** No setting becomes required, no command reaches the network, and no
  tracker code is even loaded.
- **`tcw validate` never contacts Jira.** Projects commonly run it as a check
  before an item can be completed, and a check that failed on that step stops the
  item moving. Finishing your work must not depend on Jira being reachable, on
  the credential variables being set in that shell, or on a token that has not
  expired.

Which commands reach Jira: `list`, `show` and `link` read a ticket; `import`
changes the ticket and then writes the work item; `unlink` touches only your
repository and needs no tracker configured. For an item linked to a ticket,
`start`, `submit`, `rework`, `complete` and `tcw work tracker sync` also write to
the ticket. No other command reaches Jira.

## Configuration

The settings go in the project's `tcw-config.yaml`, under `work.tracker`:

```yaml
work:
    tracker:
        provider: jira-cloud # the only accepted value
        base-url: https://yourcompany.atlassian.net
        candidate-query: assignee = currentUser() AND status = "To Do"
        inbox-query: project = EX AND status = Triage # optional
        credentials:
            email-env: TCW_JIRA_EMAIL
            token-env: TCW_JIRA_API_TOKEN
        transitions:
            start: Start Progress
            complete: Finish # optional: only where the status cannot say
            discard: Abandon # optional: may also be one name per resolution
        statuses: # optional: where a linked ticket goes as its item moves
            backlog: To Do # where a *created* ticket lands
            active: In Progress
            review: In Review
            completed: Done
            discarded: Won't Do
        pre-backlog: # optional: statuses before the backlog, and the way out
            Triage: Accept
        create: # optional: how to make a ticket for an item
            project: EX
            issue-type: Task
            issue-types: # optional: by what the item is
                epic: Epic
                bug: Bug
            components: [Platform] # optional
            on-new: false # optional, default false
        exclusive-claim-transition: Start Progress # optional; required under strict mode
        comments: false # optional, default false
        link: https://tcw.example.com/work/{slug} # optional
        strict: false # optional, default false
        timeout-seconds: 15 # optional, default 15
```

| Key                     | Required | What it is                                                                                                                                             |
| ----------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `provider`              | yes      | `jira-cloud`; nothing else is accepted.                                                                                                                |
| `base-url`              | yes      | Your Jira Cloud site.                                                                                                                                  |
| `candidate-query`       | yes      | The Jira Query Language (JQL) search that `tracker list` runs.                                                                                         |
| `inbox-query`           | no       | The JQL search for tickets waiting to be triaged, which `tcw work inbox list` shows. See [Tickets in the inbox](#tickets-in-the-inbox).                 |
| `create`                | no       | How to make a ticket for an item that has none. Required before `tcw work tracker create` will run. See [Making a ticket for an item](#making-a-ticket-for-an-item).                                                |
| `credentials.email-env` | yes      | The **name** of the environment variable holding your Jira account's e-mail address.                                                                   |
| `credentials.token-env` | yes      | The **name** of the environment variable holding your Jira API token.                                                                                  |
| `transitions.start`, `.submit`, `.rework`, `.complete`, `.discard` | no | The transition each move should use, for a workflow where the status alone cannot say which one. Leave a move out and TCW works its transition out from the status the move is heading for. Naming `start` is still the right answer on a workflow with two transitions into the active status, and `tcw work tracker import` needs it whatever your workflow looks like. `transitions.start` was called `transitions.claim` in version 2.3.0 and earlier; see [Renaming the start transition](#renaming-the-start-transition). See [Naming a transition](#naming-a-transition).  |
| `exclusive-claim-transition` | no; yes under [strict mode](#strict-mode-no-work-without-a-ticket) | A transition `tracker claim` asserts through, where the workflow refuses a second claimant. **Moves the ticket**, which claiming otherwise does not. Not the same key as `transitions.start`. See [When two people claim at once](#when-two-people-claim-at-once). |
| `statuses`              | no       | The Jira **status** a linked ticket should be in for each of the item's statuses. See [Tickets following their items](#tickets-following-their-items). |
| `pre-backlog`           | no       | Each Jira status a ticket waits in **before** the backlog, mapped to the transition that takes it to `statuses.backlog`. See [Tickets waiting in triage](#tickets-waiting-in-triage). |
| `comments`              | no       | `true` to post a short comment on the ticket for each move. See [Comments on the ticket](#comments-on-the-ticket).                                     |
| `link`                  | no       | A web address added to each comment.                                                                                                                   |
| `strict`                | no       | `true` to refuse work that no claimed ticket authorizes. See [Strict mode](#strict-mode-no-work-without-a-ticket).                                     |
| `timeout-seconds`       | no       | How long to wait for Jira before giving up. Default 15.                                                                                                |

**Credentials are named, never stored.** The file holds the names of two
environment variables, and TCW reads their values only at the moment it makes a
request. Set those variables in the shell that runs `tcw`. Never write the e-mail
address or the token into `tcw-config.yaml`.

**An unknown key is reported, not ignored.** A configuration written for a later
release of TCW then complains in `tcw validate` rather than quietly doing less
than you asked. This also means **every copy of `tcw` working on the project must
understand a key before you set it**: an older copy that does not know `comments`
or `link` treats the whole `tracker` block as broken. The same goes for the
`transitions` keys other than the start one: version 2.3.0 and earlier reject the
whole block when any of them is set, and they know the start transition only under
its old name — see [Renaming the start transition](#renaming-the-start-transition).

**A block with any problem counts as no tracker at all.** TCW never uses a
half-valid configuration, because a block whose token variable name is mistyped
but whose site address is fine would otherwise send an unauthenticated request to
a real site. `tcw work list` and `tcw work show` keep working either way;
`tcw validate` is where you hear about the problem. (Strict mode is the exception:
see [Strict mode](#strict-mode-no-work-without-a-ticket).)

**TCW cannot tell you that `transitions.start` is misspelled.** A ticket that does
not offer the transition may simply not have reached the point where it applies,
or may already be past it, and a whole query of such tickets looks the same as a
typo. `tracker show` reports it as information, not as an error. Copy the name
from your project's workflow.

It *can* tell you the key is not set at all, which is a different thing: `tracker
show` says so in as many words, and `tracker import` refuses and names the key.

After editing the block, run `tcw validate`, then `tcw work tracker list` to
confirm the query and the credentials work.

## Inherited settings

A project's **board** below means its own work store: the work items it keeps.

In a workspace of connected projects that all use one Jira site, the site, the
credential variable names and the start transition — where a project sets one —
are usually the same everywhere, and only the query differs. A project can therefore write only what is
its own:

```yaml
# workspace root (tcw-config.yaml), a project with no board of its own
work:
    tracker:
        provider: jira-cloud
        base-url: https://yourcompany.atlassian.net
        credentials:
            email-env: TCW_JIRA_EMAIL
            token-env: TCW_JIRA_API_TOKEN
        transitions:
            start: Start Progress
```

```yaml
# packages/api (tcw-config.yaml)
work:
    tracker:
        candidate-query: project = EX AND component = api AND status = "To Do"
```

The rules:

- **It is opt-in.** Only a project whose own `tracker` block has at least one key
  inherits. A project with no block, or with `tracker: {}`, has no tracker and
  reports no tracker problems, whatever its parents hold. That is also how you turn
  a parent's tracker off for one project. An empty block is skipped when blocks are
  merged, so that project's own children still inherit from further up.
- **Parents are found through connected projects, not folders.** The parent must
  be connected to the child through `connected-projects` (see
  [Working across repositories](multi-repo.md)).
- **Every ancestor counts**, nearest first, all the way up, including projects that
  keep no board. The nearest file that sets a key wins that key.
- **Nested settings merge key by key.** `credentials`, `transitions` and
  `statuses` merge one key at a time, so a child can set `credentials.token-env`
  alone and keep its parent's `credentials.email-env`.
- **`null` means "not set here".** A nearer `timeout-seconds: null` lets the
  parent's value through. A child cannot remove a key a parent set; to use a
  different value, set it in the child.
- **`credentials` must come from the same file as `base-url`, or a nearer one.** A
  project that sets its own `base-url` and inherits `credentials`, or even one of
  its two keys, has no tracker, and `tcw validate` says why. This applies even when
  the address is the same as the parent's, because the rule is about which file
  chose the site. Without it, a project pointed at a different site would send its
  parent's token there.
- **Once a project opts in, the merged settings are checked in full.** A project
  with its own board that holds shared settings is checked like any tracking
  project, so it needs a `candidate-query` of its own. Keeping shared settings in a
  project without a board, such as a workspace root, avoids that.

**Problems name the file to fix.** A problem in the project's own file starts
with `tcw-config.yaml:`. A problem with a value inherited from a parent names that
parent's file and project:

```
/work/ex/tcw-config.yaml (project 'ex-root'): work.tracker.base-url: expected a non-empty string, got int
```

A missing required key is blamed on the project being checked, since no file
wrote it. A bad value in a parent is reported once for every project that
inherits it, because each of them has no tracker until it is fixed. If a declared
parent is not checked out on this machine, any tracker problem comes with one more
that names that parent and suggests `tcw provision`, since the missing settings may
be the cause.

## Claimable and exclusive

`tcw work tracker show` answers two different questions, and it keeps them
separate on purpose:

- **claimable**: does this ticket, right now, offer the transition configured as
  the claim?
- **exclusive**: would the workflow refuse a _second_ person who tried to claim
  the same ticket?

```
TCWCLAIM-6  [To Do]
summary: A ticket nobody has started
assignee: Probe
claimable: claimable
workflow: not determined from this ticket
note: 'Start Progress' leads to 'In Progress'. A ticket already in that status can
      show a workflow that is not exclusive, but never one that is. That is
      confirmed only when a claim is made, or from the workflow definition.
```

Whether a workflow is exclusive can only be seen from the status the claim leads
to. Many Jira workflows allow every status change from every status. On one of
those, applying the claim twice succeeds, so two people who both take a ticket
both succeed and neither is told. A ticket already in the status the claim leads to shows
that plainly:

```
workflow: not exclusive
note: 'In Progress' is still offered from 'In Progress', the status it leads to, so
      applying it twice succeeds and a second claimant would not be refused.
```

A ticket nobody has started reports `not determined`, because it cannot show
what happens to a second person. So does a started ticket on a workflow that _is_
exclusive: the claim is no longer offered there, so the ticket cannot say where
the claim led, and running `show` again will not settle it. Only making a claim,
or reading the workflow definition, does. Making a workflow exclusive is a change
a Jira administrator makes; TCW cannot do it for you.

## Taking a ticket

`tcw work tracker import <ticket>` takes the ticket and then creates a work item
for it.

**The claim decides from the ticket, never from Jira's reply.** Jira's answer to a
refused transition does not reliably say why: the same refusal has been seen
worded as a permissions problem when someone else had simply got there first. So
TCW:

1. reads the ticket, and refuses one that is closed or assigned to someone else;
2. applies the transition named in `transitions.start`, and refuses, naming the
   key, when nothing is set there — a claim has no status of its own to work a
   transition out from, and guessing would assign the ticket as well as move it;
3. assigns the ticket to you, only if that transition applied and nobody had it;
4. reads the ticket again, and counts the claim only if the ticket is now in the
   status the claim leads to and assigned to you.

Assigning only after the transition applied is what keeps two people apart on a
workflow that refuses a second claim: the second person's transition is refused,
so they never reach the assignment step and cannot take the ticket from the first.
If Jira did give a reason, it is shown on a `detail:` line, never as the
explanation.

**What `import` creates:**

- a **backlog** item titled `<KEY> — <summary>` (or your `--title`), with no
  owner, because importing is not starting;
- its **intake**, holding the ticket's description with a link back to the
  ticket. The `request` stage still runs as usual;
- a **binding**, `tracker.yaml` in the item's folder, naming the ticket.

**Running it again is safe.** A second `import` of the same ticket prints the item
you already have. If the first run took the ticket but stopped before creating the
item, the ticket is already yours and no longer offers the claim, so the second
run binds it without a transition ("not claimed by this run") and finishes the
job.

**One ticket can become several items on purpose**, with `--part api`,
`--part web` and so on. A part name is lowercase letters, digits and hyphens; the
default is `default`.

The check for an existing item covers unresolved items **in this project** of
**this working copy**. A binding nobody has committed and pushed is invisible to
other clones, and a binding in one project is invisible to the others, so
importing one ticket in two projects of a workspace gives an item in each, even
when they share inherited settings.

`import` refuses a ticket that is linked here but not claimed: `tcw work start`
is what claims a linked ticket.

## Tickets in the inbox

`candidate-query` selects tickets that are ready to be taken. Tickets that still
need triage are usually a different set, so they have their own setting,
`inbox-query`. It is optional; a project without it sees the inbox exactly as
before. An empty `inbox-query` is a problem, because an empty search selects every
ticket on the site.

With it set, `tcw work inbox list` prints two sections:

```
raw intake:
  2026-09-14-serve-accepts-writes.md | file | 2026-09-14-serve-accepts-writes

tracker tickets:
  EX-482 | Triage | unassigned | Login retries twice on a 502
```

An empty section says `(none)`. If Jira cannot be reached, the raw intake is still
printed, the ticket section says `(not listed)`, the reason goes to the error
stream, and the command exits 1.

`tcw work inbox show <key>` prints a ticket as `tracker show` does, followed by its
description. `tcw work inbox accept <key>` takes the ticket exactly as
`tracker import` does — the same claim, the same checks, and `--part` and `--title`
work the same way; running it again gives you the item you already have.

**An inbox entry wins a name clash.** `show` and `accept` look for an inbox entry
first and only then ask Jira, so a file named `EX-482.md` hides ticket `EX-482`.
Add `--ticket` to read the name as a ticket key anyway. TCW cannot warn you about
the clash without asking Jira every time.

**The query decides what appears.** TCW does not hide tickets that already have a
work item, so write the query to leave them out (for example by status). A ticket
both queries select appears in both `tracker list` and `inbox list`; both are true.

### Tickets waiting in triage

A ticket in a status that comes before the backlog — Jira's **Triage** is the
usual one — does not offer the transition that starts work, so on its own TCW
cannot claim it. `tracker import`, `inbox accept`, `start` and `sync` all refuse
it, and the refusal ends by naming the setting that would
change that:

```
If 'Triage' is where tickets wait before your backlog, name it and the transition
out of it under work.tracker.pre-backlog.
```

Name each such status, and the transition that takes a ticket from it to your
backlog status:

```yaml
work:
    tracker:
        statuses:
            backlog: To Do # required when pre-backlog is set
            active: In Progress
        pre-backlog:
            Triage: Accept
```

With that set, anything that takes a ticket for work first takes it out of triage:
`tracker import`, `inbox accept`, `start` (with or without strict mode), and a
`sync` that still owes the ticket a claim. TCW checks that `Accept` is offered exactly once and
leads to `statuses.backlog` **before** sending it — a transition cannot be taken
back — then reads the ticket again and claims it from there, so it notices if
somebody took or closed the ticket in between. Every command that does this says
so: `SYNC-1 was moved out of 'Triage'.`

`submit` and `rework` do it too, but only in one situation: when the item still
carries a start that never reached the tracker. That recorded start is what takes
the ticket, and it cannot take one that is still in triage, so the ticket leaves
triage first and the message says so. With no such record they take no ticket and
move nothing out of triage.

Nothing else ever does. `complete`, a discard, `tracker claim`, and
`tracker create` never do, and a ticket assigned to somebody else is refused with
nothing sent. Whether a ticket is in triage is decided by its status only, never
by whether it happens to offer a transition called `Accept`.

`tcw validate` refuses the key when `statuses.backlog` is unset, when a status is
listed twice, or when a status is also mapped under `statuses` — a status cannot be
both before the backlog and on it.

**If the claim fails after the ticket left triage**, the ticket stays in your
backlog status, which is no longer what `inbox-query` selects, so the message says
it was moved. Pick up from there with the command you were running: `sync` for
`start` and the other moves; `tcw work start` again for a
strict-mode start, which records nothing for `sync` to resume; and the same
`tracker import <key>` or `inbox accept <key>` for those.

**Without the setting**, importing a Triage ticket that is already assigned to you
still creates the item as before, leaving the ticket in Triage, and now prints a
warning naming `pre-backlog`. `tracker show` and `inbox show` add a note when a
ticket is in a status you listed.

## Holding and releasing a ticket

Taking a ticket and starting work on it used to be the same act. They are not:
`tcw work tracker claim` says a piece of work is yours, and nothing else.

```sh
tcw work tracker claim 2026-09-14-rename-the-widget
tcw work tracker release 2026-09-14-rename-the-widget
```

**`claim` sets two things and moves nothing.** It records you as the item's owner,
and assigns the ticket to you. The item's status does not change — a backlog item
stays in the backlog — and neither does the ticket's. No workflow transition is
applied.

**Ownership is one thing, not two.** The item's owner and the ticket's assignee
are written by the same command in the same run, so they cannot drift apart. If
the ticket cannot be assigned, nothing is written locally either, and the command
tells you why.

**`release` gives it back.** It clears the owner and leaves the ticket assigned to
nobody. The item's status, the ticket's status and the binding are all untouched.
Releasing an item that is already under way is the normal way to hand work over:
it stays active with no owner until somebody claims it — with `tracker claim`, or
with `tcw work start`, which takes an active item nobody holds rather than refusing
it. Until then `submit` and `rework` are refused, since the ticket is nobody's.

Under [strict mode](#strict-mode-no-work-without-a-ticket) that retake can be
refused. A released ticket is left in `statuses.active`, and strict mode takes a
ticket only through `exclusive-claim-transition` — which a workflow that excludes a
second claimant does not offer from there. The refusal says so and names the two
ways forward: assign the ticket to yourself in Jira and run the command again, or
move the ticket back to a status that offers the transition and run it again.

**Running either one twice is safe.** Claiming something you already hold succeeds
and sends nothing; releasing something nobody holds does the same. So after a
failure that left one half done, running the command again is the fix.

**An item with no ticket can still be claimed.** You get the local half, and TCW
says the ticket half was skipped. (You do still need a tracker configured in that
project — these live under `tcw work tracker`.)

### When two people claim at once

TCW assigns the ticket and then **reads it back**. Whoever assigned last holds it,
and the other person is told who has it rather than quietly losing their claim.

That is not a lock, and this guide will not pretend otherwise: if two claims
overlap exactly — both read, both assign, both read back — they can both report
success. The window is small and the usual collision is caught.

If that is not good enough for your project, and your Jira workflow genuinely
refuses a second claimant, name the transition to assert through:

```yaml
work:
  tracker:
    exclusive-claim-transition: "Start Progress"
```

With this set, a claim — `tracker claim`, or the claim `tcw work start` makes —
applies that transition before assigning, so a second
person's transition is refused and they never reach the assignment. On a ticket
that is already yours, no transition is applied and none can be — the claim has to
be safe to run twice, and TCW cannot tell a ticket whose transition ran earlier from
one somebody assigned in Jira without it. Under strict mode, what is checked there
instead is that your workflow would still refuse a second person: that the
transition is not offered again from the status it leads to. That can be read only
from a ticket in `statuses.active`; one you hold that is still in your backlog
status says nothing about it, and is accepted unchecked. **It costs a
status move**: applying a transition moves the ticket, which is the thing claiming
otherwise avoids. That is the trade, and it is why the setting is optional and off
by default — except under [strict mode](#strict-mode-no-work-without-a-ticket), which
promises that only one person can take a ticket and so requires it.

It is a different setting from `transitions.start`, which is the transition a
`tcw work start` applies to move the ticket to `statuses.active` once it is
claimed. Setting one does not set the other. When both name the same transition, a
start applies it once: the claim moves the ticket there, and nothing is left to do.

**No lifecycle move applies the transition to a ticket that is already past
`statuses.active`** — one in your review status, say. It leads *onto*
`statuses.active`, so applying it from above would move the ticket backwards, and
no lifecycle move does that. What happens instead depends on strict mode:

- **Without strict mode**, the transition is skipped. The ticket is taken by the
  assignment and its read-back alone — the ordinary claim, without the extra
  guarantee — and it is left where it is. The output says so, naming the setting,
  so you can see which kind of claim you got.
- **Under strict mode**, `tcw work start` is refused before the item moves, and
  nothing is sent. Strict mode's promise that only one person can take a ticket
  *is* that transition, and an assignment on its own is not the proof it asks for.
  The message gives you the two ways out: move the ticket back to
  `statuses.active` in the tracker and run the start again, or turn
  `work.tracker.strict` off.

`tcw work tracker claim` is the deliberate exception: it applies the transition
from wherever the ticket is — refusing only where that status does not offer it —
and says so when it has moved one. Under strict mode it also refuses where the
workflow would let a second person claim the ticket, before anything is sent when
the ticket is already in `statuses.active`, and for a released item's ticket it
names the way forward. Elsewhere its refusal lists what the ticket does offer. A lifecycle move
is doing something else and happens to need the ticket; `tracker claim` is you
asking for the ticket and nothing else, so it does what you asked and tells you
what that cost.

### Taking something somebody else holds

`claim --take-over` claims an item and ticket held by another account.
`release --force` releases one. Both exist for the same situation — recovering
work from somebody who has gone away — and both refuse without the flag, naming
whoever holds it.

## Making a ticket for an item

`tracker import` builds an item from a ticket and `tracker link` binds two things
that both already exist. **`tcw work tracker create` goes the other way: it makes
a ticket for an item that has none, and binds it.**

```sh
tcw work tracker create 2026-09-14-rename-the-widget
tcw work tracker create --all --dry-run   # what a sweep would make
tcw work tracker create --all             # every open item with no ticket
```

The ticket's summary is the item's title, and its description is the item's own
request — `initial-request.md`, or `intake.md` when the request has not been
written yet — followed by a line naming the slug. The item stays the source of
truth and the ticket points back at it, so the description is plain paragraphs
rather than a faithful rendering of the Markdown.

Its type comes from `create.issue-type`, and `create.issue-types` overrides that
for an item that is an epic or carries the `bug` tag. An epic wins over a bug.

### Where a created ticket lands, and why `statuses.backlog` is required

Jira, not TCW, decides which status a brand-new issue starts in. In a project
with a triage column that is **Triage** — which is very often exactly what
`inbox-query` selects. A ticket left where Jira put it would come back through
`tcw work inbox` as new inbound work, offering to create a second item for the
one that just created it.

So moving it out is part of creating it. `create` puts every new ticket in
`statuses.backlog`, and **refuses to create anything at all when that is unset.**
It picks the transition by where it lands, never by its name: in this project the
hop from `Triage` to `To Do` is called `Accept`.

**If you already set `statuses`, your first `tracker create` will be refused**
until you add `backlog` to it. That is deliberate. The alternative is a ticket
sitting in your triage column that TCW believes it filed.

Everything that can be refused is refused *before* the ticket exists, because
TCW never deletes a ticket and cannot take one back. `create` refuses when:

- no tracker is configured, or `create` has no `project`;
- `statuses.backlog` is unset;
- the item is already bound to a ticket — it reports the binding and exits 0,
  rather than making a second one;
- the item is `completed` or `discarded`. A ticket created only to be closed is
  noise; use `tracker link` if one already exists;
- the item is under way and somebody else holds it;
- `--part` is not a valid part name.

`--all` sweeps every open item with no ticket, epics first so the sweep reads in
the order you would work the board. It skips items other people hold rather than
failing, and stops if a ticket is made whose key cannot be written down here —
carrying on would leave one ticket per remaining item that nothing can find
again.

It also refuses to start if **any** open item has a `tracker.yaml` that cannot
be read. Binding checks whether a ticket is already taken by looking at every
item, so one unreadable file means nothing can be bound — and a sweep would
make a ticket per item and bind none of them. Repair or remove the file first;
the message names it.

Run it with `--dry-run` first: on a board of any size this is the command
that turns one mistake into one mistake per item.

**If a run is interrupted** between making the ticket and writing the binding,
the key is already on disk. Running `create` again binds that key instead of
making a second ticket, and says so. You do not have to clean up by hand. The
board shows the item meanwhile:

```
2026-09-14-rename-the-widget | backlog | ... | ticket: ENG-604 made, not bound
```

If that ticket is gone — deleted, or moved somewhere this project cannot reach —
`tcw work tracker unlink <slug> --reason "<why>"` forgets the recorded key so
`create` can start again. It changes nothing in the tracker; close the old ticket
there yourself if it is not wanted.

If `work.tracker.link` is set, the created ticket's description ends with a link
back to the item.

### Making the ticket when the item is filed

Set `create.on-new: true` and `tcw work new`, and `tcw work inbox accept` of a
raw entry, make the ticket as part of filing. (Accepting a *ticket* from the
inbox is `tracker import`, which binds the ticket you already have.) Epics are
included, although strict mode exempts them: strict cannot demand a claimed
ticket for a container nobody works directly, while creation has no such
difficulty, and an epic on the board with no ticket is a hole in the tracker's
picture of the work. Strict mode and `create.on-new` can therefore both be set
— tasks come from tickets, epics filed here get theirs made.

TCW does not set a parent or epic link in the tracker. A created ticket is a
ticket; the hierarchy stays in TCW.

**Filing never fails because the tracker is unreachable.** The item is written
first, so a failure afterwards would leave you with an item you did not know you
had. Instead the ticket is recorded as *owed*:

```
$ tcw work new "Rename the widget"
2026-09-14-rename-the-widget
→ no ticket was created for 2026-09-14-rename-the-widget: the network is
  unreachable. It is recorded as owed; `tcw work tracker create
  2026-09-14-rename-the-widget` makes it.

$ tcw work list
2026-09-14-rename-the-widget | backlog | ... | ticket: owed since 2026-09-14
```

The debt shows on the board so it cannot be forgotten, and
`tcw work tracker create`, with or without `--all`, settles it. An owed ticket is
**not** a binding: the item has no ticket, it is expecting one.

`tcw work tracker sync` does **not** settle an owed ticket. Its job is the other
kind of unfinished business: an item that already has a ticket whose status
change never reached the tracker. Asked about an item that is owed one, it says
so and names `tracker create`.

**Filing on the web board records the debt but never makes the ticket.** The web
app does not talk to the tracker at all — no credentials, and no page waiting on
Jira — so an item filed there in a project with `create.on-new` comes out owed,
every time. `tcw work tracker create --all` settles those along with the rest.

If creation succeeds and the binding does not, the ticket is **not** recorded as
owed — it exists. The item reads `<KEY> made, not bound` instead, and
`tracker create` binds it.

## Linking and unlinking

**`tracker link` records that an item and a ticket are the same work, and does
nothing else.** It reads the ticket, which is how a key that does not exist is
refused, and writes the binding. Jira is left alone: the ticket keeps its status
and whoever holds it, so you can link a ticket somebody else is assigned. In your
repository nothing but `tracker.yaml` is written, so the item keeps its status,
owner and documents.

Any item can be linked, a finished one included. That is how work already done
gets tied to the ticket that tracked it. A finished item's folder is kept out of
git by default, so a binding on one stays on your machine along with the rest of
that item.

**Linking an item that is already under way leaves its ticket alone unless you
ask.** If the ticket is not in the status the item maps to, `link` warns you and the
binding notes that its status was not synced. While the
ticket stays out of step like that, later moves of the item do not bring it along:
each one says the ticket was linked without its status synced, moves nothing, and
does not count as a failure. Under strict mode those moves are refused, with the same
explanation. Everything else is reported as it always was — a ticket somebody else
holds, one nobody has claimed, or a transition name the ticket does not offer, is
still a conflict — and once
the ticket is in step, by your hand or otherwise, it is an ordinary linked ticket and
follows its item from then on. A ticket already in step when you link it is an
ordinary linked ticket from the start.

**To bring a linked ticket along, take it and then sync it:**

```sh
tcw work tracker link <slug> <KEY>
tcw work tracker claim <slug>     # assigns it to you; moves nothing
tcw work tracker sync <slug>      # moves it to where the item is
```

`sync` moves it in one transition, so a ticket that has to pass through more than
one status to reach the item is left for you to move by hand. This replaces
`link --sync-status`, which is retired: passing it now refuses, names these three
commands, and writes nothing.

A binding an earlier version's `--sync-status` wrote carries `catch-up: true`. TCW
still reads it, and `sync` still walks such a ticket up through the statuses you
mapped, one at a time, so nothing already linked that way is stranded. No command
writes it any more.

**`tracker unlink <slug> --reason <text>`** removes a binding. It keeps a record
of what was bound, when, and your reason, makes no call to Jira, and needs no
tracker configured, so a binding can be removed even after the `tracker` block is
gone. Like `link`, it works on any item, so a binding pointed at the wrong ticket
is repairable wherever you find it. The ticket stays where it is.

**A binding is not proof of a claim.** It is a file in your repository and anyone
could edit it. `import` reads the ticket even when a binding exists, and refuses
when Jira says the ticket is someone else's. A binding that cannot be read, or two
open items bound to one ticket and part, makes `import` and `link` refuse and name
the items rather than guess. Bindings are written by these commands; the web app
shows them but offers no way to edit one.

A binding whose ticket address is on a different Jira site from the configured
`base-url` is never written through: `import` and `link` refuse it and name the
item.

## Seeing which ticket an item answers

A bound item says so wherever you read it:

- `tcw work show` adds a `tracker:` line with the ticket, the provider, the part
  and the ticket's address;
- its row in `tcw work list` ends with `ticket: <KEY>`, noting the part and
  anything not yet sent to the ticket;
- `tcw work show --json` carries it as `tracker`;
- the item's page in `tcw serve` shows the ticket as a link.

All of these report what the binding records, not what Jira says right now, so
none of them needs the tracker configured or reachable. A binding file that cannot
be read is reported in the same places instead of breaking the board.

## Tickets following their items

For a bound item in a project with a tracker configured, lifecycle commands send
each move on to the ticket, **after** the move itself is done and committed:

| Command                        | What happens to the ticket                                                 |
| ------------------------------ | -------------------------------------------------------------------------- |
| `tcw work start`               | claims it — assigns it to you and reads that back — then moves it to `statuses.active` |
| `tcw work submit`              | moves it to `statuses.review`                                              |
| `tcw work rework`              | moves it back to `statuses.active`                                         |
| `tcw work complete` as `done`  | moves it to `statuses.completed`, whoever holds it                         |
| `tcw work complete` as discard | moves it to `statuses.discarded`, or the status mapped for that resolution, whoever holds it |

**Claiming does not move the ticket.** It is an assignment, read back, exactly as
`tcw work tracker claim` does it — unless you name `exclusive-claim-transition`,
which the claim applies first (see
[When two people claim at once](#when-two-people-claim-at-once)). The move to
`statuses.active` is then an ordinary move, using `transitions.start`.

**A start leaves a ticket already past `active` where it is.** If the ticket is in
review already, say, `start` claims it, says it was not moved back, and exits 0.
Where `exclusive-claim-transition` is set, that claim skips the transition rather
than move the ticket back with it, and says so — or, under strict mode, the start
is refused before the item moves (see
[When two people claim at once](#when-two-people-claim-at-once)).

**No lifecycle move moves a ticket back past its own window.** A `rework` does move
a ticket from your review status down to your active status — that is the move's
whole purpose, and the ticket is inside the window `rework` is entitled to act in.
What no lifecycle move does is drag a ticket back out of somebody else's window:
a `start` out of the backlog has no window at all, so a ticket anybody moved on
ahead of it is left alone. `tcw work tracker sync` has no window either, and does
reconcile in both directions, because that is the command you run to ask for it.

**`submit` and `rework` need the ticket to be yours.** For an item with a ticket
bound, they are refused before the item moves when the ticket is assigned to
somebody else (the message names them) or to nobody (the message names
`tcw work tracker claim`). This applies with or without strict mode. An item with no
ticket is not affected, and neither is the item's local owner: only the ticket's
assignee counts. When Jira cannot be reached, nothing can say the ticket is
somebody else's, so the move goes ahead and reports that the ticket did not follow;
strict mode refuses instead.

**`complete` and a discard need no claim.** Finishing or abandoning work is not
taking it, so they move a ticket assigned to somebody else, or to nobody, and leave
the assignment as it was.

**One exception, and only on an old binding.** A binding written by an earlier
version's `link --sync-status` carries `catch-up: true`, and completing such an
item walks the ticket up through your working statuses on the way to `completed`.
Climbing those statuses *is* work, so that walk still needs the ticket held: a
`complete` on a catch-up binding whose ticket somebody else holds is refused,
naming them. Nothing writes `catch-up: true` any more, so this only affects
bindings made before the flag was retired. Take the ticket with
`tcw work tracker claim <slug> --take-over`, or relink the item, and the ordinary
rule applies again.

A status you leave out of `statuses` sends nothing for that move. **`active` is
required once you map any other status**, because every move checks that the
ticket is still where the previous move left it, and that chain starts at
`active`. Status names match ignoring case and extra spaces. `discarded` can name
one status, or one status per discard resolution:

```yaml
statuses:
    active: In Progress
    discarded:
        wontfix: Won't Do
        duplicate: Duplicate # superseded is unmapped, so it sends nothing
```

The only resolutions are `wontfix`, `duplicate` and `superseded`.

**TCW moves a ticket only when it is assigned to you** — or it is being completed
or discarded — **and only when it can tell which transition to use.** With no
`transitions` entry for the move, that means exactly one of the ticket's offered
transitions leads to the target status; where two do, name the one you want (see
[Naming a transition](#naming-a-transition)). Otherwise a ticket someone else holds is
left alone. So is a ticket already resolved: TCW does not reopen one, and does not
change one resolution to another.

A lifecycle move — `start`, `submit`, `rework`, `complete`, a discard — also
expects the ticket to be where the previous move left it, or somewhere on the way
to where this one is going. That is how a ticket somebody moved by hand is told
apart from one TCW has not managed to move yet, and a ticket outside that window
is reported rather than moved.

**`tcw work tracker sync` has no such window, because no move just happened.** It
puts the ticket where the item's status says it belongs, from wherever the ticket
is: one that was moved on is brought back, and one that fell behind is brought
forward. Your work item is what decides. A backwards move prints a line naming the
ticket, the status it was in and the status it was put in, so a move you made on
purpose does not get undone in silence.

**A ticket several rungs behind its item is walked up only for an older binding
that asked for it.** A binding an earlier version's `link --sync-status` wrote
(it carries `catch-up: true`) is still honoured: TCW claims the ticket and moves it
to where the item is, straight there when the workflow allows, otherwise up through
the statuses you mapped, one transition at a time. It only ever goes forward,
only through statuses in your `statuses` mapping, and it stops at the first step it
cannot make, leaving the ticket where it got to and telling you; `tcw work tracker
sync <slug>` carries on from there. A plain `sync` makes one move, not a walk.

One limit worth knowing: if your workflow forces a ticket through a status you have
not mapped — `In Progress → Code Review → In Review`, with no `review`-style entry
for `Code Review` — the walk stops there, because TCW will not route a ticket
through statuses you did not name. Map the status, or move that one ticket by hand.

**When a ticket does not follow, your move still happens.** It is committed first;
the command then exits 1, says the item moved, and records why in `tracker.yaml`:

- **pending**: Jira could not be reached, it limited the request rate, the
  credentials are missing or wrong, or the tracker block has problems;
- **conflicting**: Jira answered, and its answer stopped the move, for example
  the ticket is assigned to someone else or is no longer where TCW expected.

If the claim at `start` never succeeded, the record says so by naming the `start`
as the move it still owes, and `tcw work tracker sync <slug>` tries the claim
first, then delivers that start, then whatever move came after it. `submit` and
`rework` will not do it for you: the ticket is not yet yours, so they are refused
and name `tcw work tracker claim <slug>`. A claim that failed because Jira did not
answer is recorded as pending; one Jira refused is conflicting.

Once a second failure writes a different move over that record, no command claims
the ticket for you any more, and the same two commands are how you take it. The
same is true when another part's item holds the ticket: the hold clears this item's
record, because while it is held the item owes the tracker nothing, and that takes
the note of the owed claim with it.

`tcw work show` prints a `tracker sync:` line with the state, the move, when, and
the reason; the `tcw work list` row reads `ticket: <KEY> (pending)`; and
`show --json` carries `tracker.sync`. A ticket that followed first time leaves no
record and no change in your repository.

**`tcw work tracker sync <slug>`**, or `--all`, retries once the cause is fixed.
It acts only on items you started, because it acts as whoever runs it. It removes
the record once the ticket is where it should be, and exits 1 while any item it
acted on is still pending or conflicting.

If you name a slug that somebody else started, it is skipped — and that is an
**exit 1**, saying so and naming the record still owed, because you asked about
that one item and nothing was done to it. Run it as them with
`TCW_WORK_OWNER=<their identity>`, or take the item over with
`tcw work start <slug> --take-over`. A `--all` sweep still exits 0 walking past
other people's work, which is what a sweep is for.

A `--all` sweep visits the items that have a record or an owed comment, which is
what it is for; reconciling a ticket nothing is recorded for is something you ask
for by naming the item.

Naming an item that has nothing recorded is only a check, and it never leaves a
record behind: if Jira cannot be reached, or refuses the move, the command says so
and the item is exactly as it was. For a finished item — completed or discarded —
whose ticket somebody reopened in Jira, it closes the ticket again whoever holds
it, as the completion itself would have. A claim gates work, not finishing it.

**Several parts.** A ticket bound to several parts moves only when the last open
part in this project moves. Parts in other projects are not seen — and because a
hold leaves no trace outside the checkout it happened in, `tcw work tracker sync`
will not reconcile a ticket whose binding names a `--part` unless a record says
what that item owes. It reports what it found instead. A ticket bound as the
default part, which is every binding you did not pass `--part` for, is reconciled
normally.

**Two moves are not caught.** A move made in `tcw serve`, and a command
interrupted between its commit and its call to Jira, leave no record, so the board
shows them as in step. `tcw work tracker sync <slug>` puts such an item right: it
does not need a record to know where the ticket belongs.

**An item about to be removed.** If a project does not keep resolved items
(`work.retain`) and the ticket fails to follow, no record is written and the item
is kept instead of removed. Move the ticket by hand, then run `tcw work delete`.

### Naming a transition

Many workflows have two transitions ending in the same status: one for finished work
and one for abandoned work, both landing in `Done`. TCW will not guess between them,
so without help neither `complete` nor a discard can ever sync. Name them:

```yaml
transitions:
    start: Start Progress
    complete: Finish
    discard:
        wontfix: Abandon # sets the matching Jira resolution
        duplicate: Mark Duplicate
```

You only need to name the moves that are ambiguous — anything you leave out keeps
working out the transition from the status, exactly as before. `discard` takes one
name, or one per resolution, and a resolution you leave out falls back to the derived
rule. That includes `start`: leave it out and a start finds its transition from the
status it is heading for, the same way the other four moves do.

Two reasons to name `start` anyway. If your workflow has **two** transitions out of
the backlog status into the active one, the status cannot say which, so a start with
no name refuses rather than guessing — that is the ambiguous case this whole section
is about. And `tcw work tracker import` and `tcw work inbox accept` claim a ticket
*through* that transition, whatever your workflow looks like, so without the key
they refuse and tell you to set it.

A name that the ticket does not offer, or that matches two transitions, or that leads
somewhere other than the status you mapped, is refused and nothing is sent — TCW does
not quietly fall back, because then a misspelled name would never be noticed.

### Renaming the start transition

In version 2.3.0 and earlier, the key that names the start transition was called
`transitions.claim`. It is now `transitions.start`, alongside `submit`, `rework`,
`complete` and `discard`, because claiming a ticket and starting one stopped being
the same act.

It was a required key when it was called `transitions.claim`, so **every project
connected to a tracker has to change that one word.** Nothing else moves, and the
value stays exactly as it was. TCW does not accept the old spelling, so nothing
changes quietly behind you: `tcw validate` names the file and the replacement.

```
tcw-config.yaml: work.tracker.transitions.claim: renamed to
work.tracker.transitions.start, the transition the start move applies, alongside
submit, rework, complete and discard
```

`transitions.start` itself is no longer required, so you may also simply delete the
old key — but read [Naming a transition](#naming-a-transition) first, because
`tracker import` still needs a name and so does a workflow with two ways in.

In a workspace where a parent node holds the shared settings, the old key is in the
parent's file and that is the file the message names, even when you are validating a
child.

## Comments on the ticket

Set `comments: true` in the `tracker` block and each lifecycle move also leaves a
short comment on the ticket, for anyone who follows the work in Jira rather than
in the repository:

```
TCW: "Checkout page" (part api) went to review.
```

The wording is `started`, `went to review`, `went back to work`, `was completed`
or `was discarded as <resolution>`. Nothing from `spec.md`, `plan.md` or any other
lifecycle document is ever copied into a comment.

**Adding a link.** `link` adds a web address to each comment:

```yaml
comments: true
link: https://tcw.example.com/work/{slug}
```

It must start with `https://` or `http://` and contain no spaces. Its only
placeholders are `{project}` (the TCW project id) and `{slug}`, each
percent-encoded; any other placeholder is a problem `tcw validate` reports. Use an
address that survives a move: a team hosting `tcw serve` can link each item's page
as above, but a link into a Git host's file tree breaks at the next move, because
an item's folder is named after its status. A `link` with `comments` off does
nothing and is not a problem, so a child project can set `comments: false` under a
parent that sets both.

**When a comment is posted.** Only while the ticket is assigned to you; a ticket
someone else holds gets none. When a comment cannot be posted, the command exits 1,
`tcw work show` prints a `tracker comment:` line, and `tcw work tracker sync` sends
it later. Before resending, `sync` looks for the comment among your newest 100
comments on the ticket, so a post that landed without an answer is not repeated.

**Limits.** A newer move's comment replaces one still waiting. Two runs at once,
or a comment edited or deleted in Jira, can still produce a repeat. Moves made in
`tcw serve` post nothing.

**Jira Service Management:** a comment may be visible to customers. Leave
`comments` off on such a project unless item titles may be seen by them.

## Strict mode: no work without a ticket

Set `strict: true` when every piece of work must come from a ticket you have
claimed. Strict mode needs `statuses.active`, `statuses.completed`,
`statuses.discarded` as either one status or a status for each of `wontfix`,
`duplicate` and `superseded`, `exclusive-claim-transition`, and
`transitions.start`; `tcw validate` reports whichever is missing, and strict
commands refuse until it is set.

`transitions.start` is optional everywhere else, but not here. Strict mode creates
work only from a ticket, and the two commands that do that — `tcw work tracker
import` and `tcw work inbox accept` — claim the ticket through this transition.
Without it, a strict project could create no work at all.

`exclusive-claim-transition` is required because strict mode promises that only one
person can take a ticket, and a transition your workflow will not apply to a ticket someone has already
taken is what stops a second person. Set
it to the transition that takes a ticket into work. Setting it means
`tcw work tracker claim`, and the claim a strict `tcw work start` makes, apply that
transition, so a claim moves the ticket. Every strict claim — `import`,
`inbox accept`, `start` and `tracker claim` — then checks that your workflow does
not offer the transition again from where it led, and refuses when it does: such a
workflow would let a second person claim the ticket too. See
[When two people claim at once](#when-two-people-claim-at-once).

```yaml
strict: true
exclusive-claim-transition: Start Progress
transitions:
    start: Start Progress
statuses:
    active: In Progress
    review: In Review
    completed: Done
    discarded: Won't Do
```

With it on:

| Command                                             | Under strict mode                                                                                                                                                                                                                                                      |
| --------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tcw work new`, `tcw work inbox accept` of an entry | refused, pointing you at `tcw work tracker import <ticket>`. `new --epic` is allowed, because an epic only groups work. Where `inbox-query` is set, `inbox accept` of a ticket is allowed, and refused exactly where `tracker import` would be.                                                      |
| `tcw work start`                                    | refused for an item with no ticket. For a bound item, the ticket is claimed **first**, through `exclusive-claim-transition`, and the item starts only if the claim worked and the workflow does not offer that transition again from where it led: a second person whose claim the workflow refuses is stopped before their item moves. An epic may start without a ticket, but not with `--worktree`, since code on an epic's own branch would have no ticket behind it. |
| `tcw work submit`, `rework`                         | the ticket is read first; refused unless it is assigned to you and in the status the item's last move left it in. For a `--worktree` item this is checked before anything is merged, and against the item as its worktree holds it — the moves made there are committed on the branch, so the primary checkout's copy is out of date until the merge-back.                                                                                   |
| `tcw work complete` as `done`                       | the ticket is read first; refused unless it is in the status the item's last move left it in. Who holds it is not asked: a claim gates work, not finishing it. Checked before anything is merged, as above. |
| `tcw work complete` as a discard                    | always allowed.                                                                                                                                                                                                                                                        |
| `tcw work drop`                                     | refused for an item that was ever bound. Discard it instead, so the record stays.                                                                                                                                                                                      |
| `tcw work tracker import`                           | the way into strict work; it claims through `transitions.start`, which strict mode therefore requires. Refused after the claim when the ticket is not in `statuses.active` or still offers `exclusive-claim-transition` from there. The ticket stays claimed for you to release.                                                                                                                 |
| `tcw serve`                                         | refuses the same changes, since it cannot check a ticket, and names the command to use.                                                                                                                                                                                |

Also under strict mode:

- **Jira must be reachable.** While it cannot be reached, or while an item has a
  move not yet delivered, the commands in the table above refuse. Run
  `tcw work tracker sync <slug>` first. An owed comment does not cause a refusal.
- **A tracker block with problems does not turn strict mode off.** Those commands
  refuse until it is fixed; run `tcw validate`.
- **There is no way past a refusal.** `--force` and `--take-over` do not bypass it.
- **`create.on-new` may be on as well, and it applies to epics.** Strict mode
  refuses `tcw work new` for everything except an epic, and creation-on-filing
  covers epics, so the pair means "tasks come from tickets, epics filed here get
  theirs made". `tcw work tracker create` itself works under strict mode too,
  for an item that reached your board some other way.
- **Never refused:** `tcw work edit`, writing lifecycle documents, and
  `tracker link` / `unlink`. The one exception is `tcw work edit --type`: an epic
  is not gated by a ticket, so changing an item's type is refused. Create an epic
  with `tcw work new --epic`.
- **Parts handled elsewhere.** A ticket shared by several parts is recognized
  only from the parts' items in this checkout. If the part that held the ticket
  back was completed in another clone, or was not kept (`work.retain`), the last
  part's `complete` is refused; put the ticket in the status the message names, or
  discard.

A refusal exits 1, changes nothing in your project, says what did not happen and
how to fix it, and writes no record. A `start` or `import` refused after it
claimed the ticket leaves the ticket claimed. To turn strict mode off, set
`strict: false` or remove the key.

## Limits

These are known and accepted, not bugs waiting for a workaround:

- **Two people can take one ticket** on a workflow that offers the claim from its
  own destination status, and both get an item. `tracker show` reports such a
  workflow as `not exclusive`, and strict mode refuses a claim on one.
- **Two runs by the same Jira account at the same moment**, such as two agents
  sharing credentials, can both create an item.
- **Each project keeps its own bindings.** Importing one ticket in two projects
  of a workspace gives two items.
- **A ticket held by a finished item can be bound to a second item**, open or
  finished, with no warning. A discarded item's ticket is meant to be available
  again, and TCW cannot tell that case from the others.
- **Moves in `tcw serve` never reach Jira**, and leave no record to retry.
