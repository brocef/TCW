# Spec — tcw migrate reads a capabilities.yaml taxonomy entry prefixed with a child project's ID as a path in the item's own taxonomy

## Capability changes

- **changed** `tcw.capabilities/cli/migrate-a-tcw-3-x-project-to-tcw-4`. Its
  description says the migration writes "every reference the project's files
  make to its own objects" as a full identifier. After this change it also
  says that a reference to another project's object names that project: one
  prefixed with an inherited project's ID, and, in an item's
  `capabilities.yaml`, an entry prefixed with a listed child's ID, in the
  `taxonomy:` lists as well as the capability lists. No other capability and
  no taxonomy term changes.

## Reproduction

Verified on 2026-11-03 against `tcw 4.0.0` (this tree, `main` at `07c31ddb`)
and, for the 3.x side, `tcw-cli==3.0.2` installed in a throwaway virtual
environment. The script is the one the regression test copies
(plan, test 1); by hand:

1. Make two folders, `A` and `B`, each a git repository (`git init`).
2. `A/tcw-config.yaml` (3.x form):

    ```yaml
    id: a
    work:
      backend: filesystem
    projects:
      children:
        b: ../B
    ```

    `A` keeps no taxonomy and no capabilities ledger.

3. `A/docs/work/2026-10-01-a/item.yaml` is `title: A` / `stage: implement`,
   and its `capabilities.yaml` is:

    ```yaml
    changed:
    - b/cli/x
    taxonomy:
      changed:
      - b/turn
      new:
      - b/never
    ```

4. `A/docs/work/2026-10-02-b/item.yaml` is `title: B` / `stage: completed`,
   and its `capabilities.yaml` is `taxonomy: {removed: [b/turn]}`.
5. `B/tcw-config.yaml` is `id: b` with `projects: {parent: {a: ../A}}`; `B`
   keeps the term `turn` (`docs/taxonomy/turn/meta.yaml`, `name: Turn`,
   `kind: Vocabulary`) and the capability `cli/x`
   (`docs/capabilities/cli/x/meta.yaml`, `id: cap-123abc`, `name: X`,
   `Status: Supported`), each with a `description.md`. `B` has no term
   `never`.
6. With 3.0.2, `tcw validate` in `A` already exits 1:

    ```text
    error: docs/work/2026-10-01-a/capabilities.yaml: term b/never: could not be checked: project 'a' keeps no taxonomy
    error: docs/work/2026-10-01-a/capabilities.yaml: term b/turn: could not be checked: project 'a' keeps no taxonomy
    2 errors, 3 warnings, 0 unresolved
    ```

7. With 4.0.0, `tcw migrate` in `A` (exit 0), then `tcw migrate` in `B` (exit
   0). `A`'s first item's `capabilities.yaml` now reads:

    ```yaml
    changed:
    - b.capabilities/cli/x
    taxonomy:
      changed:
      - a.taxonomy/b/turn
      new:
      - a.taxonomy/b/never
    ```

    and the second item's `taxonomy: removed:` holds `a.taxonomy/b/turn`.
    The capability entry was routed to the child; the three term entries were
    not.

8. `tcw validate` in `A` exits 1:

    ```text
    error: docs/work/2026-10-01-a/capabilities.yaml: term a.taxonomy/b/never: could not be checked: project 'a' keeps no taxonomy
    error: docs/work/2026-10-01-a/capabilities.yaml: term a.taxonomy/b/turn: could not be checked: project 'a' keeps no taxonomy
    2 errors, 3 warnings, 0 unresolved
    ```

    (The three warnings are the hand-made item's missing request, spec and
    plan, and are not part of this defect.) Three bad lines gave two errors:
    the completed item's line is not checked.

9. Rewriting the three lines by hand to `b.taxonomy/turn` and
   `b.taxonomy/never` makes `tcw validate` end `0 errors`, although `B` has
   no term `never` (see Problem, part 3).

**Expected:** step 7 writes `b.taxonomy/turn` and `b.taxonomy/never`, the
same child-first reading the capability entry beside them gets, and step 8
gives no error for these lines.

## Problem

### 1. The migration routes a `capabilities.yaml` capability entry to a child, never a term entry

`Owners.owner_of` (`tcw/migrate/references.py:103-144`) converts each value
of an item's `capabilities.yaml`. Only a capability entry goes through the
3.x router: the branch at `references.py:119` is taken when
`row.namespace == "capabilities"`, and calls `route_entry_3x`
(`tcw/migrate/legacy.py:958-983`), which sends `<child>/<rest>` to the child
(`legacy.py:972-978`). Every other value, the three `taxonomy:` lists
included (`tcw/reference_fields.py:58-60`), goes to `bare_owner_3x`
(`references.py:135-136`; `legacy.py:937-955`), which knows the project's own
id-paths and its `extends` sources, never its children: a first part that is
not a source falls through to "the project's own" (`legacy.py:955`). The
view does hold the children (`View.children`, filled at
`tcw/migrate/stores.py:454`); the term branch never reads it.

This copies 3.x exactly. At v3.0.2, `route_capability_path`
(`tcw/work/gates.py:331-380`) routed capability entries to children, and
`_LedgerReader.term` (`gates.py:430-437`) read every term entry in the
project's own taxonomy, answering "could not be checked: project '<id>' keeps
no taxonomy" when there was none. So in 3.x these entries were never
checkable; but beside capability entries written `B/<path>` and routed to
`B`, a term entry written `B/<term>` plainly means `B`'s term, and 4.0's
full identifiers can say so.

**Correction to the request.** The request says 4.0 "turns 'unchecked' into
an error". It does not: 3.0.2 already reported the same line as an error, in
plain `tcw validate` for a project whose work is in files (v3.0.2
`tcw/validate.py:602`) and in `tcw validate --remote` for one in Jira (v3.0.2
`tcw/work/jira/remote.py:535`, `run.error`); step 6 of the Reproduction shows
it. A Jira-mode project that never ran `--remote` in 3.x would not have seen
it. This does not change what the fix should be.

### 2. Why plain `tcw validate` passed the evaluator's project

Plain `tcw validate` does check item records in a project whose work is in
files: `_work_findings` runs `records_problems` over every unfinished item
(`tcw/validate.py:828-838`), which is how step 8 above fails. In a Jira-mode
project it does not: offline, the work findings are the store's names, the
recorded references, the rounds and whether each `capabilities.yaml` parses
(`validate.py:795-804`, `_declaration_findings` at `validate.py:846-868`),
because an item's stage is kept in Jira and the check skips finished items.
`_declaration_findings`'s docstring says so ("The records the file declares
are checked only under `--remote`"), and so does the linking and validation
guide (`docs/guide/linking-and-validation.md:216-225`). This is by design.

The 3.x to 4.0 migration guide does not say it. Its step 3 says "Then run
`tcw validate`. It should end `0 errors, 0 warnings, 0 unresolved`"
(`docs/migration-guide-3.X-to-4.0.0.md:343`), and its Jira order says
"`tcw migrate --no-jira`; `tcw validate`, and read the changes; `tcw
migrate`" (`:446-449`). A Jira-mode reader who follows it gets a clean result
that never looked at an item's declared records. The same holds for the check
`tcw migrate` itself runs after a real run (A12), which is plain validate.

### 3. Why 9 bad lines gave 6 errors, and why a missing term gave none

The records check `--remote` runs (`_model_checks`,
`tcw/work/jira/remote.py:532-578`) reads each item folder whose key Jira
returned a ticket for (`remote.py:537`) and then, per item:

- **skips an item whose stage is terminal**, `completed` or `discarded`
  (`remote.py:568`; `tcw/work/model.py:364-366`);
- **skips an item whose stage is unknown** (`item.stage is None`,
  `remote.py:568`). A ticket's stage is the stage whose configured status it
  is at; a status no stage names gives no stage
  (`tcw/work/jira/mapping.py:219`). An epic whose issue type has a workflow
  of its own, at a status such as "In Progress" that no stage uses, is such
  an item. Nothing reports the skip;
- **skips a `capabilities.yaml` that does not parse** (`remote.py:574`),
  already reported offline;
- reads every list otherwise, `new:`, `changed:` and `removed:`, capability
  and taxonomy alike (`tcw/work/gates.py:233-236`). No list is skipped.

It runs with `finished=False` (`remote.py:576`), so for each term it reports
only an entry that is malformed or cannot be checked (`gates.py:207-210`). A
term declared `new` or `changed` that is absent, or one declared `removed`
that is still there, is not reported mid-work (`gates.py:211-212`); the
records gate reports it when the item moves past implementation
(`records_gate`, `gates.py:240-241`, run by `tcw/work/advance.py:208`).

So:

- **6 errors for 9 lines.** Each wrong line in a checked item gives one
  error, whatever its list. The 3 unreported lines were in items the check
  skips: items at `completed` or `discarded`, or items whose ticket is at a
  status no stage names. Which of the two applies to the evaluator's three
  items is an **assumption**: their tickets are not available here. The
  Reproduction shows the terminal case (3 lines, 2 errors).
- **The missing term in the epic's `taxonomy: new:` list.** Under the
  corrected address `B.taxonomy/<term>` no error is right by design: the term
  is absent and the item is not finished, so only the records gate reports it
  (Reproduction step 9). Under the wrong address `A.taxonomy/B/<term>` an
  unfinished item with a known stage *would* have reported "could not be
  checked", whatever the list; that it did not means the epic was skipped,
  terminal or at an unmapped status (an **assumption** for the same reason).

Neither skip is a defect in the migration. Skipping finished items and not
reporting a change not yet made are the records check's design, unchanged
since 3.0.2 (v3.0.2 `remote.py:527`, `gates.py:202-210`). An item silently
skipped because its ticket's status maps to no stage is a separate question
about `tcw validate --remote` in Jira mode, not about migration; it is out of
scope here (Non-goals) and proposed as its own item (Notes).

## Goals

1. `tcw migrate` converts a `capabilities.yaml` `taxonomy:` entry (`new:`,
   `changed:` or `removed:`) whose first part is one of the project's listed
   children to `<child>.taxonomy/<rest>`, when the project's own and
   inherited taxonomy do not hold the whole path and have no first folder of
   that name.
2. Where the project's own or inherited taxonomy holds the whole path, the
   entry keeps 3.x's reading (that taxonomy's term), since 3.x resolved and
   checked it there.
3. Where the path is not held but the child's ID is also a first folder of
   the project's own or inherited taxonomy, the run is refused with B10, as
   `route_entry_3x` refuses the same ambiguity for a capability entry, and
   says how to write the entry by hand.
4. The migration guide says that in a Jira-mode project plain `tcw validate`
   does not check the records an item's `capabilities.yaml` declares, and
   that `tcw validate --remote` does, for items not yet finished.

## Non-goals

- **Other reference fields.** A term's `relatesTo` and `vocabulary`, a
  capability's `Subject` and `Feature`, and `tcw://T/…` links keep 3.x's
  reading (`bare_owner_3x`, `link_owner_3x`). The sweep for "a first part
  that is a child's ID, read as a path in the project's own store" covered
  every row of `tcw/reference_fields.py:49-72` and every caller of
  `bare_owner_3x` (`references.py:134`, `:136`; `legacy.py:994`). Only
  `capabilities.yaml` had 3.x route anything to a child, so only there is the
  author's meaning shown by a sibling entry; elsewhere 3.x's `get` never read
  a first part as a child, and changing that would rewrite references 3.x
  resolved. A value elsewhere that 3.x could not resolve still gives a
  `tcw validate` finding after the migration, so it is not silent.
- **Checking that the child holds the term.** The migration writes the
  address the author meant; whether `B` has `<rest>` is `tcw validate`'s and
  the records gate's job, as for a capability entry routed to a child today.
- **The records check's skips** (finished items, items at a status no stage
  names, absent terms mid-work). Unchanged; the unmapped-status skip is
  proposed as a separate item.
- **Making plain `tcw validate` check item records in Jira mode.** It would
  need each item's stage from Jira; offline it cannot have it.
- **Already-migrated projects.** A project already converted holds
  `A.taxonomy/B/<term>`, a full identifier, which a second run leaves alone
  (`references.py:105`). Its user fixes the lines by hand, as the evaluator
  did; the release note says how.

## Design

### 1. The rule, for a `capabilities.yaml` `taxonomy:` entry

In `Owners.owner_of`, a value from a `capabilities-yaml` row whose namespace
is `taxonomy` is read by a new function in `tcw/migrate/legacy.py` beside
`route_entry_3x`, `route_term_entry_3x(path, *, children, own, sources,
project_id)`. With `head` the entry's first part and `rest` what follows the
first `/`:

| Case | Result |
| --- | --- |
| no `/` in the entry, or `head` is not a listed child | `bare_owner_3x(path, own, sources)`, as today |
| `head` is an `extends` source (a source and a child at once) | `bare_owner_3x`, as today: the source, `<head>.taxonomy/<rest>` |
| the whole path is among the project's own term id-paths, or any source's | `bare_owner_3x`, as today (3.x found it there) |
| `head` is the first folder of any id-path in the project's own taxonomy or a source's | B10, refused (below) |
| otherwise | the child: `<head>.taxonomy/<rest>` |

The rows are tried in that order. `own` and `sources` are what
`owner_of` already passes `bare_owner_3x` for the taxonomy namespace
(`View.own["taxonomy"]`, `View.sources_of("taxonomy")`), so a project that
keeps no taxonomy has an empty `own`, and a source's terms count, as they do
for `route_entry_3x`'s `own_namespaces` (`references.py:123-124`).
`View.children` is the list `view_of` already fills (`stores.py:454`).

**The ambiguous case, decided: refuse.** Where `A`'s taxonomy, or one `A`
inherits through `taxonomy.extends`, keeps a folder `b` and `A` lists a
child `b`, an entry `b/turn` that neither holds could mean a term to be added
under that folder or `b`'s term. Neither reading is safer than the other, and
the migration does not guess: it is the ambiguity `route_entry_3x` refuses
for a capability entry (`legacy.py:975-977`), refused the same way. The user
writes the full identifier and runs again; a value already in full form is
left alone (`references.py:105`).

The blocker names the project or projects whose taxonomy has the folder, and
offers one full identifier for each reading: the child's term, then the
same path in each project that has the folder, the project's own first and
then its sources in the order the run lists them. For the project's own
folder:

```text
B10 <item folder>/capabilities.yaml: b/turn: ambiguous — 'b' is both a child project of this project and a namespace in this project's taxonomy; write it as 'b.taxonomy/turn' or 'a.taxonomy/b/turn', then run 'tcw migrate' again
```

For a folder only in the taxonomy of `lib`, which `A` inherits:

```text
B10 <item folder>/capabilities.yaml: b/turn: ambiguous — 'b' is both a child project of this project and a namespace in the taxonomy it inherits from 'lib'; write it as 'b.taxonomy/turn' or 'lib.taxonomy/b/turn', then run 'tcw migrate' again
```

When both have it, the places are joined with "and" (`this project's
taxonomy and the taxonomy it inherits from 'lib'`; several sources read
`the taxonomies it inherits from 'lib' and 'core'`), and the identifiers are
listed with commas and a final "or" (`'b.taxonomy/turn', 'a.taxonomy/b/turn'
or 'lib.taxonomy/b/turn'`). Naming only the project's own path would, for an
inherited folder, suggest a term the project does not have, and for a parent
with no taxonomy of its own would write back the very address this item
fixes.

The function returns this refusal as a small value holding the blocker's
`why` and `fix` texts (`TermClash`), so `owner_of` passes both to `Blocker`
unchanged, as `Blocker` prints `"{code} {where}: {why}; {fix}"`.

**The held path, decided: keep 3.x's reading.** If `A`'s taxonomy has
`b/turn` itself, 3.x checked the entry against it and it passed; reading it
as `b`'s now would change what a working reference points at.

**The two halves of the file differ here, deliberately.** On a path the
project's own taxonomy holds whose first part is a child's ID, the term rule
keeps 3.x's reading, while `route_entry_3x` refuses the same shape for a
capability entry whenever the first part is also a folder of the ledger,
held or not. So this is not one rule for both halves. Each half stays
faithful to what 3.x did with it: 3.x's capability router refused that
ambiguity, so the migration refuses it too; 3.x read every term entry in the
project's own taxonomy, so a term entry that taxonomy holds was found and
checked there, and keeping that reading changes nothing that worked. Only
where 3.x's term reading could not have found anything (the path not held)
does the migration use the child-first reading the capability entries
beside it got.

### 2. What else is unchanged

- Capability entries, through `route_entry_3x`, exactly as now.
- An entry already in full form, one with a path `id_path_problem` refuses,
  and a bare entry with no `/`: as now.
- The owner the run gives each value is still recorded in the plan's
  `owners` (`references.py:143`), so the progress record says why the bytes
  are what they are.
- Dry run: the same lines, with the new value or the B10.

### 3. The migration guide

`docs/migration-guide-3.X-to-4.0.0.md` gains:

- in step 3, after "Then run `tcw validate`": a passage for a project whose
  work is kept in Jira, saying plain `tcw validate` (and the check `tcw
  migrate` runs after a real run) does not check the records an item's
  `capabilities.yaml` declares, because the item's stage is kept in Jira;
  that `tcw validate --remote` checks them, for items not yet finished; and
  that an entry naming a record not made yet is reported when the item moves
  past implementation, not before. The Jira order's step 2 says `tcw
  validate --remote` once the tickets are converted;
- in the B10 bullet: the new ambiguous case;
- in "Names and addresses": a row saying how a `capabilities.yaml` entry
  prefixed with a listed child's ID is converted (`<child>/<path>` to
  `<child>.capabilities/<path>`, and under `taxonomy:` `<child>/<term>` to
  `<child>.taxonomy/<term>`), unless, under `taxonomy:`, the project's own
  or inherited taxonomy has a term at that whole path, which keeps that
  term. Since this states the rule, it also says in one sentence that the
  difference from a capability entry (which is refused in that case) is
  deliberate: each half does what 3.x did, and 3.x read every term entry in
  the project's own taxonomy.

## Abstraction litmus test

No new operation on what a backend owns. The change is inside `tcw migrate`'s
reading of repository files (`capabilities.yaml`, taxonomy folders), which
the repository owns in both modes, so the second question answers it: read
as files, true for the files backend and Jira alike. `route_term_entry_3x` is
a pure function over id-path sets the migration already collected; a
non-filesystem store could hand it the same sets.

## Use cases

- **UC-3, UC-4 (a parent with children: a monorepo root, a workspace).** The
  case reported: a parent that keeps no taxonomy and declares changes in its
  children's records. After the fix its items name the children's terms.
  Checklist 1-3: the rule reads only the project's own listed children (from
  its own 3.x configuration) and the id-paths the run already gathered; it
  locates nothing new, reads no child's files, and writes only the active
  project's files.
- **UC-5 (a Jira project shared by several TCW projects) and S-3 (which
  backend).** The converted files are the same in both modes. The guide
  change is for Jira mode: there, the records check runs only under
  `--remote`. Checklist 4: no Jira search is added.
- **UC-6 (a related project not on this machine).** The child need not be
  here: the rule uses its ID from the parent's configuration only.
  `tcw validate` then reports the term as unresolved, as for any reference
  into a missing project.
- **S-8 (partial failure).** The new B10 refuses before anything is written,
  as every blocker does, and names the fix.
- **S-9 (upgrades).** The change is to the 3.x to 4.0 conversion only; no
  file format or key changes (checklist 9). A project already migrated is
  not re-read (Non-goals).
- **UC-1 (a single project).** No children, so the first row of the table
  always applies: no cost and no change (checklist 8).
- **UC-2, UC-7, UC-8, S-1, S-2, S-4 to S-7, S-10, S-11:** not touched. No
  harness, person, copy, personal file, run mode, foreign file or git
  behavior changes (checklist 5-7).
- Checklist 10: the regression test builds a two-project family (a parent and
  its child) in separate folders, as the reported setup is.

No setup is missing from `docs/use-cases.md`.

## Acceptance criteria

1. **The reported case.** In the Reproduction's family, after `tcw migrate`
   in `A`, `A/docs/work/2026-10-01-a/capabilities.yaml` parses to
   `{"changed": ["b.capabilities/cli/x"], "taxonomy": {"changed":
   ["b.taxonomy/turn"], "new": ["b.taxonomy/never"]}}`, and
   `A/docs/work/2026-10-02-b/capabilities.yaml` to `{"taxonomy":
   {"removed": ["b.taxonomy/turn"]}}`. The run exits 0 and its output has
   `write docs/work/2026-10-01-a/capabilities.yaml: C16`.
2. **Then validate is clean for these lines.** After `tcw migrate` in `B`
   too, `tcw validate` in `A` gives no finding that mentions
   `capabilities.yaml`, and exits 0. (The Reproduction's three warnings come
   from its first item being at `implement` without request, spec or plan;
   the test puts that item at `inbox`, which needs none of them, so it gives
   no such warning. Any warning that remains does not name
   `capabilities.yaml`.)
3. **The project's own taxonomy holds the path.** In a project whose own
   taxonomy has a term at `b/turn` and which lists a child `b`, the entry
   `b/turn` under `taxonomy:` converts to `<project>.taxonomy/b/turn`.
4. **The ambiguous case.** In a project whose own taxonomy has a term at
   `b/other` (and none at `b/turn`) and which lists a child `b`, `tcw migrate`
   exits 3, writes nothing, and its output holds the B10 line of Design 1
   with that item's path, word for word. The same holds when the `b/` folder
   is in the taxonomy of a project `lib` that the project inherits through
   `taxonomy.extends` rather than its own: `tcw migrate` exits 3, writes
   nothing, and prints the second B10 line of Design 1, which names `lib`
   and offers `'b.taxonomy/turn' or 'lib.taxonomy/b/turn'` (an end-to-end
   test, besides the function's table in criterion 7).
5. **Unchanged readings.** A `taxonomy:` entry with no `/`, one whose first
   part is not a listed child, one whose first part is an `extends` source,
   and one already in full form convert exactly as before this change: the
   existing tests `test_each_entry_of_an_items_capabilities_file` and
   `test_a_capabilities_yaml_entry_is_routed_as_3_x_routed_it` in
   `tests/migrate/test_migrate_references.py` pass unmodified.
6. **Other fields are not routed to a child.** A capability's `Subject:
   [b/turn]` in a project that lists a child `b` still converts to
   `<project>.taxonomy/b/turn` (the narrowed sweep, Non-goals).
7. **The function's table.** `route_term_entry_3x` returns, for each row of
   Design 1's table, the result that row names; a unit test covers every
   row.
8. **The guide.** `docs/migration-guide-3.X-to-4.0.0.md` holds the three
   additions of Design 3, and `tests/test_migration_guide_4_0.py` and
   `tests/test_migration_guide.py` pass.
9. **The capability record.** The description of
   `tcw.capabilities/cli/migrate-a-tcw-3-x-project-to-tcw-4` says that an
   item's `capabilities.yaml` entry prefixed with a listed child's ID is
   written as that child's full identifier, in both the capability and the
   taxonomy lists.
10. **The suite**, run as CI runs it (`pytest`, bare), passes, and
    `tcw validate` in this repository passes.

## Risks

- **A taxonomy folder named like a child is common in a parent that keeps
  one.** Then every child-prefixed term entry it does not hold is B10, and a
  user fixes each by hand. That is the intended trade (the migration does not
  guess), and the message says exactly what to write. It cannot happen in
  the reported setup, where the parent keeps no taxonomy.
- **A source's terms are counted for the "holds the path" and "first folder"
  checks.** That matches `route_entry_3x`'s `own_namespaces`, but means a
  library's folder named like a child turns the entry into B10. Same trade.
- **A parent that keeps a taxonomy without a folder named after the child,
  where the author meant to add `<child-id>/<term>` to the parent's own
  taxonomy under `taxonomy: new:`.** The new rule routes that entry to the
  child, silently: the parent holds neither the path nor a folder `<child-id>`,
  so nothing makes it ambiguous. This is the same choice 3.x's capability
  router made for a capability entry of that shape (`<child>/<rest>` to the
  child whenever the ledger has no folder of that name), and the more likely
  meaning beside capability entries routed the same way. If it was meant
  otherwise, `tcw validate` or the records gate reports the child's term as
  missing, and the user rewrites the line as `<parent>.taxonomy/<child-id>/<term>`.
- **The request's "4.0 turns unchecked into an error" was wrong** (Problem,
  part 1). Anyone reading the release note should not be told 4.0 added an
  error: the note says the migration now writes the child's term, which 3.x
  never checked.

## Notes

- **Proposed separate item:** `tcw validate --remote` silently skips the
  records check for an item whose ticket is at a status no stage names
  (`tcw/work/jira/remote.py:568`, `tcw/work/jira/mapping.py:219`), so an
  epic on a workflow of its own is never checked and nothing says so. It is
  not a migration defect and has its own question (warn, or check with a
  stage-free rule), so it is not folded in here. Not filed by this spec.
- Ship as 4.0.1 (the request).
