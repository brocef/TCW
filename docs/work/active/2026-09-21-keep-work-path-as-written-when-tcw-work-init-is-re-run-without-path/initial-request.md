# Keep work.path as written when tcw work init is re-run without --path

Re-running `tcw work init` (or `tcw init` including `work`) without `--path`
rewrites the `work.path` value already in `tcw-config.yaml`: `./store` becomes
`store`, and `~/store` becomes one person's absolute home-directory path in a
committed file. When the path was not given on the command line, the stored value
should be left exactly as written.

## Notes

- Written during an unattended run (2026-09-26); there was no requester to ask.
  The request is taken from `intake.md`, which was filed by a code review.
- References: asked; none provided beyond the intake's pointer to `tcw/store/fs.py`
  (`init`'s handling of an existing `work.path`).
