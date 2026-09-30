# Outcome

`tcw work rename <slug> <new-slug>` gives an open item a new slug.

- **The date is kept.** The new slug can be given whole or as only the part
  after the date.
- **One commit** moves the folder and rewrites everything on the board that
  names the item:
  - blockers;
  - `parent` and `initiative`;
  - graveyard `initiative` entries;
  - capability `Planning doc:` lines.
- **Other boards:** an epic's initiative children there are repointed, each
  committed in its own repository.
- **The old slug is recorded in `renames.yaml`** and keeps resolving:
  - reads (`show`, `path`) follow it with a note;
  - blockers from any project follow it, including to the resolved record in a
    clone where the completed folder is absent;
  - `tcw://` links resolve to the renamed item;
  - no new item is ever given it.
- **Commands that change an item refuse the old slug** and name the new one.

## What shipped

| Task | Commit |
| --- | --- |
| Store, CLI and lookup; tests | `66032658` |
| Documentation: capability `work/rename-a-work-item`, skill, guide, `AGENTS.md`, changelog, release notes | `0d5b757b` |
| Review fixes | `5b2d961f` |
| Re-review fixes | `fb2bacd5` |
| `renames.yaml` added to `OWNED_YAML_NAMES` | `590afbc3` |

## Tests

- **`tests/test_rename_work_item.py`: 28 tests.** Every assertion was
  mutation-checked. One mutation first survived: its test used a `slug`
  blocker, which never reached the unqualified `external` path. A test for
  that path was added.
- **`tests/test_refs.py`:** the stand-in store in the "non-filesystem store"
  test gained `renamed`. The test is renamed to say that link resolution needs
  three reads.
- **Full suite, bare `pytest`, at `fb2bacd5`:** 5072 passed, 1 failed, 3
  skipped. The failure was `renames.yaml` missing from the owned-names set,
  fixed in `590afbc3`; `test_validate.py` and the rename tests then pass (65).

## What the plan or spec got wrong

- **"A re-run completes the move" was false.** A half-done rename was refused
  by either slug. Now every refusal runs before the first write, and a failure
  after it is undone. The spec is corrected in place.
- **The spec said the validation was shared, but it was all in `fs.py`.**
  `slugify`, `rename_slug` and `WorkStore.rename_refusal` now live in
  `tcw/store/base.py`, and `tcw.store.fs` still exports `slugify`.
- **Plan Task 3.1 said an item with uncommitted edits is refused.** The first
  build did not refuse it; it does now.
- **The `AGENTS.md` edit missed the first commit.** `CLAUDE.md` is a symlink
  to it, so staging `CLAUDE.md` did not stage the real file.

## Autonomous decisions

- **Review round 1** (`adversarial-code-reviewer`): NOT DONE, with 3 blocking
  and 4 significant findings. All were accepted and fixed:
  - B1: resolved records under the new slug;
  - B2: refuse before writing, then undo;
  - B3: destination folder exists;
  - S1: `tcw://` links;
  - S2: the ticket was never found, because the binding shape was misread;
  - S3: uncommitted item edits;
  - S4: `@abstractmethod` had moved from `tombstone` to `renamed`.
- **Rejected or narrowed from round 1:**
  - **Having the CLI call `_held_by_someone_else`:** narrowed. The store's
    refusal now carries the same way out (`TCW_WORK_OWNER=…`, `--take-over`).
    Keeping it in the store covers every caller.
  - **Rewriting resolved folders' `state.yaml`:** left as it is. Those folders
    exist only where they are kept; the reviewer agreed it is harmless.
- **Review round 2**, limited to the fixes. Everything it found was accepted
  and fixed:
  - the undo failing silently when git failed;
  - the cleanliness check using the store's repository for capability files
    that live in another repository;
  - the `test_refs` regression;
  - the commit-failure wording.
  After this round I stopped reviewing, with every finding that belonged to
  this change fixed. I did not ask for a third round.
- **Needs a separate change**, all agreed with the reviewer:
  - web app item routes and tracker verbs following renames;
  - the capability drift check following renames;
  - validation under the single store lock (#73);
  - the claim check matching `<slug>-2` as well as `<slug>`.
- **No advisors were consulted at implementation.** The design questions (a
  separate `renames.yaml` rather than tombstones; reads follow and writes
  refuse) were settled with advisors at the spec stage and recorded there.
