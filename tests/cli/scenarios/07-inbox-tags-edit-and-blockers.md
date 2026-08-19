# 07 — Inbox intake, tags, edits, and blocking links

The item-metadata surface: how work enters the system informally, and how an
item's fields change after creation.

## Functionality covered

- `tcw work inbox list|path|show|accept`, `--title`
- `tcw work tags list|add|rm`, `--tag` on `new`
- `tcw work edit` — `--title`, `--priority`, `--effort`, `--complexity`,
  `--tag`, `--untag`, `--initiative`
- `--blocked-by`, `--blocks`, `--unblocked-by`, and external blocker text

## What is tested

| # | Assertion |
| - | --------- |
| 1 | A Markdown file dropped into the inbox folder (located via `tcw work inbox path`, never composed) appears in `tcw work inbox list`. |
| 2 | `tcw work inbox show <entry>` prints its content, exit 0. |
| 3 | `tcw work inbox accept <entry>` creates a backlog item, prints its slug on stdout, and the entry is no longer listed as raw intake. |
| 4 | The accepted item's title is derived from the document; `--title "Override"` sets it instead. |
| 5 | The raw document's text survives onto the item as its intake artifact — accepting does not discard the original wording. |
| 6 | `tcw work inbox accept no-such-entry` exits non-zero, stdout empty, and creates no item. |
| 7 | `tcw work tags add bug cli` registers both; `tcw work tags list` shows them. |
| 8 | `tcw work new "T" --tag bug` succeeds; `--tag not-registered` is **refused** non-zero and creates nothing. (If unregistered tags are instead accepted with a warning, pin that — but pin one of the two.) |
| 9 | `tcw work tags rm bug` unregisters it; an item already carrying `bug` is unaffected (removal is from the registry, not from items). |
| 10 | `tcw work list --tag bug` filters; two `--tag` flags match **any**, not all. |
| 11 | `tcw work edit $SLUG --title "New title"` changes the title and **leaves the slug unchanged** — asserted by re-resolving the original slug afterwards. |
| 12 | `--effort H` and `--effort high` store the same value; an invalid value (`--effort enormous`) is refused non-zero with the item unchanged. |
| 13 | `tcw work edit $SLUG --tag x --untag y` applies both in one call. |
| 14 | `--blocked-by <other-slug>` records a structured blocker; `tcw work show` renders it. |
| 15 | `--blocked-by "waiting on vendor"` records an **external** blocker as free text, and the text survives round-tripping through `show`/`show --json` **including commas** — a comma must not split one external blocker into two. |
| 16 | `--unblocked-by` accepts the exact `external: …` form that `show`/`list` display, so a user can copy what they were shown. |
| 17 | `--blocks a,b` sets the reverse link on both named items, and both then report the blocker. |
| 18 | Completing the blocking item clears the block: the blocked item then starts without `--force`. |
| 19 | `tcw work edit $SLUG --initiative ""` clears the back-pointer. |

## Refusals asserted

- unknown inbox entry (6)
- unregistered tag, or its pinned alternative (8)
- invalid effort/complexity value (12)

## Explicitly not covered here

Cross-node delegation into another node's inbox — scenario 10.

## Notes for the implementer

Assertion 15 is a fixed defect (`2026-07-23-blocker-refs-comma-split-mangles-external-text-...`)
and therefore a regression test: use a blocker string with a comma **and** a
colon in it, since both are structural characters in the display form.
