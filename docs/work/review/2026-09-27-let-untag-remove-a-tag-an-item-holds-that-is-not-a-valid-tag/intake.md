# Let --untag remove a tag an item holds that is not a valid tag

Since 2026-09-26-read-item-tags-normalized-and-keep-non-tag-work-tags-entries-visible,
an item's tag that cannot be normalized — a hand-typed `'cli,docs'`, `'!!!'`, a
bare `7` — is read as its text so `tcw validate` reports it. But it cannot be
removed through the CLI: `tcw work edit <slug> --untag cli,docs` splits the
argument into `cli` and `docs`, and `--untag '!!!'` fails normalization. Until
the item's `state.yaml` is edited by hand, every `edit --tag` on it, and every
web save that resends its tags, is refused by `_validate_tags`.

Predates that item (the raw read behaved the same way). Found by its code
review, 2026-09-27. Likely direction: let `--untag` also match an argument
against the item's text tags exactly, before splitting and normalizing.

## References

- tcw/work/cli.py `edit` (`--untag`, `_tags` / `_tag_list`)
- tcw/store/base.py `read_tags`; tcw/store/fs.py `_validate_tags`
