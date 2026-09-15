# Finding overlap with tracked work

## What this answers

Is one idea already tracked, partly tracked, blocked by something tracked, or
only related to it? The answer covers open items **and** the work inbox, whose
entries are not items and never appear in `tcw work list`.

**It is read-only.** No transition, no `tcw work edit`, no file written. The
`work-create` skill decides what to do with the answer.

## Candidates

1. `tcw work list`. Its rows are `backlog`, `active` and `review` items.
2. `tcw work inbox list`, then `tcw work inbox show <entry>` for any entry whose
   title could plausibly be the same work.
3. `tcw work list --all`, but only to notice closed (`completed`, `discarded`)
   items. A closed item can be named as a reference. It is never a match.

Most rows can be ruled out from the title alone. For the rest, grep before you
read. `tcw work path` with no slug prints the store folder: search under it for
the idea's distinguishing words, then open the likely items with
`tcw work path <slug>`. Read the body (`initial-request.md`, or `intake.md` when
there is no request), and `spec.md` only when the body does not settle it. Never
build a store path yourself.

Judge by what an item is **about**, not by shared words. An item that mentions
the idea's terms in passing is not a match.

## Relations

Give each plausible candidate exactly one relation:

| Relation | Meaning |
| --- | --- |
| `covers` | Doing that item would deliver the idea |
| `partly covers` | It delivers some of the idea, not all of it |
| `blocks` | The idea cannot proceed until that item lands |
| `related` | Shared subject or files, but it neither delivers nor blocks the idea |

- **`blocks` is narrow.** Sharing a topic, touching the same files, or a
  preferred order makes a candidate `related`, not `blocks`.
- **For `partly covers`,** say whether the rest of the idea could stand alone as
  its own piece of work.

## Return

One line per candidate you judged:

```
<ref> | <relation> | <status and stage letters> | <evidence>
```

- `<ref>` is the item's slug, or the inbox entry's name.
- Copy the status and stage letters from the `tcw work list` row; never work
  them out yourself. For an inbox entry, write `inbox`.
- `<evidence>` is the sentence or heading in the item that decided it.
- Add `(rest can stand alone)` or `(rest cannot stand alone)` to a
  `partly covers` line.

Close with a line naming what you read:

```
searched: tcw work list · tcw work inbox list · tcw work list --all
```

When nothing matches, answer `no overlap` followed by that `searched:` line.
Silence is not an answer, because "searched and found nothing" and "never
searched" must not look the same.
