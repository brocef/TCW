# Make tcw init honor a configured taxonomy or capabilities path

When `taxonomy.path` or `capabilities.path` in `tcw-config.yaml` points at a
folder that does not exist, every taxonomy or capabilities command says "no tcw
taxonomy node here — run `tcw init`". Following that advice does not help:
`tcw taxonomy init` scaffolds `docs/taxonomy` instead of the configured folder,
and the next command gives the same advice again. `tcw work init` already
honors a configured `work.path`.

Wanted: following the advice works — or the advice says what is actually wrong.
A configured path must not be rewritten by `init` (the fix in
`2026-09-21-keep-work-path-as-written-when-tcw-work-init-is-re-run-without-path`).

## Notes

- Unattended run (2026-09-29); from `intake.md`. Reference material: asked; none
  beyond the intake's.
- Reproduced 2026-09-29 in a scratch node with `taxonomy: {path:
  knowledge/terms}`: `tcw taxonomy init` created `docs/taxonomy`,
  `knowledge/terms` stayed absent, and `tcw taxonomy list` still said "run
  `tcw init`".

## References

- `tcw/store/fs.py` `init` (reads back only `work.path`) and `find_node` (the
  `StoreLocationUnusable` → None branch that produces the advice).
- `tcw/validate.py` — already reports an unusable configured path.
