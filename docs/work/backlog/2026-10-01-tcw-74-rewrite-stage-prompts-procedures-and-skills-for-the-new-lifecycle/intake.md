# TCW-74 — Rewrite stage prompts, procedures and skills for the new lifecycle

Imported on 2026-10-01 from [TCW-74](https://proposit.atlassian.net/browse/TCW-74) (jira-cloud).

Part of the TCW 3.0 redesign (epic TCW-68). The original decision record is attached to the epic; where this ticket differs from it, this ticket is current (it includes the outcome of an adversarial review).

h1. What this delivers

The instructions agents follow at each stage, rewritten for the new stages, artifacts and readers, free of any assumption about how a project uses git, with one source for each.

h1. The prompt set

One built-in prompt per stage table row that has work to do: inbox, request, spec, plan, implement, review, qa, postmortem. Completed and discarded have no prompt. Today's {{verify}} prompt and stage text are replaced by review and qa.

* *inbox*: decide whether an arrival becomes work. Filesystem mode: inbox-stage items. Jira mode: {{tickets list}} and {{tickets adopt}}. No {{inbox accept}}, no {{intake.md}}.
* *request*: what to build at a product level, written for any reader. Template sections:
** What and why
** Product changes: what users will be able to do differently; what the change adds, changes or removes; "none" is valid
** Out of scope
** Constraints
** References, each with one line on why it matters
* Light on code references unless the work is technical by nature (TCW-67).
* *spec*: what to build technically. Writes {{spec/spec.md}} and {{spec/capabilities.yaml}}, and posts the *QA plan* with {{tcw work comment}}. The comment is the plan's only home; a revised spec posts a new comment that supersedes it. Minimum contents of the QA plan:
** one scenario per product change in the request
** expected behavior
** environment or accounts needed
** what is not tested
* *plan*: how to build it, as ordered, checkable steps.
* *implement*:
** Builds it.
** Changes taxonomy and capability records in the same change as the code.
** Writes {{implement/round-N.md}}.
** A later round reads the latest rejection: a review round file, a qa round file, or in Jira mode the latest qa rejection comment.
* *review*: code verification against the spec and plan, including that the records changed alongside the code. Writes {{review/round-N.md}} with a verdict.
* *qa*: product behavior against the request and QA plan. Filesystem mode: {{qa/round-N.md}}. Jira mode: a person moves the ticket; a rejection needs a comment saying why.
* *postmortem*: writes {{postmortem/postmortem.md}}, plus an optional comment (off by default) about what the request missed, in the request's language.
* Every prompt that resumes work reads the newest {{<stage>/handoff-*.md}} first.

h1. Capabilities skill reversal

Stated explicitly:

* no seeding {{Missing}} records at planning;
* no planning-doc pointers;
* no flipping records at completion.

Records change during implement, and {{Missing}} means a known gap the team has acknowledged, not a plan.

h1. Backend-specific text

* One file per stage. Backend-specific passages are marked with {{<!-- backend: jira -->}} / {{<!-- backend: filesystem -->}} sections, and {{stage prompt}} strips the ones that don't apply.
* Project and personal prompt files get the same filtering.

h1. One source each

* Stage text exists once: today's duplicates in {{skills/work/references/lifecycle/stage-*.md}} are deleted.
* Each procedure exists once: the duplicate copies under {{tcw/work/procedures/}} and {{skills/work/references/procedures/}} have already diverged.
* {{tcw/work/templates.py}} is deleted along with {{scaffold}}; the request template lives in the request prompt.

h1. No git in built-in text

* Built-in prompts, procedures, skills and agents never mention git. Committing, pulling or pushing is the project's choice, made through its own bindings or hooks.
* The scope is everything matching git, commit, push, pull, worktree, trunk or branch: about 41 files outside {{documentation-sync}}. The heaviest are:
** the work skill's {{transitions.md}} and {{commands.md}}
** {{commands-pause-work}}
** {{create-work.md}}
** the post-mortem agent's "commit history"
* The {{documentation-sync}} release flow is outside this rule.
* Strings in the Python code belong to TCW-73.

h1. Disposition of every skill, agent and procedure

The spec must include a keep / rewrite / delete table covering every entry in {{skills/}}, {{agents/}} and {{tcw/work/procedures/}}, defaulting to delete. Candidates to settle:

* the five {{commands-*}} skills ({{commands-verify-work}} is built on the old verify);
* {{work-stage}}, which duplicates {{stage prompt}};
* the {{post-mortem}} skill and agent;
* the {{verifier}} and {{backlog-auditor}} agents;
* {{work-create}};
* the {{extras-*}} skills;
* {{skills/work/references/transitions.md}}, {{cross-node-deltas.md}} and {{epic-deltas.md}};
* the {{delegation}}, {{unattended-work}}, {{triage-issues}} and {{consolidate-plans}} procedures.

The work, capabilities, taxonomy, configure and setup skills are rewritten. The setup skill gains the Jira workflow compatibility walkthrough, built on {{tcw validate --remote}}. The pause-work skill (if kept) writes {{<current stage>/handoff-<timestamp>.md}}.
