# Make tcw init honor a configured taxonomy or capabilities path

When `taxonomy.path` or `capabilities.path` in `tcw-config.yaml` points at a
folder that does not exist, every taxonomy or capabilities command says "no tcw
taxonomy node here — run `tcw init`". Following that advice does not help: `init`
(`tcw/store/fs.py`) reads only `work.path` back from the configuration file, so
`tcw taxonomy init` scaffolds `docs/taxonomy` instead of the configured folder,
and the next command gives the same advice again. `tcw work init` already honors a
configured `work.path`, so the advice is right for work.

Either make `init` scaffold a tree store at its configured path (then the
existing advice becomes correct for all three components), or say what is wrong
("taxonomy.path is not a directory: …") instead of suggesting `tcw init`. Watch
for the work.path rewrite fixed by
2026-09-21-keep-work-path-as-written-when-tcw-work-init-is-re-run-without-path:
a configured path must not be written back.

## Origin

Found on 2026-09-26 while specifying
2026-09-21-let-a-broken-extends-reach-the-user-instead-of-find-node-answering-no-node-here.
Both advisors (Codex, Opus) judged it a separate problem from that item. Bug.

## References

- tcw/store/fs.py `find_node` (the `StoreLocationUnusable` → None branch) and `init`
- tcw/validate.py already reports an unusable configured path
