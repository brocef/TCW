# CLI pass: one command surface and one output contract across all three axes

TCW 3.0 (epic [TCW-68](https://proposit.atlassian.net/browse/TCW-68)) promises a
command line that people and agents can rely on. Today each command group grew on
its own: names, flags, where output goes and what an exit code means all differ
from one command to the next. This slice makes the whole `tcw` command line follow
one set of rules, across `tcw work`, `tcw taxonomy`, `tcw capabilities` and the
top-level commands.

## What is wanted

1. **One output contract.** Standard output (stdout) carries the command's
   product and nothing else: the slug a command created, the stage an item moved
   to, a path, a list, a record. Standard error (stderr) carries the narration:
   what happened, every file written or removed, and what to do next. No command
   asks a question interactively; long text (a comment, the request on `new`)
   arrives on standard input.
2. **One exit-code table**, the same for every command: 0 ok, 1 error, 2 usage,
   3 refused, 4 not found, 5 remote unreachable, 6 "the item moved, but something
   after the move failed". The ticket lists what falls under each.
3. **One way to name a work item.** A command accepts the full slug, the bare
   folder name within the current project, or (in Jira mode) the Jira key, and
   nothing else: no prefix matching, no old names after a rename. It always prints
   the full slug.
4. **One command shape.** Commands read `tcw noun [child-noun] verb`, with
   single-purpose readers (`lifecycle`, `docs`, `procedure`) allowed to stand
   without a verb. The ticket lists the final command set for `tcw work` and the
   top level, and what is removed or merged.
5. **Useful `--help`** on every command, to one standard.
6. **Taxonomy and capabilities get the same pass.** Same contract and help
   standard; `taxonomy check` and `capabilities check` fold into `tcw validate`;
   `extends` stays; none of these commands touch git; `capabilities drift` uses
   the drift rule from TCW-69, reading each completed item's declared record
   changes.
7. **`tcw validate`** runs TCW-69's mid-work records check in place of today's
   capability gate, and gains `--remote` for the Jira checks.
8. **"Project" replaces "node" everywhere it survives**: commands
   (`tcw work nodes` becomes `tcw projects list`), the `connected-projects`
   config keys, the `TCW_NODE_ROOT` hook variable, and internal code.
9. **No git in the Python code's built-in help and messages.**
10. **The `detect-capability-drift` capability record is rewritten**, because it
    promises that drift never depends on the work axis, and 3.0 drift reads
    completed work items.

The agreed decisions are in the ticket ([TCW-73](https://proposit.atlassian.net/browse/TCW-73));
`intake.md` holds it as imported, including its "Update from TCW-69's spec"
section. They are the requirement. Where they differ from the epic's attached
decision record, the ticket is current. Where they differ from TCW-69's confirmed
spec on anything the core model defines, TCW-69 wins.

## Constraints

- **Breaking changes are expected.** This ships in 3.0.0. No 2.x compatibility
  code and no aliases for old command names; migration is a written guide
  (TCW-76).
- **Simplicity of implementation comes first**, and predictability for agents
  matters as much as for people.
- **Build on TCW-69 without redefining it**: the stage table, slugs, exit-code
  constants, `advance`'s outcomes, the records check and drift are TCW-69's.
- **Every operation passes the abstraction litmus test**
  ([`docs/lifecycle/abstraction.md`](../../../lifecycle/abstraction.md)).
- **Anything that must be guaranteed lives in the CLI**, which behaves the same
  under Claude and Codex ([`docs/lifecycle/harness.md`](../../../lifecycle/harness.md)).
- **TCW never changes git state.** It writes files, names them on stderr, and may
  read git for checks.

## Out of scope

Owned by sibling slices:

- The work model itself, `advance`, gates and drift logic: TCW-69.
- The filesystem backend's storage and the behavior of the item commands it
  serves: TCW-70.
- The Jira backend, `tickets list` / `tickets adopt`, and what `validate --remote`
  checks in Jira: TCW-71.
- `tcw config show` and personal configuration: TCW-72.
- `tcw serve`: TCW-77.
- Prompt, procedure and skill text, including git mentions there: TCW-74.
- User-facing documentation, including the written description of this contract:
  TCW-75.
- Migration: TCW-76.

## Notes

- **There was no user to ask.** This request was written from the ticket, the
  epic, its design record, TCW-69's confirmed spec and the sibling tickets, as the
  epic's reference pack directs. Reference material was not asked for; the
  references below are the ones the pack supplies.
- **Assumption:** the ticket's stdout list covers the work commands only. Taxonomy,
  capabilities and the top-level commands need their own rows, chosen by the spec
  under "same output contract".
- **Assumption:** "the `connected-projects` config keys" in the ticket means the
  `connected-projects` key itself, whose name still says "connected"; its
  `parent`, `children` and `upstream` entries are already in project terms.
- **The boundary with TCW-70 is not drawn by either ticket.** TCW-70 "wires the
  work model into `tcw work`" and TCW-73 owns "the final command surface". The
  spec must say which slice builds which command, so the two do not both claim
  one.
- **The ticket is out of date in one place:** it says `capabilities drift` reads
  `spec/capabilities.yaml`; its own update section and TCW-69's confirmed spec put
  the file at the item root (`<item>/capabilities.yaml`).
- **This may be larger than one item.** It touches every command, the tree stores'
  write path, `tcw validate`, drift, the project registry and the ledger. The spec
  should say whether it splits.
- **Self-hosting.** This changes `tcw/` itself, so from implementation onwards the
  repository's own board is driven by editing files, not through the CLI, as
  `CLAUDE.md` requires.

## References

- [TCW-73](https://proposit.atlassian.net/browse/TCW-73): the ticket; the agreed
  decisions for this slice (`intake.md`).
- [TCW-68](https://proposit.atlassian.net/browse/TCW-68): the epic's vision ("a CLI
  that agents and people can rely on") and its attached design record.
- `docs/work/backlog/2026-10-01-tcw-69-core-work-model-stage-table-item-folders-that-never-move-and-advance/spec.md`:
  TCW-69's confirmed spec; the exit codes, slug parsing, `advance` outcomes,
  records check and drift this slice wires in.
- [TCW-70](https://proposit.atlassian.net/browse/TCW-70),
  [TCW-71](https://proposit.atlassian.net/browse/TCW-71),
  [TCW-72](https://proposit.atlassian.net/browse/TCW-72),
  [TCW-77](https://proposit.atlassian.net/browse/TCW-77): the slices that build
  commands this slice gives their final shape.
- [TCW-74](https://proposit.atlassian.net/browse/TCW-74),
  [TCW-75](https://proposit.atlassian.net/browse/TCW-75),
  [TCW-76](https://proposit.atlassian.net/browse/TCW-76): the slices that rewrite
  skills and docs for the new surface, document the contract, and carry the
  old-to-new command table into the migration guide.
- `tcw/cli.py`, `tcw/work/cli.py`, `tcw/taxonomy/cli.py`,
  `tcw/capabilities/cli.py`: the argparse definitions of today's command surface.
- `tcw/validate.py`: today's `tcw validate`, including the `capability_gate`
  call this slice replaces.
- `docs/capabilities/capabilities/detect-capability-drift/`: the record the
  ticket says must be rewritten.
