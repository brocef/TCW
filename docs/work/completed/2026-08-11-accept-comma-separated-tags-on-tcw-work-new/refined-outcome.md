# Refined outcome — Accept comma-separated tags

**Accepted.** Both defects closed, all eighteen acceptance criteria met,
`2617 passed` against a `2594` baseline.

## The verification decision

Taken autonomously, on four independent readings plus my own hands-on use.

- **`adversarial-spec-reviewer`**, before implementation. Found the blocking
  defect in the spec: it covered where tags are applied and missed where they
  are registered, which is where a node actually gets corrupted. Also found that
  adding a second option spelling breaks the `--ta` abbreviation that works
  today, and that the deduplication the spec proposed already exists at every
  call site.
- **Codex**, on the same brief, independently. Reached the same two conclusions
  and added that `action="extend"` with a list-returning converter does
  everything the proposed custom argparse action would, removing a class of code
  entirely.
- **`tcw-verifier`**, after implementation. Drove all fifteen runnable criteria
  against the installed CLI on four scratch nodes rather than reading the tests,
  ran the full suite itself and reproduced `2614` exactly at that commit, and
  confirmed the outcome's self-assessment was accurate and understated.
- **`adversarial-code-reviewer`**, after implementation. Found the release note
  telling users to delete a legitimate tag, three untested properties, and two
  assertions weak enough to pass against the pre-fix code.
- **My own**: four scratch nodes including one deliberately poisoned before the
  fix, a mutation check that removing the split turns fourteen tests red, a
  second targeted mutation for the all-or-nothing property, and a trace of every
  reader of the tag registry.

## What acceptance rests on

Not the suite. The suite was green on this change before three of the four
reviews, and each of them found something real afterwards. What acceptance rests
on is that the corruption path was **reproduced, fixed, and re-reproduced as
fixed** against the real CLI, and that a node poisoned before the change was
built and confirmed neither repaired nor made worse.

## The one thing worth remembering

**The spec's design table was built by grepping for `action="append"`.** That is
a search for a mechanism, and the question was about a meaning — every place a
tag can be named. The two commands that write the registry use `nargs="+"`, so
they were invisible to the search, and they are precisely where the damage is
done. The first spec would have shipped the cure for the symptom.

This is the second item in this run to fail the same way: the heading item's
sweep was scoped by one heading level and missed the largest section in the
tree. The transferable rule is to enumerate the whole surface and read it, then
write the table — never to let a grep define the scope.

## Deferred, and why

- **The lifecycle condition matcher**, to
  `docs/work/inbox/2026-09-11-lifecycle-tag-conditions-compare-raw-strings.md`.
  `when: { tags: [...] }` is compared as a raw string with no normalization and
  no registry check, so a binding naming `CLI`, `"cli,docs"` or a typo silently
  never fires and `tcw validate` reports the node sound. This repository has a
  live binding of that kind. The revised capability names this exception rather
  than claiming the gap is closed. Filed with the two decisions a fix must make,
  including that normalizing the include list cannot break anything that works
  today while the exclude list is not symmetric.
- **Repairing an already-poisoned node.** Out of scope and stated as such. The
  release note tells a reader how to find the signature safely — a registered tag
  whose two halves are themselves registered tags — after a first draft gave
  advice that would have had them delete `tech-debt`.
- **The version cut.** Changelog and release notes accumulate in `upcoming.md`
  per the run's standing instruction.
- **Closing an originating GitHub issue.** There is none; filed from a live
  papercut.
