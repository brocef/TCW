# Web viewer: a single-process document reader and editor with autocomplete everywhere

TCW 3.0 (epic [TCW-68](https://proposit.atlassian.net/browse/TCW-68)) narrows what
`tcw serve` is for. Today it is a second front end to the whole of TCW, lifecycle
included, and it needs Node.js to run. In 3.0 it becomes a focused local web app
for **reading and editing the documents in the TCW structure and creating new TCW
objects**, across taxonomy, capabilities and work, and it leaves moving work
through the lifecycle to the CLI.

## What is wanted

1. **One Python process, no Node.js at runtime.** `tcw serve [--port <n>] [--no-open]`
   starts one Python process that serves the prebuilt browser client and a small
   JSON API on `127.0.0.1`, and prints the URL on stdout. Node and pnpm stay
   contributor tools for building the client and running the browser tests.
2. **No logic of its own.** The API calls the same operations as the CLI (TCW-69's
   backend operations, the shared item-folder layout, the taxonomy and capabilities
   stores). Anything the viewer can do, the CLI can do too.
3. **Documents first.** Read and edit the markdown documents in an item folder
   (stage documents, rounds, handoffs) and the taxonomy and capability records;
   create missing documents for enabled stages; edit the item's declared record
   changes through a small form instead of raw YAML.
4. **Creating objects.** New work items, taxonomy entries and capabilities. In Jira
   mode, list inbox tickets and adopt them.
5. **The rule for Jira mode.** The viewer edits what is on disk. What lives in Jira
   (the request, comments, status, and the item's properties) is shown read-only with
   an "Open in Jira" link. Creating and adopting still work.
6. **Autocomplete everywhere.** Every editable field either autocompletes from the
   values TCW knows or is a fixed choice. The ticket's table lists, field by field,
   what is offered and what happens when something else is typed.
7. **No lifecycle.** No advance, discard, start, complete or drop, and no
   Definition-of-Done checklist. The stage is shown, not edited.
8. **One project.** Entries inherited through `extends` are shown and offered in
   autocomplete, marked as inherited. Child projects' boards are no longer combined.

The ticket ([TCW-77](https://proposit.atlassian.net/browse/TCW-77)), held as
imported in `intake.md`, is the requirement. Where it differs from the epic's
attached decision record, the ticket is current.

## Constraints

- **Keep every protection the Fastify layer gave:** loopback binding, a loopback
  `Host`/`Origin` check on every API request (reads included), JSON content type on
  writes, a 1 MiB body cap, and a `default-src 'self'` content security policy.
- **Jira credentials stay in the server process** and never reach the browser.
- **Jira being unreachable must not stop work on disk:** files stay readable and
  editable, and Jira-owned content shows as unavailable with a retry.
- **Breaking changes are expected.** This ships in 3.0.0 with no 2.x compatibility
  code.
- **TCW never changes git state** (TCW-69), so the viewer never commits.
- **Abstraction litmus test** ([`docs/lifecycle/abstraction.md`](../../../lifecycle/abstraction.md))
  and **harness compatibility** ([`docs/lifecycle/harness.md`](../../../lifecycle/harness.md))
  apply as for every slice.

## Out of scope

- Any lifecycle move from the browser (the CLI's `advance` and `discard`).
- Combining child projects' boards, and writing to another project's records.
- The backend operations themselves (TCW-69, TCW-70, TCW-71), the CLI's output
  contract and exit-code table (TCW-73), personal configuration (TCW-72), and the
  README's web app section (TCW-75). This slice uses them.

## Notes

- **Where the input came from.** There was no user to ask at this stage. This
  request is written from the ticket, the epic, TCW-69's confirmed spec and the
  sibling tickets in the epic reference pack. Reference material: asked; none
  provided beyond the epic pack, which is listed below.
- **Assumption:** the ticket's `spec/capabilities.yaml` means the declaration file
  TCW-69 settled, which lives at the item root (`<item>/capabilities.yaml`), as the
  owner confirmed on 2026-10-01.
- **Assumption:** "No Node.js at runtime" means at install time too. Today the client
  is built by contributors and committed into the Python package
  (`scripts/build_web.mjs`, `pyproject.toml` package data), so an installed TCW
  never needs Node to build anything; only the Fastify server needs Node to run.
- **Assumption:** "single process" also excludes child processes started per request,
  such as the desktop file opener the 2.x API starts. The spec decides this.
- **Builds on** TCW-69 (model and layout), TCW-70 (filesystem backend), TCW-71 (Jira
  backend, `tickets list` and `tickets adopt`), TCW-72 (`user.name`) and TCW-73
  (exit codes, `show --json`, `validate`). It cannot be finished before those land.
- **Self-hosting.** This changes `tcw/` itself, so from implementation onwards the
  repository's own board is driven by editing files, not through the CLI, as
  `CLAUDE.md` requires.

## References

- [TCW-77](https://proposit.atlassian.net/browse/TCW-77) (`intake.md`): the ticket;
  the agreed scope, the Jira-mode rule and the autocomplete table.
- [TCW-68](https://proposit.atlassian.net/browse/TCW-68): the epic; "a focused web app"
  is one line of its vision.
- TCW-69's `spec.md` (`docs/work/backlog/2026-10-01-tcw-69-…/spec.md`): the stage
  table, layout, `path`, verdicts, the backend interface and the declaration schema
  this slice must use without redefining.
- [TCW-70](https://proposit.atlassian.net/browse/TCW-70),
  [TCW-71](https://proposit.atlassian.net/browse/TCW-71): what each backend stores and
  where; Jira-only ticket commands; delegation.
- [TCW-72](https://proposit.atlassian.net/browse/TCW-72): `user.name`, the identity the
  assignee field offers in filesystem mode.
- [TCW-73](https://proposit.atlassian.net/browse/TCW-73): `tcw serve`'s stdout and exit
  codes; `show --json` and `list --json`, which the API should return unchanged.
- [TCW-75](https://proposit.atlassian.net/browse/TCW-75): owns the README's web app
  section; this slice owns `docs/guide/web-viewer.md`.
- `tcw/serve/__init__.py`, `tcw/serve/runtime.py`, `web/server/src/server.ts`: today's
  Python API, Node supervisor and Fastify server, which this slice reshapes.
- `docs/work/backlog/2026-09-19-aggregate-descendant-nodes-taxonomy-and-capabilities-in-tcw-serve`:
  an open item this slice makes obsolete, since child projects are no longer combined.
