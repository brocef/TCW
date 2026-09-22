# Spec — Make `transitions.start` optional now that a start goes through `assess_move`

## Capability changes

None. No capability is added, removed, or reworded. The change removes a
configuration requirement; every command keeps the same name, arguments and
purpose.

## Problem

`work.tracker.transitions.start` is required, and the reason it was required is
gone.

**The reason, as the code states it.** Three places say a start has no
status-derived rule to fall back on, because it applies its transition through
the claim rather than through `assess_move`:

- `tcw/store/base.py:1263-1266` — the comment above `TRACKER_TRANSITION_KEYS`.
- `tcw/store/base.py:1503-1506` — the comment above the parser check.
- `tcw/store/base.py:1693-1695` — `_parse_tracker_transitions`' docstring.

**The reason is false today.** The sibling item
`2026-09-16-compose-the-lifecycle-moves-from-claim-and-sync` (completed
2026-09-22, documents retained in commit `8e9937b4`) routed a start through
`assess_move`. A start now reaches the status-derived rule exactly as the other
four moves do. Three code paths carry a start into `assess_move`, and all three
get the name from the same function:

1. **The ordinary lifecycle start** — `tcw/tracker/sync.py:872-874`:
   `named = transition_name(config.move_transitions, move, item.resolution)` with
   `move == "start"`, then `assess_move(..., named_transition=named)`.
2. **The owed-start catch-up that runs before a later move** —
   `tcw/tracker/sync.py:823-825`:
   `assess_move(ticket, target=active, expected=(), move="start",
   named_transition=transition_name(config.move_transitions, "start", None))`.
3. **A ladder hop onto the active rung inside `walk()`** —
   `tcw/tracker/sync.py:549-551` and `:557-559`. The hop's move is
   `MOVE_ONTO[local_name]`, and `MOVE_ONTO["active"] == "start"`
   (`tcw/tracker/sync.py:88-89`), so a walk that climbs onto the active rung is
   serving a start.

`transition_name` returns `""` for a move nobody configured
(`tcw/store/base.py:1741-1746`), and an empty `named_transition` sends
`assess_move` past the `if named_transition:` block at `tcw/tracker/sync.py:271`
to the status-derived tail at `:298-307`, which applies the single offered
transition whose destination is the target status.

Run against the tree at this item's spec (unmodified source):

```
transition_name({}, 'start', None) -> ''
assess_move(ticket in 'To Do' offering ('Start Progress' → 'In Progress',
            "Won't Do" → "Won't Do"), target='In Progress', expected=(),
            move='start', named_transition='')
  -> ('apply', Transition(id='21', name='Start Progress', to_status='In Progress'))
```

That is the proof the whole item rests on, and it holds.

**What the requirement costs.** Every tracker-backed project must name a
transition TCW can work out for itself, and three comments in the source assert
something that is no longer true.

### Two required checks, not one

The initial request names one check, `tcw/store/base.py:1507-1508`:

```python
if "start" not in transitions:
    problems.append("work.tracker.transitions.start: required")
```

There is a **second** one the request does not mention. `transitions` is parsed
by the shared `nested` helper (`tcw/store/base.py:1426-1440`), called at `:1443`, and that helper reports `work.tracker.<key>: required` whenever the
mapping itself is absent or null. Removing only the check the request names
leaves this behind:

```
tcw-config.yaml: work.tracker.transitions: required
```

Measured: with only the named check removed, `tcw validate` on a node whose
tracker block has no `transitions` key exits 1 with exactly that message. A
project would still have to write `transitions: {}`, which is a requirement with
no remaining purpose once all five keys under it are optional. Both checks go.

### Three readers of the name that have no derived rule

`config.start_transition` is the parsed value of `transitions.start`
(`tcw/store/base.py:1193`, set at `:1531`). Three places outside the lifecycle
moves read it directly, and none of them has a status to derive from. Today they
can never see an empty string, because the parser refuses one. After this change
they can.

1. **`tcw/tracker/intake.py:650`**, inside `_claim_from` — the claim that
   `tcw work tracker import` and `tcw work inbox accept` make. Both commands go
   through `_tracker_import` (`tcw/work/cli.py:2528`, and `:851` for
   `inbox accept`), which claims through `intake.claim` at `:2586`. The claim's
   design is "apply the transition, then assign" (`tcw/tracker/intake.py:634-638`),
   so with no transition named there is nothing to apply. Measured today, with the
   parser checks patched out:

   ```
   tcw work tracker import: TCWCLAIM-6 is in 'To Do', unassigned, and does not
   offer ''. It offers: 'Start Progress'.
   ```

   No item is created and the ticket is untouched, which is safe — but the
   message blames the ticket for a configuration that names nothing.

2. **`tcw/work/cli.py:2468`**, inside `_print_ticket` — what
   `tcw work tracker show` and `tcw work inbox show` print. Measured the same
   way:

   ```
   claimable: not claimable
   workflow: not determined from this ticket
   note: work.tracker.transitions.start is '', which this ticket does not offer.
         It offers: 'Start Progress'. Either the name is wrong, or ...
   ```

   It reports a wrong name where none is set.

3. **`tcw/tracker/sync.py:1062-1067`**, inside `claim_refusal` — reached only
   from `tcw/work/cli.py:2606-2609`, the strict-mode check `_tracker_import` runs
   after a successful claim. With rule 4 below in place this is reachable with an
   empty name only through the claim's row `1e` (a ticket the running account
   already holds), where nothing was applied and nothing is being promised.

## Goals

- A tracker configuration with no `transitions` mapping, and one with
  `transitions: {}`, both pass `tcw validate`.
- A start with no configured transition name finds its transition from the
  target status, on every code path that serves a start.
- A configuration that **does** set `transitions.start` behaves exactly as it
  does today.
- The refusal that names a transition a ticket does not offer gives the same
  advice for all five moves.
- The two commands that claim through the name refuse clearly, and the two that
  display it report it honestly, when the name is not set.
- The comments and documents that state the old reason stop stating it.

## Non-goals

- **`tcw validate` does not suggest removing the key.** The requester ruled this
  out on 2026-09-22: a permitted setting should not be one TCW nudges people
  away from.
- **No change to what a start does when the key is set.** This is not a breaking
  change and must not become one.
- **No change to `work.tracker.exclusive-claim-transition`**, to strict mode's
  requirement of it (`tcw/store/base.py:1281-1286`, appended at `:1483`), or to the claim itself.
- **No change to deriving a transition.** The status-derived rule at
  `tcw/tracker/sync.py:298-307` is used as it stands.
- **No change to this repository's own `tcw-config.yaml`**, which keeps
  `transitions.start: Start` (line 12-13) as a live example of the setting still
  being honored.
- **No migration.** A configuration written before this change keeps working
  unaltered.

## Design

### 1. Both required checks go, and a null `transitions` stays a wrong value

Delete `tcw/store/base.py:1503-1508` (the comment and the `"start" not in
transitions` check). Replace the unconditional `nested` call at `:1443` with the
shape this parser already uses for its other optional blocks —
`exclusive-claim-transition` at `:1497-1501` and `inbox-query` at `:1421-1424`:

```python
if "transitions" in raw and raw["transitions"] is None:
    problems.append("work.tracker.transitions: expected a mapping, got NoneType")
transitions = (nested("transitions", TRACKER_TRANSITION_KEYS)
               if raw.get("transitions") is not None else {})
```

Absent is fine and yields `{}`. An explicit `transitions: null` is a **wrong
value**, not a missing required one, which is the distinction the two neighbours
above already draw. A non-mapping value keeps the `expected a mapping` problem
`nested` already reports, and an unknown or retired sub-key keeps the problem
`nested` already reports for it.

`start = move_transitions.get("start", "")` at `:1509` stays: `config.start_transition`
becomes `""` when nothing is configured, which is what rules 4 and 5 handle.

**Abstraction:** this is parsing of a configuration document, not a store
operation. Nothing here touches the filesystem.

### 2. The "or remove it" advice becomes uniform

Delete the special case at `tcw/tracker/sync.py:276-281`, so the line reads:

```python
drop = ", or remove it to let TCW find the transition itself"
```

— or, more simply, fold the text into the message and drop the variable. Its
stated reason, that removing the key is something `tcw validate` refuses, stops
being true under rule 1. All five moves then get the same advice.

### 3. The three comments stop asserting the old reason

- `tcw/store/base.py:1263-1266`: `start` is no longer the exception. The comment
  keeps what is still true — a move with no name here keeps the status-derived
  rule, and an unknown key is reported.
- `tcw/store/base.py:1503-1506`: deleted with the check.
- `tcw/store/base.py:1693-1695`: `_parse_tracker_transitions`' docstring drops
  "That `start` is required is the caller's check"; the rest, that absent is
  `{}` and leaves every move on the status-derived rule, is now the whole story.
- `tcw/tracker/sync.py:276-279`: deleted with rule 2.

A fourth comment, `tcw/tracker/ownership.py:8-15`, mentions
`client.config.start_transition` but only to explain why `intake.claim` is not
reused. It stays true and is not touched.

### 4. `import` and `inbox accept` refuse clearly when no name is set

`tcw/tracker/claim.py` gains one verdict constant and one early return in
`assess`, which is pure and has no other input to consult:

```python
NOT_CONFIGURED = "no start transition configured"
```

```python
if not claim_transition.strip():
    return Assessment(claimable=NOT_CLAIMABLE, exclusivity=NOT_DETERMINED,
                      verdict=NOT_CONFIGURED,
                      detail="work.tracker.transitions.start names no transition, "
                             "so there is none to claim this ticket through.")
```

The guard goes in `assess` rather than in each caller because all three readers
named in the Problem section reach it, and one guard in the shared function is
smaller than three guards in callers — the rule this repository's epic learned
twice, where a fix covered one of two paths.

`tcw/tracker/intake.py`, inside `_claim_from`'s `if not matches:` block, gains a
new refusal row `1d` (the id is free; the rows in use are `1a`, `1b`, `1c`,
`1e`, `1f`, plus `0f` and `0-read` from the pre-backlog step):

```python
if not matches:
    if ticket.assignee_id == ticket.me_id:
        return claimed("1e", ...)                    # unchanged, and first
    if assessment.verdict == NOT_CONFIGURED:
        return refused("1d", f"{key} cannot be claimed: "
                             f"work.tracker.transitions.start is not set, and this "
                             f"command claims through it. Set it, or take the ticket "
                             f"with `tcw work tracker claim` and bind an item to it "
                             f"with `tcw work tracker link`.")
    offers = ...
    return refused("1f", ...)                        # unchanged
```

**The order matters and is load-bearing.** Row `1e` — a ticket the running
account already holds — must keep winning. It is what lets a claim that
succeeded and then failed locally finish on a re-run
(`tcw/work/cli.py:2532-2536`), and what lets somebody take a ticket with
`tcw work tracker claim` (assignment only, no transition) and then import it.
Putting the new refusal first would break both.

**Why refuse rather than derive.** The claim is not a lifecycle move. It has no
`target` status of its own — `statuses.active` is itself optional, so on a
project that sets neither key there is nothing to derive from — and a wrong
guess here assigns the ticket as well as moving it. Refusing costs four lines
and tells the reader exactly which key to set.

### 5. `tracker show` and `inbox show` need no edit

`_print_ticket` (`tcw/work/cli.py:2458-2474`) prints `result.detail` on a
`note:` line, so rule 4's new `detail` reaches the reader without touching
`cli.py`. `claimable: not claimable` stays, which is accurate for the claim this
word has always described — the one `import` makes.

### 6. Documentation and the tests that assert the requirement

Six existing tests fail once rules 1 and 2 land. Measured by applying rule 1 to
a scratch copy of the tree and running `pytest tests/test_tracker_config.py
tests/test_tracker_inheritance.py`:

| Test | Why it fails | What it becomes |
| ---- | ------------ | --------------- |
| `test_tracker_config.py::test_a_missing_required_key_is_reported_by_name[transitions]` | `transitions` is no longer a required key | the `transitions` parameter is dropped; the other required keys stay |
| `test_tracker_config.py::test_a_missing_start_transition_is_reported_by_name` | there is no such problem any more | inverted: a block with `transitions: {}` validates |
| `test_tracker_config.py::test_the_retired_claim_key_names_its_replacement` | its last assertion expects the `required` problem alongside | keeps the retired-key half; asserts no `required` problem is emitted |
| `test_tracker_config.py::test_only_the_required_start_transition_is_there_by_default` | its name and docstring assert the requirement | renamed; asserts `move_transitions == {"start": "Start Progress"}` for the same input |
| `test_tracker_inheritance.py::test_a_missing_nested_key_under_an_ancestors_mapping_is_blamed_on_the_node` | uses `transitions.start: required` to demonstrate the C22 attribution rule | re-pointed at another nested required key under an ancestor-supplied mapping, e.g. `credentials.token-env` |
| `test_tracker_inheritance.py::test_a_nested_required_key_nobody_set_is_blamed_on_the_child` | same | same |
| `test_tracker_inheritance.py::test_a_retired_key_in_a_parent_names_the_parents_file` | its last assertion expects the `required` problem | keeps the attribution half; drops that assertion |
| `test_tracker_sync.py::test_only_a_removable_transition_key_is_offered_for_removal` | parametrized `("start", False)` | both moves become removable; the parameter collapses or `start` flips to `True` |

`attribute_tracker_problems`' docstring (`tcw/store/base.py:1859-1862`) uses
`transitions.start: required` as its worked example of a problem about a key
nobody set. That message no longer exists, so the example is replaced by one the
parser can still produce.

Documents to change: `docs/guide/jira.md` (the key table at `:84`, the
"Naming a transition" paragraph at `:868-873`, the "Renaming the start
transition" sample output at `:891-893`, the import steps at `:248`, and the
"Inherited settings" paragraph at `:129-133`);
`skills/configure/references/tracker.md` (`:5`, `:35`, `:52`, `:63-68`, `:79-81`);
`skills/work/references/commands.md` (`import`'s refusals);
`docs/changelogs/upcoming.md`; `docs/release-notes/upcoming.md`. `README.md:554`
and the sample blocks in `docs/guide/configuration.md` and `docs/guide/work.md`
need no edit: the first still sets the key, and the other two are about
`work.lifecycle.transitions`, a different key with the same last word.

## Abstraction litmus test

No new operation. Each change is one of:

- **Configuration parsing** (rules 1 and 3) — `parse_tracker_config` is already
  pure, takes a plain mapping, and is shared by every store. A non-filesystem
  store parses the same document the same way. Verdict: **model**.
- **A pure decision over one ticket read** (rules 2 and 4) — `assess_move` and
  `claim.assess` take values, not a client and not a path, and return a verdict.
  Verdict: **model**.
- **A refusal message and a printed line** (rules 4 and 5) — presentation over
  the above. Verdict: **model**; nothing here is a filesystem trick.

Nothing is pushed into the filesystem adapter, because nothing added reads a
path, a directory or a git object.

## Acceptance criteria

Each criterion names the mutation — a deliberate break in the shipped code —
that must turn its test red. A criterion whose test stays green under its
mutation is not a test.

1. **A block with no `transitions` key at all validates.** `parse_tracker_config`
   on an otherwise valid tracker block with no `transitions` key returns a
   config with `problems == []`, `config.move_transitions == {}` and
   `config.start_transition == ""`. (C4's acceptance criterion 16, which C4
   moved here.)
   *Mutations, both of which must turn it red:* (a) restore `if "start" not in
   transitions: problems.append("work.tracker.transitions.start: required")`;
   (b) restore the unconditional `transitions = nested("transitions",
   TRACKER_TRANSITION_KEYS)`.

2. **`transitions: {}` validates too**, with the same three results. This is the
   case the single check named in the request unlocks; criterion 1 is the case
   the second check unlocks, and they are separate parameters of one test.
   *Mutation:* criterion 1's mutation (a).

3. **`transitions: null` is a wrong value, not a missing one.**
   `parse_tracker_config` reports `work.tracker.transitions: expected a mapping,
   got NoneType` and returns no config, and emits no `work.tracker.transitions:
   required` problem.
   *Mutation:* delete the `if "transitions" in raw and raw["transitions"] is
   None` guard, so `raw.get("transitions") is not None` swallows an explicit
   null and the block validates.

4. **A present but unusable value is still reported.** Each of `transitions:
   {start: null}`, `{start: ""}`, `{start: "   "}` and `{start: 5}` produces
   `work.tracker.transitions.start: expected a non-empty tracker transition
   name` and no config — the same wording its four siblings get.
   *Mutation:* remove `"start"` from `TRACKER_MOVE_TRANSITION_KEYS`.

5. **The retired-key message survives on its own.** `transitions: {claim:
   Start}` reports exactly one problem about `work.tracker.transitions.claim`,
   that problem names `work.tracker.transitions.start` as the replacement and
   does not say "unknown key", and no `work.tracker.transitions.start: required`
   problem is emitted.
   *Mutation:* restore criterion 1's mutation (a) — the last clause goes red.

6. **A configuration that sets the key is unchanged.** On a workflow offering
   **two** transitions from the backlog status into `statuses.active` (ids `21`
   "Start Progress" and `22` "Fast Track"), with `transitions.start: Start
   Progress`, `tcw work start` on a bound backlog item exits 0 and posts exactly
   one transition, id `21`. (C4's criterion 14, first half, on a fixture where
   the configured name is load-bearing rather than merely agreeing with the
   derived answer.)
   *Mutation:* delete the `if named_transition:` block at
   `tcw/tracker/sync.py:271-297`, so every move derives — the start then refuses
   as ambiguous.

7. **A start with no key uses the derived rule.** With no `transitions` key and
   a workflow where exactly one offered transition leads to `statuses.active`,
   `tcw work start` on a bound backlog item exits 0, posts exactly one
   transition — that one — and leaves the ticket assigned to the running
   account. (C4's criterion 14, second half, which C4 could not test because the
   key could not be unset.)
   *Mutation:* make the derived tail at `tcw/tracker/sync.py:298-307` return
   `CONFLICTING` instead of `("apply", leads[0])`.
   *Measured on a scratch copy with rule 1 applied:* exit 0, one POST to
   `/transitions`, `applied == ["21"]`.

8. **No configured name is consulted for a start.** With no `transitions` key
   and the two-route workflow from criterion 6, the same `tcw work start` posts
   nothing, exits non-zero, still moves the item locally to `active`, and writes
   a sync record with `state: conflicting` whose reason contains `offers more
   than one transition to 'In Progress' (ids 21, 22); TCW will not guess which`.
   A name, had one been consulted, would have resolved the ambiguity.
   *Mutation:* make `transition_name` return `"Start Progress"` for `move ==
   "start"` when nothing is configured — the start then succeeds.
   *Measured on a scratch copy with rule 1 applied:* exit 1, `applied == []`,
   local status `active`, record reason exactly as quoted.

9. **All three start-bearing code paths derive, not only `tcw work start`'s.**
   With no `transitions` key, each of these applies the single transition
   leading to `statuses.active` and posts nothing else:
   (a) the ordinary lifecycle start (`tcw/tracker/sync.py:872-874`);
   (b) the owed-start catch-up that runs before a later move
       (`tcw/tracker/sync.py:823-825`), reached by `tcw work tracker sync` on an
       item carrying a `move: start`, `claim: owed` record while the item has
       not finished;
   (c) a ladder hop onto the active rung inside `walk()`
       (`tcw/tracker/sync.py:549-551`, `:557-559`), reached from a binding
       carrying `catch-up: true` (the `legacy_catch_up` helper at
       `tests/test_tracker_sync.py:1357`).
   *Mutation:* criterion 7's mutation. It must turn **all three** red; a path
   that stays green is a path the test does not reach.

10. **`tracker import` refuses clearly with no name set.**
    `tcw work tracker import` on an unassigned, unclaimed ticket with no
    `transitions` key exits non-zero, names `work.tracker.transitions.start` in
    its message, creates no item, applies no transition, and leaves the ticket
    unassigned. The message `does not offer ''` does not appear.
    *Mutation:* remove the row `1d` branch from `_claim_from` — the old message
    returns.
    *Measured on a scratch copy with rule 1 applied and rule 4 not yet applied:*
    `tcw work tracker import: TCWCLAIM-6 is in 'To Do', unassigned, and does not
    offer ''. It offers: 'Start Progress'.`

11. **`inbox accept` refuses the same way**, because it is the same function
    (`tcw/work/cli.py:851` → `_tracker_import`). Same assertions as criterion 10,
    through `tcw work inbox accept`.
    *Mutation:* criterion 10's mutation.

12. **A ticket the account already holds still imports with no name set.**
    `tcw work tracker import` on a ticket already assigned to the running
    account, with no `transitions` key, exits 0 and creates the bound item — row
    `1e`, unchanged.
    *Mutation:* move the row `1d` branch above the row `1e` branch in
    `_claim_from`.

13. **Strict mode does not refuse that import.** With `strict: true`,
    `exclusive-claim-transition` set, and no `transitions` key, criterion 12's
    import is not stopped by `claim_refusal`.
    *Mutation:* make `assess`'s empty-name return carry `exclusivity=NOT_EXCLUSIVE`.

14. **`tracker show` reports the unset key honestly.**
    `tcw work tracker show <ticket>` with no `transitions` key exits 0 and its
    `note:` line says the key names no transition; the sentence
    `work.tracker.transitions.start is '', which this ticket does not offer`
    does not appear. The same holds for `tcw work inbox show`, which prints
    through the same `_print_ticket`.
    *Mutation:* remove the empty-name early return from `claim.assess`.
    *Measured on a scratch copy with rule 1 applied and rule 4 not yet applied:*
    the forbidden sentence is printed verbatim.

15. **The removal advice is uniform across all five moves.** `assess_move` with
    a `named_transition` the ticket does not offer ends its reason with `Fix
    work.tracker.transitions.<move>, or remove it to let TCW find the transition
    itself.` for each of `start`, `submit`, `rework`, `complete` and `discard`.
    *Mutation:* restore `drop = ("" if move == "start" else ", or remove it to
    let TCW find the transition itself")`.

16. **`exclusive-claim-transition` is untouched.** `strict: true` without it is
    still refused by name, and a block that sets it while omitting `transitions`
    entirely validates.
    *Mutation:* delete the `STRICT_NEEDS_EXCLUSIVE_CLAIM` append at
    `tcw/store/base.py:1281-1286`, appended at `:1483`.

17. **Problem attribution still has a test.** The C22 rule — a nested required
    key nobody set is blamed on the node being checked, not on the ancestor that
    supplied the enclosing mapping — is still proved by a test, re-pointed at a
    nested key that is still required, and
    `attribute_tracker_problems`' docstring no longer uses an example the parser
    cannot produce.
    *Mutation:* in `attribute_tracker_problems`, match a problem on the nearest
    enclosing recorded mapping instead of the longest recorded key-path prefix.

### Coverage

Design rules: 1 = both required checks go; 2 = uniform removal advice;
3 = comments corrected; 4 = `import`/`inbox accept` refuse clearly;
5 = `show` needs no edit; 6 = documents and existing tests.

Rule 3 is comment text and rule 5 is the absence of a change; neither has a
behavior a test can hold, so their cells are `n/a` with the line that makes them
so.

| # | rule 1 | rule 2 | rule 3 | rule 4 | rule 5 | rule 6 |
| - | ------ | ------ | ------ | ------ | ------ | ------ |
| 1 | criterion 1 | — | n/a (comment only, `base.py:1263-1266`) | — | — | — |
| 2 | criterion 2 | — | n/a (as above) | — | — | — |
| 3 | criterion 3 | — | n/a (as above) | — | — | — |
| 4 | criterion 4 | — | n/a (as above) | — | — | — |
| 5 | criterion 5 | — | n/a (as above) | — | — | criterion 5 |
| 6 | — | — | — | — | — | — |
| 7 | criterion 7 | — | — | — | — | — |
| 8 | criterion 8 | — | — | — | — | — |
| 9 | criterion 9 (a), (b), (c) | — | — | — | — | — |
| 10 | — | — | — | criterion 10 | — | — |
| 11 | — | — | — | criterion 11 | — | — |
| 12 | — | — | — | criterion 12 | — | — |
| 13 | — | — | — | criterion 13 | — | — |
| 14 | — | — | — | criterion 14 | criterion 14 (`cli.py:2468` prints `result.detail`) | — |
| 15 | — | criterion 15 | n/a (comment deleted with the code, `sync.py:276-279`) | — | — | criterion 15 |
| 16 | criterion 16 | — | — | — | — | — |
| 17 | — | — | n/a (docstring, `base.py:1861`) | — | — | criterion 17 |

Every rule with observable behavior has at least one criterion, and criterion 6
is the "nothing changed" gate that no rule owns: it is what makes the change
non-breaking, and it must stay green under every rule.

## Risks

- **A path that serves a start is missed.** Three are named in the Problem
  section and each has a criterion under 9, with one mutation that must redden
  all three. The known failure mode in this epic is a fix that covered one of two
  paths; naming them and sharing one mutation is the guard.
- **A reader of `config.start_transition` is missed.** Three are named, found by
  grepping the identifier across the tree (`tcw/tracker/intake.py:650`,
  `tcw/work/cli.py:2468`, `tcw/tracker/sync.py:1062`). `tcw/serve/` and `web/src`
  contain no reference. The `tcw/tracker/ownership.py:8-15` mention is a comment
  about why `intake.claim` is not reused and stays true.
- **Row ordering in `_claim_from`.** Putting the new refusal before row `1e`
  would break the documented re-run recovery and the `tracker claim` then
  `import` sequence. Criterion 12 exists only to hold that order.
- **A project that omits the key on an ambiguous workflow gets a worse error
  than before.** Before, `tcw validate` refused the configuration up front;
  after, `tcw work start` moves the item locally and records a conflicting
  delivery (criterion 8). This is the same shape every other move already has
  when its status is ambiguous and no name is set, so it is uniformity rather
  than a new failure — but it is a real downgrade for that one project, and the
  guide should say plainly that naming the transition is still the right answer
  on a workflow with two routes.
- **Nothing in the wild breaks.** Every existing tracker-backed configuration
  sets the key, because it was required; the key keeps working. The only
  configurations whose meaning changes are ones that could not exist before.

## Notes

- The measurements quoted above were taken by applying rule 1 to a scratch copy
  of the working tree, running probes, and restoring the tree. The tree is
  unmodified as this spec is committed.
- The request's file:line citations were checked one by one against the tree at
  commit `ec36b392` and all four resolve exactly to what it claims:
  `tcw/store/base.py:1263-1266`, `:1503-1506`, `:1507-1508`, `:1693-1695`, and
  `tcw/tracker/sync.py:276-281`.
- What the request got wrong: it names one required check where there are two
  (see "Two required checks, not one"), and it does not mention the three
  readers of `config.start_transition` that have no status to derive from (rules
  4 and 5). Neither contradicts the request's scope — "drop the requirement, and
  nothing more" — because both are what dropping the requirement entails without
  shipping a new defect.
