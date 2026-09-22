# Require an exclusive claim transition under strict tracker mode

## Capability changes

No new capability. One existing capability changes; it is already `Supported`, so
nothing is seeded and nothing is flipped:

```yaml
changed:
    - work/require-tracker-backed-work
```

Its statement says "`tcw validate` reports a strict block missing
`statuses.active`, `statuses.completed`, or a `statuses.discarded` that covers
every discard resolution". That sentence gains
`work.tracker.exclusive-claim-transition`. The statement's sentences about how a
claim proves it is exclusive ("if, once claimed, the ticket still offers the claim
transition, `start` and `tcw work tracker import` refuse") describe
`claim_refusal`, which C4 removes from the lifecycle. They are C4's to rewrite,
not this item's, because this item does not change what a strict `start` checks.

## Problem

A project with `work.tracker.strict: true` (strict tracker mode: local work is
refused unless a ticket claimed by the running account authorizes it) believes
that starting an item takes its ticket exclusively, meaning a second person
cannot take the same ticket. Today that belief is enforced by `claim_refusal`,
which asks, after the claim, whether the workflow still offers
`transitions.start`. Its strict-mode call is at `tcw/tracker/sync.py:629-634`.

C4 (`2026-09-16-compose-the-lifecycle-moves-from-claim-and-sync`) stops the claim
from moving the ticket, so that question stops meaning anything and C4 deletes
the lifecycle call sites (C4 plan, Task 4). After C4 the only thing that can make
a claim exclusive is C1's optional key, `work.tracker.exclusive-claim-transition`:
a transition the claim applies first, so that a workflow which refuses a second
claimant stops the second person before they reach the assignment
(`tcw/tracker/ownership.py`, module docstring). Today only `tcw work tracker
claim` reads that key (`tcw/work/cli.py:3196-3198`).

A strict project that has not set the key would therefore keep believing in a
guarantee that nothing enforces. C4's spec (Design section 4, Risk 1) decided
that strict mode must require the key; this item carries that decision out,
ahead of C4, so no build of `main` ever has C4's behaviour without the
requirement.

How the parser treats strict mode today, from the code:

- `parse_tracker_config` (`tcw/store/base.py`) already requires three statuses
  under strict mode, in the `if strict:` block at `tcw/store/base.py:1455-1467`.
  Each missing one is a problem reading `work.tracker.statuses.<key>: required
  when strict is true`.
- The key itself is parsed as optional at `tcw/store/base.py:1479-1485`. Absent
  gives `""`. A present `null` or a blank or non-string value is already a
  problem (`expected a non-empty string, got …`).
- The parser **fails closed** (any problem makes the whole configuration `None`;
  docstring at `tcw/store/base.py:1373-1377`). So every problem, including the
  new one, disables the tracker block as a whole.

## Goals

1. `tcw validate` reports a strict tracker block that does not set
   `work.tracker.exclusive-claim-transition`, as a problem whose text names the
   key, says strict mode is why, and says what to set.
2. Because that is an ordinary parser problem, every strict move refuses until
   the key is set, through the refusal strict mode already gives for a broken
   configuration. Nothing new is invented for it.
3. A project that is not strict is untouched: the key stays optional for it.
4. The documentation and the release notes tell an upgrading strict project what
   changed and what to do, and the split of that text between this item and C4
   is stated so neither says it twice.

## Non-goals

- **Wiring strict `start` to the key.** Today's strict start
  (`_strict_claim`, `tcw/work/cli.py:395`, → `intake.claim` → `claim_refusal`)
  is unchanged. C4 routes a strict start through `assert_ownership`, which
  already asserts through the key. Until C4 lands the key is required under
  strict mode and read only by `tcw work tracker claim`.
- **Removing `claim_refusal`'s lifecycle call sites and deleting
  `_strict_claim`.** C4 plan, Task 4.
- **Making `transitions.start` optional.** That is
  `2026-09-18-make-transitions-start-optional-now-that-a-start-goes-through-assess-move`.
- **Checking the named transition against the live Jira workflow.** `tcw
  validate` works offline and must not open a connection
  (`tcw/validate.py:271-283`, guarded by `tests/test_tracker_validate.py`).
- **Changing the strict-mode refusal text for a broken configuration.**
  `_STRICT_BROKEN` (`tcw/work/cli.py:367-368`) says the configuration has
  problems and to run `tcw validate`; it does not name the problem. See Design
  section 3 for why that is acceptable here and `## Notes` for the possible
  follow-up.
- **Requiring the key to differ from, or equal, `transitions.start`.** They
  answer different questions (`tcw/store/base.py:1194-1199`); either value is
  legal.
- **Using `TRACKER_RENAMED_KEYS`** (`tcw/store/base.py:1273-1276`). That table is
  for a key that was renamed; nothing is renamed here. What is copied from C3 is
  the content of its message: say what changed and what to write instead.

## Design

### 1. One more requirement in the existing strict block

Inside the `if strict:` block at `tcw/store/base.py:1455`, beside the three
status requirements, add: when the merged tracker mapping has **no
`exclusive-claim-transition` key at all**, append

```
work.tracker.exclusive-claim-transition: required when strict is true. Strict
mode promises that only one person can take a ticket, and a claim keeps that
promise by applying this transition, which your workflow will not apply to a
ticket that has already been taken. Name the transition that takes a ticket
into work.
```

(one line in the code; wrapped here for reading).

The exact wording can be adjusted at plan or implementation time, but it must
keep three things, which the acceptance criteria check: the prefix
`work.tracker.exclusive-claim-transition: required when strict is true`, the
reason (the words `only one person`), and what to do (the words `Name the
transition`).

The sentence is written to be true both before and after C4. Before C4 a claim
through `tcw work tracker claim` applies the key; after C4 every claim does. It
does not say that `tcw work start` uses the key, which is only true after C4.

**When the key is present but wrong** (`null`, blank, or not a string), the
existing check at `tcw/store/base.py:1481-1485` already reports it and the new
one does not fire. One problem per key, the same rule C3's retired-key note
follows (`tcw/store/base.py:1426-1430`): a second "required" line about a key the
user did write would be noise.

**Only a real `true` counts.** A non-boolean `strict` is already a problem and is
read as `false` for parsing (`tcw/store/base.py:1450-1454`), so the new check does
not fire for it. The block fails closed anyway.

The comments at `tcw/store/base.py:1456-1457` ("Strict mode gates completing and
discarding against these") and `:1479` ("Optional") are updated so they no longer
claim the key is simply optional, or that the strict block only concerns statuses.

This passes the abstraction test (`docs/lifecycle/abstraction.md`): it is a rule
in the pure parser, which reads a mapping and touches no filesystem, so any store
that holds a tracker block enforces it the same way. It is enforced by the `tcw`
CLI, so Claude and Codex users get it identically (`docs/lifecycle/harness.md`).

### 2. Inheritance: where the key can be set

`merge_tracker_blocks` (`tcw/store/base.py:1744-1786`) lays a node's
`work.tracker` over its ancestors' key by key, and the merged mapping is what the
parser sees (`tcw/store/fs.py:5941-5943`). So:

- The key can be set in the node's own block or in any ancestor block the node
  inherits from. Setting it once in a shared parent block satisfies every child
  that opts in to inheritance.
- A child that sets `strict: false` over a strict parent is not strict and does
  not need the key.
- A `null` in a child does not unset an ancestor's value; the ancestor's value
  shows through (`tcw/store/base.py:1792-1796`). So a child cannot accidentally
  remove the key its parent set.
- A node whose own block is empty or absent does not inherit at all
  (`tcw/store/fs.py:5918-5920`), so it has no tracker and no requirement.

The new problem names a key path that nobody wrote, so
`attribute_tracker_problems` (`tcw/store/base.py:1840-1866`) attributes it to the
node being validated (`own_label`), even when `strict: true` came from an
ancestor. That is the same attribution a missing `statuses.active` gets today and
is acceptable: the fix works in either file. Nothing in the merge changes.

### 3. What a strict project missing the key sees

- **`tcw validate`**: the problem above, prefixed with the config file it is
  attributed to (`tcw/validate.py:283`, `tcw/store/fs.py:5899-5903`).
- **Any strict lifecycle move** (`start`, `submit`, `rework`, `complete` as
  `done`, `new`, `inbox accept`): `tracker_strict()` still answers `True` for a
  block with problems (`tcw/store/fs.py:5956-5961`), `tracker_config()` answers
  `None`, and the move refuses with `_STRICT_BROKEN`: "refused under strict
  tracker mode; … The tracker configuration has problems, and strict mode refuses
  until it is fixed. Run `tcw validate`." (`tcw/work/cli.py:360-368`, used at
  `:386-387` and `:402-404`). That message **does** point at `tcw validate`, which
  then names the key. It does not name the key itself. That is the behaviour a
  strict project missing `statuses.completed` gets today, which the request asked
  this item to keep.
- **Every `tcw work tracker …` command** (`list`, `show`, `claim`, `sync`, `link`,
  `import`, …) goes through the helper at `tcw/work/cli.py:2264-2273`, which
  prints each problem, so these name the key directly. They all refuse, because
  the block is disabled as a whole.
- **`tcw serve`** keeps refusing the strict actions it already refuses; it reads
  only `tracker_strict()` (`tcw/serve/__init__.py:230`), which is unchanged.

So the user is never left with only a generic message: the refusal names the
command that names the key.

### 4. Existing tests that turn strict mode on

Every test fixture that sets `strict: true` without the key becomes a
broken-configuration fixture. That would not only break tests; it would make some
of them pass for the wrong reason. `test_a_broken_strict_block_names_validate`
(`tests/test_tracker_strict.py:688-692`) breaks the block on purpose with
`timeout-seconds: -1` and asserts the refusal names `tcw validate`; with the key
missing it would pass even if that line were removed. So the plan must add the key
to every strict fixture, so that a fixture meant to be valid is valid and a
fixture meant to be broken is broken only by the thing it breaks:

- `strict_node` in `tests/test_tracker_strict.py:32-36` (and the `BASE` mapping
  at `:24-29` used by `parsed`), which every strict gate test is built on;
- `tests/test_tracker_strict.py:706-715` (inheritance chains);
- `tests/test_tracker_validate.py:92`, `:326`, `:333`;
- `tests/test_tracker_cli.py:1408`, `:1589`, `:1644`.

Adding the key to these fixtures changes no behaviour those tests exercise: the
only reader of the key today is `tcw work tracker claim`
(`tcw/work/cli.py:3196-3198`), and no strict test calls it.

`test_strict_is_reported_as_unknown_because_c4_owns_it`
(`tests/test_tracker_config.py:151-157`) is already stale: `strict` has been an
accepted key since strict mode shipped, and the test passes today only because
its block lacks the strict statuses and that message happens to contain the word
"strict". Checked against the tree: with `strict: true` and no statuses, the
parser reports three `statuses.…: required when strict is true` problems and no
unknown-key problem. It is rewritten or removed here, because the new problem
would give it another accidental reason to pass.

### 5. Documentation, and who writes which release-note sentence

The epic ships across version cuts, not in one (see `## Risks` 2), so each
item's text must be true at the moment it lands.

**This item writes:**

| Entry | What |
| --- | --- |
| `skills/configure/references/tracker.md` (Configuration-Key-Change) | The strict paragraph (`:172-178`) adds the key to what strict mode needs; its YAML example (`:185-192`) sets it. The key's own paragraph (`:84-99`) says it is optional **except under strict mode**, qualifying "Leave it unset unless the project needs it". |
| `docs/guide/jira.md` (Tracker-Change) | The settings table row (`:86`) says required under strict mode. "Strict mode: no work without a ticket" (`:873-885`) adds the key to what strict mode needs and to its YAML example. "When two people claim at once" (`:433-434`, "why the setting is optional and off by default") gains the strict exception. |
| `docs/release-notes/upcoming.md` (Public-API) | The **first** entry, marked as a breaking change for strict projects: strict mode now needs `work.tracker.exclusive-claim-transition`; `tcw validate` reports it missing and strict commands refuse until it is set; set it to the transition your workflow uses to take a ticket into work, one it will not apply to a ticket already taken; setting it means `tcw work tracker claim` applies that transition, which moves the ticket. |
| `docs/changelogs/upcoming.md` (Any-Code-Change) | Under Changed: `parse_tracker_config` requires `exclusive-claim-transition` when `strict` is true. |

**C4 writes**, in its own entry placed after this one: that a strict `start` now
takes its ticket through `exclusive-claim-transition` rather than through
`transitions.start`, and why (a claim no longer moves the ticket, so the start
transition can no longer prove exclusivity). C4's entry must **not** restate that
the key is required, what `tcw validate` does, or what to set. C4's plan
currently says its release-note entry "must lead with strict mode's new required
key", and lists the same requirement under its `tracker.md` and `jira.md` rows;
those rows need amending to "follows this item's entry and does not repeat it"
before C4 is implemented. This item does not edit C4's plan.

**Not firing, with reasons:** `README.md` (Public-API): its strict section
(`README.md:524-537`) lists what strict mode refuses, not which keys it needs, and
its configuration example is not strict. `skills/work/SKILL.md` and
`skills/work/references/commands.md` (Skill-Driven-Component): the strict section
(`commands.md:234-260`) already says a block with problems refuses and to run
`tcw validate`, which stays true. `docs/guide/<topic>.md`: no other guide names
strict mode's required keys.

### 6. The sweep for sibling defects

Repo-wide, not narrowed:

- **Other places that decide what strict mode requires.** Only
  `parse_tracker_config`. `tracker_strict()` in `tcw/store/fs.py:5893-5897` and
  the base default at `tcw/store/base.py:3229-3234` read `strict`, never the
  requirement list. `tcw/serve/__init__.py:230` reads `tracker_strict()` only.
- **Other text that says strict mode needs only three statuses.** The two docs
  in section 5, and the capability statement. Found with
  `grep -rn "strict" skills/ docs/guide README.md`.
- **Other fixtures turning strict mode on.** Section 4's list is the full result
  of `grep -rn '"strict": True\|strict: true\|strict=True' tests/ evals/`; `evals/`
  has none.
- **A test passing for the wrong reason.** One found and handled (section 4).

## Acceptance criteria

Each criterion says which mutation (deliberately breaking the code) must turn its
test red. A test that stays green under its mutation is not accepted.

1. `parse_tracker_config` on a block with `strict: true`, the three required
   statuses, and **no** `exclusive-claim-transition` returns `None` and exactly
   one problem, which starts with
   `work.tracker.exclusive-claim-transition: required when strict is true` and
   contains `only one person` and `Name the transition`.
   *Mutation:* delete the new check → red.
2. The same block with `exclusive-claim-transition: Start Progress` parses, with
   no problems and `config.strict is True`.
   *Mutation:* make the check fire whether or not the key is set → red.
3. A block with no `strict` key, or `strict: false`, and no
   `exclusive-claim-transition` parses with no problems.
   *Mutation:* drop the `if strict:` condition from the new check → red.
4. Under `strict: true`, `exclusive-claim-transition: null` and
   `exclusive-claim-transition: ""` each give exactly one problem naming the key,
   and it is the existing `expected a non-empty string` one, not the new
   `required when strict is true` one.
   *Mutation:* test key presence with `raw.get(...)` instead of `in raw` → the
   `null` case gets two problems → red.
5. `tcw validate` on a strict node whose block lacks only the key reports a
   problem beginning `tcw-config.yaml: work.tracker.exclusive-claim-transition:
   required when strict is true`, and `tcw work list` on that node still exits 0.
   *Mutation:* same as 1.
6. On that node, `FsWorkStore.tracker_strict()` is `True`, `tracker_config()` is
   `None`, and `tracker_problems()` has exactly one entry. Then `tcw work start`
   and `tcw work submit` on a bound item each exit 1 with stderr containing
   `refused under strict tracker mode` and `tcw validate`, and the item's status
   is unchanged.
   *Mutation:* same as 1 → `tracker_config()` is not `None` and the one-entry
   assertion fails. The exactly-one assertion is what stops this test passing
   because of some other problem in the fixture.
7. Inheritance, with `test_tracker_inheritance.py`'s `_chain`: (a) a parent block
   with `strict: true` and the key, and a child that opts in with a
   `candidate-query`-only block, validates with no tracker problem for the child;
   (b) the same parent without the key gives the child a problem naming the key,
   attributed to the child's own config file; (c) a strict parent without the key
   and a child that sets the key in its own block validates clean for the child;
   (d) a child with `strict: false` under a strict parent that lacks the key has no
   tracker problem.
   *Mutation:* same as 1 turns (b) red; the variant in 2 turns (a), (c) and (d)
   red.
8. Every existing fixture listed in Design section 4 sets the key, and the full
   suite passes. Then, for `test_a_broken_strict_block_names_validate` and
   `test_a_broken_strict_block_refuses_inbox_accept_even_with_ticket`
   (`tests/test_tracker_strict.py:688`, `:820`): removing the line that breaks the
   block (`timeout-seconds: -1`) turns the test red. Before this item's fixture
   change that removal would leave them green once the key became required.
9. `test_strict_is_reported_as_unknown_because_c4_owns_it` no longer exists in its
   current form: either removed, or rewritten to a test whose name says what it
   checks and which fails under its own mutation.
10. `skills/configure/references/tracker.md` and `docs/guide/jira.md` each state
    that strict mode requires `exclusive-claim-transition`, and every YAML example
    in them containing `strict: true` also contains `exclusive-claim-transition`.
    Checkable with `grep -n -A8 "strict: true"` on both files.
11. `docs/release-notes/upcoming.md` opens with an entry that names
    `work.tracker.exclusive-claim-transition`, says it is a breaking change for
    strict projects, and says what to set. `docs/changelogs/upcoming.md` has the
    matching Changed line.
12. The capability `work/require-tracker-backed-work`'s statement names the key in
    its sentence about what `tcw validate` reports for a strict block.

## Risks

1. **It breaks every strict project on upgrade, on purpose.** Until the key is
   set, the whole tracker block is disabled: every strict move and every `tcw work
   tracker` command refuses. That is how strict mode already treats any missing
   required key, and the alternative is a guarantee nothing enforces (C4 spec,
   Design section 4, Risk 1). The request notes no project on this machine sets
   `strict: true`, including this repository's own `tcw-config.yaml`; checked,
   `grep -n strict tcw-config.yaml` finds nothing.
2. **The epic does not ship in one version cut.** `initial-request.md` says the
   window between this item and C4 "never reaches a user, because the whole epic
   ships in one version cut". The release history contradicts that: C1 and C3
   shipped in v2.4.0 (`docs/release-notes/v2.4.0.md:6-16`, `:362-366`), and v2.5.0
   and v2.5.1 were cut after them without C4. So a version could be cut with this
   item and without C4. In that release strict projects must set a key that a
   strict `start` does not yet use; only `tcw work tracker claim` applies it. The
   design limits the damage by keeping every sentence this item writes (the
   validate message, both docs, its release-note entry) true in that state, and
   leaving the sentence about `start` using the key to C4. Whether to hold the
   next version cut until C4 lands is a question for the user (`## Notes`).
3. **Complying moves tickets on claim.** A strict project that sets the key gets
   the cost C1 documented: `tcw work tracker claim` applies the transition and so
   moves the ticket. That is the release-note entry's last sentence, so it is not a
   surprise.
4. **A fixture change that hides a regression.** Adding the key to every strict
   fixture is required (Design section 4) but it also means no existing test runs
   without the key. Criteria 1, 5 and 6 are the tests that do, and each must go red
   under its mutation.
5. **Every child of this epic shipped a defect its full suite did not catch.**
   Hence the per-criterion mutation, and the exactly-one-problem assertions, which
   stop a test passing because of an unrelated problem in its fixture.

## Notes

- **Contradiction with `initial-request.md`:** the "one version cut" premise, in
  Risk 2. It does not change the scope (validation only still holds); it changes
  how the text must be written, and raises a sequencing question.
- **Contradiction with C4's plan:** its Documentation Sync rows for
  `docs/release-notes/upcoming.md`, `skills/configure/references/tracker.md` and
  `docs/guide/jira.md` claim the strict-requires-the-key text. Per Design
  section 5 that text is this item's; C4's rows should be amended to follow it
  without repeating it. C4's spec still lists criterion 15 and Risk 1 as its own,
  while C4's plan (`## Notes`) says criterion 15 moved here; the spec should be
  annotated to match. Neither file is edited by this item.
- **For C4:** its criterion 14 ("with `exclusive-claim-transition` unset, a `tcw
  work start` posts exactly one workflow transition") can only be tested on a
  non-strict node once this item lands, because a strict node without the key no
  longer parses.
- **Open question for the user:** should the next version cut wait for C4? Not
  blocking; the design is safe either way (Risk 2).
- **Possible follow-up, not in scope:** strict refusals caused by a broken
  configuration could list the problems inline, as the non-strict delivery path
  already does (`tcw/work/cli.py:1159-1161`), rather than only naming `tcw
  validate`. That would change every strict refusal, not only this key's, which
  the request ruled out.
- No spec review round is called for by the stage instructions.
