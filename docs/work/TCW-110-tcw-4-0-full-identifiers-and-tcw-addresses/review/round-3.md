---
verdict: accepted
judges: 3
---

# Review round 3 — TCW-110

Reviewed by a separate read-only agent (the `tcw:reviewer` agent) on
2026-10-23 at `00398379`, against review round 2's items (a) to (d) and the
change in `673175da..HEAD`. Rounds 1 and 2 checked every acceptance criterion
and every capability record; their findings are all resolved, so this round
judges the last fixes and carries the earlier results forward.

## Checks run

- The full suite as CI runs it, `.venv/bin/pytest -q -p no:cacheprovider`, at
  `d04642af` (the last code commit): `5759 passed, 114 skipped in 516.12s`,
  run by the dispatching session and recorded in `implement/round-3.md`.
- The five touched test files: `278 passed, 1 skipped in 16.52s`.
- `documentation-sync`: unchanged from round 1. The two `upcoming/` files are
  written; README, the guides, the skills, `skills/configure/references/` and
  `docs/use-cases.md` are deferred to TCW-117, whose ticket holds the note on
  what each must say. No capability record quotes the changed messages.

## Round 2's items

- (a) Met. `tcw init --id rr --work-path /tmp/x work` and
  `--capabilities-path '~/x'` exit 2 with a message that offers no `tcw://`
  address, and write nothing. A location read from the configuration still
  gets the full message in `tcw validate`, `tcw capabilities list` and
  `tcw init capabilities`. The new `address` parameter of
  `store_location_problem` defaults to true; only the two checks of a path
  typed on the `init` command line pass false (`tcw/cli.py:75`,
  `tcw/store/fs.py:648`).
- (b) Met. `show` and `rm` of the `tcw://` address of a capability or term
  folder that breaks the rule exit 2 with the rule and "rename it by hand"; a
  `//` slip gets only the rule.
- (c) Met. `AmbiguousRef` takes the namespace (`tcw/store/base.py:39`), and
  both raisers pass it; `test_cli_rm_ambiguous` and
  `test_resolution_ambiguous_errors` assert the text.
- (d) Met.

## Acceptance criteria

All 25 are met, as round 1 found; 20a's served-board half is for qa's
end-to-end pass, as the plan says. Every path in `capabilities.yaml` is
present and describes what the code does.

No finding belongs to this change. One minor note, in code this round did
not touch: a refused `tcw://` address is quoted in the error without its
`tcw://` prefix. It reads clearly, and is kept as a small wording follow-up
for the 4.0 run rather than a new item.
