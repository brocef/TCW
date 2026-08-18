## Inbox manifest

- `versioning-section-has-the-same-defect-as-documentation-sync.md`

## Inbox body

# The `## Versioning` section has the same defect as `## Documentation Sync`

Deferred out of scope by
`docs/work/active/2026-08-18-serve-documentation-sync-entries-from-tcw-config-yaml-instead-of-scraping-the-agent-guide/spec.md`,
which says to flag it rather than fold it in silently. Flagging it.

`skills/documentation-sync/SKILL.md:117` sends the version-cut path to "the
project's own version-cut process (every project bumps differently; its
`CLAUDE.md` / Versioning section names the files and the script)". That is the
same shape as the documentation-sync defect: an instruction that TCW must
guarantee, obtained by name-matching a Markdown section in a file TCW does not
own, in a format nothing validates.

The doc-sync item establishes the pattern for fixing it — a `work.*` block in
`tcw-config.yaml`, a pure parser with an advisory problem list, a method on the
`WorkStore` interface, and a read-only verb to serve the non-stage invocation
point. If that lands, this is the same shape a second time and should be much
cheaper.

## What a fix would have to carry

This repo's own `## Versioning` section is more than a file list — it names five
version-bearing files that must move in lockstep, the script that moves them
(`scripts/cut_version.py`), and the test that guards the invariant
(`tests/test_plugin_manifests.py`). Config would need to express at least the
file list and the cut command; the prose about *why* they are duplicated is
project documentation and can stay in the agent guide.

## Worth deciding first

Whether this is worth doing at all, or whether the version-cut path is
sufficiently project-specific that naming a script in config buys nothing over
naming it in prose. The doc-sync case was clear because the *gate* has to fire
reliably; a version cut is always user-initiated and never automatic, so the
guarantee argument is weaker. Do not assume the answer is yes because the
previous one was.

## Not blocked, but sequence it after

The doc-sync item is in `active` and unimplemented. There is no point designing
this until that pattern is real, since the whole value here is reusing it.
