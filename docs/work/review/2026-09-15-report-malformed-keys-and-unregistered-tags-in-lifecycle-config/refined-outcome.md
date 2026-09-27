# Refined outcome: report malformed keys and unregistered tags in lifecycle config

## Decision

**Accepted** on 2026-09-26 in an unattended run (`extras-autonomous-work`), by
the coordinating session on the verifier's recommendation; no user present.

## Evidence

- Criteria 1-8: `tests/test_lifecycle_config_tags.py` (27 of its first 30 tests
  failed on the pre-branch code, the other 3 are guards), and the verifier's
  hands-on runs of each criterion, including all six non-string-key sites, which
  crash main's build with a `TypeError`.
- Criterion 9: full suite 4528 passed, 3 skipped on the code before the verify
  fix. The verify fix changed one message; its file, the tag, validate-target,
  config-writer, lifecycle and procedure tests passed (242 + 31 + 53), and after
  merging main the affected files passed again (294). This repository's own
  `tcw validate`: OK.

## Fixed at verify

A condition-tag problem was located by a position that counted only the entries
left after parsing, so it named the wrong entry when an earlier one was dropped.
It now names the entry by its `kind: value`.

## Follow-ups

- Filed earlier: `2026-09-26-read-item-tags-normalized-and-keep-non-tag-work-tags-entries-visible`.

## Closeout

- Route: `tcw work complete`, merging into `main` locally; not pushed.
- Jira TCW-25 moves with the item through tracker sync.
- No capability ledger change. Version not cut.
