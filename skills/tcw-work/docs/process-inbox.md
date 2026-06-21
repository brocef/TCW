# Recursive process-inbox

`docs/work/inbox/` holds raw request docs — including `delegate`/`escalate` drops carrying `---\nfrom: …\n[initiative: …]\n---` front-matter. Inbox holds raw `.md` docs only; `tcw work new` creates a **backlog** folder, never an inbox folder.

For each doc:
1. Read it; extract `initiative:` / `from:` from the front-matter.
2. `tcw work new "<title>" [--initiative <slug>]`, piping the **body with the front-matter stripped** as stdin (`tcw work new` reads stdin for the body but does not parse front-matter).
3. `git rm` the source doc — it has been ingested into the new backlog item.

Across child nodes (`tcw work nodes`), an orchestrator triages **its own** inbox and *delegates* down (`tcw work delegate <child> "<title>"`); it never writes into a child's tracking tree directly.
