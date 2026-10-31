---
verdict: accepted
judges: 3
---

# Review round 3 — TCW-113

Reviewed by a separate read-only agent (the `tcw:reviewer` agent) on
2026-10-24 in a frozen worktree at `e309b806`, branch `v4` with TCW-115 also
landed, against review round 2's finding and the item found by TCW-115's
review round 3, over `7a75a565..e309b806`. Earlier rounds' results carry
forward.

## Checks run

- The full suite as CI runs it, run by the dispatching session at `79ece028`
  in two halves by folder: `2183 passed, 2 skipped` and `5110 passed,
  111 skipped`, recorded in `implement/round-3.md`. `pnpm test`
  `233 passed`; `tsc --noEmit`, `pnpm lint`, `pnpm check:build` clean.
- By the reviewer: `tests/serve/test_scope.py` and
  `tests/serve/test_other_project.py`, `50 passed`;
  `tests/work/test_scope_work.py`, `25 passed`; the four
  `tests/test_scope_*.py` files, `107 passed` (implement round 3's `105` was
  counted before item (c)'s two cases were added).
- By hand, through a guarded wrapper and `tcw serve`, on a fresh family: a
  full identifier of one project with `project=` naming another answers 400
  `usage` with the command line's exact words, for work, capabilities and
  taxonomy; 200 when `project` matches or is absent; a folder name with
  `project=` names that project's item, byte for byte what `tcw work show
  --project … --json` gives. In a headless browser with the page's project
  filter set, the list still filters, and links to the served project's and
  another project's items open the right page with no error. With a parent's
  stores declared in a repository and not fetched, `taxonomy show` and
  `capabilities show` under `own` print `list`'s warning, naming `tcw -C
  <parent folder> project provision --component <axis>`, then the not-found
  line, and exit 4; `--scope up` exits 7.

## Round 2's item and the added item

- (a) Met. The folder-name reading follows Design 2.3 word for word.
- Item (c) Met. Leaving out the hint when the view cannot be built follows
  Design 4.8; the changed assertion keeps its force; `tcw serve`'s 404 is
  unchanged, and the spec asks for nothing there.
- The mutations described in implement round 3 would each turn their tests
  red (reasoned from the code).

No finding belongs to this change, and none needs a separate change. The
reviewer notes that item (c)'s test checks only that the warning is not the
last line, not that it comes right before the not-found line; weak, and
enough.
