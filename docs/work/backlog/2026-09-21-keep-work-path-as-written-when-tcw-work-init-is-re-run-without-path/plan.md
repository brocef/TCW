# Plan: keep work.path as written when init is re-run without --path

## Tasks

1. **Failing tests first.** Add to `tests/test_config_edit_writers.py` (which
   already holds the "a config write changes only its own lines" tests):
   - re-running `init(["work"], root)` on a node whose config says
     `path: ./store` leaves the file byte-identical (criterion 1);
   - the same with `path: ~/store` under a monkeypatched `HOME` (criterion 2);
   - an explicit `work_path=Path("other")` still writes `path: other`
     (criterion 3).
   Proof: the first two fail on the current tree, the third passes.
2. **Fix** `tcw/store/fs.py` `init`: when the work location was read from the
   configuration file, keep using it for planning and scaffolding but leave it
   out of the `SetScalar` edits. Proof: task 1's tests pass; full suite green
   (criterion 4).

## Documentation Sync

- `docs/changelogs/upcoming.md` [Any-Code-Change] — a `### Fixed` entry.
- `docs/release-notes/upcoming.md` [Public-API] — one plain-language line: a
  re-run of `tcw work init` no longer rewrites a `work.path` you wrote.
- `README.md`, guides, skills, configure references: no trigger fires — no CLI
  surface, key, or documented behavior changes (the guides never promised the
  rewrite). Re-checked against the finished diff at implement.

## Verification

Hands-on: in a scratch git repository, provision a store at `./store`, set
`work.path: ./store`, run `tcw work init` from the worktree's source, and diff
the configuration file (expect no change); repeat with `~/…` under a temporary
`HOME`.
