# TCW-68 — TCW 3.0: a simpler work lifecycle with Jira as a first-class backend

Imported on 2026-10-01 from [TCW-68](https://proposit.atlassian.net/browse/TCW-68) (jira-cloud).

_Grew out of TCW-67 (Formalize Jira in work lifecycle). The decision record from the design session is attached as_ {{TCW-68-design-decisions-2026-09-30.md}}. The child tasks carry those decisions as refined after an adversarial review of each, and where they differ from the attachment, the child task is current.

h1. Why

Since TCW gained Jira support, the work lifecycle has been hard to use smoothly. The root cause is that the same facts, above all a work item's status, are stored in two places (the repository and Jira), and a lot of machinery exists only to keep them in step. Behind that sits a wider lack of clarity: what each lifecycle stage is for, where its work happens, and what the TCW CLI and Jira are each responsible for.

h1. The vision

TCW 3.0 is what TCW would look like if we wrote it from scratch today: *simple, predictable and minimal*, in both its design and its implementation.

* *Every fact has exactly one owner.* A project picks one work backend. With Jira, Jira owns everything a non-engineer reads or changes: the request, status, assignee, estimates, links. The repository owns the technical record: specs, plans, implementation and review notes. Nothing is copied between them, so nothing can drift.
* *Jira is where product meets engineering.* Anyone in the organization (product, QA, support, marketing) can write a ticket describing what the product should do, in plain language. Engineers pick it up, and the technical detail lives in the repository, linked from the ticket. QA and product verify the result on the ticket.
* *Filesystem-only TCW stays first-class.* A project that does not use Jira works the same way, with everything kept in the repository.
* *The product's description lives with its code.* Taxonomy and capabilities stay in the repository and change in the same commit as the code that changes them, so any commit shows the product as it was at that moment. Tickets describe _changes_; the repository describes the _product_.
* *A clear lifecycle.* Each stage has one purpose and one folder: request (what, for anyone), spec (what, technically), plan (how), implement, review (the code), qa (the product's behavior), and postmortem. Items move between stages with one command, {{advance}}, and gates refuse by default unless the caller deliberately forces the move and says why.
* *TCW stays out of git.* TCW writes files and never commits, pushes or branches. Projects that want that behavior add it through their own prompts and hooks.
* *A CLI that agents and people can rely on.* Intuitive command names, useful help, the command's product on stdout, the narrative on stderr, and meaningful exit codes.
* *A focused web app.* {{tcw serve}} is for reading and editing TCW's documents and creating new TCW objects, with autocomplete on every reference and known value. It runs as a single Python process and leaves the lifecycle to the CLI.
* *Room for each person.* Untracked personal configuration lets each user state who they are and adjust TCW for their own workflow, inheriting from or replacing the team's settings, without changing anything for the team.

This is a major version with deliberate breaking changes. Existing projects move over by following a written migration guide with an agent, starting with the TCW repository itself.

h1. The work

# TCW-69: Core work model: stage table, item folders that never move, and {{advance}}
# TCW-70: Filesystem work backend on the new model
# TCW-71: Jira work backend: Jira as the single owner of status and the request
# TCW-72: Personal configuration: user identity and per-user overrides
# TCW-73: CLI pass: one command surface and one output contract across all three axes
# TCW-74: Rewrite stage prompts, procedures and skills for the new lifecycle
# TCW-75: Documentation for TCW 3.0: README, guides and the opt-in git example
# TCW-77: Web viewer: a single-process document reader and editor with autocomplete everywhere
# TCW-76: Migration guide from 2.x to 3.0.0, and migrate the TCW repository first

The core model (TCW-69) comes first; both backends and the web viewer build on it. The migration guide (TCW-76) comes last, once the 3.0 layout is settled.

While TCW's own code is being changed, its work is tracked by editing the board's files directly rather than through the {{tcw}} CLI, as the repository's contributor guide requires.
