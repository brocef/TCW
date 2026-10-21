# Spec — Describe the real project setups TCW must work in, and check every spec against them

## Capability changes

None. This changes this repository's own documents and its own lifecycle
configuration, not what TCW does for its users.

## Problem

TCW's specs are checked against the abstraction litmus test
(`docs/lifecycle/abstraction.md`) and the harness rule
(`docs/lifecycle/harness.md`), but against no list of the setups TCW actually
runs in. The setups are known only piecemeal: the relationship model is in
`docs/guide/multi-repo.md`, one layout is in `docs/lifecycle/implementation.md`
("A project's work store is often in a different git repository"), and the
rest lives in the projects themselves. Defects that show only in one setup
ship and are found by the project that hits them: issues #15-18
(implementation.md), and TCW-100/TCW-101, found by an agent working a monorepo
whose work stores sit in a separate workspace repository.

## Goals

1. `docs/use-cases.md` describes each architecture TCW is used in, from a real
   project, with what it requires of TCW and where TCW is known to fall short
   (by work item).
2. It also describes the working situations that cut across architectures:
   who is present to decide, which harness, which backend, what is on this
   machine.
3. It ends with a checklist a spec author can run.
4. Every spec written in this repository names the use cases it touches: a
   `## Use cases` section in both spec templates.
5. A documentation entry makes the document move with the code.

## Non-goals

Changing TCW's behavior in any setup; deciding TCW-99's redesign; publishing
the document as user documentation (it is for people changing TCW).

## Design

1. **The document.** Sections: how to use it; the dimensions that vary; one
   section per architecture (UC-1 to UC-6), each with a real example, its
   layout, its requirements as checkable statements, and known gaps by item;
   cross-cutting situations (S-1 onward); the checklist; how to add a case.
   Real projects are named, because the point is that the cases are real;
   only their shapes are described, never their content.
2. **Spec templates.** `docs/lifecycle/templates/spec.md` and `spec-bug.md`
   gain `## Use cases`, after `## Abstraction litmus test`: "Name each case and
   situation in `docs/use-cases.md` this change touches, and say how it
   behaves in each. 'None' needs a reason."
3. **Documentation entry** in `tcw-config.yaml`: `docs/use-cases.md`, trigger
   `Project-Setup-Change`: update when a change alters how TCW behaves in one of
   its setups, or a new real setup or known gap is found.
   `tests/test_repo_lifecycle.py`'s `DOCUMENTATION` gains the entry.
4. **`CLAUDE.md`** names the document beside the prime directive, so a session
   that changes TCW outside the lifecycle still finds it.

## Abstraction litmus test

No new operation.

## Use cases

This change is about the cases themselves; it changes no behavior in any of
them.

## Acceptance criteria

1. `docs/use-cases.md` has a section for each of: a standalone project; a
   library read by others; a monorepo of several projects with inheritance;
   several repositories with many projects and inheritance; work stores kept
   in another repository; one Jira project shared by several TCW projects.
   Each names a real example and lists requirements and known gaps.
2. Every behavior it states is checked against the code or a guide, with the
   file named.
3. Both spec templates carry `## Use cases`; `test_a_template_carries_every_
   spec_section` passes.
4. `tcw work docs` lists the new entry; `tcw validate` is clean; the
   documentation-entry test passes.
5. Bare `pytest` passes.

## Risks

- **The document drifts.** Guarded by the documentation entry, and by the
  spec section that makes every author open it.
- **It names private projects.** It describes their shapes only, as
  `docs/lifecycle/implementation.md` already does.
