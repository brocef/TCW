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
        credentials:
            email-env: TCW_JIRA_EMAIL
            token-env: TCW_JIRA_API_TOKEN
        transitions:
            claim: Start Progress
        statuses: # optional: where a linked ticket goes as its item moves
            active: In Progress
            review: In Review
            completed: Done
            discarded: Won't Do
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
| `credentials.email-env` | yes      | The **name** of the environment variable holding your Jira account's e-mail address.                                                                   |
| `credentials.token-env` | yes      | The **name** of the environment variable holding your Jira API token.                                                                                  |
| `transitions.claim`     | yes      | The workflow transition that starts a ticket, spelled exactly as Jira spells it.                                                                       |
| `statuses`              | no       | The Jira **status** a linked ticket should be in for each of the item's statuses. See [Tickets following their items](#tickets-following-their-items). |
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
or `link` treats the whole `tracker` block as broken.

**A block with any problem counts as no tracker at all.** TCW never uses a
half-valid configuration, because a block whose token variable name is mistyped
but whose site address is fine would otherwise send an unauthenticated request to
a real site. `tcw work list` and `tcw work show` keep working either way;
`tcw validate` is where you hear about the problem. (Strict mode is the exception:
see [Strict mode](#strict-mode-no-work-without-a-ticket).)

**TCW cannot tell you that `transitions.claim` is misspelled.** A ticket that does
not offer the transition may simply not have reached the point where it applies,
or may already be past it, and a whole query of such tickets looks the same as a
typo. `tracker show` reports it as information, not as an error. Copy the name
from your project's workflow.

After editing the block, run `tcw validate`, then `tcw work tracker list` to
confirm the query and the credentials work.

## Inherited settings

A project's **board** below means its own work store: the work items it keeps.

In a workspace of connected projects that all use one Jira site, the site, the
credential variable names and the claim transition are usually the same
everywhere, and only the query differs. A project can therefore write only what is
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
            claim: Start Progress
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
2. applies the transition named in `transitions.claim`;
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
| `tcw work start`               | claims it, by the same rules as `import`                                   |
| `tcw work submit`              | moves it to `statuses.review`                                              |
| `tcw work rework`              | moves it back to `statuses.active`                                         |
| `tcw work complete` as `done`  | moves it to `statuses.completed`                                           |
| `tcw work complete` as discard | moves it to `statuses.discarded`, or the status mapped for that resolution |

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

**TCW moves a ticket only when it is assigned to you and still where the item's
previous status left it**, and only when exactly one of the ticket's offered
transitions leads to the target status. A ticket someone else holds, one moved on
in Jira, or one whose workflow has no single transition to the mapped status is
left alone. TCW never pulls a ticket back to match an item.

**When a ticket does not follow, your move still happens.** It is committed first;
the command then exits 1, says the item moved, and records why in `tracker.yaml`:

- **pending**: Jira could not be reached, it limited the request rate, the
  credentials are missing or wrong, or the tracker block has problems;
- **conflicting**: Jira answered, and its answer stopped the move, for example
  the ticket is assigned to someone else or is no longer where TCW expected.

If the claim at `start` never succeeded, the record says the claim is still owed,
and every later attempt tries the claim first.

`tcw work show` prints a `tracker sync:` line with the state, the move, when, and
the reason; the `tcw work list` row reads `ticket: <KEY> (pending)`; and
`show --json` carries `tracker.sync`. A ticket that followed first time leaves no
record and no change in your repository.

**`tcw work tracker sync <slug>`**, or `--all`, retries once the cause is fixed.
It acts only on items you started, because it acts as whoever runs it. It removes
the record once the ticket is where it should be, and exits 1 while any item it
acted on is still pending or conflicting. On an item with no record it checks the
ticket but does not move it.

**Several parts.** A ticket bound to several parts moves only when the last open
part in this project moves. Parts in other projects are not seen.

**Two moves are not caught.** A move made in `tcw serve`, and a command
interrupted between its commit and its call to Jira, leave no record, so the board
shows them as in step. `sync <slug>` checks such an item but will not move its
ticket.

**An item about to be removed.** If a project does not keep resolved items
(`work.retain`) and the ticket fails to follow, no record is written and the item
is kept instead of removed. Move the ticket by hand, then run `tcw work delete`.

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
claimed. Strict mode needs `statuses.active`, `statuses.completed`, and
`statuses.discarded` as either one status or a status for each of `wontfix`,
`duplicate` and `superseded`; `tcw validate` reports whichever is missing.

```yaml
strict: true
statuses:
    active: In Progress
    review: In Review
    completed: Done
    discarded: Won't Do
```

With it on:

| Command                                             | Under strict mode                                                                                                                                                                                                                                                      |
| --------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tcw work new`, `tcw work inbox accept`             | refused, pointing you at `tcw work tracker import <ticket>`. `new --epic` is allowed, because an epic only groups work.                                                                                                                                                |
| `tcw work start`                                    | refused for an item with no ticket. For a bound item, the ticket is claimed **first**, and the item starts only if the claim worked. An epic may start without a ticket, but not with `--worktree`, since code on an epic's own branch would have no ticket behind it. |
| `tcw work submit`, `rework`, `complete` as `done`   | the ticket is read first; refused unless it is assigned to you and in the status the item's last move left it in. For a `--worktree` item this is checked before anything is merged.                                                                                   |
| `tcw work complete` as a discard                    | always allowed.                                                                                                                                                                                                                                                        |
| `tcw work drop`                                     | refused for an item that was ever bound. Discard it instead, so the record stays.                                                                                                                                                                                      |
| `tcw work tracker import`, and the claim at `start` | refused after the claim when the ticket is not in `statuses.active` or still offers the claim transition. The ticket stays claimed for you to release.                                                                                                                 |
| `tcw serve`                                         | refuses the same changes, since it cannot check a ticket, and names the command to use.                                                                                                                                                                                |

Also under strict mode:

- **Jira must be reachable.** While it cannot be reached, or while an item has a
  move not yet delivered, the commands in the table above refuse. Run
  `tcw work tracker sync <slug>` first. An owed comment does not cause a refusal.
- **A tracker block with problems does not turn strict mode off.** Those commands
  refuse until it is fixed; run `tcw validate`.
- **There is no way past a refusal.** `--force` and `--take-over` do not bypass it.
- **Never refused:** `tcw work edit`, writing lifecycle documents, and
  `tracker link` / `unlink`.
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
