# Refined outcome

**Accepted by the user on 2026-10-01**, together with its three sibling items.

## The acceptance criteria

All five met (`tests/test_damaged_state_on_edit.py`, 13 passed): `edit` with
`--tag`, `--title`, `--priority` and `--blocked-by` refuses naming the item,
the file and `tcw validate`, leaving the file byte-for-byte unchanged; `start`
refuses the same way; `tcw validate` reports the file with PyYAML's excerpt; a
broken `tcw-config.yaml` names its file.

## Folded in at verify

Two rounds, recorded in `outcome.md`: more readers name their file
(`d4fbdc38`); the sidecar error names its full path, plus a stale comment and a
contradictory changelog line (`d61a543f`).

## Deferred, with reasons

- Two YAML errors still name no file: a character YAML forbids (raised before
  the loader has a name) and a duplicate key (no position at all). Disclosed in
  `outcome.md` and the loader's docstring; not worth a work-around.

## Evidence

- Full suite under bare `pytest` at `d61a543f`, clean tree: **5231 passed, 3 skipped**. This is
  the first full run after `d49c4fee`, which `outcome.md` noted had not had one;
  an earlier run at `0080da55` gave 5228 passed, 3 skipped.
- Each item was assessed against its spec by a separate read-only verifier that
  ran the item's targeted tests and reproduced the behaviour by hand in a
  throwaway project. Every acceptance criterion was met.

## Closeout

- The four items were built, reviewed and tested together and are accepted
  together. The code is already on `main`; there is no merge-back.
- The item was moved to `review` by hand in the session that built it (that
  session was editing `tcw/`); it is completed with `tcw work complete`, run
  against a clean, committed tree.
- No originating GitHub issue. The version cut that ships these four is the
  user's call; nothing is pushed or published by this closeout.
