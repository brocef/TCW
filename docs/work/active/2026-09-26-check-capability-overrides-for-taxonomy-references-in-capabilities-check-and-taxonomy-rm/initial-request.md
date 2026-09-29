# Check capability overrides for taxonomy references in capabilities check and taxonomy rm

A local override — a capability folder with `overrides:` that adjusts an
inherited capability — can set `Subject` or `Feature` to a local taxonomy term.
Neither `tcw capabilities check` nor `tcw taxonomy rm`'s refusal to remove a
term a capability still names looks at overrides, so a broken reference in one
is never reported, and `rm` can remove a term an override still names.

Wanted: both commands treat an override's references the way they treat a local
capability's.

## Notes

- Written during an unattended run (2026-09-29) with nobody to ask; everything
  comes from `intake.md`, filed by the code review of
  `2026-09-24-close-the-remaining-gaps-in-tcw-taxonomy-rm`. Reference material:
  asked; none beyond the intake's.
- Reproduced on 2026-09-29 (scratch script `repro3.py`): an override with
  `Subject: [zed]` and `Feature: nope` — `check()` returns `[]`, and
  `FsTaxonomyStore.remove("zed")` removes the term.

## References

- `tcw/store/fs.py` `FsCapabilitiesStore._local_paths`, `check`, `_term_refs`;
  `FsTaxonomyStore._capability_referrers` — the two readers and the shared
  definition of which references count.
