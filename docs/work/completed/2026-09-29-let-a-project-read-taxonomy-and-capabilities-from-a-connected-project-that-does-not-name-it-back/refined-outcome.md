# Refined outcome

**Accepted by the user on 2026-09-29.**

## Evidence

An independent read-only verifier checked the diff against every acceptance
criterion, running the worktree's own code: 405 targeted tests passed and
`tcw validate` passed. It probed further than the tests — `submit`, `rework`,
`complete`, `delete`, `scaffold` and `stage prompt` on an upstream item by hand
(all refused, core untouched), the taxonomy and capabilities write routes of
`tcw serve`, and every graph walk (children, ancestors, loading, provisioning)
for a path to or past an upstream. It found none.

| # | Criterion | Evidence |
| - | --------- | -------- |
| 1 | reader, one hop | `test_the_cli_reads_an_upstream_one_hop`; `taxonomy list` run by the verifier |
| 2 | reader, through a parent | `test_the_cli_reads_an_upstream_through_a_parent`; all three real packages, by hand |
| 3 | public upstream, reader-only checkout | `test_a_public_upstream_is_provisioned_into_a_reader_only_checkout`, `test_the_override_variable_redirects_an_upstream_from_the_cli` (now with `list`), `test_an_absent_upstream_is_a_warning_and_extends_says_unreachable`; the real app repository cloned alone, by hand |
| 4 | refused writes | `test_a_write_into_an_upstream_is_refused_as_read_only`, `test_delegate_into_an_upstream_is_refused`, `test_serve_refuses_a_write_into_an_upstream` (8 routes); 403 by `curl` on the real configs |
| 5 | read-only from every direction | the same tests, run from `a`, `b` and the root |
| 6 | reads allowed | `test_reading_an_upstream_item_is_allowed` (now with `stage validate`), `test_serve_reads_an_upstream_item`, `test_a_link_into_an_upstream_item_resolves` |
| 7 | not walked, not beyond | `test_the_upstream_stays_off_the_familys_lists`, the `nodes` tests, `test_a_project_beyond_an_upstream_cannot_be_named`, `test_provision_does_not_follow_an_upstreams_own_connections` |
| 8 | graph problems | the self-, child-, sibling- and grandparent-upstream tests; the two duplicate-declarer tests |
| 9 | migration order | `test_the_proposit_migration_passes_through_no_blocked_state`, `test_the_reverse_migration_order_still_fails`; steps 1, 2, 5-before-4, 4 and 5 on copies of the six real configs |
| 10 | reciprocity tests unchanged | `tests/test_project_registry.py` untouched by the diff; 68 passed |
| 11 | full suite | bare `pytest` at `f5f3fa81`: 4984 passed, 3 skipped, 0 failed; `tcw validate` OK |

Criterion 9's wording ("the warning in core and the root") is narrower than the
behavior: every node that loads core reports it. Recorded in `outcome.md`.

## Fixed at verify

`tcw work stage validate` refused an upstream item it only reads; it now uses the
reading form. The criterion-3 test checks `taxonomy list` as worded. Both in
`f5f3fa81`.

## Deferred, not filed

- A `duplicate project id` reached once as a child and once as an upstream names
  only the upstream's declarer. Minor; left as is with the user's acceptance.

## For the requester (the Proposit orchestrator)

- Before step 5, rewrite or unlink the 12 `tcw://W/proposit-app/…`,
  `proposit-shared/…` and `proposit-app-repo/…` links in 11 finished items on
  core's board; after step 5 core cannot see those projects and `validate`
  reports each one.
- `proposit-server` has two pre-existing malformed links (`tcw://proposit-…`
  with no axis letter), unrelated to this change.

## Closeout

- Origin: a peer request from the Proposit orchestrator session, not a GitHub
  issue — nothing to close.
- Release: the user publishes. After merging, the orchestrator is told the
  version is ready to publish.
