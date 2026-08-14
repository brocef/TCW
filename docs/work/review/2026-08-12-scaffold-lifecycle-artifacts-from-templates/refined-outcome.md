# Refined outcome — Scaffold lifecycle artifacts from templates

**Accepted** by the requester on 2026-08-14, with no rework.

## What was checked, and by whom

The coordinating session re-ran everything rather than accepting the
implementation's report:

- **1510 tests passed** at C5's final commit (`7f86db0`), and 1561 after C6
  landed on top with no C5 test edited.
- **The eleven lifecycle baselines are byte-unmodified** —
  `git diff eb80d14~1..HEAD -- tests/fixtures/lifecycle_baseline/` is empty.
  That is criterion 12, and it is the assertion the two-commit `produces` split
  existed to keep attributable.
- `tcw capabilities check` → `capabilities OK`; `tcw capabilities drift` → `no
  capability drift`; `tcw validate` → `validate OK`.
- The `produces` / `produces_note` invariant (criterion 11) was verified against
  all twelve `LIFECYCLE_STEPS` rows before implementation began, because
  criterion 13 had already turned out to be unimplementable in exactly that way.

## Criteria

All 18 met. Three were corrected before implementation started, in `6ee69bb`:

- **13** asked for exact-set equality between a stage document's `Produce`
  section and its `produces` tuple. The plan stage ran the assertion against the
  tree: three of seven stage documents fail it on prose that legitimately names
  an artifact they do not produce. Reduced to the subset direction, which is
  what catches the real substring-matching defect. C7 may tighten it if its
  reduction makes equality achievable.
- **17** cited "the same guard `tcw work stage` has". No such guard existed in
  either direction; the item shipped it as a new positive assertion covering
  both verbs.
- The **ordered steps and the Design section disagreed** on where the draft
  refusal happens. Design won: the check and the write are one store call.

## Decisions taken at this stage

None affecting C5. The one requester decision at this verify stage — raising the
stage-prompt line ceiling — belongs to C6 and is recorded there.

## What was accepted without a test behind it

Stated plainly, because no criterion covers either:

- **The eight built-in templates are asserted to exist and to be written
  byte-for-byte, not to be good.** They were read once in place against a
  scratch node. Accepted on that basis.
- **The draft-versus-artifact distinction reading as obvious** in the README and
  release notes is a judgement, not an assertion.

## Carried forward

- **`read_artifact`'s `p.is_file()` (`tcw/store/fs.py:3478`) still disagrees with
  C1's canonical presence rule (`fs.py:2217-2221`).** C5 routed around it rather
  than fixing it, exactly as its Risks required, so the inconsistency outlives
  this item and no test will remind anyone. **C8 candidate.**
- **The pre-implementation spec review never completed.** A second-round
  `codex`/`bllm-review` pass over the revised spec was dispatched and never
  returned findings, so `--force`, the removal of `read_draft`, and the spec's
  file:line citations went unreviewed by it. The coordinating session verified
  the load-bearing claims by hand — `resolve_artifact` having no implicit
  built-in fallback, the presence rule, `STAGE_STATUSES`, and the
  `produces_note` invariant — and the plan stage independently disproved
  criterion 13. Recorded as a real gap rather than a completed check.
