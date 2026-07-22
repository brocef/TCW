# Recursive process-inbox

`docs/work/inbox/` holds raw request files or folder packages, including
`delegate`/`escalate` Markdown drops. Raw entries are not work items.

For each entry:

1. Run `tcw work inbox list`, then `tcw work inbox show <entry>` to inspect it.
2. If it should become formal work, run
   `tcw work inbox accept <entry> [--title <title>]`. The command creates the
   backlog item, preserves named attachments, generates `initial-request.md`,
   and consumes the raw source only after success.
3. Use `tcw work edit` for formal metadata such as an `initiative` relation when
   the raw delegate/escalate body requests one.

Across child nodes (`tcw work nodes`), an orchestrator triages **its own** inbox and _delegates_ down (`tcw work delegate <child> "<title>"`); it never writes into a child's tracking tree directly.
