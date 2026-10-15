---
name: commands-process-inbox
description: Decide on every arrival in a TCW project's work inbox, then write the request for each one accepted.
when_to_use: Use when a user asks to process, triage, or clear a TCW project's work inbox — deciding whether each arrival becomes work, accepting, splitting or turning it away, and running the request stage on each item accepted.
allowed-tools: Bash(tcw *), Read, Edit, Write
metadata:
    author: Brian Cefali
license: Apache-2.0
dynamic_skill: false # which skills a project may override, and why: ../README.md
---
**Version check.** Under Claude Code, skip this: the session-start hook already ran it. Under any other harness, once per session before your first `tcw` command, run `bash "<plugin>/scripts/check_versions.sh"`, where `<plugin>` is two folders above the folder holding this `SKILL.md`, and pass on anything it prints to the user.

Use the `work` skill. This skill covers the stage range **`inbox` →
`request`**.

1. Run `tcw work stage prompt inbox` and follow it over every arrival it
   names. Where arrivals are items at the inbox stage, `tcw work list --stage
   inbox` lists them; where the backend is Jira, they are the tickets
   `tcw work tickets list --json` lists. The prompt says how to accept, split
   or turn one away in this project's backend, and when to leave one for a
   person.
2. For each item accepted, run `tcw work stage prompt request <slug>` and
   write its request, asking the user whatever is unclear, since that is what
   the stage exists for. Where the backend keeps the request (in Jira, the
   ticket's description), the prompt has you propose changes in a comment
   rather than write it; a person moves the ticket on.
3. Report each arrival: accepted (with its slug), split (with every slug),
   turned away or left for a person (with the reason), and recorded on an
   existing item (naming it).

Do not move an item past request: running spec is the `commands-plan-work`
skill. Leave each accepted item at request with its request written.
