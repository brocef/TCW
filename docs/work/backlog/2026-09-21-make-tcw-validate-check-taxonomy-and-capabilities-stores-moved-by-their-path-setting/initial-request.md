# Make tcw validate check taxonomy and capabilities stores moved by their path setting

`tcw validate` should check a taxonomy or capabilities store wherever it lives —
moved with `<component>.path`, or kept in another repository with
`<component>.repository` — as `tcw taxonomy check` and `tcw capabilities check`
already do. Today it only looks at `docs/taxonomy` and `docs/capabilities`, so a
moved store is never checked, scanned for YAML syntax, or scanned for links.
Also folded in: with `taxonomy.path` pointing at a missing folder, `tcw validate`
crashes inside the capabilities check instead of listing a problem.

Once `validate` finds stores by where they really are, retire the temporary
bookkeeping the leftover-config item added for this gap.

## Notes

- Written during an unattended run (2026-09-26) from `intake.md`; no requester
  to ask. References: asked; none beyond the intake's (`tcw/validate.py`; the
  leftover-config item's spec, design section 4; `FsCapabilitiesStore._taxonomy`).
