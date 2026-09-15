# Let a project override the tools and procedures TCW's own skills mandate

## What should change and why

TCW's shipped skills are supposed to be polymorphic: the skill carries the
reasoning, the project carries the facts. `work.lifecycle.stages.<id>.prompt`
already does this for lifecycle stages — a stage's instructions are composed at
read time from `builtin:`, `file:` and `skill:` sources a maintainer declares —
and the doctrine is stated outright in
`skills/tcw-work/references/procedures/delegation.md`: "Delegable means
permitted, never required", "**No behavior depends on it**", and, of the three
shipped agents, "all three are **accelerators only**. Every document they serve
stands alone without them."

Some shipped skills do not honor that. They name a specific third-party binary,
a specific model, a specific agent, or a specific git workflow as a
**requirement**, in prose a project maintainer has no way to override. The
result is a skill that only works in the environment of the person who wrote it.

The exemplar is `skills/tcw-extras-autonomous-work/SKILL.md`:

- **Two named advisors, mandatory.** "Run both in parallel" — the Codex CLI
  (line 22, with its exact invocation `codex -C <repo> exec -c
  sandbox_mode=read-only`, three of its failure modes, and the standing claim on
  line 40 that "Codex is the reliable half") and an Opus subagent (line 26,
  `Agent tool, model: opus`). The adjudication rule is built on the count — "not
  a majority (there is no majority of two)" (line 32) — so the number is
  load-bearing prose, not an example.
- **Harness-specific tooling given as instruction.** `Agent tool` and
  `SendMessage` (line 38) are Claude Code mechanics. The same `skills/` directory
  ships in `.codex-plugin/plugin.json`, so under Codex this skill instructs the
  agent to use two tools that do not exist and to consult a second copy of
  itself.
- **A pinned model.** `model: opus` dates the file and presumes that tier is
  available to the reader.
- **An agent TCW does not ship.** `adversarial-code-reviewer` (line 49) occurs
  exactly once in the whole repository — on that line. It is hedged with "where
  the project has one", but it is still one user's agent name in a published
  skill.
- **One git workflow, hardcoded.** "merge the feature branch into main
  **locally**. Never `git push`" (line 55) fixes both the trunk branch name and
  the publish policy in prose, while `work.trunk-branch` and
  `work.publish-transitions` already exist in `tcw-config.yaml` as the
  maintainer's way to say exactly those two things.
- **One version policy, hardcoded.** "Never cut one. Accumulate into
  `upcoming.md`" (line 54) assumes this repository's own changelog rotation.
- **None of it is declared.** The skill has neither `allowed-tools:` nor
  `compatibility:` in its frontmatter, although `tcw-setup` and
  `tcw-extras-triage-issues` both declare theirs. Its hardest external
  dependency — a second AI CLI, installed, on PATH and authenticated — is
  invisible to a reader deciding whether the skill applies to them.

## What is being asked for

Two things, in this order.

1. **Audit every shipped skill and procedure for this class of defect** — a
   tool, binary, model, agent name, forge or procedure presented as mandatory
   where the project should be able to say otherwise. The audit needs a stated
   test, because not every named tool is a violation and the sweep should not
   turn into a purge:
     - `skills/documentation-sync/references/cut-version.md` names npm, Cargo,
       `pyproject.toml`, plugin manifests, a `VERSION` file and Go module tags —
       it enumerates ecosystems instead of mandating one. That is the pattern
       working.
     - `skills/tcw-extras-triage-issues` hard-requires the GitHub CLI and says
       "Do not fall back to scraping the web UI", but declares it in
       `compatibility:` and is a skill *about* GitHub issues. An honest declared
       requirement is a different thing from a silent one — though it is worth
       asking why the tracker axis is abstracted behind `work.tracker` while the
       forge is not.
     - `skills/tcw-extras-autonomous-work` declares nothing and mandates
       everything. That is the defect.
2. **Make what the audit finds overridable by the project maintainer**, in the
   same spirit as the stage-prompt composition rather than by inventing a second
   mechanism. Whether that is a new `work.*` block, a lifecycle binding at a new
   id, or simply rewriting the skill so the roster is an example and the reasoning
   is the requirement, is a `spec` question — but a project that has configured
   nothing must keep working as it does today.

## Out of scope

- The version-cut half of the same principle, already tracked as
  `2026-08-18-serve-version-cut-instructions-from-tcw-config-yaml-instead-of-the-agent-guide`.
  This item should not redesign that; if `work.*` config for version cutting has
  landed by the time this is specced, reuse it for the autonomous skill's
  version rule rather than adding a second way to say it.
- Renaming skills or agents — `2026-09-15-drop-the-tcw-prefix-from-the-plugin-s-skill-and-agent-names`
  edits the same files for an unrelated reason.

## Origin

Raised in chat by the user after reading `tcw-extras-autonomous-work` and
noticing it requires Codex reviews. Described as "a violation of the polymorphic
and generic behavior that we've been building out recently with the dynamic
context injection and dynamic prompts for the lifecycle stages", with the
explicit ask to re-evaluate all the other commands and procedures for the same
problem so TCW does not "require certain technologies or steps or procedures".

## References

- `skills/tcw-work/references/procedures/delegation.md` — the doctrine this
  violates, in TCW's own words; the audit's test should be derived from it.
- `skills/tcw-configure/references/work.md` — the existing composition mechanism
  (`work.lifecycle.stages.<id>.prompt`, kinds `builtin:`/`file:`/`skill:`) and
  the `work.trunk-branch` / `work.publish-transitions` keys the autonomous
  skill's closeout rule bypasses.
- `2026-08-18-serve-version-cut-instructions-from-tcw-config-yaml-instead-of-the-agent-guide`
  — partly covers: same principle, stated there as "Config carries the facts;
  the guide carries the reasoning", applied to one other path.
- `2026-08-31-upstream-the-acceptance-criteria-coverage-table-to-tcw-s-own-spec-stage`
  — the mirror-image question, worth reading before the audit: it holds off on
  shipping this repo's own invention to every TCW user because "a rule that
  ships to every TCW user should have been used in anger first".
- `2026-09-15-fill-codex-gaps-in-skills-and-give-each-skill-one-capability` —
  same violation class, opposite remedy (write the missing Codex path in, rather
  than make it overridable); the two should agree on which skills get which
  treatment.
- `2026-09-11-refine-the-plugin-skills-and-lifecycle-prompts-against-the-eval-findings`
  — the other open item that edits shipped skill prose wholesale; sequence to
  avoid collision.
