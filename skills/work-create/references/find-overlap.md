# Finding overlap with tracked work

## What this answers

Is one idea already tracked, partly tracked, blocked by something tracked, or
only related to it? The answer covers every unfinished item, arrivals waiting
in the inbox included.

**It is read-only.** No move, no `tcw work edit`, no file written. The
`work-create` skill decides what to do with the answer.

## Candidates

1. `tcw work list --json`. Its rows are every unfinished item, at any stage
   from inbox to qa. Where the project keeps its work in Jira, its inbox is
   tickets that are not items yet: read them with `tcw work tickets list --json`
   as well.
2. `tcw work list --all --json`, but only to notice finished items (at
   `completed` or `discarded`). A finished item can be named as a reference. It
   is never a match.

Most rows can be ruled out from the title alone. For the rest, read what each
asks for with `tcw work show <slug>`, which prints its request and comments, and
its spec (`tcw work path <slug> spec`) only when the request does not settle
it. Where the request is a file, you may search under the folder `tcw work path`
prints for the idea's distinguishing words first, to choose which to open.
Never build a store path yourself.

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
<ref> | <relation> | <stage> | <evidence>
```

- `<ref>` is the item's slug, or a Jira ticket's key for an inbox ticket.
- Copy the stage from `tcw work list --json`; never work it out yourself. For
  an inbox ticket, write `inbox`.
- `<evidence>` is the sentence or heading in the item that decided it.
- Add `(rest can stand alone)` or `(rest cannot stand alone)` to a
  `partly covers` line.

Close with a line naming what you read:

```
searched: tcw work list · tcw work list --all
```

adding `tcw work tickets list` where you read it. When nothing matches, answer
`no overlap` followed by that `searched:` line. Silence is not an answer,
because "searched and found nothing" and "never searched" must not look the
same.
