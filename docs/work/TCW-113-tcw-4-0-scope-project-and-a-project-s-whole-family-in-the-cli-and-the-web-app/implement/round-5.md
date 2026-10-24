# Implement round 5 — TCW-113

Answers review round 4: its findings 1 and 2, and the navigation item the
dispatching session folded in. Client code only. Made on the branch `v4` in
the worktree `.claude/worktrees/v4`, in commit `fd4c2ad1`. No lifecycle
command was run, no ticket was moved or written to, and nothing was pushed:
the dispatching session makes every move. The hand check used the scratchpad
wrapper on a copy of the round 4 reviewer's family, never the repository as
the project.

## (a) Leaving a capability's page clears its error

**Found (finding 1).** Open `/capabilities/desktop.capabilities/nosuch`,
then click Work: the board's pane kept "no such capability" until an item
was picked. The term and capability effect (`web/client/src/ui/app.tsx`)
clears only `detail` when the axis is work, and the work effect, when no
item is chosen, cleared only `workDetail`. The pane shows `detailError` on
every axis, so the old message stayed.

**Done.** The work effect, when the axis is work and no item is chosen, now
clears `detailError` as well. It clears it only on the work axis, so a
change to its own inputs while a capability's page is shown cannot wipe that
page's error. With an item chosen it already cleared the error before
reading the item. Clicking Work and the browser's back button both reach the
board through this effect, so this one change covers both.

## (b) Every project with its own object at the path is linked

**Found (finding 2).** "Status by project" (`StatusByProject`,
`web/client/src/ui/content-views.tsx`) linked only the page's own object and
the objects that override it. On another project's override page,
`desktop.capabilities/abc` under `down`, the line `Missing: shared |
Supported: desktop | Omitted: server` linked only `desktop`, to itself.
Design 6.9 links every project that has its own object at the path.

**What the record carries.** Each `statuses` entry carries `project`,
`status` and `inherited`, and no full identifier. `inherited` is false when
the project's own object at the path sets the status (`tcw/store/base.py`,
`ProjectView.sets_status`), so such an entry always has its own object at
the record's id-path. The record also gives full identifiers of its own: its
`full-id`, the object it `overrides`, and its `overridden-by`.

**Done.** Each entry with `inherited: false` is linked to
`<project>.capabilities/<the record's id-path>`. Then the full identifiers
the record gives (`full-id`, `overrides`, `overridden-by`) are added, and
where they name the same project they take precedence. A project whose
entry is `inherited: true` and that the record does not name is plain text,
as before. This is the same rule on every page that shows the line: the
served project's page, an override's page, and any other project's page.

## (c) A link to the page already shown keeps it shown

**Found (folded in).** `navigateTo` (`app.tsx`) set the detail to nothing
and then set the same axis and selection again. The reads depend on the
axis and the selection, so nothing read the page again and the pane showed
"Select an entry.". This happened for a status line's link to its own page,
which (b) makes more common, and for a row clicked a second time.

**Done.** When the axis and key asked for are the ones shown, `navigateTo`
keeps `detail` and `workDetail`. Everything else it resets (the editor, the
work form, unsaved-change state, errors, the conflict) is reset as before.

## (d) Design 2.2's message template

The spec's Design 2.2 gives the template of the `--project` refusal with two
possible endings. Since implement round 4 the code has three: the third,
`no project with ID '<id>' is known or found near this one; check the
spelling`, is used when no project has the ID at all. The spec is not edited
at implement. TCW-117, or the 4.0 epic's documentation, can bring the
template in line.

## Decisions

- (a): clear the error in the work effect only on the work axis, rather
  than in the term and capability effect's work branch. That effect also
  runs when the lists reload, which on the board would wipe a real error
  from reading a work item. Decided by the implementing agent.
- (a): no clear was added to `navigateTo`. A first version had one; the
  mutation check showed it changed nothing the tests or the review's path
  could observe, since the effect already covers every way onto the board,
  so it was removed. Decided by the implementing agent.
- (b): derive a link from `inherited: false` and the record's own full
  identifiers, rather than change the server to give each entry its full
  identifier, since this round is client code only. What this leaves out: a
  project that has its own object at the path, whose own object does not
  set the status, and that the record does not name. Such a project stays
  plain text. On the served project's page under `down` the record's
  `overridden-by` names every override, so this can only happen on another
  project's page. Giving each `statuses` entry the full identifier of its
  view object would close it. Decided by the implementing agent; it belongs
  on the 4.0 run's list of small follow-ups if wanted.
- (c): a link to the page shown still adds a browser history entry, as
  before. Replacing the entry instead was tried and taken out, since no test
  would observe it. Decided by the implementing agent.

## Tests

In `web/client/src/ui/app.test.tsx`:

- `a capability's error does not follow to the board`: opens
  `/capabilities/desktop.capabilities/nosuch?scope=down`, sees the not-found
  message, clicks Work: the board's items are shown and the message is gone.
- `a capability's error does not follow back to the board`: the same, but
  reaching the board with the browser's back button.
- `an override's page links each project with its own object at the path`:
  on `desktop.capabilities/abc`, `p`, `desktop` and `server` (all
  `inherited: false`) link to `/capabilities/abc`,
  `/capabilities/desktop.capabilities/abc` and
  `/capabilities/server.capabilities/abc`; `tablet` (`inherited: true`) is
  plain text, marked "(inherited)".
- `the object an override names is linked though its status is inherited`:
  `p`'s entry is `inherited: true`, and the record's `overrides` names
  `p.capabilities/abc`: `p` is linked.
- `a link to the page already shown keeps it shown`: on `abc`'s page,
  clicking `p` in "Status by project" leaves the page shown.
- `a row clicked twice keeps its page shown`.

All six failed before the change, each for the reason it targets.

## Mutation results

Each change was reverted alone, the client tests run, and the change put
back.

| Change reverted                                          | Result                                       |
| -------------------------------------------------------- | -------------------------------------------- |
| (a): the work effect's clear                             | both error tests red                         |
| (b): links from `inherited: false` entries               | the override page test red                   |
| (b): `inherited: true` entries linked too                | the override page test red (`tablet` linked) |
| (b): the record's `overrides` not used                   | the inherited-status test red                |
| (c): the page shown always cleared (`same` always false) | the self-link and row-twice tests red        |
| (a): a first version's extra clear in `navigateTo`       | all green, so it was removed (see Decisions) |

## Checks run

- `pnpm test`: `245 passed` (17 files).
- `pnpm exec tsc --noEmit`, `pnpm lint`, and `prettier --check` on
  `web/client/src`: clean.
- `pnpm build`, the rebuilt bundle committed with the change; then
  `pnpm check:build`: clean (exit 0).
- By hand, headless Chromium against `tcw serve --port 8907` run through the
  scratchpad wrapper in `shared` of a copy of the round 4 reviewer's family:
    - (a) `/capabilities/desktop.capabilities/nosuch?scope=down` showed "no
      such capability: 'desktop.capabilities/nosuch'"; clicking Work went to
      `/work?scope=down` and the pane said "Select an entry.".
    - (b) on `/capabilities/desktop.capabilities/abc?scope=down`, the line
      `Missing: shared | Supported: desktop | Omitted: server | unavailable:
mobile` linked `shared` to `/capabilities/abc`, `desktop` to
      `/capabilities/desktop.capabilities/abc`, and `server` to
      `/capabilities/server.capabilities/abc`. Following `server` opened
      `server.capabilities/abc`, "owned by server", with one request,
      `/api/capabilities/server.capabilities%2Fabc?scope=down`.
    - (c) clicking `desktop` on its own page kept the page shown; clicking the
      `Abc` row twice on `/capabilities?scope=down` kept `abc`'s page shown.
    - The server was stopped afterwards.

## The suite

The full Python suite was not run by the implementing agent. This round
changes no Python. The dispatching session runs the suite, as CI runs it,
before the next review.
