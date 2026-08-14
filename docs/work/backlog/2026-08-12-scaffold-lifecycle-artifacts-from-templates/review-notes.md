# Review notes — C5, before implementation

**Not a lifecycle artifact.** Raw findings from the `codex` / `bllm-review` pass
over `spec.md`, saved here because the session paused between the review and the
spec revision and regenerating them costs another full pass. The next session
should verify each one against the code, fold the survivors into `spec.md`, name
the rejections with reasons, and then **delete this file** — it is scaffolding for
one revision, not a document the item keeps.

Nothing below has been verified yet. Treat every claim as a hypothesis.

## codex — ranked, highest first

1. **A second `scaffold` silently overwrites a partially authored draft.** The
   spec calls a draft "a file to type into" and claims a retry is clean, but
   nothing says what happens when one already exists. Decide: refuse, overwrite
   only with a flag, or guard by revision.
2. **"Real artifact already exists" contradicts C1's presence rule.** C1 defines
   presence as *exists and non-whitespace* (`fs.py:2217`); the spec says "already
   exists" and criterion 3 says "exists". An implementation refusing on a
   whitespace-only `spec.md` passes criterion 3 while `artifacts()` and the board
   both say the artifact is absent — two definitions of "exists" again. Use the
   canonical presence result unless empty placeholders should deliberately block.
3. **`produces` / `produces_note` is an unchecked split source of truth.** The
   compatibility mechanism works, but nothing asserts the tuple and the note
   agree: `produces = ("refined-outcome", "rework")` with
   `produces_note = "outcome.md"` passes every criterion as written. Needs an
   explicit consistency assertion.
4. **The parity test gets weaker, not stronger, if moved naively.**
   `artifacts_in()` regexes filenames out of prose and only checks that each
   expected artifact *occurs* — a document claiming `spec` produces `plan.md` too
   passes today. The tuple holds extensionless names while the prose holds
   filenames, so `for artifact in step.produces` would substring-match `spec`.
   The revised test must convert names to filenames and compare **exact sets**.
5. **Criterion 12 claims a declaration that does not exist.** The item has no
   `capabilities.yaml` and there is no `work/customize-lifecycle-artifact-templates`
   ledger entry. The criterion fails before implementation starts.
6. **`serve` must stay unaware of drafts everywhere**, not only in `artifacts()`
   and the board. Criterion 10 covers two surfaces; `serve`'s detail and list
   responses are others.
7. **C7 needs things C5 does not promise**: whether `[ref]` is optional (the epic
   says `[ref]`, C5's heading says `<ref>`), the exact help and error wording, a
   draft locator story documentation can describe without filesystem-only advice,
   and C5's own README / release-note / changelog / skill updates — the epic plan
   makes each child own those before C7 consolidates.

**Criterion-escape audit (codex's own summary, abbreviated):** every one of the
twelve is escapable as written. The recurring shapes: testing one artifact where
the rule is universal (1, 5, 11); testing one surface where the property spans
several (2, 10); testing the tested failure where "resolve fully" is broader (6);
and hard-coding an expected value that both sides can be wrong about together
(8, 9).

## bllm-review

- **`.produces` type change needs a full audit**, not just the parity test.
  (Known consumers: `cli.py:662` human render, `cli.py:911` JSON,
  `test_skill_lifecycle_parity.py:85`.)
- **Atomicity.** "Resolve fully, then write" covers hook failure but not an I/O
  failure mid-write. Write to a temp file in the same directory and `os.replace`
  — which is what `inbox_accept` already does.
- **Concurrency.** Two parallel `scaffold` calls race on the existence check and
  the write. Decide, or document as a known limit.
- **Empty `intake.draft.md` and existence checks.** If a draft's presence is ever
  tested, an empty one must count as present or it will be silently regenerated.
- **`--json` mechanism underspecified** — same ground as codex 3.

## Rejected on sight (still verify before relying on this)

- *"Test `write_draft`/`read_draft` on all supported store backends"* — there is
  one adapter; the epic forbids building another.
- *"`generate` hook environment isolation, clean temp dir"* — C3 owns the hook
  contract and settled it; re-litigating it here is out of C5's scope.
