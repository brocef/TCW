As a user or agent, I run `tcw work scaffold <artifact> <ref>` to get a starting
point for a lifecycle document. TCW resolves that artifact's template — mine, if
I declared one under `work.lifecycle.artifacts:`, and its own built-in otherwise
— writes it, and prints where it put it on stdout and nothing else. Every
lifecycle document has a built-in template, so this works in a project that has
configured nothing.

**What it writes is a draft, and a draft is never the document.** `spec.draft.md`
is a file to type into; `spec.md` is the spec. The board still shows the spec as
unwritten, `tcw work show --json` still reports it absent, and the local web app
does not list it. Nothing claims the work has been done until I do it. That is
the point of the command having a separate name for what it produces: a tool that
wrote `spec.md` would light the board for a document nobody had written.

It refuses in two situations, both to protect something that already exists.
Once the real artifact is written, there is nothing to scaffold and a draft
beside it would only compete with it. And a draft I have already typed into is
not overwritten — running the command a second time out of habit does not cost me
a half-written spec. `--force` replaces one when I mean to. A draft I have not
typed anything into yet is regenerated with no flag at all, which is also what
makes `tcw work scaffold intake` work: intake's built-in template is deliberately
empty, because raw input has no shape TCW gets to prescribe.

Whether the artifact "exists" is the same question the board answers, not whether
a file happens to be there: a `spec.md` holding nothing but whitespace reads as
absent everywhere, so it does not block scaffolding either.

A stage that could not run yet cannot have its document scaffolded: asking for
`outcome` on a backlog item is refused with the statuses it does run in, the same
rule `tcw work stage` applies. Raw intake is the exception, and deliberately so —
no stage produces it, so scaffolding it is legal wherever the item is.

Nothing is written until the whole template has resolved. A `generate:` template
that fails — by exiting non-zero, running past the timeout, or printing past the
output cap — leaves no draft at all, so fixing it and running again gives me a
clean one rather than a fragment. That does mean my generator runs again on each
retry and under `--force`, so it has to be side-effect-free. A failure reports on
stderr and puts nothing on stdout, so a script reading stdout for a path never
receives one for a file that does not exist.

A write that Git refuses — a lock another process holds, a hook that says no — no longer leaves a half-made object behind: whatever that save *created* is removed. A save that *changed* something already there is a different case and is not undone — the edit stays on disk, and re-saving once Git is happy is the fix.
