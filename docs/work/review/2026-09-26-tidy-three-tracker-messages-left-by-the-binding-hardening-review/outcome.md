# Outcome — Tidy three tracker messages left by the binding hardening review

## What shipped

| Task | Commit | What |
| ---- | ------ | ---- |
| 1–2 | `cce6c3f0` | Tests, then all five fixes: `_staged_paths` (`-z`, from the top); `-z` for two `ls-tree` readers; `JiraClient._payload` and a string-only key/id read in `create.py`; `_create_one` adds a reason when binding fails; `_check_issue`/`_text` type-check six values; `intake.binding_record` and `drop_refusal` for both drop gates. |
| docs | `bf56ced7` | `docs/guide/jira.md` (drop row), changelog and release-note entry files. |
| review | `63ba5843` | `surrogateescape` decoding for `-z` output (`_GIT_PATHS`); `_tracked_source`'s `ls-files` takes `-z`; the hint is `_merge_back_hint`, tested from a node below the top; `ever_bound` removed; spec and changelog name the real functions. |

## Tests

- `tests/test_tracker_message_tidy.py`, 11 tests, one or more per criterion;
  `tests/test_tracker_hardening.py`'s shape table gains five value-type cases
  and loses the `create_issue` case, whose behavior this item changes on purpose.
- Every new test was run against the code before the fix: all failed there
  except the first nested-item test, which passed because the store runs git
  from the node folder (so a non-ASCII parent folder never appears in its
  output); it was rewritten with a non-ASCII `work.path` and then failed as it
  should.
- Mutation-checked at review: the hint's call site reverted to the node folder,
  a strict decode, and `_tracked_source` without `-z` each turn their test red.
- Full suite after the review fixes: 4810 passed, 2 failed, 3 skipped; the two
  failures are `test_check_versions.py::test_a_hanging_cli_is_abandoned_silently`,
  a timing test, which passes rerun alone (load average above 50 at the time).

## What the plan or spec got wrong

- **The sweep searched for `--name-only` only**, and missed an `ls-files`
  reader with the same defect. Found by review.
- **`-z` alone was a new crash**: it prints raw bytes, which a strict decode
  refuses for a path that is not UTF-8. Found by review.
- **Two function names in the spec were wrong** (`_committed_resolved_folder`,
  `_web_strict_refusal`); corrected.
- The plan asked for one commit per concern; the five fixes went in one commit.

## Autonomous decisions

- No advisor consult: no open question. One design choice made alone: run the
  staged-files `diff` from the repository top rather than pass
  `--no-relative`, because nothing in the project records a minimum git
  version and `--no-relative` needs git 2.28.
- Review (adversarial-code-reviewer, "merge after fixes"): accepted findings
  1–3, the doc names, and removed `ever_bound`. Left for a separate change, not
  filed: `create_issue` answering with text that is not JSON still gets "not
  JSON" rather than the "may exist" warning; `apply_transition` and
  `add_comment` raise "unexpected shape" on an odd answer after a POST that
  may have taken effect.
