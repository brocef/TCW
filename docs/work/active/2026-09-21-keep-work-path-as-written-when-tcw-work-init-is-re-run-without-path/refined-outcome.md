# Refined outcome: keep work.path as written when init is re-run without --path

## Decision

**Accepted** on 2026-09-26, in an unattended run (`extras-autonomous-work`):
the decision was made by the coordinating session on the verifier's
recommendation, with no user present.

## Evidence

- Criteria 1-3: `tests/test_config_edit_writers.py` (37 passed after the
  verify fold-in); the verifier re-ran the command by hand for `./store`,
  `~/store` under a temporary `HOME`, and an explicit `--path other`, and put
  the old `fs.py` back to see two of the three tests fail on the bug itself.
- Criterion 4: full suite 4478 passed, 3 skipped — run twice, by the
  implementer and independently by the code reviewer.
- Hands-on by the coordinating session: `diff` of the configuration file before
  and after `tcw work init` was empty in both cases.

## Follow-ups

- Filed: `2026-09-26-make-tcw-init-honor-a-configured-taxonomy-or-capabilities-path`.
- Folded in rather than filed: the `~name` traceback the reviewer found.

## Closeout

- Route: `tcw work complete`, merging `work/<slug>` into `main` locally; not pushed.
- No capability ledger change (none declared, none shipped).
- Version: not cut; entries wait in `docs/*/upcoming.md` for the next release.
