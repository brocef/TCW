# Spec — Configure an external tracker and read its tickets

## Capability changes

One new capability, seeded `Missing` at the epic's planning and flipped by this
item's completion:

- `work/inspect-external-tracker-work` — "Inspect external tracker work"
  (`cap-1b0a04`), already carrying `Feature=external-work-tracker`,
  `Subject=work-item, cli, reference`, and `Planning doc` pointing here.

No existing capability changes. `work/manage-the-work-inbox` in particular does
not: the filesystem inbox and an external tracker are distinct intake sources, and
this item adds no intake at all.

The `external-work-tracker` Feature already exists
(`tcw taxonomy show external-work-tracker`), registered by the epic because all
four of the initiative's capabilities name it.

## Problem

A project cannot tell TCW that it uses a tracker, and TCW cannot read one. Three
specifics, each checked.

1. **There is no configuration surface for a tracker.** The node sentinel is read
   through `FsWorkStore._config` (`tcw/store/fs.py:5036`) and narrowed to the
   `work:` mapping by `_work_config` (`tcw/store/fs.py:5051`). The keys it
   recognizes are `tags`, `lifecycle`, `documentation`, `repository`, `retain` and
   `path`. Nothing names a tracker.
2. **Nothing in the package speaks HTTP.** The only `urllib` imports are
   `urllib.parse` for unquoting references (`tcw/refs.py:27`,
   `tcw/serve/__init__.py:18`). There is no client, no credential handling, and no
   error taxonomy to extend.
3. **Whether a tracker's workflow can support a claim is unknowable today, and it
   is not a detail.** The epic's experiment (`jira-claim-experiment.md`) measured
   both cases on a live Jira Cloud site. On a workflow whose transitions are
   global, the claim transition stays available after it is applied, so applying it
   twice succeeds and concurrent claims all succeed. On a workflow with directed
   transitions only, it disappears, and four concurrent-race trials produced
   exactly one winner each. The difference is entirely in the customer's workflow
   configuration.

## Goals

1. A project declares its tracker in `tcw-config.yaml`, with credentials named
   rather than embedded.
2. A developer sees the tickets the configured query selects, and one ticket in
   detail, from the terminal.
3. TCW can state whether the configured workflow is capable of excluding a second
   claimant, and refuses the strict mode when it is not.
4. Failures are distinguishable by cause, not collapsed into one error.
5. A project with no tracker configured is unaffected in every observable way.

## Non-goals

- **Claiming, importing, or binding anything.** No `tracker.yaml`, no
  `import`/`link`/`unlink`. This item reports whether claiming could work; it never
  claims. Those are C2.
- Outbound synchronization, `sync`, drift (C3). The strict mode's gates on
  `work new` and `work start` (C4) — this item only *refuses to enable* strict mode
  on a non-conforming workflow, which is a configuration verdict, not a gate on
  work.
- Anything in `tcw work show --json`, `tcw work list`'s columns, or the web app
  (C5).
- A provider abstraction. One Jira module behind a narrow seam; no base class, no
  provider registry, no fake provider. Settled at the epic.
- A new runtime dependency, Jira Data Center, OAuth, token persistence, and any
  tracker other than Jira Cloud.
- Writing anything to the tracker. Every operation here is a read. The workflow
  check reads transitions; it does not apply one.

## Design

### 1. Configuration

A `work.tracker` mapping in the node sentinel. Parsed by a pure function beside
the existing ones, `parse_tracker_config(raw) -> (TrackerConfig | None, list[str])`,
in `tcw/store/base.py` next to `parse_documentation_entries`
(`tcw/store/base.py:1590`).

```yaml
work:
    tracker:
        provider: jira-cloud # the only accepted value
        strict: false
        base-url: https://example.atlassian.net
        candidate-query: assignee = currentUser() AND status = "To Do"
        credentials:
            email-env: TCW_JIRA_EMAIL
            token-env: TCW_JIRA_API_TOKEN
        timeout-seconds: 15 # optional, default 15
        transitions:
            claim: Start Progress
```

Only the keys this item uses are accepted. The terminal and submit/rework mappings
the epic's request sketches belong to C3, and accepting them here would mean
validating a shape nothing reads.

**The store surface follows the existing two-method contract exactly**, because
that contract is what keeps a malformed config from breaking the board:

- `WorkStore.tracker_config() -> TrackerConfig | None` — problems discarded, like
  `documentation()` (`tcw/store/fs.py:5276`) and `lifecycle_policy()`.
- `WorkStore.tracker_problems() -> list[str]` — problems prefixed with the
  sentinel name, like `documentation_problems()` (`tcw/store/fs.py:5283`), and
  added to `check()` beside the other three (`tcw/store/fs.py:5420`).

Both are concrete on `WorkStore` with a `None`/empty default, so no existing
adapter breaks and a tracker-less store answers correctly by omission.

**Credentials are read from the environment at the point of use**, never stored on
`TrackerConfig`. The config holds the variable *names*; the values are fetched when
a request is about to be made. A `TrackerConfig` that never reaches a network call
never touches a secret.

### 2. The Jira client

A new module, `tcw/tracker/jira.py`, with `tcw/tracker/__init__.py`. Not under
`tcw/store/`: a tracker is not a store, and the epic's litmus table puts tracker
operations outside `WorkStore` deliberately so no adapter owes a tracker
implementation.

Standard library only. `urllib.request` with basic authentication built by hand
from the email and token. Five operations, which is everything this item and the
workflow check need:

1. `myself()` — who the credentials authenticate as.
2. `search(jql, limit)` — the configured candidate query.
3. `issue(key)` — one ticket.
4. `transitions(key)` — the transitions available for an issue *right now*.
5. `project_statuses(project_key)` — the statuses and issue types of a project,
   used by the workflow check.

**Every request passes an explicit `timeout`.** `urllib.request.urlopen` falls back
to the global socket default when none is given, and that default is unset, so the
omission is an indefinite hang rather than a slow call.

### 3. The error taxonomy

One exception base, `TrackerError`, with a subclass per cause, because every later
child needs to tell these apart and the experiment showed the HTTP status alone
does not:

| subclass | raised for |
| -------- | ---------- |
| `TrackerAuthError` | 401, and 403 with no issue context |
| `TrackerPermissionError` | 403 on a specific resource |
| `TrackerNotFound` | 404 |
| `TrackerRequestInvalid` | 400 — the request was refused |
| `TrackerRateLimited` | 429, carrying `Retry-After` when present |
| `TrackerUnavailable` | 5xx, connection failure, timeout |

`TrackerRequestInvalid` is deliberately **not** named "conflict" or "already
claimed". The experiment recorded three different `400` bodies for the same logical
condition, one of which blames permissions for a lost race. The bodies are carried
as opaque detail for the message and never parsed. Deciding *why* a 400 happened is
C2's read-modify-verify job, and this taxonomy exists so C2 has something honest to
build on.

### 4. The workflow capability check

The reason this item exists rather than being folded into C2. Given the configured
claim transition name:

1. Resolve it to a transition id, and to the status it lands in.
2. Read the transitions available from that landing status.
3. If the claim transition is among them, the workflow **cannot exclude** a second
   claimant.

Reported by `tcw validate` and `tcw work check`. When `strict: true` and the
workflow cannot exclude, it is an **error** and validate exits non-zero. When
`strict: false` it is a **warning**, because a project may legitimately want intake
and visibility without the guarantee.

Step 2 needs the transitions available from a status the caller may not have an
issue sitting in, so it cannot be answered by `transitions(key)` on an arbitrary
issue. It is read from the project's workflow, and **the route is settled and
measured** (2026-09-12):

```
POST /rest/api/3/workflows
{"projectAndIssueTypes": [{"projectId": "<id>", "issueTypeId": "<id>"}]}
```

One call, from a project id alone. The response carries every transition with its
`type` (`INITIAL`, `GLOBAL`, `DIRECTED`) and, for a directed one, its
`links[].fromStatusReference`. The verdict rule is then two lines:

- a `GLOBAL` claim transition is by definition available from every status,
  including its own destination, so the workflow **cannot exclude**;
- a `DIRECTED` one cannot exclude only if its `links[].fromStatusReference`
  contains its own `toStatusReference`.

Verified against both fixtures. `TCWTEST` returns transition 21 as `GLOBAL`, so
"cannot exclude". `TCWCLAIM` returns it as `DIRECTED` from `10012` to `3`, and `3`
is not among its from-links, so "can exclude". Those are the right answers, and
they match what the live race trials actually did.

A third verdict is required: **cannot determine**. If the call is refused for lack
of permission, the check must say so and must not be read as either pass or fail.
A check that failed open would be worse than no check.

### 5. The commands

`tracker` as a nested subcommand group under `tcw work`, beside `inbox`
(`tcw/work/cli.py:1846`), `tags` (`tcw/work/cli.py:1879`) and `stage`
(`tcw/work/cli.py:1968`).

```text
tcw work tracker list
tcw work tracker show <ticket>
```

Both read-only. `list` runs the configured query and prints one row per ticket: key,
status, assignee, summary. `show` prints the ticket's product content, assignee,
workflow state, and whether it is claimable under the configured claim transition.
With no tracker configured, both exit non-zero with one line saying so and naming
the config key, and neither is reachable in a way that changes any other command.

## Abstraction litmus test

| Operation | Verdict | Why |
| --------- | ------- | --- |
| `tracker_config()` / `tracker_problems()` on `WorkStore` | **store interface** | A config-derived fact about the node, exactly like `documentation()`, `lifecycle_policy()` and `registered_tags()`. Any adapter can answer both, and a tracker-less one answers `None` and `[]`. |
| The `TrackerConfig` value — provider, base url, query, credential variable names, timeout, claim transition name | **model** | Portable data. Every field has an analogue for any tracker. |
| `myself` / `search` / `issue` / `transitions` / `project_statuses` | **neither — a module beside the store** | Operations on the tracker, not on the work store. Behind `WorkStore` they would make every adapter owe a tracker implementation, which inverts what a store is for. No tracker call goes inside `FsWorkStore`. |
| "Can this workflow exclude a second claimant?" | **model concept, adapter mechanism** | Every tracker has some notion of whether a state change is exclusive. *How* it is discovered is Jira-shaped and stays in the Jira module. |
| JQL, REST paths, basic-auth header construction, HTTP status mapping, environment variable names | **adapter private detail** | None of it appears in a signature outside `tcw/tracker/jira.py`. |

No filesystem trick anywhere. Nothing here reconstructs state from git, globs a
store folder, or hard-codes a path.

## Acceptance criteria

1. With no `work.tracker` key, the full suite passes with no existing test edited,
   and `tcw work list`, `tcw work show` and `tcw validate` produce byte-identical
   output to the commit before this item.
2. `tcw work tracker list` with no tracker configured exits non-zero and its
   message names `work.tracker`.
3. With the `TCWCLAIM` fixture configured, `tcw work tracker list` prints one row
   per ticket the query selects, and `tcw work tracker show TCWCLAIM-1` prints its
   status and assignee.
4. `tcw validate` exits non-zero when `strict: true` and a required key
   (`provider`, `base-url`, `candidate-query`, `credentials`, `transitions.claim`)
   is absent, and the message names the missing key.
5. `tcw validate` exits non-zero when `provider` is any value other than
   `jira-cloud`, naming the value it got.
6. A malformed `work.tracker` — a scalar where a mapping belongs, an unknown key —
   is reported by `tcw validate` and `tcw work check`, and **`tcw work list` still
   exits zero and prints the board**.
7. Configured against `TCWTEST`, whose workflow offers all transitions from all
   states, the workflow check reports that the workflow cannot exclude a second
   claimant. With `strict: true` that is an error and `tcw validate` exits
   non-zero; with `strict: false` it is a warning and validate exits zero.
8. Configured against `TCWCLAIM`, whose transitions are directed, the workflow
   check reports the workflow can exclude, and `tcw validate` exits zero under
   `strict: true`.
9. Each of the six error subclasses is raised for its own condition, proven
   against a stub HTTP layer returning that status. A 400 raises
   `TrackerRequestInvalid` and **no** code path infers "already claimed" from it.
10. A request against a server that accepts a connection and never responds fails
    within the configured timeout rather than hanging. Proven against a socket
    that accepts and never writes.
11. No secret appears in any tracked file, any command's stdout or stderr, or any
    exception message. Proven by setting a sentinel token value, exercising every
    command including every failure path, and grepping the captured output and the
    whole work store for it.
12. `work/inspect-external-tracker-work` reads `Supported` before this item
    completes, and `tcw capabilities check` and `tcw validate` exit zero.

### Coverage

The Design section numbers five parts, so the axes are those. A cell names the
criterion that reaches that part, or `n/a` with what makes it so.

| # | 1 config | 2 client | 3 errors | 4 workflow check | 5 commands |
| - | -------- | -------- | -------- | ---------------- | ---------- |
| 1 | yes | yes | yes | yes | yes |
| 2 | yes | n/a — never reached without config | n/a | n/a | yes |
| 3 | yes | yes | n/a | n/a | yes |
| 4 | yes | n/a | n/a | n/a — key presence only | n/a |
| 5 | yes | n/a | n/a | n/a | n/a |
| 6 | yes | n/a | n/a | n/a | n/a — board read, no tracker call |
| 7 | yes | yes | n/a | yes | n/a |
| 8 | yes | yes | n/a | yes | n/a |
| 9 | n/a | yes | yes | n/a | n/a — surfacing is C5 |
| 10 | yes — the timeout value | yes | yes — raises `TrackerUnavailable` | n/a | n/a |
| 11 | yes | yes | yes | yes | yes |
| 12 | n/a | n/a | n/a | n/a | n/a — ledger, not code |

Criterion 1 spans every part because every part can break it. Criterion 11 spans
every part because a secret can leak from any of them, and the check is one grep
over all of them rather than five separate ones.

## Risks

1. **The workflow read may be admin-only.** Every call measured on 2026-09-12
   authenticated as a site admin. If `POST /rest/api/3/workflows` requires an admin
   permission an ordinary project member lacks, the check returns "cannot
   determine" for most real users, and the guarantee it supports becomes much
   weaker in practice. This is the first thing the plan must settle, and the only
   honest way to settle it is a non-admin account or an account with the Jira
   administrator permission removed. If it is admin-only, the fallback is to
   observe transitions from a live issue in the landing status, which needs such an
   issue to exist and cannot answer for an empty project.
2. **`TCWTEST` and `TCWCLAIM` are live fixtures on a shared site.** Criteria 7 and
   8 depend on their workflows staying as they are. Anyone with admin access could
   change them. The mitigation is that both are named as throwaway in their
   descriptions, and that the automated suite runs against a stub HTTP layer, so
   only the manual verification depends on the live site.
3. **Hand-rolling an HTTP client means hand-rolling its failure handling.**
   Retries, pagination and status mapping all get written here. Mitigated by the
   operation set being five reads, and by the error taxonomy being the deliverable
   rather than an afterthought.
4. **Six exception types for one provider may be more than is earned.** They are
   justified by what C2, C3 and C4 need to tell apart, not by this item's own use.
   If two of them never get distinguished by any caller, collapse them at C3 rather
   than keeping a distinction nobody reads.
5. **`strict` is accepted here but enforced in C4.** A project could set
   `strict: true` after this item ships and get the workflow verdict without the
   work gates, which is a partial promise. Acceptable because the verdict is the
   honest half and it is the half that prevents a bad configuration; C4's release
   notes should say the gates arrived later.

## Notes

**The workflow read is settled.** An earlier draft of this spec left the route
for design part 4 unresolved and deferred it to the plan. It was resolved the same
day instead: `POST /rest/api/3/workflows` with `projectAndIssueTypes` answers it in
one call from a project id, and the verdict logic was run against both fixtures and
returned the right answer for each. The design section carries the detail.

**Assumption, not verified.** That the same call succeeds for a **non-admin**
account. Every request measured authenticated as a site admin. This is Risk 1 and
it is the plan's first task, because it decides whether the check is a real
guarantee for ordinary users or only for administrators.

**A second assumption.** That one issue type's workflow represents the project's.
A scheme can map different issue types to different workflows, so a project could
be conforming for `Task` and not for `Bug`. The check should read every issue type
the scheme maps and report the worst verdict, rather than sampling one. This costs
nothing extra in the same call, which accepts a list.

**Fixtures.** `TCWTEST` (project 10003) is deliberately non-conforming;
`TCWCLAIM` (project 10004) carries `TCW Bridge Claim Workflow` with directed
transitions only. The pair is what criteria 7 and 8 need, and both were built and
measured on 2026-09-12. `~/.claude/bin/jira` is a working wrapper for checking
behavior by hand.
