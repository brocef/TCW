# Outcome: keep comments and formatting when tcw writes a key into tcw-config.yaml

Implemented in the `work/<slug>` worktree against a private virtual environment
pinned to it. The `tcw` CLI was not used to drive the lifecycle while `tcw/` was
being changed; only read-only checks (`tcw capabilities check`) were run from the
worktree.

## What shipped, task by task

| Plan task | Commit | What |
| --- | --- | --- |
| 1 and 2 | `30f62162` Add a routine that changes one key of tcw-config.yaml in place, or refuses | `tcw/store/config_edit.py`: reading without line-ending translation, locating keys with `yaml.compose`, the four edits, list edits (item by item when the lists allow it, whole only without comments), the two-part verification, refusal messages. `tests/test_config_edit.py`. |
| 3 | `39520060` Make extends and tags change only their own lines of tcw-config.yaml | `_write_node_config` takes key edits; `_persist_extends` updates memory after the write; `_write_tags` refuses a non-mapping `work` or non-list `tags`; `_atomic_write_all` writes with `newline=""`. `tests/test_config_edit_writers.py`. |
| 4 | `cb50c3d9` Make tcw init write tcw-config.yaml once, in place, before touching folders | `init` builds `id` plus every `<component>.path` into one verified edit written before `shutil.rmtree` or any `mkdir`; `write_sentinel` shares `_sentinel_edits` and fixes `id: null`; non-mapping component sections refused. |
| 5 | `c08ec3b1` Check that in-place config edits mean what the old whole-file writer produced | Table of shapes × edit kinds against a copy of the old dict logic. |
| (found at verification) | `756a2203` Name the change in every config refusal, and fix the advice for a brace-only file | See "What the plan or spec got wrong", item 7. |
| 6 | `7d279ca7` Document that config writes keep comments, and the new refusals | Changelog, release notes, migration guide section, configure reference, two guides, three capability statements. |

## Test result

Full suite, run once without any git identity, as instructed
(`GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null pytest -q -p no:cacheprovider`):

`4015 passed, 3 skipped in 973.74s (0:16:13)` — exit 0, at commit `7d279ca7`.

## Mutation checks

Every new test group was checked by breaking the behavior it names and
confirming it went red, and why:

- `config_edit.py`: block-collection end taken from the end mark (red: the two
  "comment after a block list" tests); each of the four verifier checks disabled
  in turn (red: its own verifier test); null filled at the colon (red: the
  `extends: # note` test); line ending forced to `\n` (red: Windows test);
  byte-order mark ignored (red); incremental list edits disabled (red: three list
  tests); `...` ignored (red); alias check disabled (red); brace-section add
  allowed (red); block scalar allowed (red); no-op detection disabled (red);
  emptied section kept, null section treated as absent, `id` inserted at file
  start (red: equivalence tests); brace-root instruction and verifier headline
  (red).
- `fs.py`: old whole-file writer restored (17 of 18 writer tests red — the
  eighteenth is the scalar-`work` refusal, which fires before the writer and has
  its own mutation); memory updated before the write (red); scalar `work` allowed
  (red); store deleted before verifying (red); scalar section check removed
  (red); `id: null` kept (red); sentinel rewritten whole (red).
- **Three checks first stayed green**, and each was a weak test rather than a
  missing behavior: the alias and brace-section refusals were also caught by the
  verifier further down, so the tests now assert the specific reason; the anchor
  verifier test was refused by a parse error instead, so it now uses a case only
  the anchor check can catch. The confined-text check first looked green because
  the mutation left its second copy in place.

## Verification done by hand

- **The original report.** A scratch copy of proposit-app's real
  `tcw-config.yaml` (78 lines, 4-space indent, long comment blocks, a folded
  documentation description, a long `candidate-query`), in a scratch topology
  under `/private/tmp`: `tcw work tags add bug` staged a 1-line diff (`+ - bug`
  in its sorted place); `tcw taxonomy extends add proposit-shared` and
  `tcw capabilities extends proposit-shared` staged a 6-line diff appending the
  two sections. The report's version was 31 insertions and 22 deletions.
- **Refusal messages read as a person would.** Printed one of each kind (braces,
  removal from braces, reordered commented list, alias, brace-only file, anchor);
  each names the file, the key and the reason, and its instruction cannot produce
  a second section or delete a sibling key. Reading them found the brace-only-file
  defect fixed in `756a2203`.
- `pyproject.toml` runtime dependencies unchanged (`git diff main -- pyproject.toml`
  is empty).
- Windows (`newline=""` on write) is covered only by reading the code; neither
  macOS nor the Linux CI translates line endings on write.

## What the plan or spec got wrong

1. **Tasks 1 and 2 are one commit.** The list edits and the verifier's comment
   rule were built together, and splitting the module across two commits would
   have meant committing list code with no tests. The suite was green at the
   commit either way.
2. **Flow lists are rewritten as a whole value, not token by token.** The spec
   said "the item and one adjoining `, ` separator are inserted or removed".
   The implementation rewrites the `[…]` from the original: every surviving item
   keeps its own spelling, and the list keeps its own opening and closing padding
   and its first separator. The result is byte-identical for regularly spaced
   lists; irregular separators (`[a,b, c]`) are normalized to the first one.
3. **A single value filling an empty key goes after the colon**, not at the end
   of the key's line: `path: # note` becomes `path: value # note`. The spec's
   end-of-line rule is kept for lists, where it is needed.
4. **Removal deletes the comments on the lines it removes.** The spec's verifier
   rule named only a removed list item's end-of-line comment. Removing a key also
   removes a comment on the key's own line, and removing the last key of a
   section removes a comment on the section's line. Full comment lines are still
   never deleted.
5. **Emptying a one-per-line `tags` list** (`tags rm` of the last tag) replaces
   the value with `[]` from the colon onward, so a comment on the `tags:` line
   makes it refuse. Not in the spec either way.
6. **`_write_node_config` still reads the config first** so a malformed file
   refuses with `load_config`'s existing message, not a YAML error from the
   editor. The plan did not say.
7. **The spec's refusal wording missed the brace-only file.** A file written as
   one `{…}` mapping was told to edit "the existing `work` section (do not add a
   second one)" even when it had none. Now it is told to change the key inside
   its braces. And refusals found by the final check said "cannot change it";
   they now name the key and whether it was being added, changed or removed.
8. **The anchor and alias checks are a second line of defense.** Mutation showed
   the parse-and-compare check alone refuses every alias and anchor case the
   tests could construct from real edits; the dedicated checks matter only for an
   edit that keeps an anchor while changing its value. They stay, and are tested
   directly.
9. **Release notes intro.** `docs/release-notes/upcoming.md` opens with "Nothing
   else changed" about v2.5.1. That was already false once any v2.5.1 item
   landed; this branch adds a section below it and leaves the sentence for
   whoever merges the batch to reword.
10. `_UniqueKeyLoader` stayed in `fs.py`, imported lazily by `config_edit.py`
    (the plan left this open).

## Notes

- Documentation Sync: changelog, release notes, `docs/guide/taxonomy-and-capabilities.md`,
  `docs/guide/work.md`, `skills/configure/references/projects.md` updated.
  README, `skills/work|taxonomy|capabilities/SKILL.md` evaluated — none describe
  how the config is written (grep for "rewrit", "comment", "re-render") — no
  change. `docs/guide/jira.md` does not fire.
- The leftover-config item edits other parts of the migration guide; this branch
  touched only the "One more thing" section at its end.
