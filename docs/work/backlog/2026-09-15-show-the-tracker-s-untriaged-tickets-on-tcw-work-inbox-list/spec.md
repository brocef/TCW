# Spec — Show the tracker's untriaged tickets on `tcw work inbox list`

## Capability changes

No ledger record is written here. Four existing capabilities change; none is new,
and none is removed.

| Capability                             | What stops being true                                                                                                    |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `work/manage-the-work-inbox`           | The inbox reports only raw intake, and `show`/`accept` take only a raw entry.                                             |
| `work/inspect-external-tracker-work`   | `work.tracker` declares one query. It gains a second, and a third command reads the tracker.                              |
| `work/manage-external-tracker-intake`  | `tcw work tracker import <key>` is the only way to take a ticket.                                                          |
| `work/require-tracker-backed-work`     | "`tcw work new` and `tcw work inbox accept` refuse and point me at `tcw work tracker import`" — half of that stops holding. |

No new capability is declared. The behavior is the inbox and the tracker bridge
each doing more of what they already describe; a fifth capability spanning them
would restate four descriptions and drift from all of them.

Taxonomy: no change. `work-inbox` ("the intake surface through which users
inspect and accept raw requests as formal work items") and
`external-work-tracker` ("the coordination boundary between a project's TCW work
store and an external tracker that owns ticket existence, assignment and claim
state") both already cover this; the vocabulary they cite (`work-item`, `cli`,
`reference`) needs no new term. A ticket the tracker owns arriving on an intake
surface is precisely the boundary the second Feature names.

## Problem

Triage on a project that has connected Jira happens in two places. `tcw work
inbox list` reports the raw intake TCW holds (`_inbox_list`, `tcw/work/cli.py:448`),
and `tcw work tracker list` reports tickets — but only the ones
`work.tracker.candidate-query` selects, which is the set that is *ready to be
taken* (`_tracker_list`, `tcw/work/cli.py:1872`; README.md:380 documents the query
as `assignee = currentUser() AND status = "To Do"`). Tickets still awaiting triage
are selected by neither. Nothing in the product answers "what is waiting to be
triaged here?" in one list, and the two halves are not even reachable from one
command: an entry is `inbox show`/`inbox accept`, a ticket is `tracker show`/
`tracker import`.

## Goals

1. A project can **declare** which of its tracker's tickets are inbox items, as a
   query, separately from the ones ready to be taken.
2. `tcw work inbox list` reports both, in two labelled sections.
3. `tcw work inbox show` and `tcw work inbox accept` act on a ticket the section
   printed, with accept doing what taking a ticket already does.
4. A project that has not declared the query sees no change whatsoever.
5. A tracker that cannot be reached does not cost the user their raw intake.

## Non-goals

- **A second tracker provider.** `jira-cloud` remains the only `provider` that
  parses (`TRACKER_PROVIDERS`, `tcw/store/base.py:1075`).
- **Filtering out tickets that already have a work item.** The requester settled
  this: the declared query accounts for it. No board scan, no binding read.
- **Changing what `tracker list`, `tracker show` or `tracker import` select or
  print.** Each keeps its behavior exactly.
- **An inbox in the web app.** `tcw serve` exposes no inbox surface at all —
  `grep -rn inbox tcw/serve/` returns nothing — so there is no second view to
  keep in step. This is the whole of the sibling sweep: `inbox list` is the only
  surface in the repository that lists raw intake, which is why the sweep is
  narrow rather than repo-wide.
- **Making a ticket addressable anywhere else** (`tcw work show`, the board,
  references). A ticket becomes a work item by being accepted; until then it is
  addressable from the inbox commands and nowhere else.

## Design

### 1. A second declared query: `work.tracker.inbox-query`

Optional, a non-empty string when present, beside `candidate-query`:

```yaml
work:
    tracker:
        candidate-query: assignee = currentUser() AND status = "To Do"
        inbox-query: project = EX AND status = Triage AND assignee IS EMPTY
```

- Added to `TRACKER_KEYS` (`tcw/store/base.py:1077`), so it stops being reported
  as an unknown key, and parsed in `parse_tracker_config`
  (`tcw/store/base.py:1092`) onto a new `TrackerConfig.inbox_query: str = ""`
  field (`tcw/store/base.py:1042`).
- **Absent is `""` and not a problem.** Blank or non-string **is** a problem: an
  empty JQL selects every ticket on the site. The parser fails closed on any
  problem, so a mistyped `inbox-query` disables the whole block — that is the
  existing, deliberate behavior and this key does not get an exception from it.
- **Inheritance is free and needs no new rule.** `merge_tracker_blocks`
  (`tcw/store/base.py:1318`) merges key by key without enumerating keys, so a
  parent can hold it and a child override it. Being optional, it adds no clause
  to the `credentials`-beside-`base-url` rule and none to the rule that a node
  with its own board needs its own `candidate-query`.

Reusing `candidate-query` was rejected: the two sets are different by
construction, and a project that wants them identical can write the same JQL
twice, whereas a project that wants them apart could not separate them again.

### 2. The tracker section is composed in the CLI

`WorkStore.inbox_list` is unchanged and gains no ticket awareness. The rows come
from `JiraClient.search` called beside it, exactly as `_tracker_list` does.

This is the litmus test answered, not dodged: the question "could a non-filesystem
store implement this?" does not arise, because no store operation is being added —
a tracker is not a store, and `tcw/tracker/__init__.py` says why in as many words
("putting these operations behind `WorkStore` would make every adapter owe a
tracker implementation, which inverts what a store is for"). A DynamoDB-backed
store gets this feature for free and implements nothing.

### 3. Output

With no tracker, or a tracker whose `inbox_query` is `""`, `inbox list` prints
what it prints today — no headings, no indent, no empty-section marker, no note.
`tests/test_work.py:2533` pins that output as an exact string and must keep
passing unedited.

With the query declared:

```
raw intake:
  2026-09-14-serve-accepts-writes.md | file | 2026-09-14-serve-accepts-writes

tracker tickets:
  EX-482 | Triage | unassigned | Login retries twice on a 502
```

- An empty section prints `  (none)`, so an empty half is never confusable with a
  half that failed.
- The headings do not say "files". The request's words were "files on disk", but
  a store's inbox entries are opaque refs it hands out, and writing the
  filesystem adapter's shape into the output would teach it as the contract. The
  `kind` column already says `file` when that is what an entry is.
- Truncation is reported as `tracker list` reports it, on stderr, naming
  `work.tracker.inbox-query` as the thing to narrow. `SearchResult` reports no
  total and none is invented (`tcw/tracker/jira.py`, `SearchResult`).

### 4. Resolving a ref: the store first, the tracker second

`inbox show <ref>` and `inbox accept <ref>` ask the store first. Only when the
store says **no such entry**, and an `inbox-query` is declared, is the ref tried
as a ticket key. Local intake therefore always wins, the common case makes no
network call, and the order is fixed rather than inferred from the ref's shape —
parsing `EX-482` as "looks like a ticket" would hard-code one provider's key
format in the CLI.

This needs *not found* to be distinguishable from *ambiguous*. Both raise a bare
`ValueError` today (`tcw/store/fs.py:5699`, `:5732`), and falling through to the
tracker on an ambiguous raw entry would be wrong. So `InboxEntryNotFound(ValueError)`
is declared in `tcw/store/base.py` beside the inbox operations and raised where
`no such inbox entry` is raised now; ambiguity keeps the plain `ValueError`.
Because it is a subclass, `_ERRORS` (`tcw/work/cli.py:49`) already catches it and
no existing caller changes. It is portable: telling "no such ref" from "several
match" is a question any store answers.

`--ticket` on both commands forces the tracker, for the one case the precedence
cannot serve: a raw entry whose name is a ticket key shadows the ticket.

### 5. What each command does with a ticket

- **`inbox show <key>`** prints the ticket as `tracker show` does — status,
  summary, assignee, `claimable`, `workflow` — and then its description. The
  description is included because `inbox show` on a raw entry prints the body,
  and triage decides from the text.
- **`inbox accept <key>`** is `tracker import`: the same claim, the same
  re-read-before-creating, the same binding, the same idempotence, by calling the
  same function rather than a second copy of it (`_tracker_import`,
  `tcw/work/cli.py:1976`). It is parameterized on the label so its messages read
  `tcw work inbox accept`. `accept` gains `--part`; it already has `--title`.

### 6. Strict mode

`_inbox_accept` refuses outright under strict mode today and points at
`tracker import` (`tcw/work/cli.py:490`). That refusal moves to **after**
resolution: a raw entry is still refused, in the same words; a ticket is not,
because accepting one *is* claiming a ticket. `_tracker_import`'s own strict check
(`tcw/work/cli.py:2037`) then applies unchanged, so a claim the workflow could not
have made exclusive still creates no item.

### 7. Failure isolation

The raw-intake section is printed before the tracker is contacted. A tracker that
cannot be reached leaves that section intact, prints `  (not listed)` under the
tracker heading, puts the cause on stderr, and exits non-zero — the listing is
short, and this codebase does not return short lists silently. A tracker block
that has *problems* cannot be told from one that never declared `inbox-query`
(the parser fails closed), so that case prints today's output with one stderr
line naming it, and exits 0.

## Acceptance criteria

**Configuration**

1. `work.tracker.inbox-query: <string>` parses, and `tcw validate` reports no
   problem for it.
2. `inbox-query` absent leaves `TrackerConfig.inbox_query == ""` and produces no
   problem.
3. `inbox-query: ""`, `inbox-query: "   "` and `inbox-query: 42` each produce the
   problem `work.tracker.inbox-query: expected a non-empty string, got <type>`,
   and `parse_tracker_config` returns `None` for the whole block.
4. A parent node's `inbox-query` is inherited by a child that declares a
   `tracker` block of its own, and a child's own value wins.
5. A node that declares `inbox-query` but no `candidate-query` still fails, and a
   node that declares neither still fails: the new key changes no existing rule.

**`inbox list`, without the query**

6. With no `work.tracker` block, `tcw work inbox list` stdout is byte-for-byte
   what it is today. `tests/test_work.py:2533` passes unedited.
7. With a valid `work.tracker` that omits `inbox-query`, stdout is likewise
   unchanged and no tracker request is made.
8. With a `work.tracker` that has problems, stdout is unchanged, exit is 0, and
   stderr names the tracker configuration once.

**`inbox list`, with the query**

9. Stdout carries `raw intake:` and `tracker tickets:` as headings, each row
   indented by two spaces, tickets as `KEY | status | assignee | summary`.
10. The request sent carries `inbox-query`'s JQL, not `candidate-query`'s.
11. An empty inbox prints `  (none)` under `raw intake:`; no matching tickets
    prints `  (none)` under `tracker tickets:`. Exit 0 in both cases.
12. `isLast: false` prints a "there are more" line on stderr naming
    `work.tracker.inbox-query`, and no total.
13. When the search raises any `TrackerError`, the raw-intake section is still
    printed in full, `  (not listed)` appears under `tracker tickets:`, the cause
    is on stderr, and the exit code is non-zero.

**`inbox show` / `inbox accept`**

14. A raw entry resolves to the raw entry for both commands, whether or not
    `inbox-query` is declared and without any tracker request being made.
15. A ref that is no raw entry resolves as a ticket key when `inbox-query` is
    declared: `inbox show` prints the ticket's status, summary, assignee,
    `claimable`, `workflow` and description.
16. `inbox accept <key>` creates the same item, with the same intake and the same
    `tracker.yaml` binding, as `tcw work tracker import <key>` does for the same
    ticket; running it twice yields the one item, not two.
17. `inbox accept <key>` messages say `tcw work inbox accept`, never
    `tcw work tracker import`.
18. A raw entry named exactly like a ticket key resolves to the raw entry;
    `--ticket` on the same ref resolves to the ticket.
19. An ambiguous raw-entry ref still raises its ambiguity error and is **not**
    tried as a ticket key.
20. A ref that is neither says so in one message naming both possibilities, and
    with no `inbox-query` declared the message is today's `no such inbox entry`.

**Strict mode**

21. Under `strict: true`, `inbox accept <raw-entry>` is refused in the words it
    uses today.
22. Under `strict: true`, `inbox accept <ticket-key>` is **not** refused for being
    strict, and is refused by `_tracker_import`'s own claim check exactly when
    `tcw work tracker import` would be.

**Non-regression**

23. `tcw work tracker list|show|import|link|unlink|sync` behave identically; their
    tests pass unedited.
24. No credential value reaches stdout or stderr on any new path, including every
    new error branch (the sentinel-token discipline of
    `tests/test_tracker_cli.py`).
25. A project with no tracker configured imports no tracker module on any inbox
    command.

## Risks

- **Scope.** The requester chose full triage parity, so this item carries a
  config key, a list surface, two resolution paths, a strict-mode change and a
  store error type. It is one coherent change — every part serves "triage from
  one list" — but it is the upper end of one item. If the plan cannot keep it
  one, the split is `list` first, then `show`/`accept`.
- **A shadowed ticket key is silent.** Precedence means a raw entry named
  `EX-482.md` takes `EX-482` and the user is not told the ticket exists, because
  finding out would cost a request on every resolution. `--ticket` is the escape
  hatch and the documentation has to say so; a warning is not possible without
  the request that precedence exists to avoid.
- **`accept` now reaches the network.** A command that was local can claim a
  ticket. That is the requester's explicit choice; the mitigation is that it is
  the *same* code path as `import`, so it cannot fail in a new way.
- **Two queries are two things to get right.** A project that writes overlapping
  JQL will see a ticket in both `tracker list` and `inbox list`. That is
  correct — both statements are true — but it will look like a bug, so the
  documentation states what each query is for.

## Notes

- Every claim about current behavior above was read from the tree at
  `09138c9`, and each carries its `file:line`.
- Criterion 6 was run: `python -m pytest tests/test_work.py -k inbox -q` is 40
  passed on that commit, so it is a baseline and not an aspiration.
- Criterion 25 is asserted from `_resolved_tracker` returning before any
  `tcw.tracker` import when a node declares no `tracker` block
  (`tcw/store/fs.py:5420`); it is stated as a criterion because the plan should
  pin it with a test rather than trust the reading.
