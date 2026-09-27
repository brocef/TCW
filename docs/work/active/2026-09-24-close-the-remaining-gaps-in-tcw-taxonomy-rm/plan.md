# Plan: close the remaining gaps in tcw taxonomy rm

## Tasks

1. **Tests first** in `tests/test_taxonomy_rm_gaps.py`: criteria 1-5 through
   `main(["taxonomy", "rm", ...])`, each asserting the term still lists after a
   refusal; criterion 6 through the serve test helpers.
2. **Capability guard** in `FsTaxonomyStore.remove` (`tcw/store/fs.py`), with the
   abstract contract in `tcw/store/base.py` updated.
3. **Children and own files**: compare the listing's folders under the term with
   git's tracked folders; refuse the untracked ones; refuse an untracked own
   `meta.yaml`; verify after `git rm`.

## Documentation Sync

- Changelog and release notes: Fixed entries.
- `skills/taxonomy/SKILL.md` [Skill-Driven-Component]: `rm` refusals.
- `docs/guide/taxonomy-and-capabilities.md` [Guide-Topic-Change]: if it lists
  what `rm` refuses.

## Verification

Hands-on in a scratch node for criteria 1, 3 and 4 with the worktree's `tcw`.
