# Keep a reporter's private project details out of an upstream TCW report

Filed from chat. The `tcw-report` skill teaches an agent how to file a bug or a
suggestion on **this project's public issue tracker**. The agent doing the
filing is working inside somebody else's project, and that project may well be a
private repository.

Nothing in the skill tells it to be careful about that. The skill closes with
the opposite instruction:

> Keep it concrete: a real command, a real error, a real scenario beats an
> abstract description.

So an agent filling in the bug skeleton does the natural thing — it pastes the
command it actually ran, the output it actually got, and the item it was
actually working on. Real node ids, work-item slugs, capability wording,
absolute paths, repository names and branch names all travel with that, straight
into a public issue that nobody can un-publish.

## What is wanted

Implore an agent writing an upstream report **not** to disclose specifics about
the project it is working in. It should instead invent a **generic example that
mirrors the reporter's setup** — the same shape of node, config, or item, with
the identifying detail replaced — so the maintainer still receives something
concrete enough to act on.

Beyond that, encourage the agent to sketch **steps that reproduce the problem on
a fresh environment**: a clean install and a scratch project, starting from
nothing.

## Constraints

Decisions taken during this stage, in answer to direct questions:

- **Generic by default, with an approval escape hatch.** Generic is what the
  agent produces on its own. It may include a real detail only if it asks the
  user first and they explicitly approve that specific disclosure. It must not
  decide on its own that a given detail is harmless.
- **Verbatim output is preferred generic, but the reporter's choice.** State the
  preference for output captured from a generic reproduction; a reporter who
  chooses to paste output from their own system and environment may do so. This
  half is a preference, not a prohibition.
- **Suggest delegating the reproduction.** Point out that the agent can hand the
  reproduction to a subagent or an agent team member and have it done in a
  temporary directory, rather than in the reporter's own checkout.
- **Fresh-environment steps are encouraged, not required.** A clean-room
  reproduction is sometimes impractical; the report should still be fileable
  without one.

## Out of scope

- `tcw-triage-issues`, which writes replies on the user's *own* repository.
  Nothing leaves the project there, so it is a different problem.
- Any change to the `tcw` CLI. This is skill guidance.

## Notes

- The tension to resolve, rather than ignore: the skill's existing "keep it
  concrete" advice is good advice and the reason most reports are actionable.
  Generic must not become vague. A mirrored example is the thing being asked
  for — abstraction that keeps the shape.
- Reference material: asked; none provided.
