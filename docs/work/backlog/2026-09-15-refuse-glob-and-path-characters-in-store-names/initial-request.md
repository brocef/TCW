# Refuse path-shaped and glob-shaped store identifiers before pathlib or git reads them

## What is wanted

A name given to a TCW store — a work item slug, a capability or a taxonomy term —
should only ever mean that one thing. Today two kinds of name can mean more:

1. **Glob characters.** Git reads every path it is given as a pattern, so a folder
   named `a*` matches `abc` too. TCW accepts such names (`tcw capabilities add 'a*'`
   works). Deleting the capability `a*` once deleted `abc` as well; deletes were fixed
   by telling git to read paths literally, but staging (`git add`), moving (`git mv`)
   and the intake move's `git ls-files` still read them as patterns, so a write can
   stage more than it touched.
2. **A slug beginning with `/`.** The claim lookup hands it to `Path.glob`, which raises
   `NotImplementedError` from inside `pathlib` instead of "no such work item". Plain
   `get` crashes the same way. It is not reachable from the command line, which resolves
   the slug first; whether `tcw serve` can pass one through after percent-decoding is
   unestablished.

## Decided with the maintainer at triage

**Refuse characters that have a special meaning to git or the filesystem** — at least
`*`, `?`, `[`, `/` and `\` — in a store name, with a clear message. The maintainer
chose this over keeping such names and reading them literally everywhere.

## Constraints

- **Nested names must keep working.** Capabilities and terms are addressed by paths such
  as `work/complete-a-work-item` and `admin/permission`, where `/` separates levels. The
  refusal applies within a single name, not to the separator between levels. (Recorded
  as the reading of the maintainer's answer; confirm at spec if it should be stricter.)
- **Every entry point, not only the claim path.** The absolute slug was found in the
  claim path because someone was looking there. Other store entry points must be checked
  for the same shape before fixing one; today no `FsWorkStore` entry point calls
  `_safe_store_id`.
- Names that already exist with such characters must not become unreachable without a
  way to rename or remove them; how is for the spec.

## Notes

- Merged at triage from two inbox entries, because both are about a store name handed to
  something that reads it as more than a name, and both point at `_safe_store_id` in
  `tcw/store/fs.py`. Both kept verbatim in `intake.md`.
- The first entry's constraint still applies: the escaping item deliberately did not use
  `_safe_store_id` because it did not reject glob characters. Refusing them here changes
  that premise; it does not mean the earlier reasoning was wrong.
- Checked at triage on `main`: `git_rm` alone passes `--literal-pathspecs`;
  `_safe_store_id` rejects a leading `/`, `\` and NUL but not `*`, `?`, `[`; `get('/x')`
  and `_claiming_dirs('/x')` raise `NotImplementedError`.
- Reference material: asked; none provided.

## References

- `docs/work/completed/2026-09-09-validate-a-slug-before-the-claiming-lookup-globs-with-it/spec.md` —
  its Problem section explains why `_safe_store_id` did not address pattern syntax.
- `docs/work/completed/2026-09-14-delete-a-capability-with-tcw-capabilities-rm/` — found
  the `a*` / `abc` deletion and added `--literal-pathspecs` to `git_rm`.
