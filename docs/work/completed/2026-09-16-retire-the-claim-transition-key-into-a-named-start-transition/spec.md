# Spec: Retire the claim transition key into a named start transition

## Capability changes

**None.** No ledger entry is added, removed or reworded by this item.

The epic lists four capability deltas
(`docs/work/active/2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs/spec.md`,
"Capability changes"), and every one of them belongs to a sibling: the new
`work/hold-a-tracker-ticket` is C1's, the reworded
`work/manage-external-tracker-intake` and `work/require-tracker-backed-work` are
C4's (they describe the claim applying a transition, which stays true until C4),
and `work/synchronize-external-tracker-work` is C2's. The epic's plan agrees:
its capability table names C1, C2 and C4 for those entries and never C3
(`plan.md:127`, `:130` name C3 only for documentation).

Two ledger entries were checked for wording this item falsifies and neither is:
`work/manage-external-tracker-intake` says "the configured claim transition"
without naming the key, and `work/inherit-tracker-settings-from-parent-nodes`
(`cap-69ba01`) describes merging by key without naming any. Renaming a key
changes how a setting is spelled, not what a user can do.

## Problem

`work.tracker.transitions` has five keys' worth of meaning and two kinds of key.

Four of them — `submit`, `rework`, `complete`, `discard` — arrived with pull
request #45. Each names the tracker transition its lifecycle move should apply;
each is optional, because a move with no name falls back to deriving the
transition from the target status; each is parsed by one loop over
`TRACKER_MOVE_TRANSITION_KEYS` (`tcw/store/base.py:1382`); each is read by one
function, `transition_name` (`tcw/store/base.py:1405`).

The fifth, `claim`, predates them and is none of those things. It is required
(`tcw/store/base.py:1241`, through `nested_str`, which reports
`work.tracker.transitions.claim: required` when it is absent). It is parsed by
its own call, not the loop. It is stored on its own field,
`TrackerConfig.claim_transition` (`tcw/store/base.py:1079`). And it is read
directly by name at four places — `tcw/tracker/intake.py:329`,
`tcw/tracker/sync.py:743` and `:747`, and `tcw/work/cli.py:2224` — none of them
through `transition_name`.

The code says out loud that the fifth key is why there is no `start` key:

> `# start` is absent deliberately: it is the claim, and `transitions.claim`
> names it. (`tcw/store/base.py:1128`)

and again, in the inverse, above `MOVE_ONTO`:

> `# active` is the claim's move, not `rework`: reaching it from nothing is
> claiming, and the claim has its own transition name. (`tcw/tracker/sync.py:53`)

and again to users:

> There is no `start` key: `transitions.claim` already names that one.
> (`docs/guide/jira.md:566`)

The epic removes the premise. Once claiming a ticket is its own act that applies
no transition, the transition formerly called "the claim's" is not the claim's:
it is the one the `start` move applies, and every reason it is spelled and read
differently from its four siblings has gone.

One consequence is visible in the code as a contradiction, though not as a live
defect. The catch-up walk asks for the start hop's named transition —
`transition_name(config.move_transitions, hop, ...)` at `tcw/tracker/sync.py:402`
and `:410`, where `hop` is `MOVE_ONTO["active"]`, which is the string `"start"` —
and can only ever get `""` back, because `start` can never be in
`move_transitions`. So the walk asks a question the configuration is built to be
unable to answer.

**Amended twice during implementation, and the first amendment was also wrong.**

The first version of this section said the walk derives the hop from the status
while a start applies the configured name, and the Design, Sweep and Risks
sections called that a sibling defect fixed here. That was not grounded.

The first amendment replaced it with "the walk's start hop is not reachable, so
this change alters no behaviour at all", on the strength of a probe in
`transition_name` that fired zero times across four tracker test modules. **The
claim about the walk is right; the conclusion drawn from it was not.** Zero hits
meant no test exercises the call, not that nothing reaches it — and the probe
was in `transition_name`, which has a *third* call site the sweep never
examined: `tcw/tracker/sync.py`, at the end of `deliver`, where the move served
is `move = move or (record["move"] if record else None)`. A recorded move
outlives the item's status, so `start` arrives there for an item that is already
past it. Putting `start` into `move_transitions` therefore **did** change
behaviour, and the change stranded work. Design section 5 states the defect and
the fix; `outcome.md` records how it was found.

## Goals

1. `work.tracker.transitions.start` names the transition the `start` move
   applies, and is spelled, parsed and read exactly as `submit`, `rework`,
   `complete` and `discard` are.
2. `work.tracker.transitions.claim` is not accepted.
3. A configuration file still carrying `transitions.claim` is told what to write
   instead, by name, in the file it was written in — not told that a key is
   unknown. Every tracker-backed project in existence carries the old key,
   because it is required today, so this is the ordinary case and not the edge.
4. Nothing about what a start does to a ticket changes.

## Non-goals

- **Making `transitions.start` optional.** See Design decision 2; it stays
  required, as `claim` was, and C4 is what makes it optional.
- **Accepting `transitions.claim` as an alias.** Criterion 10 of the epic asks
  for it to be reported, and this repository already has a settled way to retire
  a spelling: `_stage_removed_form` (`tcw/work/cli.py:1516`) registers the old
  form only so it can name the new one, and refuses to act — "a migration nobody
  is forced to make is one nobody makes".
- **Changing what a claim does.** `intake.claim` (`tcw/tracker/intake.py:310`)
  still transitions and then assigns, on every start, reading the same string
  from a differently-named field. That is C4's to change.
- **The `claim: owed | done` sync record** (`tcw/store/base.py:423`,
  `tcw/work/projection.py:125`, `tcw/work/cli.py:216`). It is a different
  `claim`, in `tracker.yaml` rather than in `tcw-config.yaml`, and it is C2's,
  which is in flight in another worktree.
- **`work.tracker.exclusive-claim-transition`.** C1 added it, it is a top-level
  key rather than one under `transitions`, and it is genuinely the claim's. It
  keeps its name.

## Design

### 1. `start` becomes an ordinary move transition key

`TRACKER_TRANSITION_KEYS` (`tcw/store/base.py:1127`) drops `claim` and gains
`start`. `TRACKER_MOVE_TRANSITION_KEYS` (`:1128`) gains `"start"`, and the
comment saying `start` is deliberately absent goes with the reason for it.

`_parse_tracker_transitions` (`:1366`) then parses all five keys in its one loop,
with no special case, and `move_transitions["start"]` holds the name. The
`discard`-only mapping branch is untouched: `start` takes a plain name, as
`submit`, `rework` and `complete` do.

It also makes the catch-up walk's start hop answerable:
`transition_name(config.move_transitions, "start", ...)` at
`tcw/tracker/sync.py:402` and `:410` returns the configured name instead of
`""`. No current path reaches *those two* call sites with a `start` move, so
they change nothing today; they are worth correcting because leaving `start` out
is what made the question unanswerable, and a later change reaching the hop
would otherwise get the wrong transition silently.

The third call site is a different matter and is Design section 5.

### 2. `transitions.start` stays required

Uniform spelling and uniform reading, not uniform optionality.

The four keys from pull request #45 are optional because a move with no name has
a working fallback: derive the transition from the target status. The start move
has no such fallback today, because it does not go through `assess_move` at all
— `deliver` calls `claim(client, ticket)` (`tcw/tracker/sync.py:522`), which
reads `client.config.claim_transition` and applies it (`tcw/tracker/intake.py:329`).
A start with no name would reach `assess` (`tcw/tracker/claim.py:72`) with the
empty string, match no transition, and be refused.

So making the key optional in this item would ship a configuration that parses
and a start that cannot run — a hole C3 opens and C4 closes. Requiring it keeps
the migration a one-word rename in every file that has one, which is what risk 4
of the epic asks for, and leaves optionality to the item that can honour it.

The required check moves from `nested_str` to a plain membership test, so the
loop reports a wrong *value* the way it does for the other four and the
membership test reports an absent *key*:

```python
if "start" not in transitions:
    problems.append("work.tracker.transitions.start: required")
```

One consequence is deliberate: `transitions: {start: null}` is now reported as
"expected a non-empty tracker transition name, got NoneType" rather than
"required". That is the message its four siblings already give for a null, and
the value is wrong rather than missing, so it is the truer of the two.

### 3. `TrackerConfig.claim_transition` becomes `start_transition`

Same string, same dataclass, new name, populated from `move_transitions["start"]`
at the end of the parse. The four readers — `tcw/tracker/intake.py:329`,
`tcw/tracker/sync.py:743` and `:747`, `tcw/work/cli.py:2224` — change by name
only.

The field is kept rather than replaced by a `move_transitions` lookup at each
reader, because those three call sites want *the start move's transition*
specifically and none of them is walking the ladder; `transition_name` is for
callers that have a move in a variable. Holding the same string twice cannot
drift: both are written once, from one value, in `parse_tracker_config`.

`exclusive_claim_transition` keeps its name, and its docstring's cross-reference
("Not `transitions.claim`, which is the transition a *start* applies") is
updated to name `transitions.start` — a line that reads oddly today precisely
because the key was misnamed.

### 4. The old key is reported by name, with its replacement

Unknown keys under `transitions` are reported by the shared `nested` helper
(`tcw/store/base.py:1194-1198`), which says `unknown key` for anything outside
the allowed set. A retired key gets a sentence instead:

```python
# A key that used to exist, with what replaced it, so a config written for an
# older tcw is told what to change rather than only that a key is unknown.
TRACKER_RENAMED_KEYS = {
    ("transitions", "claim"):
        "renamed to work.tracker.transitions.start, the transition the start "
        "move applies, alongside submit, rework, complete and discard",
}
```

and `nested`'s loop looks the key path up before falling back to `unknown key`.
Reporting it there rather than after the fact is what keeps it to one problem:
the generic message would otherwise be appended as well.

The parse still fails closed, so such a config yields `None` and no tracker, as
every other tracker problem does. The user sees both problems together —
`transitions.claim: renamed to …` and `transitions.start: required` — which
between them say exactly what to edit.

`attribute_tracker_problems` (`tcw/store/base.py:1520`) needs no change and does
the rest: it matches a problem to the file that supplied its key path, so in a
workspace where a parent node sets `transitions.claim` the message names the
parent's file, which is the file to edit. Its own docstring example
(`transitions.claim: required`) is reworded to the key that still exists.

### 5. Documentation, skills and this repository's own configuration

`docs/guide/jira.md` (the `transitions` table at `:72`, the misspelling note at
`:101`, the claim sequence at `:234`, the cross-reference at `:365`, the
inheritance examples at `:49`, `:129` and `:556`, and the "there is no `start`
key" sentence at `:566`), `README.md:544`,
`skills/configure/references/tracker.md` (`:5`, `:22`, `:33`, `:50`, `:62`,
`:78`, `:175`), `skills/work/references/commands.md:291`, and this repository's
own `tcw-config.yaml:13`, which carries `claim: Start` and would otherwise stop
validating the moment the code lands.

`docs/release-notes/v2.1.0.md:20`, `docs/changelogs/v2.1.0.md:82`,
`docs/changelogs/v2.1.2.md:9` and `:121` are **not** edited: a changelog records
what shipped in a past version, and `transitions.claim` is what shipped then.

### 5. A recorded move outlives the item's status, and the name must not

Putting `start` into `move_transitions` widened a defect that was already there
for the other four keys, and made it universal.

`deliver` serves the recorded move when its caller names none —
`move = move or (record["move"] if record else None)`, `tcw/tracker/sync.py` —
but `target` comes from the item's *current* status, not from that move. The two
disagree whenever a record outlives the status it was written under. The
transition configured for a move leads where that move lands, so naming it for a
target it does not lead to can only refuse, and the item is stranded with no way
forward.

The reachable route, confirmed end to end:

1. `tcw work start` on a bound item. The claim transition and the assignment
   both apply and the confirming read then fails, so `intake.claim` returns row
   `3-read` and `deliver` records `state: pending, move: start` while the ticket
   really is in the active status and really is ours.
2. The item reaches `review` through something that delivers nothing — the web
   app, `tcw serve`, or a command interrupted between its commit and its tracker
   call. Nothing rewrites the record, so it still says `start`.
3. `tcw work tracker sync` arrives with `move` saying `start` and `target`
   saying the review status, and refuses.

**The fix is one guard at the shared site**: use the configured name only when
the move's own mapped status is the one being moved to.

```python
named = (transition_name(config.move_transitions, move, item.resolution)
         if move and MOVE_STATUS.get(move) == local else "")
```

Every move a caller passes agrees with `local` by construction — `submit` with
`review`, `complete` with `completed`, and so on — so this narrows nothing any
caller asked for. What it catches is a stale record, where deriving the
transition from the target status is the only honest answer, and is what the
code did before `start` joined the mapping.

It is placed at the one site all of these callers route through rather than at
the `start` case that reported it, because the defect is not `start`-shaped: a
record naming `complete` under an item back in `review` was wrong the same way
before this item existed, and reached the same dead end wherever a project had
named `transitions.complete`. Both are covered by one parametrized test.

**The refusal's advice also had to change.** It offered "or remove it to let TCW
find the transition itself", which is generic over the move and was written for
the four optional keys. `transitions.start` is required, so that advice tells a
user to do something `tcw validate` then refuses. It is now offered only for a
key that can actually be removed.

**What this does not fix** is the deeper question of whether `deliver` should
serve a stale `start` at all when the work in front of it is really a `submit`.
The record's `move` is a statement about what was last attempted, and treating
it as a statement about what to do now is the coupling C4 is rewriting. This
item makes the stale case behave as it did before the rename — derived from the
status, which works — rather than redesigning the record. The narrower change is
the right one here: it restores a working path without pre-empting C4's design,
and it leaves nothing stranded in the meantime.

### Abstraction litmus test

**Passes.** The guard added in Design section 5 is pure logic over two local
strings — the move being served and the item's status — compared through
`MOVE_STATUS`, a constant mapping in the tracker module. No filesystem, no
adapter, nothing a non-filesystem store would do differently; it is a decision
about which of two values already in hand to use, made before any store or
tracker call. It belongs exactly where it is, at the point that chooses the
transition, because that is the only place that holds both values.

The rest barely engages. Everything else here is node configuration, parsed by
a pure function that touches no filesystem, reads no environment variable and
never raises (`parse_tracker_config`'s own docstring, `tcw/store/base.py:1135`).
A non-filesystem store reads the same mapping from wherever it keeps node
settings and gets the same `TrackerConfig`. No operation is added, removed or
changed; one key in a mapping is spelled differently.

### Harness compatibility

**Unaffected.** The rename lands in `parse_tracker_config` and is reported by
`tcw validate`, which behave identically under Claude and Codex. The only
harness-adjacent files touched are `skills/configure/references/tracker.md` and
`skills/work/references/commands.md`, which are plain reference documents both
harnesses read.

### Sweep

Repo-wide, not narrowed. `transitions.claim`, `claim_transition` and a `claim:`
key nested under `transitions:` were searched across every tracked file. The
results are the list in Design section 5 plus the code in sections 1–4, the
tests named under Risks, and the changelog entries deliberately left alone.

The sweep was **not thorough enough, and this is the item's main lesson.** It
found the two catch-up-walk call sites of `transition_name` and missed the third
— the one at the end of `deliver`, which serves a *recorded* move rather than
the caller's. Grepping for `transitions.claim` and `claim_transition` could not
have found it, because that site never names the key: it reads
`config.move_transitions` through `transition_name`, so the sweep had to be over
*the readers of the dictionary the key now lands in*, not over the key's own
spelling. Adding a key to a shared mapping means auditing every reader of that
mapping. Design section 5 is the consequence.

## Acceptance criteria

1. A `work.tracker` block whose `transitions` is `{start: Start Progress}`
   parses with no problems, and the resulting config has
   `start_transition == "Start Progress"` and
   `move_transitions["start"] == "Start Progress"`.
2. A block whose `transitions` is `{claim: Start Progress}` does not parse. Its
   problems include one for `work.tracker.transitions.claim` naming
   `work.tracker.transitions.start` as the replacement, and one for
   `work.tracker.transitions.start: required`. No problem for
   `work.tracker.transitions.claim` says `unknown key`, and there is exactly one
   problem about that key.
3. A block whose `transitions` omits `start` entirely reports
   `work.tracker.transitions.start: required`.
4. A block whose `transitions.start` is `null`, an empty string, or a non-string
   is reported with the same wording its four siblings get for the same value.
5. In a workspace where a parent node sets `transitions: {claim: ...}` and a
   child inherits it, `tcw validate` in the child prefixes the renamed-key
   problem with the parent's label, so the file to edit is named.
6. `transition_name(config.move_transitions, "start", None)` returns the
   configured name — the public reader every other move goes through finds the
   start move's transition too. And `TrackerConfig` has no `claim_transition`
   attribute, and no module reads one.
   `work.tracker.exclusive-claim-transition` and
   `TrackerConfig.exclusive_claim_transition` are unchanged.
7. This repository's own `tcw-config.yaml` reads `transitions: {start: Start}`
   and `tcw validate` reports no tracker problem.
8. No file under `docs/guide/`, `skills/`, or `README.md` mentions
   `transitions.claim` or shows a `claim:` key under a `transitions:` block.
   Files under `docs/changelogs/` and `docs/release-notes/` for already-released
   versions still do.
9. An item whose binding records `move: start` while the item itself has
   reached `review` is not stranded: `sync` moves the ticket to the review
   status rather than refusing. The same holds for a record naming `complete`
   under an item at `review` where `transitions.complete` is set.
10. A refusal naming `work.tracker.transitions.start` does not advise removing
    it; one naming an optional key still does.
11. The whole test suite passes.

## Risks

1. **Adding `start` to `move_transitions` changes what `deliver` does with a
   stale record, and the first version of this item shipped that as a
   regression.** Stated wrongly twice before it was stated right: first as a
   defect in the catch-up walk, then as no behaviour change at all. Both were
   drawn from an incomplete sweep. Design section 5 has the route, the guard and
   the reasoning, and the parametrized regression test is
   `test_a_stale_record_does_not_strand_an_item_that_has_moved_on`.
   The guard is deliberately narrow, so the risk that remains is the one it does
   not address: `deliver` serving a stale move at all. That is C4's.
2. **Nine test modules construct a `TrackerConfig` or assert on the key.**
   `tests/test_tracker_claim.py:31`, `tests/test_tracker_client.py:35` and
   `tests/test_tracker_ownership.py:33` pass `claim_transition=` to the
   constructor; `tests/test_tracker_config.py:45`, `:88`, `:91`, `:200`, `:294`,
   `:297` and `:300` assert on the field and the key name;
   `tests/test_tracker_inheritance.py:229` and `:523` assert on the exact
   problem string `work.tracker.transitions.claim: required`. Each has to move
   to the new name, and the two inheritance assertions are the ones that must
   not simply be reworded away — they are the evidence for criterion 5, and one
   of them becomes the test for the renamed-key message.
3. **`tcw/store/base.py` is edited by C2 at the same time**, around
   `SYNC_FIELDS` (`:423`). This item's edits are at `:1079`, `:1127-1128`,
   `:1194-1198`, `:1241`, `:1271`, `:1366-1402` and `:1525` — more than a
   thousand lines away, in a different function, with no shared region. Nothing
   here reformats or reorders anything it does not change.
4. **`skills/configure/references/tracker.md` is edited by C1 too**, per the
   epic's documentation table (`plan.md:130`): C1 adds
   `exclusive-claim-transition` to the same document C3 renames a key in. C1 has
   landed, so its text is already in the tree and this item edits on top of it
   rather than beside it.
5. **A user upgrading gets a hard refusal, not a warning.** Their tracker stops
   working until they edit one word, and every tracker-backed node has the old
   key. That is what epic criterion 10 asks for and what this repository does
   with retired spellings, but it is the user-visible cost and it belongs in the
   release notes, not only in a validation message.

## Notes

- The catch-up walk consistency described at the end of the Problem section was
  found by reading `MOVE_ONTO` while grounding the claim that `transitions.claim`
  is read outside `transition_name`. It is stated as fact because
  `MOVE_ONTO["active"] == "start"` (`tcw/tracker/sync.py:55`) and `"start"` was
  absent from `TRACKER_MOVE_TRANSITION_KEYS` (`tcw/store/base.py:1128`), so
  `transition_name` could only return `""` for it.
- No acceptance criterion here is runnable against the tree as it stands: every
  one of them describes the state after the rename. The two that describe
  today's behavior in order to contrast it — the wording in criterion 4 and the
  attribution in criterion 5 — were checked against the current code by reading
  `_parse_tracker_transitions` and `attribute_tracker_problems`, and by the
  existing assertions at `tests/test_tracker_inheritance.py:229` and `:523`.
