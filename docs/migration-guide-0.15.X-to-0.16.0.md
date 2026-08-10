# Migrating from 0.15.x to 0.16.0

Version 0.16.0 **removes a requirement**. The `documentation-sync` skill no
longer asks you to wrap changelog entries in the range of git commits they came
from, and the version-fold procedure no longer carries a step for repairing those
ranges after a fold.

**There is nothing you have to do.** Unlike previous migrations, no file moves,
no command changes its flags, and nothing is rejected on upgrade. If you stop
reading here, you are already migrated.

## What changed

The skill used to require this shape:

```markdown
<changes starting-hash="abc1234" ending-hash="def5678">
- Renamed `host` parameter to `hostname` in `createClient`
</changes>
```

It no longer does. The `## Changelog Entry Format` section is gone in full — the
wrapper, the `git rev-parse --short HEAD` recipe for obtaining the hashes, and
the escape hatch for skipping them. A changelog entry is now prose describing
what changed. Everything else about entries is unchanged: include everything,
reference file paths, group by category.

The requirement was dropped because the hashes decayed. Nothing pinned them to
the commits they named, so any rebase, amend, or squash falsified them — and the
fold procedure had to carry a dedicated repair step for ranges the fold itself
invalidated. `git log --grep` and `git blame` answer the same question from the
entry's text, without going stale.

## Your existing entries keep working

Entries you already wrote under the old rule are **fine as they are**. The
`<changes>` wrappers are inert Markdown: they render as nothing, they break no
tooling, and no `tcw` command has ever read them. TCW does not rewrite them and
does not ask you to.

## Optional: clean them up

Only if you want to. Find them first:

```sh
rg '<changes|starting-hash|ending-hash' docs/changelogs/
```

Two reasonable positions, both defensible:

- **Leave released versions alone.** A `docs/changelogs/v1.2.3.md` describes a
  version that already shipped; the hashes in it were accurate when written.
  This is what TCW did to its own history.
- **Strip the unreleased working file.** `docs/changelogs/upcoming.md` has not
  shipped yet, so bringing it in line costs nothing and means your next release
  ships a changelog whose form matches the rule the release announces. This is
  also what TCW did to its own.

If you strip them, remove the hash attributions and leave the entry prose alone —
the wrapper and the ``(`hash`)`` suffixes are the change, not the sentences
around them.

## If you copied the recommended Documentation Sync entry

The suggested line for your project's `CLAUDE.md` / `AGENTS.md` changed:

```diff
-- `docs/changelogs/upcoming.md` [Any-Code-Change] — Developer changelog with commit hash ranges
+- `docs/changelogs/upcoming.md` [Any-Code-Change] — Developer changelog; technical, grouped by category
```

Updating it is cosmetic — the trigger is what does the work, and the trigger did
not change. But an entry still promising hash ranges will read as a live
instruction to the next agent that opens the file, so it is worth the one-line
edit.

## What you don't have to do

- **Nothing to your version-cut process.** If you use `scripts/cut_version.py` or
  an equivalent, the only change is the header text it writes into a fresh
  `upcoming.md`. Rotation, bumping, tagging, and the fold are otherwise
  identical — the fold is simply one step shorter.
- **Nothing to the documentation gate.** Documentation is still written in one
  pass at the end of implementation, not task-by-task. That rule stands; it just
  rests on one reason now instead of two. Docs written mid-implementation
  describe a shape the change no longer has by the time it lands.
- **Nothing about post-mortems.** Reading `git log` over an item's commits during
  a post-mortem is unaffected. That is reading git, which was never the problem;
  the problem was copying hashes into prose that then drifted from them.
