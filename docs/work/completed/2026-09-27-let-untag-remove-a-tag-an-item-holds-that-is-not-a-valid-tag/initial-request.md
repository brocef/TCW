# Let --untag remove a tag an item holds that is not a valid tag

An item can hold a tag that is not a valid tag — a hand-typed `'cli,docs'`,
`'!!!'` — which the board now shows as its text so `tcw validate` reports it.
But nothing in the CLI can remove it: `tcw work edit <slug> --untag cli,docs`
splits the argument into `cli` and `docs`, and `--untag '!!!'` fails
normalization. Until `state.yaml` is edited by hand, every `edit --tag` on the
item, and every web save that resends its tags, is refused.

Wanted: `--untag` can remove any tag the item actually holds, exactly as shown.

## Notes

- Unattended run (2026-09-29); from `intake.md`, filed by the code review of
  `2026-09-26-read-item-tags-normalized-and-keep-non-tag-work-tags-entries-visible`.
  Reference material: asked; none beyond the intake's.
- Reproduced 2026-09-29 in a scratch node: `--untag 'cli,docs'` answers
  "tag 'cli,docs' holds several tags; list them separately"; `--untag '!!!'`
  answers argparse's "invalid tag '!!!': empty after normalization". Both leave
  the tags unchanged.

## References

- `tcw/work/cli.py` `_edit` (`--untag`), `_tags` / `_tag_list`.
- `tcw/store/base.py` `read_tags`; `tcw/store/fs.py` `_validate_tags`.
