# Refuse glob and path characters in store names

Two ways a store identifier is read as more than a name:

1. A work slug beginning with `/` crashes `get`, `start` and `submit` with
   `NotImplementedError: Non-relative patterns are unsupported` from `Path.glob`
   in the claim lookup, instead of "no such work item".
2. Git reads every path the store hands it as a pattern (a "pathspec"), even
   after `--`. A store folder whose name holds `*`, `?` or `[` matches others:
   writing the capability `a*` stages an unrelated edit to `abc`, and its commit
   takes `abc` along. Only `git rm` was fixed, by `--literal-pathspecs`.

## Notes

- From the intake (Jira TCW-20), triaged 2026-09-15; both reproduced on main
  2026-09-26. Written during an unattended run; no requester to ask.
  References: asked; none beyond the intake.
- Despite the title, names are not refused: the fix makes every such name
  behave as the literal name it is (see the spec's advisor note).
