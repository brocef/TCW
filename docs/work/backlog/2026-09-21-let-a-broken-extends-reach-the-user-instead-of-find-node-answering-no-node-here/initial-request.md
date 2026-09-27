# Let a broken extends reach the user instead of find_node answering no node here

A taxonomy or capabilities command run in a node whose `extends` is broken (an
unknown project, a store extending itself) tells the user "no tcw taxonomy node
here — run `tcw init`". That is wrong advice: the node is right there, and
`tcw init` could scaffold a second, empty store beside the real one. The user
should see the actual problem instead, as they already do for the two
provisioning errors. Keep answering "no node here" for the cases that genuinely
mean there is no store.

## Notes

- Written during an unattended run (2026-09-26) from `intake.md`; there was no
  requester to ask. References: asked; none provided beyond the intake's pointers
  (`find_node` in `tcw/store/fs.py`; the outcome of
  `2026-09-21-report-a-leftover-pre-2-5-0-store-config-file-instead-of-silently-dropping-its-extends`,
  retained in commit 49ceb80a, whose "Spec gap" note describes the reproduction).
