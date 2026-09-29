# Check capability overrides for taxonomy references in capabilities check and taxonomy rm

A local override (a capability folder with `overrides:`) can set `Subject` or
`Feature` to a local taxonomy term, but neither `tcw capabilities check` nor
`tcw taxonomy rm`'s capability guard reads overrides: both use
`list_all(local_only=True)`, and `_local_paths` excludes override folders. So a
dangling reference in an override is never reported, and `rm` can remove a term
an override still names.

Found by the code review of 2026-09-24-close-the-remaining-gaps-in-tcw-taxonomy-rm
and placed in a separate change (the two readers are consistent with each other
today). Bug.

## References

- tcw/store/fs.py `FsCapabilitiesStore._local_paths`, `check`, `_term_refs`;
  `FsTaxonomyStore._capability_referrers`
