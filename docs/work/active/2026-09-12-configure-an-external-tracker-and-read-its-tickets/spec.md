# Spec — Configure an external tracker and read its tickets

**Revised 2026-09-12 after a three-way review.** The largest change: the
authoritative workflow read is gone from this item. It needed a project
identifier the configuration does not carry, a possibly administrator-only
endpoint, a warning tier `tcw validate` does not have, and it would have put
blocking network calls inside a command this repository binds as a `pre` hook on
`complete`. What replaces it costs one field on a call this item already makes.
See `## Notes`.

## Capability changes

One new capability, seeded `Missing` at the epic's planning and flipped by this
item's completion:

- `work/inspect-external-tracker-work` — "Inspect external tracker work"
  (`cap-1b0a04`), already carrying `Feature=external-work-tracker`,
  `Subject=work-item, cli, reference`, and `Planning doc` pointing here.

No existing capability changes. `work/manage-the-work-inbox` in particular does
not: the filesystem inbox and an external tracker are distinct intake sources, and
this item adds no intake at all.

## Problem

A project cannot tell TCW that it uses a tracker, and TCW cannot read one.

1. **There is no configuration surface for a tracker.** The node sentinel is read
   through `FsWorkStore._config` (`tcw/store/fs.py:5036`) and narrowed to the
   `work:` mapping by `_work_config` (`tcw/store/fs.py:5051`). The keys it
   recognizes are `tags`, `lifecycle`, `documentation`, `repository`, `retain` and
   `path`. Nothing names a tracker.
2. **There is no HTTP client.** The package serves HTTP — `tcw/serve/__init__.py:15`
   imports `BaseHTTPRequestHandler` — but nothing in it makes an outbound request.
   The only `urllib` imports are `urllib.parse` for unquoting references
   (`tcw/refs.py:27`, `tcw/serve/__init__.py:18`). No client, no credential
   handling, no error taxonomy to extend.
3. **Whether a tracker's workflow can support a claim is unknowable today.** The
   epic's experiment (`jira-claim-experiment.md`) measured both cases live. Where a
   workflow's transitions are global, the claim transition stays available after it
   is applied, so applying it twice succeeds and concurrent claims all succeed.
   Where they are directed, it disappears, and four concurrent-race trials produced
   exactly one winner each.

## Goals

1. A project declares its tracker in `tcw-config.yaml`, with credentials named
   rather than embedded.
2. A developer sees the tickets the configured query selects, and one ticket in
   detail, from the terminal.
3. When TCW can see that a ticket's workflow will not exclude a second claimant, it
   says so, from information it already has.
4. Failures are distinguishable by cause, and each cause produces a distinct,
   actionable message.
5. A project with no tracker configured is unaffected in every observable way, and
   **a project with a tracker configured gains no new network dependency in any
   existing command**.

## Non-goals

- **Claiming, importing, or binding.** No `tracker.yaml`, no
  `import`/`link`/`unlink`. C2.
- **The authoritative workflow-shape verdict.** Reading a project's workflow
  definition to decide, before any ticket exists, whether the workflow can exclude
  a second claimant. Moved to C4, where the strict mode that consumes it lives.
  See `## Notes`.
- **The `strict` key.** Not accepted here, not parsed here. C4 introduces it
  together with the gates that honour it. A configuration setting it on a build of
  this item is reported as an unknown key, which is the intended behavior.
- Outbound synchronization, `sync`, drift (C3). Anything in `tcw work show --json`,
  `tcw work list`'s columns, or the web app (C5).
- A provider abstraction, a new runtime dependency, Jira Data Center, OAuth, token
  persistence, any tracker but Jira Cloud.
- **Any write to the tracker.** Every operation here is a read.
- **Any network call from `tcw validate` or from any lifecycle transition.** This is
  a hard non-goal, not a preference; see Design part 4.

## Design

### 1. Configuration

A `work.tracker` mapping in the node sentinel, parsed by a pure function
`parse_tracker_config(raw) -> (TrackerConfig | None, list[str])` in
`tcw/store/base.py` beside `parse_documentation_entries`
(`tcw/store/base.py:1590`).

```yaml
work:
    tracker:
        provider: jira-cloud # the only accepted value
        base-url: https://example.atlassian.net
        candidate-query: assignee = currentUser() AND status = "To Do"
        credentials:
            email-env: TCW_JIRA_EMAIL
            token-env: TCW_JIRA_API_TOKEN
        timeout-seconds: 15 # optional, default 15
        transitions:
            claim: Start Progress
```

**Every key above except `timeout-seconds` is required, unconditionally.** An
earlier draft made key presence conditional on `strict: true`. That was wrong: a
configuration missing `base-url` is equally broken either way, and goal 1 is "a
project declares its tracker", not "a project in strict mode declares its
tracker".

Unknown keys under `work.tracker` are reported as problems, following
`parse_documentation_entries`, which reports unknown keys and keeps what parses
(`tcw/store/base.py:1590`). This is **intended to be forward-incompatible**: C3
adds terminal and submit/rework mappings under `transitions`, and C4 adds
`strict`, so a configuration written for a later build reports problems on this
one. That is the honest behavior — silently ignoring a key a user set means
silently not doing what they asked.

**The store surface follows `retention_problems` / `retention_conflicts`**
(`tcw/store/base.py:2102` and `2111`), not `documentation()`. The distinction
matters and an earlier draft got it wrong: `documentation()` is `@abstractmethod`
(`tcw/store/base.py:2266`) and `documentation_problems()` is not on the base class
at all, only on the filesystem adapter. The retention pair is concrete on
`WorkStore` with empty defaults, and `tcw validate` reads it **directly**
(`tcw/validate.py:267`) rather than through `check()`. So:

- `WorkStore.tracker_config() -> TrackerConfig | None`, concrete, default `None`.
- `WorkStore.tracker_problems() -> list[str]`, concrete, default `[]`, read
  directly by `tcw validate` beside the retention lines.

No existing adapter changes and none breaks, because both have defaults.

**`tracker_config()` fails closed.** On any problem it returns `None`, following
`parse_repository_declaration` and its reasoning that "a half-read repository is
one nobody declared" (`tcw/store/fs.py:5296`). The reasoning is stronger here: a
config whose `token-env` is mistyped but whose `base-url` parses would otherwise
send an unauthenticated request to a real site.

**Credentials are read from the environment at the point of use**, never stored on
`TrackerConfig`, which holds only the variable names. A `TrackerConfig` that never
reaches a request never touches a secret.

### 2. The Jira client

A new module `tcw/tracker/jira.py`, with `tcw/tracker/__init__.py`. Not under
`tcw/store/`: a tracker is not a store, and the epic's litmus table keeps tracker
operations outside `WorkStore` so no adapter owes a tracker implementation. **This
module is the intended home for any future Jira HTTP work**, including a
`JiraWorkStore` should `2026-06-19-remote-adapter-jiraworkstore` ever be built, so
that a second Jira client never gets written.

Standard library only: `urllib.request`, with a basic-authentication header built
by hand.

**Every operation goes through one private seam:**

```python
_request(method: str, path: str, body: dict | None = None) -> tuple[int, dict, bytes]
```

That is the single function a test replaces, and naming it is a design decision
rather than an implementation detail, because four acceptance criteria depend on
substituting it. Above it, four public operations, which is all this item needs:

1. `myself()` — who the credentials authenticate as.
2. `search(jql, limit)` — the configured candidate query. Default `limit` 50; when
   more rows match, print what was returned and say the result was truncated and
   by what flag to widen it. Never silently truncate.
3. `issue(key)` — one ticket.
4. `transitions(key)` — the transitions available for that issue right now.

`project_statuses` is gone; an earlier draft listed it as "used by the workflow
check" and the check no longer exists here. The REST paths are pinned in the
plan, not here, because Atlassian is migrating search to a token-paginated
endpoint and the plan is where a current-at-the-time path belongs.

**Every request passes an explicit `timeout`,** taken from the config. It is a
parameter of `_request`, so there is exactly one place it can be forgotten and a
test can assert it is set. `urllib.request.urlopen` otherwise falls back to the
global socket default, which is unset, making the omission an indefinite hang.

### 3. The error taxonomy

One base `TrackerError` and six subclasses. All six are reachable from this item's
own code, which is the justification — not what later children need:

| subclass | raised for | reachable here via |
| -------- | ---------- | ------------------ |
| `TrackerAuthError` | 401 | a wrong or expired token |
| `TrackerPermissionError` | 403 | a query selecting a project the user cannot browse |
| `TrackerNotFound` | 404 | `tracker show` on a key that does not exist |
| `TrackerRequestInvalid` | 400 | a malformed `candidate-query` |
| `TrackerRateLimited` | 429, carrying `Retry-After` | a tight loop of `list` calls |
| `TrackerUnavailable` | 5xx, connection failure, timeout | criterion 10 |

`TrackerRequestInvalid` is deliberately **not** named "conflict" or "already
claimed". The experiment recorded three different `400` bodies for the same logical
condition, one blaming permissions for a lost race. Bodies are carried as opaque
detail for the message and never parsed.

**Each cause produces a distinct user-visible outcome**, because six exception
types that all print the same thing would be six types nobody can use:

| cause | what the user sees | exit |
| ----- | ------------------ | ---- |
| auth | the token was rejected, and the name of the env var it came from | 1 |
| permission | the resource, and that the account cannot see it | 1 |
| not found | the ticket key, and that the tracker has no such issue | 1 |
| request invalid | that the tracker refused the request, plus the config key most likely at fault | 1 |
| rate limited | that the tracker is rate limiting, and the `Retry-After` value when given | 1 |
| unavailable | that the tracker could not be reached, and the timeout used | 1 |

No message includes a credential value. No message invites the reader to conclude
a ticket is claimed.

### 4. Claimability, read from the ticket

This replaces the authoritative workflow read, and it is the change that makes
this item buildable. `tracker show` already calls `transitions(key)`. That one
response answers two questions at no extra cost:

1. **Is this ticket claimable right now?** Is the configured claim transition among
   those offered from the ticket's current status?
2. **Will this workflow exclude a second claimant?** Answerable *only when the
   ticket is already in the status the claim transition leads to*. If the claim
   transition is still offered from there, the workflow cannot exclude, and
   `tracker show` says so. Measured on both fixtures: the non-conforming project
   offers the claim transition from the landing status, the conforming one does
   not, and those are the right answers.

   **Correction, found in implementation.** There is an asymmetry this spec first
   missed. A ticket that *offers* the claim reveals where the claim leads, because
   the transition carries its own destination. A ticket that does **not** offer it
   cannot. So from one ticket alone, only `not exclusive` is detectable — the case
   where the claim is still offered from its own destination. Confirming
   `exclusive` requires the destination from somewhere else, and the assessment
   takes it as an optional argument for a caller that knows it: one that read a
   second ticket in the ready state, or, in C2, the code that has just applied the
   claim and watched where the ticket landed. That second case is the one that
   matters, because it is the moment exclusivity is about to be relied on. With no
   destination and no offered claim, the answer is `not determined`, reported
   rather than papered over.

Three outcomes, and the third is reported rather than hidden:

- **can-exclude** — the ticket is in the landing status and the claim transition is
  not offered.
- **cannot-exclude** — the ticket is in the landing status and it is offered.
- **not-determined** — the ticket is not in the landing status, so this ticket
  cannot answer the question. Printed as "not determined from this ticket", never
  as reassurance.

**Why this and not the workflow definition.** The definition route needs a project
identifier no configuration key carries, an endpoint that may require site
administrator permission, issue-type enumeration to cover a scheme that maps
several workflows, and a severity tier `tcw validate` does not have. This route
needs none of those: `GET /rest/api/3/issue/{key}/transitions` is available to
anyone who can view the issue, it works the same on team-managed and
company-managed projects, and it needs no key beyond the ticket the user already
named.

**`transitions.claim` resolution is part of this.** When the configured name
matches no transition the ticket offers *and* the ticket is in a status from which
the claim should be possible, that is a misconfiguration and `tracker show` reports
it as one, naming the configured value and listing the names actually offered. This
is the highest-value thing this item does for C2, because the experiment showed C2
*cannot* tell a wrong transition name from a lost race. When the name matches more
than one offered transition, that is also reported, and the check refuses rather
than guessing which was meant.

**Nothing here reaches `tcw validate`, and that is deliberate.**
`tcw-config.yaml:65` binds `command: "tcw validate"` as a `pre` hook on the
`complete` transition, and a `pre` failure means "do not touch the store"
(`tcw/work/hooks.py:115`). A network call on that path would mean `tcw work
complete` fails when Jira is unreachable, when the credential variables are not set
in that shell, or when the token has expired — and `tcw validate` recurses across
descendant projects, multiplying the cost. `tcw validate` therefore checks the
configuration's **shape** only, offline, exactly as it does today.

### 5. The commands

`tracker` as a nested subcommand group under `tcw work`, beside `inbox`
(`tcw/work/cli.py:1846`), `tags` (`tcw/work/cli.py:1879`), `tombstone`
(`tcw/work/cli.py:1891`) and `stage` (`tcw/work/cli.py:1968`).

```text
tcw work tracker list
tcw work tracker show <ticket>
```

Both read-only. `list` prints one row per ticket: key, status, assignee, summary.
`show` prints the ticket's content, assignee, status, and the claimability report
from part 4. With no tracker configured, both exit non-zero with one line naming
`work.tracker`.

Two words, not one: **"claimable"** describes this ticket now; **"exclusive"**
describes whether the workflow can exclude a second claimant. An earlier draft used
"claimable" for both, which would tell a user something true and misleading at once.

## Abstraction litmus test

| Operation | Verdict | Why |
| --------- | ------- | --- |
| `tracker_config()` / `tracker_problems()` on `WorkStore` | **store interface** | Config-derived facts about the node, like `retention_problems()` and `registered_tags()`. Any adapter answers both; a tracker-less one answers `None` and `[]` by default. |
| The `TrackerConfig` value — provider, base url, query, credential variable *names*, timeout, claim transition name | **model** | Portable data. Every field has an analogue for any tracker. The variable names are model data because a portable config must be able to say where a secret comes from without holding it. |
| `myself` / `search` / `issue` / `transitions` | **neither — a module beside the store** | Operations on the tracker, not on the work store. Behind `WorkStore` they would make every adapter owe a tracker implementation. No tracker call goes inside `FsWorkStore`. |
| "Is this ticket claimable, and is the transition exclusive?" | **model concept, adapter mechanism** | Every tracker has some notion of an available state change and whether it is exclusive. Discovering it is Jira-shaped and stays in `tcw/tracker/jira.py`. |
| JQL, REST paths, basic-auth header construction, HTTP status mapping, `_request` | **adapter private detail** | None appears in a signature outside `tcw/tracker/jira.py`. |

One wart, named rather than hidden: `parse_tracker_config` lives in
`tcw/store/base.py` and therefore the string `jira-cloud` appears in the abstract
layer. That follows from the settled decision to build one provider with no
abstraction. It is a validated enum value, not a behavioral branch, and when a
second provider appears the value moves into the provider registry that appears
with it.

## Acceptance criteria

Nine are automated. Three, marked **[live]**, need the Atlassian fixtures and are
discharged once by hand; their responses are then committed as replay fixtures so
the automated nine cover the same ground thereafter.

1. On a **fixture node** built by `python evals/seed_fixture.py` with no
   `work.tracker` key, `tcw work list`, `tcw work show <the fixture's item>` and
   `tcw validate` each produce the same stdout, the same stderr and the same exit
   code as the same commands on the same fixture at this item's branch point.
   Compared stream by stream, not as one blob. The earlier wording said
   "byte-identical output to the commit before this item" against the live
   repository, which cannot hold: this item's own artifacts and its capability flip
   change what `validate` scans and what the board prints.
2. No existing test is edited **to accommodate the tracker**. Adding
   `"tcw work tracker"` to `DOCUMENTED_VERBS`
   (`tests/test_documented_cli_surface.py:246`) and the matching prose to
   `docs/guide/work.md` and `skills/tcw-work/references/commands.md` is an
   addition, is expected, and does not violate this. That tuple is explicitly not
   derived from the CLI.
3. `tcw work tracker list` and `tcw work tracker show X` with no tracker configured
   exit non-zero and name `work.tracker`.
4. `tcw validate` exits non-zero when any required key is absent, naming the
   missing key, for each of `provider`, `base-url`, `candidate-query`,
   `credentials`, `transitions.claim`, independent of any other key's presence.
5. `tcw validate` exits non-zero when `provider` is not `jira-cloud`, naming the
   value it got; and when `strict` is present, naming it as an unknown key.
6. A malformed `work.tracker` — a scalar where a mapping belongs, an unknown key —
   is reported by `tcw validate`, and **`tcw work list` still exits zero and prints
   the board**.
7. **`tcw validate` makes no network call and reads no credential environment
   variable**, on a configured node. Proven by running it with the credential
   variables unset and an unroutable `base-url`, and asserting it exits zero and
   returns within one second.
8. Each of the six error causes produces its own exit path and its own message,
   proven by substituting `_request` to return that status. A 400 raises
   `TrackerRequestInvalid`, and no code path infers "already claimed" from it.
9. A request against a socket that accepts a connection and never writes fails
   within `timeout-seconds` rather than hanging, raising `TrackerUnavailable`.
10. No secret appears in any tracked file, in stdout or stderr of any command
    including every failure path, or in any exception message. Proven with a
    sentinel token value, exercising every command and every error branch, and
    grepping captured output and the work store.
11. **[live]** Against the conforming fixture, `tracker show` on a ticket in the
    landing status reports **exclusive**; against the non-conforming fixture, the
    same reports **not exclusive**. Against a ticket not in the landing status,
    both report **not determined**.
12. **[live]** `tracker list` prints one row per ticket the configured query
    selects, and `tracker show` prints a named ticket's status and assignee.
13. **[live]** With `transitions.claim` set to a name the workflow does not have,
    `tracker show` reports the misconfiguration, names the configured value, and
    lists the transition names actually offered.
14. `work/inspect-external-tracker-work` reads `Supported` before this item
    completes, and `tcw capabilities check` and `tcw validate` exit zero.

### Coverage

Five design parts, so five axes. A cell names the part a criterion reaches, or
`n/a` with what makes it so.

| # | 1 config | 2 client | 3 errors | 4 claimability | 5 commands |
| - | -------- | -------- | -------- | -------------- | ---------- |
| 1 | yes | yes | yes | yes | yes |
| 2 | n/a — docs, not code | n/a | n/a | n/a | yes |
| 3 | yes | n/a — never reached | n/a | n/a | yes |
| 4 | yes | n/a | n/a | n/a | n/a |
| 5 | yes | n/a | n/a | n/a | n/a |
| 6 | yes | n/a | n/a | n/a | n/a — board read only |
| 7 | yes | yes — proves it is not called | n/a | yes — proves it is not reached | n/a |
| 8 | n/a | yes | yes | n/a | yes — the messages |
| 9 | yes — the timeout value | yes | yes | n/a | n/a |
| 10 | yes | yes | yes | yes | yes |
| 11 | yes | yes | n/a | yes | yes |
| 12 | yes | yes | n/a | n/a | yes |
| 13 | yes | yes | yes | yes | yes |
| 14 | n/a | n/a | n/a | n/a | n/a — ledger |

Criterion 1 spans every part because every part can break it. Criterion 10 spans
every part because a secret can leak from any, and the check is one grep over all.
Criterion 7 is the one that protects the configured project, which nothing in the
earlier draft did.

## Risks

1. **Claimability cannot be answered for a ticket outside the landing status.**
   That is most tickets most of the time, so "not determined" will be the common
   answer. Accepted, because the alternative cost four unresolved design questions
   and a network call inside the completion gate. The authoritative answer arrives
   in C4 with the consumer that needs it, and C2 gets the one case that matters:
   immediately after a claim, the ticket *is* in the landing status, so C2 can
   check exclusivity exactly when it is about to rely on it.
2. **The live fixtures are on a shared site.** Criteria 11 through 13 depend on two
   throwaway projects keeping their workflows. Mitigated by committing their
   responses as replay fixtures, after which only a deliberate re-verification
   touches the site.
3. **Hand-rolling an HTTP client means hand-rolling its failure handling.**
   Mitigated by four read operations behind one seam, and by the error taxonomy
   being a deliverable rather than an afterthought.
4. **The forward-incompatible config is a real cost.** A user who writes a C3-era
   or C4-era block gets problems reported on a C1-era build. Deliberate, and
   preferable to ignoring a key someone set, but it means the release notes for C3
   and C4 must say which keys became legal when.
5. **`_request` as the only seam means a test that stubs it does not exercise
   `urllib`.** Criterion 9 covers the real socket path, and that is the one place
   where a genuine network mistake would hide.

## Notes

**Why the authoritative workflow read left this item.** A first draft of this spec
made the workflow-shape verdict the reason this item existed separately, reading a
project's workflow definition through `POST /rest/api/3/workflows`. I measured that
route working, in one call, and it gave the right verdict for both fixtures. The
review then found four things wrong with hosting it here, all of which I verified:

- `tcw validate` has no severity tier. `validate()` returns a flat `list[str]`
  (`tcw/validate.py:220`) and the command returns 1 whenever it is non-empty
  (`tcw/cli.py:447`), so a non-strict "warning that exits zero" had no mechanism.
- `tcw work check` does not exist. The first draft named it as a reporting surface
  twice.
- No configuration key identifies a project, and the route needs one.
- Worst: `tcw validate` is a `pre` hook on `complete` in this repository's own
  config, so the verdict would have made completing a work item depend on Jira
  being reachable.

The replacement uses a call this item already makes and a permission any viewer
has. It answers less, and what it gives up is needed only when strict mode gates
work, which is C4. **The epic's spec should move the authoritative read into C4's
boundary**, and this spec's non-goals say so; that edit belongs to the epic.

**This answers the epic's open question 3.** It asked whether this item depends on
`2026-09-01-make-tcw-validate-usable-as-a-gate-suppressible-references-and-graded-exit-codes`
landing first. **It does not, now.** The dependency existed only because the
workflow verdict needed a warning tier. With no verdict in `tcw validate`, every
problem this item reports is an ordinary error and the existing flat list is
sufficient. That item also wants the word `strict` on `tcw validate`; since this
item no longer accepts a `strict` key, the collision is gone too, and C4 should
pick a different name or coordinate when it arrives.

**Assumption, retired.** An earlier draft assumed `POST /rest/api/3/workflows`
might be administrator-only and made that Risk 1. It is no longer this item's
problem. It becomes C4's, and C4 should settle it with a non-admin token before
designing around the route.

**Still unverified.** Behavior on a team-managed (next-generation) project. The
issue-level transitions endpoint is expected to behave identically, which is part
of why this route was chosen, but neither fixture is team-managed and I did not
test one.

**Fixtures.** `TCWTEST` (project 10003) is deliberately non-conforming: its
workflow offers all transitions from all statuses. `TCWCLAIM` (project 10004)
carries `TCW Bridge Claim Workflow`, directed transitions only. Both were built and
measured on 2026-09-12. `~/.claude/bin/jira` is a working wrapper for checking
behavior by hand, and is the right tool for the three live criteria.
