# Give lifecycle hooks roles, kinds, and conditions

Child **C3** of the initiative
[`2026-08-12-make-the-work-lifecycle-polymorphic-and-cli-driven`][epic]. The
initiative's spec is the source of truth for the design; this request states what
C3 in particular is being asked for and why it is the riskiest slice.

## Product changes

A node can say what happens at a point in the lifecycle, in its own words, on its
own terms.

Today a binding is a `skill:` name or a `command:` string, and nothing else. A
skill name is not instructions — it is the name of something that has them, which
a node that does not ship a plugin cannot use at all. So there is no way to write
"here is what to do when writing a spec in this repository" and have TCW say it.

After this, a binding declares **what it is for** and **where its text comes
from**:

- **What for** — a `check` runs and may fail; a `prompt` resolves to text an
  agent reads; an `artifact` is a template a document is scaffolded from.
- **Where from** — `blob:` is the text written inline in the config; `file:` is a
  path in the node; `generate:` is a script the node owns, which receives the
  work item and prints whatever it likes; `builtin:` is TCW's own default.

And a binding can say **when it applies**: `when: {tags: [bug]}` gives a bug a
different prompt than a feature. Three keys, deliberately — anything harder is a
`generate` script, which is real code and can decide anything.

Nothing a user has configured today changes. Every existing shape keeps working
and keeps producing the same output.

## Technical changes

This slice writes no new command surface except `--phase` on `tcw work lifecycle`.
It rewrites the parser, the validator, and the model that every existing
`tcw-config.yaml` goes through, and it adds a resolution library that C4 and C5
call. That is deliberate: a regression shows up in the existing suite rather than
in a new feature nobody is exercising yet.

The pieces:

- The role/kind model and its validation table, including which kinds are legal
  in which role and why `command` in a prompt position is an error naming
  `generate`.
- `when:` — parsing, validation against the known type set, and matching.
- The `generate` resource contract: the item JSON on stdin, a timeout, a bounded
  output cap, a stated encoding policy, and **all stdout discarded on a non-zero
  exit** so a script that fails midway cannot leak half a prompt.
- `file:` path normalization and confinement to the node root — a footgun guard,
  not a sandbox.
- `builtin:` in full, both the syntax and the resolution. C6 ships only the
  content it resolves to.
- Back-compat for every legacy shape, including the detail that
  `_directive_text` renders skills before commands regardless of declaration
  order, so a naive conversion would change output that must stay byte-identical.

## Meta changes

**Blocked by C2**, which is what `generate` hands to a script on stdin. C2 also
left C3 a debt: the initiative's spec was amended to say **C3 bounds the `body`
it puts on a hook's stdin**, since the projection carries it in full for the web
editor's sake. That is C3's to honor, not an optional extra.

**`builtin` belongs entirely here.** An earlier draft split its syntax into C3
and its resolution into C6, which would have let C4 and C5 meet valid
configuration with no implementation behind it.

C4, C5, and C6 all unblock together when this lands, and none of them blocks
another. If the `when:` matcher or the role table comes out different from the
initiative's spec, their specs are stale and get revised before they start.

[epic]: ../../active/2026-08-12-make-the-work-lifecycle-polymorphic-and-cli-driven/initial-request.md
