# Accept comma-separated --tags on tcw work new

## Product changes

`tcw work new --tags a,b,c` works, alongside the existing repeatable
`--tag a --tag b --tag c`.

## Technical changes

Add a `--tags` option that splits on commas and merges into the same list
`--tag` populates. Same tag-registration validation either way.

## Meta changes

None.

---

## Requested outcome

Typing `--tag` three times is tedious, and `--tags cli,docs` is what a person
naturally reaches for first. It currently fails with
`tcw: error: unrecognized arguments: --tags cli,docs`, which is a hard argparse
error rather than a hint.

Keep `--tag` — this is additive sugar, not a replacement.

## Open questions for spec

- Does any other `tcw` command take a repeatable list that deserves the same
  treatment (`--blocked-by` is the obvious neighbour)? Decide whether to do this
  once, generically, or just for `--tag`.
- Do the two forms compose (`--tag a --tags b,c`), and what happens on a
  duplicate or an empty segment (`--tags a,,b`)?

## Notes

- Filed quick-and-dirty from a live papercut hit on 2026-08-11 while creating
  `2026-08-11-publish-tcw-to-pypi-with-automated-releases`. Not specced.
- Deferred deliberately: not to be done in the session that filed it.
