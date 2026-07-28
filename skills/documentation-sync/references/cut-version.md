# Cut a New Version

Read this when the user has chosen a `patch`, `minor`, or `major` bump from this
skill's completion options (see `SKILL.md` → "When to offer version and changelog
options"). It covers choosing the bump size and running the version-cut ritual.

If the user instead chose to keep the current version, **stop** — leave
version-bearing metadata, tags, and `upcoming.md` file names alone, and just
update the release-note and developer-changelog working files whose triggers
fire.

## Step 0: Does the project already have a version-cut process?

Check the project's `CLAUDE.md` (usually a `## Versioning` section) for a
documented command or script. If one exists, **use it** — it knows which files
carry the version and how they must move together. Only fall through to the
manual steps below when the project has no such process.

> TCW's own repo is the example: `python scripts/cut_version.py <patch|minor|major|X.Y.Z>`
> bumps all five version-bearing files, rotates the `upcoming.md` working files,
> commits, and tags. Doing those steps by hand there would drift.

## Choosing the Bump

Use a pragmatic, size-of-change framing rather than strict SemVer — bumps scale
to the magnitude of the change set, with reverse-incompatibility a contributing
signal rather than the sole gate:

| Bump    | Use for                                                                                                                                                                                        |
| ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `patch` | The default for routine work — bug fixes, internal refactors, small features, doc updates, dependency bumps, and anything that doesn't merit a higher bump.                                     |
| `minor` | Medium-sized change sets — substantial feature work, notable refactors, or related groups of changes shipped together. May include _some_ reverse-incompatible changes when scoped and intentional. |
| `major` | Extremely large change sets — sweeping rewrites, broad reverse-incompatible work, or dropping support for a previously-supported platform/version. **Only when explicitly instructed by the user.** |

A single localized breaking change inside an otherwise medium-sized set of work
is fine in a `minor`; a broad pattern of breaking changes across the codebase is
a `major`. If you're unsure where a change set lands, ask the user before bumping.

## Step 1: Bump the version

Bump **every** version-bearing file so they stay in sync — a desynced version is
its own kind of bug. Where the version lives depends on the ecosystem: `npm version`
/ `package.json`, `Cargo.toml`, `pyproject.toml` plus a `__version__` constant,
a plugin manifest (`.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`,
`.codex-plugin/plugin.json`), a `VERSION` file, or a Go module tag (no file edit —
the tag in Step 4 _is_ the version).

Grep for the current version string before you start; projects routinely carry it
in more places than their docs admit.

## Step 2: Rotate `upcoming.md` files

Rename both working files to versioned files, then create fresh empty
`upcoming.md` files for subsequent work:

```bash
git mv docs/release-notes/upcoming.md docs/release-notes/v{version}.md
git mv docs/changelogs/upcoming.md docs/changelogs/v{version}.md
```

If the project uses a different layout, adapt: rotate whatever per-release working
file it keeps, then start a new one. Never lose content — every entry that was in
`upcoming.md` belongs to the version being cut.

## Step 3: Commit

Stage the version bump and the rotated docs **together**, so the versioned
notes/changelog ship with the version — and keep that release commit free of
functional code changes, which belong to the commits being released. Match the
project's commit-message style if it has one; otherwise:

```bash
git commit -m "chore(release): cut v{version}"
```

## Step 4: Tag the commit

```bash
git tag v{version}
```

Tag the version-bump commit itself — not an earlier or later one. In many projects
this tag triggers release and docs-deployment workflows; even where it doesn't, it
gives readers a stable anchor.

**Publishing is a human step.** Ask before `git push` / `git push --tags`.

## Folding into an unpushed version

Run this when the user picked option 5 — the last version was cut locally but
never pushed, and the work since it should join that release rather than get a
release of its own. Typical shape:

```
A ← origin/main        B (tag: v3.2.1)        C ← HEAD
```

`v3.2.1` was cut at `B`; `C` landed afterwards. Nothing about `v3.2.1` has
reached anyone, so the tag can move to `C` and its notes can grow to cover it.

**Re-confirm it is unpushed before touching anything** — run
`scripts/unpushed-version.sh` and require exit code `0`. On `1` the tag is
published (or there is nothing to fold) and on `2` the remote could not be
reached; in both cases stop and cut a new version, or ask. A published tag that
changes meaning is worse than an extra version number.

The check has to touch the network, and a prior `git fetch` is not a substitute:
fetched tags are written into the same `refs/tags/` namespace as ones you
created, so no local ref says which of them the remote has. If the script cannot
reach the remote, ask the user — do not fetch and assume.

The version number does **not** change, so the version-bearing files are not
touched. What changes is the tag's position and the release documents' contents.

1. **Delete the local tag.**

   ```bash
   git tag -d v{version}
   ```

2. **Merge the newer content into the versioned files.** Anything written into
   `docs/release-notes/upcoming.md` and `docs/changelogs/upcoming.md` since the
   cut belongs to `v{version}.md` now — move it in, merging into the existing
   sections rather than appending a second `## Added` beside the first.

3. **Answer any still-unevaluated triggers** for the commits since the tag, into
   the same `v{version}.md` files. The fold is a documentation gate like any
   other; commits arriving after a cut are not exempt.

4. **Reset the `upcoming.md` files** to their empty-header state — their content
   just moved.

5. **Commit**, matching the project's style:

   ```bash
   git commit -m "chore(release): fold <description> into v{version}"
   ```

6. **Re-tag at HEAD.**

   ```bash
   git tag v{version}
   ```

Verify with `git tag --points-at HEAD` before reporting done — a fold that left
the tag on the old commit looks identical in `git log` and is only discovered at
push time.

## Common Mistakes

| Mistake                                                       | Fix                                                                          |
| ------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Cutting by hand when the project ships a version-cut script   | Run Step 0 first — the script exists because the file set is easy to miss    |
| Forgetting one of multiple version-bearing files              | Grep for the old version string; bump all hits that are version declarations |
| Tagging an earlier or later commit                            | Tag the version-bump commit itself                                           |
| Pushing the tag without asking                                | Pushing a tag is publishing — confirm first                                  |
| Bumping when the user chose "keep the current version"        | That choice touches changelog files only                                     |
| Folding into a tag that was already pushed                    | Both checks must pass first; otherwise cut a new version                     |
