# Make tcw taxonomy rm refuse nested terms and live references

## What is wanted

`tcw taxonomy rm` should refuse to delete a term that still has nested terms under it
or that another term's `relatesTo` still points at, naming what is in the way and
deleting nothing — the same way `tcw capabilities rm` already behaves.

Today `tcw taxonomy rm admin` deletes the whole `admin/` folder, including
`admin/permission`, and reports only `Removed term admin`. A remaining `relatesTo`
reference only produces a warning, so `tcw taxonomy check` can fail straight after a
command that reported success.

**Decided with the maintainer at triage:** refuse, for consistency with
`tcw capabilities rm`, rather than keep deleting and say more.

## Constraints

- This changes a shipped command's behaviour; the release note must say so.

## Notes

- `tcw capabilities rm` left taxonomy alone on purpose, because changing a shipped
  command is a separate decision (its spec's Non-goals). This item is that decision.
- Checked at triage on `main`: `FsTaxonomyStore.remove` runs `git rm -rf` on the folder
  with no nested check, and `tcw/taxonomy/cli.py` only prints a `relatesTo` warning.
- Reference material: asked; none provided.

## References

- `FsCapabilitiesStore.remove` in `tcw/store/fs.py` — the refusal behaviour to match.
