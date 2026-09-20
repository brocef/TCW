# Outcome — Fold the taxonomy and capabilities store configs into the root tcw-config.yaml

`extends` now lives at `taxonomy.extends` and `capabilities.extends` in
`tcw-config.yaml`. A TCW project has one configuration file.

## Test result

```
3791 passed in 852.48s (0:14:12)
```

Run against `98461892`, which is the branch tip, with a clean working tree —
checked by comparing the SHA captured before the run with `git rev-parse HEAD`
after it. `tcw validate` on that tree exits 0.

**Two earlier full runs were red, and one of those reds was reported as green.**
The first (`1 failed, 3789 passed`) found the owned-YAML guard — item 5 below.
The second was worse: this file claimed `3790 passed` against `6e581267` while
the branch tip was `f26047eb`, two commits later, and that commit broke
`tests/test_repo_lifecycle.py`. The adversarial review found it. The Notes
section below had already warned that only a run started after the last source
change is evidence; the warning was written and then not followed. Hence the
SHA in this section now, rather than a bare number.

## Review round

- **Adversarial code reviewer** — one blocking finding (the red suite above),
  two significant (both coverage holes under criteria this file had recorded as
  met), five notes. All addressed in `98461892`.
- **Codex** — first attempt produced **no answer** (usage limit, no `-o` file
  written); re-run against `98461892` reported *"No actionable regressions were
  identified"*, read-only, tests not executed. `sandbox: read-only` confirmed
  from the session header, and HEAD plus `git status` were identical before and
  after both runs.
- **`bllm`** — unavailable: `bllm is temporarily disabled for maintenance`. The
  reviewer spec permits skipping it in that state.

The two coverage holes are worth naming, because both read as covered:
`_persist_extends` could be rewritten to destroy `taxonomy.path` and **816 tests
still passed**, and the emptied-section branch was asserted as
`"extends" not in section`, which is true whether or not the section is dropped.
Both now fail under the mutation that used to pass.

## What shipped

| Plan task | Commit | Notes |
| --- | --- | --- |
| 1 — hoist the node-config accessors | `aea714e5` | plus the docstring fix, sweep finding 4 |
| 2, 3, 6, 7 — read, write, fixtures, old files inert | `ba7ca070` | had to be one commit, not two — item 1 below |
| 4 — messages name the key | `ba7ca070` | |
| 5 — two-repository write; non-git refusal | `ba7ca070` | `tests/test_non_git_writes.py` **unedited** |
| 8 — attachment surface | `ba7ca070` | reshaped — item 2 below |
| 9 — federation behaviour | `ba7ca070` | incl. the self-composing shared tree |
| 10 — configuration, guide and skill docs | `ab3ebe52` | |
| 11 — migration guide, release notes, changelog | `ab3ebe52` | `docs/migration-guide-2.4.X-to-2.5.0.md` |
| 12 — final gate | — | results above |
| (unplanned) owned-YAML guard | `e7334cbd` | item 5 below |

Ledger: `capabilities.yaml` declares `taxonomy/federate-shared-vocabulary` and
`capabilities/federate` as `changed`; both descriptions named the old files
verbatim and now name the keys. No capability is new or removed, so nothing
needs flipping at `complete`.

## Acceptance criteria

All fifteen met. The three worth naming:

- **4** (two-repository write) — `test_extends_add_stages_in_the_nodes_repository_not_the_stores`.
  Mutating `_write_node_config` to stage against the store reproduces the
  original bug exactly: `git -C <store-repo> add -- <consumer>/tcw-config.yaml`
  exits 128.
- **5** (non-git refusal) — `tests/test_non_git_writes.py` passes **with no
  edit**, which is the whole point: the corrected spec required the contract to
  hold, and an edit there would have been the failure.
- **11** — the only *code* naming either filename is the two
  `LEGACY_CONFIG_NAME` attributes (`tcw/store/fs.py:2011`, `2487`).

## What the plan and spec got wrong

**1. The commit boundary. [plan]** The plan said tasks 2 and 6 land together.
In fact 2, 3, 6 **and** 7 had to: the write paths and both `check()` methods
still referenced `CONFIG_NAME`, so the tree did not run until all four were
done. Committed as one; the plan's rule (green at every commit boundary) is
satisfied, its task grouping was not.

**2. The capabilities attachment regression does not exist. [spec]** The spec —
following the adversarial review — held that giving both stores both filenames
would silently stop a `config.yaml` in a capability folder being an attachment,
and criterion 12 demanded a test for it. Writing that test failed with
`'Capability' object has no attribute 'attachments'`. `_capability` discards
`_load_node`'s attachment list outright and composes bodies from
`prependedDocs`/`appendedDocs` read **by name** out of `meta.yaml`, so
`_node_reserved` is unobservable on the capabilities side. Only taxonomy reaches
it, via `Term.attachments`.

The design decision is unchanged — per-store is still right — but its stated
reason was false, and I had already written that false reason into the source as
the docstring justifying it. Corrected there, and criterion 12's second half is
now `test_the_capabilities_store_has_no_attachment_surface_to_regress`, which
pins *why* the concern is moot and fails if `Capability` ever grows an
attachments field.

Worth recording for the post-mortem: this is the second time in this item that a
claim survived into a document because a comment was trusted over the code under
it. The first was `_write_tags`'s docstring (sweep finding 4).

**3. Criterion 11's count. [spec]** It budgeted two code lines "plus whatever
single comment line justifies them". Explaining why the reservation stays
per-store needs three comment lines. Counting comments was the mistake; the
criterion now counts code. Corrected at `26799eee`.

**4. Task 6's file list and site count. [plan]** Two surprises, in opposite
directions. `tests/test_taxonomy.py` already had a `write_config` helper, so
repointing that one function converted 13 sites with no call-site edits at all.
Against that, `test_transitive_extends_crosses_a_second_hop_through_a_moved_tree`
rewrites `bravo`'s whole `tcw-config.yaml` mid-test; under the old scheme
`extends` lived in a file inside the tree and survived that, and now it does not.
The test went green-to-red for a reason that looked like a code defect and was
not — it needed the hop re-declared, or it would have quietly asserted something
weaker.

**5. An owned-YAML guard nobody predicted. [both]** Neither document mentioned
`tests/test_validate.py::test_every_yaml_name_tcw_writes_is_owned_or_deliberately_not`.
It greps `tcw/` for `*.yaml` literals and asserts each is owned or deliberately
excluded. Both filenames still appear — as `LEGACY_CONFIG_NAME` — so it read
them as records TCW writes and failed. They join the deliberate exclusions with
that reason (`e7334cbd`). The guard did its job; the sweep in the spec missed it
because it searched for the filenames' *use*, not for tests that reason about
the filename set.

**6. `_extends_ids`' second parameter. [neither]** Not wrong, just unnamed: it
became a label rather than a path, and `_extended_component_stores` takes it
too, where the messages then read `…: taxonomy.extends: extends project 'x' is
not reachable`. Renamed and de-duplicated.

## Notes

- The suite takes ~15–21 minutes here. Several background runs reported
  `exit code 0` for trees that had since been edited; only the run started after
  the last source change is evidence, and that is the one that found item 5.
- **The documentation-entry gap from the plan still stands.**
  `docs/guide/taxonomy-and-capabilities.md`, `docs/guide/multi-repo.md` and
  `docs/guide/linking-and-validation.md` all had to change here and are covered
  by no entry in `work.documentation`; only `docs/guide/jira.md` has one. The
  third was about to become *factually false* — it listed a store's
  `config.yaml` among the records that must be a mapping, which is exactly what
  left `OWNED_YAML_NAMES`. Nothing would have caught that. Raised for `verify`.
- **Version is 2.5.0, by Brian's decision on 2026-09-19.** Removing a supported
  configuration location with no back-compat would ordinarily argue for a major
  bump, and the first draft of this outcome said 3.0.0 for that reason; they chose
  a minor bump having seen it. The guide is named to match.
- A `work.documentation` entry for `docs/guide/<topic>.md` was added as part of
  this item rather than deferred, closing the gap noted below.
