# Refined outcome — Show the tracker's untriaged tickets on `tcw work inbox list`

**Accepted** by the requester on 2026-09-17, after the work was exercised against a
real Jira site from this repository itself.

## The decision and what it rested on

- **All 25 acceptance criteria met.** Assessed independently by a read-only verifier
  against the diff, which found no blocking defect. Its three findings were wording
  defects, all fixed before acceptance (`597e1188`, `c96fc9a9`): a message naming
  `import` when run as `inbox accept`; `--ticket` blaming a missing `inbox-query` when
  the tracker block was merely broken, and skipping the strict refusal; and three
  documents that said strict mode allows accepting a ticket without saying that
  `inbox-query` must be declared.
- **Full suite green at acceptance: 3670 passed** (bare `pytest`, as CI runs it).
  `tcw validate` OK, `tcw capabilities check` OK.
- **Verified live**, not only against the test double — see below.

## Live verification

A new Jira project, `TCW` on proposit.atlassian.net, was created for this repository's
own work (workflow, scheme and board copied from PRPI; board columns set by hand,
because the API cannot). This repository now declares the tracker block in
`tcw-config.yaml` with `inbox-query: project = TCW AND status = Triage` (`ffc4ed1a`).

The inbox entry `2026-09-17-the-web-client-shows-any-409-as-a-stale-write.md` was
copied into Jira as `TCW-1` and deleted from the repository, so it exists only as a
ticket. From this repository:

- `tcw work inbox list` prints the five remaining files under `raw intake:` and
  `TCW-1 | Triage | unassigned | …` under `tracker tickets:`.
- `tcw work inbox show TCW-1` prints the ticket and its full description.
- A malformed `inbox-query` leaves the raw intake intact, prints `(not listed)` and
  Jira's own message, and exits 1.
- A ref that is neither (`nope`, `TCW-99999`) gets the message naming both: live Jira
  answers 404 for a non-key ref, which was the open question at `implement`.

## Deferred, with the reason

- **`tcw work inbox accept <triage ticket>` does not work yet**, and this was accepted
  knowingly. Accepting claims, a claim still rides the transition named in
  `transitions.claim`, and a pre-triage status does not offer it — `TCW-1` in `Triage`
  offers only `Accept` and `Cancel`. The requester chose to change nothing in Jira and
  wait for the epic
  `2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs`, whose agreed
  verb table makes `claim` assert ownership and move no status. This instance was
  recorded there as a symptom it must dissolve (`09c7321d`). No follow-up item was
  created, because that epic is the item.
- **Closing an originating GitHub issue:** none; this came from chat.

## Follow-ups folded in rather than deferred

The requester asked for small follow-ups to land here (`fd62e098`): accepting a ticket
no longer makes an extra Jira read; `--part` on a raw entry is refused without
consuming it; a lone `inbox-query: null` reports the wrong type rather than "required";
and two gaps gained tests (`accept --ticket` on a shadowed ref, an unknown ref under
strict mode without `inbox-query`), each mutation-checked.

## Capability reconciliation

`capabilities.yaml` carries `changed:` only — five entries. The four the spec named,
plus `skills/commands-process-inbox`, added at `implement` once its skill was taught to
work tickets. Nothing new, nothing removed; `tcw capabilities check` passes.

## Closeout choices

- **Version: unchanged**, at the requester's direction. The release-note and changelog
  entries stay in `upcoming.md` for whichever version cuts next.
- **Integration: merged into `main` locally**, no pull request.
- **Documentation:** all six entries fired and were answered (`29cbbb32`, `c96fc9a9`,
  `ab830d63`).
