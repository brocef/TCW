# Serve version-cut instructions from `tcw-config.yaml` instead of the agent guide

The version-cut path has the same defect documentation-sync had, and should be
fixed the same way.

## The defect

`skills/documentation-sync/SKILL.md:117` sends the version-cut path to "the
project's own version-cut process (every project bumps differently; its
`CLAUDE.md` / Versioning section names the files and the script)". That is an
instruction TCW has to get right, obtained by name-matching a Markdown section in
a file TCW does not own, in a format nothing validates. Rename the heading,
reword the list, or move the file, and TCW silently stops knowing how the project
cuts a version.

This was deferred out of scope by the doc-sync item's spec, which said to flag it
rather than fold it in silently. This is the flag.

## What is being asked for

The machine-checkable parts of a project's version-cut process should come from
`tcw-config.yaml`, which TCW owns and can validate, rather than from prose it
scrapes. For this repo that is three things:

- the version-bearing files that must move in lockstep (here, five of them),
- the command that moves them (here, `scripts/cut_version.py`),
- the test that guards the invariant that they agree (here,
  `tests/test_plugin_manifests.py`).

The prose explaining *why* the version is duplicated across five files is project
documentation and stays in the agent guide. Config carries the facts; the guide
carries the reasoning.

## Constraints

- **Sequence it after the doc-sync item.** The whole value here is reusing a
  pattern that does not exist yet — a `work.*` block in `tcw-config.yaml`, a pure
  parser with an advisory problem list, a method on the `WorkStore` interface,
  and a read-only verb serving the non-stage invocation point. Designing this
  before that lands means designing it twice. Recorded as a blocking link.
- A project that has configured nothing must keep working as it does today.

## Notes

The doc-sync case was argued on the strength of the guarantee: a gate that has to
fire reliably cannot depend on a heading someone might rename. That argument is
weaker here, because a version cut is always user-initiated and never automatic.
The request was raised with that objection stated, and the decision was to
proceed anyway — consistency of the layering is reason enough, and once the
doc-sync pattern exists this is the same shape a second time and should be much
cheaper. Recorded so `spec` knows the weaker-guarantee point was considered and
overruled, not missed.

Reference material: asked; none provided. The requester considers the repository
itself sufficient — the doc-sync item's `spec.md` is the prior art.
