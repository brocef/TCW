# Implement round 1 — TCW 4.0: release

Steps 5, 7, 8 and 9 of the plan, carried out by an agent in a worktree of
`v4` at `34739ce5`. The dispatching session adds the other steps' records.

## Step 5 — TCW-118's own entry files (Design 3.3)

Commit `073703dc` (`TCW-118: release notes and changelog entries`).
`docs/migration-guide-3.X-to-4.0.0.md` exists on `v4`, so the step ran.

- `grep -c '^## Upgrading' docs/release-notes/upcoming/TCW-118-tcw-4-0-release.md`
  prints `1`: the six points went under the heading Step 2 began, and Step 2's
  one point there ("holding the plugin at an older version now holds the CLI
  it installs at that version too") is folded into the fifth.
- The leading paragraph says 4.0 is a major release, that it changes where a
  project keeps its files (a `.tcw/` folder) and how projects relate (parents
  in place of `projects:` and `extends`), and that a 3.x project must be
  migrated with `tcw migrate`; that sentence names `tcw migrate`, so TCW-117's
  scan for 3.x forms would allow it even if it read the `upcoming/` entries.
  It also links the migration guide (see "What the plan got wrong" below).
- The six points against Design 3.3, criterion 7:
  1. the migration guide, linked as `../migration-guide-3.X-to-4.0.0.md`: present;
  2. automation that installs `tcw-cli` kept at `tcw-cli<4` until migrated: present;
  3. everyone upgrades together, 4.0 refusing a 3.x project's files except to
     migrate them: present;
  4. commit or back up before running `tcw migrate` for real: present;
  5. the plugin installs `tcw-cli==<the plugin's version>`; the harness
     paragraph of the plan's "The open items", item 1, copied word for word
     (Claude Code, Codex, Pi); then the first-install case with
     `pipx install --force 'tcw-cli<4'`: present;
  6. the branch `3.x` holds the last 3.x code, and a 3.x patch is cut there
     and published by pushing its tag: present.
- The changelog entry gains `## Removed` (`tests/test_repo_config_pair.py`
  and the root `.gitignore` line `/tcw-config.local.yaml`, both removed at
  Step 15) and, under `## Internal`, this repository migrated to 4.0 and
  `UNMIGRATED_RECORDS` deleted. `## Changed` already held the pinned install
  and `check_versions.sh`'s advice from Step 2, and the `cut_version.py` rules
  stay under `## Internal` (decided by the dispatching session: the script is
  contributor tooling).
- Every `upcoming/` file a `TCW-118:` commit has touched:

  ```
  073703dc docs/changelogs/upcoming/TCW-118-tcw-4-0-release.md
  073703dc docs/release-notes/upcoming/TCW-118-tcw-4-0-release.md
  ```

  (and `d34ca274`, Step 2, the same two files). No other item's entry file.

**What the plan got wrong.** A leading paragraph fails
`tests/test_upcoming_entries.py::test_an_entry_starts_at_a_level_two_heading`,
which allowed leading text only in TCW-75's 3.0.0 introduction. The same
commit changes that test so each major version's introduction is allowed:
TCW-75's for 3.0.0 and TCW-118's for 4.0.0, each checked, until its cut, to
exist in both folders, to link its migration guide from the introduction
itself, and to come first in the combined notes. To meet the last of those the
introduction links the guide as well as point 1. Checked by breaking it:
taking the link out of the introduction makes
`test_the_introduction_links_the_migration_guide[4.0.0]` fail.

## Step 7 — success criterion 1 and the Known gaps (Design 3.5)

Run at `073703dc`, which differs from `v4` (`34739ce5`) only in the two entry
files and the test above; `docs/use-cases.md` and the specs are `v4`'s.

```
UC-1 12
UC-2 12
UC-3 12
UC-4 12
UC-5 12
UC-6 12
UC-7 12
UC-8 12
S-1 5
S-2 6
S-3 9
S-4 12
S-5 9
S-6 8
S-7 7
S-8 10
S-9 12
S-10 12
S-11 12
```

Every id has a count of at least 1 (criterion 9).

The Known gaps, one line per row of TCW-117 Design 6.4's table
(`docs/work/TCW-117-…/spec/spec.md:1040-1059`), against `docs/use-cases.md`
(criterion 49):

- UC-2, a library cannot warn before a breaking rename: kept, marked TCW-114
  (`:203-209`). Agrees.
- UC-3, `children:` on its own board only: gone (UC-3 reads "none recorded",
  `:272`). Agrees.
- UC-3, `--parent` when filing into another project: gone. Agrees.
- UC-3, TCW-98 and TCW-99 will change how a parent sees children: gone.
  Agrees.
- UC-4, two places rebuild a store's path from the project root: kept as one
  place, `tcw validate`'s fallback to `docs/work`, "No item yet" (`:342-344`).
  Agrees with the "otherwise kept" outcome: one place remains.
- UC-4, TCW-22, the backlog audit: gone. Agrees.
- UC-4, TCW-23, provision scoping: gone. Agrees.
- UC-5, a list fetches every ticket in the shared Jira project: narrowed,
  marked TCW-113 (`:382-387`). Agrees.
- UC-6, a missing project named in `extends` stops every command: gone (UC-6
  reads "none recorded", `:422`). Agrees.
- UC-6, `tcw://<id>/T/…` into a missing project: gone. Agrees.
- UC-6, TCW-23: gone. Agrees.
- UC-8, only `tcw validate` says where `TCW_PROJECT_<ID>` placed a project:
  narrowed, marked TCW-107 (`:473-475`). Agrees.
- S-7 (a move does not check the stage it was read at), S-8 (two gaps: a
  creation that loses its connection, and re-running `advance`), S-9 (unknown
  top-level keys): all kept, "No item yet" (`:636-638`, `:668-673`,
  `:708-710`). Agrees.
- S-9, a 2.x work store listed as empty: reworded, not removed, since
  `tcw migrate` does not refuse a 2.x store; kept with "No item yet"
  (`:702-707`). Agrees. One remark for the dispatching session, not a
  mismatch: since Step 2's fix 5, `tcw validate` names the 2.8-to-3.0
  migration guide for a stage-named folder; the gap says only that
  `tcw validate` "reports each folder as an error", which stays true.

No row goes back to TCW-117's area.
