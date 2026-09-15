# Drop commit hash ranges from changelog entries

Stop requiring that developer changelog entries carry the git commit range they
came from. The requirement should be removed from the `documentation-sync` skill
itself — so no project that adopts the skill inherits it — and from TCW's own
`AGENTS.md` Documentation Sync entry.

## Product changes

Projects using `documentation-sync` no longer have to record commit hashes when
they write a changelog entry. The changelog is prose describing what changed, not
an index into git.

## Technical changes

Nothing in the `tcw` CLI enforces the requirement; it is carried entirely by
instruction prose. The known sites are:

- `skills/documentation-sync/references/release-notes-and-changelogs.md` — the
  "Changelog Entry Format" section that mandates the `<changes starting-hash=…
  ending-hash=…>` wrapper, plus the recommended Documentation Sync entry text.
- `skills/documentation-sync/SKILL.md` — the recommended entry text and the
  rationale sentence for the end-of-`implement` documentation gate.
- `skills/documentation-sync/references/cut-version.md` — the fold-a-release
  guidance about extending stale commit ranges.
- `AGENTS.md` (`CLAUDE.md` is a symlink to it) — TCW's own Documentation Sync
  entry for `docs/changelogs/upcoming.md`.
- `scripts/cut_version.py` — the header template it writes into a fresh
  `docs/changelogs/upcoming.md` after rotation.
- `skills/tcw-work/references/stage-implement.md` — step 6's rationale sentence.
- `docs/changelogs/upcoming.md` — the current header text.

## Meta changes

None. The work lifecycle is unchanged.

## Why

Two reasons, both from the requester:

1. **The hashes go stale.** Rebase, amend, squash, or folding a release rewrites
   the commits, so a recorded range points at objects that no longer exist. A
   traceability aid that silently lies is worse than no aid.
2. **It is not worth the effort.** Computing and threading the range costs agent
   turns and clutters the diff, for a lookup nobody actually performs — `git log
   --grep` or blame finds the originating commit anyway.

## Constraints

- **Existing changelog history is left alone.** Released `docs/changelogs/v*.md`
  files keep their hashes; so does the pending `docs/changelogs/upcoming.md`. Only
  the requirement to write *new* ones goes away. Rewriting history was explicitly
  declined.
- **The end-of-`implement` documentation gate stays where it is.** Its stated
  rationale currently has two halves, and one of them is "a changelog entry can't
  state its commit range until the range exists". That clause must go, but the
  gate itself and its other half — docs written mid-implementation describe a
  shape the change no longer has by the time it lands — remain. Rewrite the
  rationale; do not move the gate.

## Out of scope

- Reconsidering *when* documentation is written during `implement`. The gate's
  placement is not up for review in this item.
- Stripping hashes from any changelog file, upcoming or released.
- The separate `skill-cefailures:documentation-sync` skill, which lives in another
  repository.

## Notes

The requester asked for removal of "the documentation sync requirement that we
provide the git commit range in the changelog". Scope, history handling, and the
gate rationale were settled by direct question before this was written; the
answers are recorded above as constraints rather than inferences.

The file list under *Technical changes* is a discovery aid from a grep at request
time, not a commitment — the `spec` stage owns confirming it is complete.
