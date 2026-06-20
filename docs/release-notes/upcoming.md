# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Update a capability's status without hand-editing

`tcw capabilities set <id> --status Supported` (or `--field "K=V"`) updates a
capability's status or fields in place — the command the lifecycle uses to flip a
capability from "missing" to "supported" as work completes. Add `#heading` when a
file holds more than one capability.

## Skills that drive the whole lifecycle

Two skills now ship alongside the tool and teach an agent to run it end-to-end:

- **tcw-work** — pick up an inbox request, plan a change (user-facing first), move
  it through start → complete, resume work across sessions, and split big work
  into an epic spanning several repos.
- **tcw-capabilities** — declare the capabilities a change will add, catch
  conflicts with what's already documented, flip the capability ledger when the
  work lands, and agree on shared wording across repos.
