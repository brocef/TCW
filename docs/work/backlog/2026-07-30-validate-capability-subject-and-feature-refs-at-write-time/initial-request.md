# Validate capability Subject and Feature refs at write time

Split out of `2026-07-30-validate-taxonomy-vocab-refs-at-write-time-and-define-bare-slug-resolution`
(spec §5 Sweep, plan Notes), which fixed the same defect on the taxonomy side.

## Product changes

`tcw capabilities set <path> --field Subject=… --field Feature=…` accepts a ref
that points at nothing and exits 0; only a later `tcw capabilities check` finds
it. Reproduced at `tcw 0.17.3`:

```
$ tcw capabilities set thing/do-it --field Subject=no-such-term --field Feature=also-bogus
Set thing/do-it
exit=0
$ tcw capabilities check
thing/do-it: Subject → dangling ref 'no-such-term'
thing/do-it: Feature → dangling ref 'also-bogus'
2 problem(s).
```

Every other TCW write path of this shape fails closed — `tcw work edit --blocks`
resolves before writing, and as of the taxonomy item so does `tcw taxonomy add
--vocab`. This is the last one that does not.

## Technical changes

`_validate_fields` (`tcw/store/fs.py`, `FsCapabilitiesStore`) checks field
*names* against `CAP_FIELDS` and `Status` values, never refs; the resolution
lives in `check` (`_check_subject` / `_check_feature`), which receives the
taxonomy store as a parameter.

**This is why it was not folded into the taxonomy item:** the fix is
structurally different. `FsCapabilitiesStore` holds no taxonomy handle —
`check(taxonomy=None)` is *given* one — so fixing it means deciding how a
capabilities store obtains a taxonomy store at write time. That is a
store-composition design question (and an abstraction-litmus question: whatever
the answer is, a non-filesystem adapter has to be able to honor it), not a
missing call.

The taxonomy item's shape is the precedent worth reusing: one private
ref-problem helper with a raising wrapper, called by both `check` and the write
path so the two can never disagree.

## Meta changes

None expected beyond the usual: `docs/changelogs/upcoming.md`,
`docs/release-notes/upcoming.md` (behavior change — a script that set fields
loosely and checked at the end will now stop at the first bad ref), and
`skills/tcw-capabilities/SKILL.md`.
