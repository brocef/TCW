# Jira claim experiment — plan task 1

**Date:** 2026-09-12
**Instance:** `https://proposit.atlassian.net` (Jira Cloud), authenticated as
`admin@proposit.app`, account id `712020:d256da6b-c47b-4fe4-a9d7-fa24ef91ef2a`.
**Fixture:** project `TCWTEST` ("TCW Bridge Test"), created for this experiment
from the `gh-simplified-scrum-classic` template. Issues `TCWTEST-1` and
`TCWTEST-2`.

## Result: the claim design in the request does not work

**The static property fails.** The request's single-winner guarantee assumes a
configured ready-to-in-progress transition acts as a mutual-exclusion boundary.
On Jira's default simplified workflow it does not: the transition is a **global
self-transition available from every state, including the one it lands in**, so
applying it twice succeeds and a loser that simply retries also "claims".

This invalidates the claim boundary as specified, not the initiative. What it
changes is that **TCW cannot assume the property — it has to verify it.**

## Observations, verbatim

### 1. Transitions offered are identical from every state

`GET /rest/api/3/issue/TCWTEST-1/transitions`, with the issue in `To Do`:

```
id=11  name=To Do        -> To Do
id=21  name=In Progress  -> In Progress
id=31  name=Done         -> Done
```

The same three ids are offered from `In Progress` and from `Done`. Confirmed
against `TCWTEST-2` after moving it to `Done`: offered ids `['11', '21', '31']`.

### 2. The claim transition succeeds twice

`POST /rest/api/3/issue/TCWTEST-1/transitions` with `{"transition":{"id":"21"}}`:

| attempt | from status | response |
| ------- | ----------- | -------- |
| first | `To Do` | `HTTP 204` |
| second | `In Progress` | `HTTP 204` |

Status after both: `In Progress`. No conflict, no error, no distinguishing
signal.

### 3. Two simultaneous claims both succeed

Two concurrent `POST …/transitions` with id `21` against `TCWTEST-2`, both
launched in parallel:

```
racer 1: HTTP 204
racer 2: HTTP 204
```

Jira may well serialize them internally, as the Atlassian change notice the
request cites describes. It does not matter here: because the transition is valid
from the destination state, the second request is a legitimate no-op rather than a
loser, so serialization yields no usable signal.

### 4. An unavailable transition is a 400 with a specific message

`{"transition":{"id":"999"}}`:

```json
{"errorMessages":["Transition id '999' is not valid for this issue."],"errors":{}}
HTTP 400
```

This is the response a loser **would** receive in a workflow where the claim
transition is not available from the destination state. Note the consequence for
C2: that response is indistinguishable by status code and body shape from *the
operator having configured a transition id that does not apply at all*. So the
bridge cannot read "already claimed" off the error. It must re-read the issue's
status and assignee and decide from those.

## What this means for the design

The mutual-exclusion property is a property of **the user's workflow
configuration**, not of Jira. A workflow whose claim transition is reachable only
from the ready state does provide it; the default simplified workflow does not.
Three consequences, all of which belong to C1 and C2 rather than being deferred:

1. **Verify the property instead of assuming it.** At configuration time, read the
   transitions available from the state the claim lands in and refuse strict mode
   when the configured claim transition is among them. This is the extension of
   acceptance criterion 9 that the review proposed, and it is now empirically
   justified rather than speculative. It is a static check against the project's
   workflow, so it is cheap and it fails closed.
2. **Do not detect contention from the transition's response.** Detect it by
   reading the issue: a claim succeeds only if the issue was in the configured
   ready state and unassigned or assigned to the authenticated identity
   immediately before, and is assigned to that identity immediately after. A
   claim is a read-modify-verify sequence, not a single write.
3. **Say plainly that the guarantee is conditional.** With a conforming workflow
   TCW can promise a single winner. With a non-conforming one it cannot, and the
   honest behavior is to refuse strict mode rather than to offer a guarantee it
   cannot keep. Goal 1 has to be restated in those terms.

## What was not tested

- **A conforming workflow.** Editing a company-managed workflow to remove the
  global transitions was not attempted; the 400 in observation 4 is the closest
  available evidence for what the loser sees. Before C2 freezes, build a
  conforming workflow in `TCWTEST` and rerun observations 2 and 3 against it.
- **Team-managed (next-gen) projects**, whose workflow model differs again.
- **Any behavior under a real second user.** Both racers authenticated as the same
  account, which is the right test for transition availability and the wrong one
  for assignment contention.

---

# Part 2 — a conforming workflow, built and measured

**Date:** 2026-09-12, same session. **Fixture:** project `TCWCLAIM` ("TCW Bridge
Claim Fixture"), project id `10004`, created empty so a workflow scheme could be
assigned to it. Jira refuses to assign a scheme to a project that already holds
issues ("Only empty projects can have workflow schemes assigned"), which is why
this is a second project rather than a reconfiguration of `TCWTEST`.

**The two fixtures are now a matched pair, and both are needed:**

| project | workflow | claim transition reachable from its destination? |
| ------- | -------- | ----------------------------------------------- |
| `TCWTEST` | default simplified, global transitions | **yes** — cannot exclude |
| `TCWCLAIM` | `TCW Bridge Claim Workflow`, directed only | **no** — excludes correctly |

The conforming workflow was built with `POST /rest/api/3/workflows/create`:
statuses `To Do` (10012), `In Progress` (3), `Done` (10009); transitions `Create`
(INITIAL → To Do), `Start Progress` (id 21, DIRECTED, To Do → In Progress),
`Finish` (id 31, DIRECTED, In Progress → Done). No global transitions. Existing
statuses are referenced by supplying both an invented `statusReference` UUID and
the real status `id`; supplying the status id alone is rejected as "not a UUID",
and supplying the name alone is rejected as already in use.

## Result: the claim works, and it is deterministic

### The static property holds

`TCWCLAIM-1`. Transitions offered in `To Do`: **only** id 21 `Start Progress`.
After applying it, status is `In Progress` and transitions offered are **only** id
31 `Finish`. The claim transition is gone. Applying id 21 a second time returns
`HTTP 400`.

### Exactly one winner, every time

Concurrent applications of the claim transition to one freshly created issue:

| issue | racers | winners | losers |
| ----- | ------ | ------- | ------ |
| `TCWCLAIM-2` | 3 | 1 | 2 |
| `TCWCLAIM-3` | 4 | 1 | 3 |
| `TCWCLAIM-4` | 4 | 1 | 3 |
| `TCWCLAIM-5` | 4 | 1 | 3 |

Four trials, no exceptions. The winner gets `HTTP 204`, every loser gets
`HTTP 400`, and the final status is `In Progress` once. **Goal 1 is achievable on
a conforming workflow**, and the epic's conditional restatement of it is the right
shape: TCW can promise a single winner when the workflow can express exclusion,
and must refuse strict mode when it cannot.

## The finding that changes C2's implementation

**Three different error bodies were observed for what is logically the same
condition, all of them `HTTP 400`:**

| condition | body |
| --------- | ---- |
| transition id does not exist at all | `Transition id '999' is not valid for this issue.` |
| sequential second attempt, same caller | `Can't move (TCWCLAIM-1). You might not have permission, or the work item is missing required information. …` |
| concurrent race loser | `Action 21 is invalid` |

So the response tells you a transition did not apply, and nothing reliable about
*why*. The second message is actively misleading: it suggests a permission problem
or a missing field when the real cause is that someone else already claimed the
ticket. Two consequences, both binding on C2:

1. **Never parse these messages, and never surface one to the user as the
   explanation.** The bridge decides what happened by re-reading the issue's
   status and assignee, not from the error body.
2. **A `400` on the claim transition is not by itself "already claimed".** It is
   "the claim did not apply". Distinguishing already-claimed from misconfigured
   requires the read: if the issue is in the claimed state and assigned to someone
   else, it was claimed; if it is still in the ready state, the configuration is
   wrong.

That is the read-modify-verify sequence the spec now specifies, and this is the
evidence for why a single write with error interpretation would have been wrong.

## What is now settled, and what is still open

Settled: the claim mechanism works; the workflow-shape check C1 performs is both
necessary and sufficient to predict it; the guarantee is conditional and TCW must
say so.

Still open, and not blocking C2: behavior with two genuinely different Jira
accounts, since every request above authenticated as the same user. That tests
assignment contention rather than transition availability, and transition
availability is what the claim rests on.
