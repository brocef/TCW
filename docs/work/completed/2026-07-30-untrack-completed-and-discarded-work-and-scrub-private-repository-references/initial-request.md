# Untrack completed and discarded work, and scrub private repository references

Two pieces of repo hygiene for what is a **public, general-purpose plugin
repository**.

## 1. Stop carrying resolved work items in git

`docs/work/completed/` and `docs/work/discarded/` hold ~80 folders of this
repo's own resolved work. Dogfooding produced them, but they are internal
history, not part of what the plugin ships. Add both directories to
`.gitignore` so resolved work stops accumulating in the tracked tree.

The requester chose **untrack going forward**, not a history rewrite: the
existing folders come out of the index (files stay on disk), and past commits
are left alone. Rewriting history would change every SHA, require a force-push,
and break existing clones and the release tags — explicitly not wanted.

## 2. Scrub references to a private project

The requester's private project is named in several places in this repo, mostly
as incidental prose and as quoted repro material in two backlog items. A
general-purpose plugin repo should not carry another project's name. Replace
each mention with a neutral equivalent that preserves the meaning of the
surrounding text.

The name itself is deliberately not written down anywhere in this item — that
would defeat the purpose. Locate the occurrences with an ad-hoc
case-insensitive grep at implementation time.

## Constraints

- No history rewrite. No force-push.
- Scrub scope is **tracked files only**. The hits inside
  `docs/work/completed/` leave the repository as a side effect of item 1, so
  rewriting them on disk is pointless churn.
- No artifact of this work item may contain the private name — including its
  own slug, which is why the title says "private repository references".
- Completing a work item must keep working afterwards, and must not quietly
  re-add the ignored folders to the index.

## Notes

- **Known snag, found while scoping:** gitignoring the folders is not
  sufficient on its own. `tcw work complete` effects the transition with
  `git mv` (`tcw/store/fs.py:270`), and `git mv` tracks a destination inside an
  ignored directory without complaint — verified in a scratch repo. Without a
  fix, every future completion would re-add the item that was just ignored.
- Reference material was not separately requested: the ask is self-contained
  repo hygiene and every source is in-repo, listed below.

## References

- `.gitignore` — where the two ignore entries go.
- `tcw/store/fs.py:270` `git_mv` — the transition mechanic that defeats a plain
  gitignore; also reached by re-parenting (`fs.py:2735`), not just by
  `complete`.
- `tcw/store/fs.py:2391` `_effect_transition` / `:2409` `_commit_transition` —
  the scoped commit that has to keep working when the destination is ignored.
- `tests/test_work_autocommit.py` — the transition-commit tests; their
  `tmp_path` repos have no gitignore, so they document the unignored path.
- `docs/plan/phase-5-work.md`, `docs/plan/phase-6-beyond.md` — the name appears
  in historical planning prose about downstream consumers.
- `docs/work/backlog/2026-07-29-make-the-reconcile-rollup-read-the-canonical-capabilities-yaml-schema/initial-request.md`,
  `docs/work/backlog/2026-07-29-resolve-relative-connected-projects-paths-against-the-main-worktree-root/initial-request.md`
  — the name appears in quoted repro material; the surrounding repro must stay
  intelligible after the rename.
