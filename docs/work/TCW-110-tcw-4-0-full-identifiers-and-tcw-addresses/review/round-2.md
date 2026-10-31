---
verdict: rejected
judges: 2
---

# Review round 2 — TCW-110

Reviewed by a separate read-only agent (the `tcw:reviewer` agent) on
2026-10-23 at `c06881ad`, against review round 1's items (a) to (e) and the
change in `0f0d50a0..HEAD`.

The reviewer recommended accepting, with two small message defects that
belong to this change. The user's rule for the TCW-99 children is that an
item is accepted only when the review finds it good enough with no open
finding belonging to the change, so the dispatching session records this
round as rejected and sends the two defects, and the reviewer's nit, back to
implement.

## Checks run

- The full suite as CI runs it, at `b2f4d595`: `5752 passed, 114 skipped in
  527.62s`, run by the dispatching session and recorded in
  `implement/round-2.md`.
- The test files the fixes touch: `678 passed, 1 skipped` and `267 passed,
  9 skipped`.
- `documentation-sync`: unchanged from round 1; the twelve records changed in
  this round are the capability records, now true of the code.

## Round 1's items

- (a) Resolved. All twelve records read in full; none states 3.x behaviour;
  doubtful claims tested by hand in scratch projects.
- (b) Resolved for the forms Design 1.6 names: `show`, `set` and `rm` of
  `cli/has.dot`, and the full identifier, name the rule and the hand rename,
  with singular nouns. Reporting a bad id-part before a wrong namespace is
  acceptable against the spec.
- (c) Resolved (`tests/work/test_gates.py:276-307`).
- (d) Confirmed: with pytest 9.1.1 the order `jira_full_identifiers,
  test_ids, jira_list` gives 17 fixture errors, and the same files with the
  two Jira files together pass; a four-file project outside the repository
  behaves the same. The cause is outside this repository.
- (e) Resolved: the `AmbiguousRef` message no longer gives 3.x advice;
  `tcw init` refuses a `tcw:` value for each path option with exit 2 and
  writes nothing; the three store-location records say so. `TCW://` in
  capitals is a relative path, as everywhere else the scheme is lowercase.

## Findings

1. `tcw init --id rr --work-path /tmp/x work` is refused with a message
   offering "or a tcw:// .path address", a form `init` now refuses. The text
   comes from `store_location_problem` (`tcw/config.py:330-333`).
2. `tcw capabilities show tcw://demo.capabilities/cli/has.dot` names the rule
   but not the hand rename: `parse_address` raises before `sort_input` adds it
   (`tcw/ids.py:343-346`). The full-identifier form of the same folder does
   name it.
3. Nit: the `AmbiguousRef` message prints a literal
   `<project>.<namespace>/web/login` although the command knows the
   namespace.

## What implement must do

- (a) Give `init`'s refusal of an absolute or `~` path a message without the
  `tcw://` option.
- (b) Make the address form of a folder that breaks the rule name the hand
  rename, as the other forms do.
- (c) Print the real namespace in the `AmbiguousRef` message.
- (d) A test for each, and `implement/round-3.md`.
