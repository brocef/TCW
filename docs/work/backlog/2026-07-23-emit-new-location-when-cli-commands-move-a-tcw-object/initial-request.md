# Emit new location when CLI commands move a TCW object

## Requested outcome

When a `tcw` CLI command moves a TCW-managed object to a new location, the
success message should tell the user *where the object now lives*, not just that
the transition happened.

Concrete example from the request:

```
tcw work start <slug>
# now:  started <slug>
# want: <slug> started and moved into docs/work/active/<slug>
```

**Motivating problem:** agents (and humans) routinely look for a started item in
the old `backlog/` folder instead of the new `active/` folder, because the
current message (`started <slug>`) never names the new location. Naming the
destination in the output removes that guesswork.

Apply the same treatment to **every CLI command that changes the location of a
TCW-managed object**, not just `tcw work start`.

## Scope (broad strokes)

Location changes in TCW's filesystem realization are **work-item folder moves**
between the `backlog / active / completed` folders (plus `inbox → backlog` on
accept). The candidate command set to confirm during spec:

- `tcw work start` (backlog → active)
- `tcw work complete` (active/backlog-epic → completed)
- `tcw work inbox accept` (inbox → backlog)
- any other status transition / de-nest / parent move that relocates the folder

Commands whose "status" is an **in-place field** (taxonomy terms, capability
status via `tcw capabilities set --status`) do **not** move an object and are
out of scope — that confusion doesn't arise there.

## Known constraints / non-goals

- **Abstraction litmus (prime directive).** "moved into docs/work/active/<slug>"
  is a filesystem path — a filesystem realization, not a model concept. The
  message must be expressed so a non-filesystem store (Jira, wiki) could realize
  its own location string (issue URL, status label) instead. The CLI must obtain
  the location from the store, not hardcode `docs/work/<status>/` string-building
  in the command handler. Resolving *how* (reuse the FS-only `path()`, or promote
  a small abstract locator to the store interface) is the central spec decision.
- Message wording should be concise and greppable; keep the slug in it so
  existing habits still match.
- Non-goal: changing transition semantics, adding new commands, or touching the
  taxonomy/capabilities axes.
- Non-goal: reformatting unrelated CLI output.

## User decisions already made

- Applies to all location-changing commands, using `tcw work start`'s message as
  the template.

## Open questions for spec

1. Exact inventory of location-changing commands (confirm delegate/escalate,
   decompose/parent de-nest, worktree-start path).
2. Abstraction approach: reuse existing FS `path()` vs. add an abstract
   `locate(slug)`-style accessor returning a human-readable location string.
3. Absolute vs. repo-relative path in the message (relative reads better and is
   what agents grep for).
4. Should the message go to stdout (like the current `started <slug>`) or is any
   of it a stderr hint?

## Tags

`cli`
