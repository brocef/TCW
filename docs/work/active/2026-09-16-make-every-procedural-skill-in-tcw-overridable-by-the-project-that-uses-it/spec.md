# Spec — Make every procedural skill in TCW overridable by the project that uses it

An overview spec. Child boundaries, ordering and initiative-wide acceptance
criteria only; each child specs its own implementation.

## Capability changes

Planned ledger deltas only. Nothing is written to the ledger at this stage.
Children carry the deltas for the skills they convert; this epic owns the two
below.

```yaml
added:
    - work/run-a-procedure # composing a non-stage procedure's instructions
    - work/configure-procedures # declaring a project's own procedure bindings
changed:
    - work/configure-the-work-lifecycle # gains a sibling key it must not absorb
```

`work/run-a-lifecycle-stage` is **not** changed. Procedures are resolved by the
same library but are not stages: they have no gate, no artifact and no place in
the ladder, so folding them into that capability would make its own text false.
The two new capabilities mirror the pair that already exists for stages —
`work/run-a-lifecycle-stage` and `work/configure-the-work-lifecycle` — because
running and configuring are separate user actions there and are here too.

Each child converting a skill carries `changed: skills/<skill-name>` for the
skill's own ledger entry, since what the skill does is unchanged but where its
text comes from is not.

## Problem

1. **Composition stops at lifecycle stages.** `resolve.py:445` reads
   `policy.stage(stage_id) or [Binding(kind="builtin")]` — a project's bindings
   if it has them, TCW's shipped text otherwise. `LifecyclePolicy`
   (`tcw/store/base.py:1560-1590`) exposes `stage()`, `stage_checks()`,
   `transition()` and `artifact()`, and nothing else. The configuration surface
   under `work.lifecycle` is fixed at `tcw/store/base.py:2267` to
   `{"stages", "transitions", "timeout", "artifacts", "output-cap"}`, and
   `load_builtins()` (`tcw/work/resolve.py:48-86`) derives its prompt set from
   `set(STAGE_IDS)` — the seven ids at `tcw/store/base.py:932`. There is no key,
   no id space and no verb for a procedure that is not one of those seven.

2. **So every other procedure ships as fixed prose.** The worst case is
   `skills/tcw-extras-autonomous-work/SKILL.md`, which mandates:
   - two named advisors, the Codex CLI with its exact invocation (`:22`) and an
     Opus subagent through Claude Code's `Agent` tool (`:26`), with the
     adjudication rule built on the count — "not a majority (there is no majority
     of two)" (`:32`);
   - `SendMessage` (`:38`), a Claude Code tool, and the claim "Codex is the
     reliable half" (`:40`);
   - `adversarial-code-reviewer` (`:49`), whose only occurrence in the repository
     is that line;
   - one git closeout, "merge the feature branch into main **locally**. Never
     `git push`" (`:55`), although `work.trunk-branch` and
     `work.publish-transitions` already exist for exactly those two statements
     (`skills/tcw-configure/references/work.md:113-123`);
   - one version policy, "Never cut one. Accumulate into `upcoming.md`" (`:54`).

   Its frontmatter (`:1-4`) carries neither `allowed-tools:` nor
   `compatibility:`, while `skills/tcw-setup/SKILL.md` and
   `skills/tcw-extras-triage-issues/SKILL.md` both declare theirs — so its
   hardest dependency is undeclared.

3. **It contradicts TCW's own doctrine.**
   `skills/tcw-work/references/procedures/delegation.md:22-26` says "Delegable
   means permitted, never required" and "**No behavior depends on it**";
   `:68-70` says the three shipped agents are "**accelerators only**. Every
   document they serve stands alone without them."

4. **The same skills ship to Codex.** `.codex-plugin/plugin.json` points `skills`
   at `./skills/`, the same directory, so a Codex reader of
   `tcw-extras-autonomous-work` is told to use the `Agent` tool and
   `SendMessage`, neither of which that harness has, and to consult a second
   instance of the harness it is already running under.

5. **Nothing marks which skills are which.** A reader cannot tell
   `skills/tcw-work-stage/SKILL.md`, whose body is deliberately a template around
   injected content (`:20`, `:24`), from `skills/tcw-extras-autonomous-work`,
   whose body is one maintainer's practice — both are `SKILL.md` files of similar
   length.

## Goals

1. **The two rules are written down** in a document the classification cites and
   a future skill author reads before adding a skill.
2. **Every shipped skill, reference document and agent is classified** against
   them, with the verdicts recorded.
3. **A procedure composition point exists** with the same binding grammar,
   the same `builtin` floor and the same resolver as stages, reached by a `tcw`
   CLI verb rather than by context injection alone.
4. **Every skill classified overridable composes its body** from that point,
   with today's text shipped as its `builtin` default, so a project that
   configures nothing behaves exactly as it does today.
5. **A reader can tell the two kinds apart** from the skill file itself.
6. **The exemplar mandates nothing.** `tcw-extras-autonomous-work`'s body states
   what an advisor must be and how many are wanted; the roster, the review
   procedure, the closeout and the version policy come from resolved text, whose
   default is today's wording.

## Non-goals

- **Changing what any converted skill does.** This initiative moves where a
  skill's instructions come from. A skill that mandated something still
  recommends it, as a default.
- **Making `tcw-configure`, the three axis skills, `tcw-extras-report` or
  `tcw-setup` overridable.** Fixed under Rule 1.
- **Making the four `tcw-commands-*` skills overridable.** Fixed under Rule 2.
- **A second binding grammar.** Procedures reuse `Binding`, its kinds and its
  `when:`; only the id space and the config key are new.
- **Executing procedure bindings.** Like stage bindings, they are read, never
  run (`tcw/store/base.py:1571-1574`). `pre`-style checks are out of scope.
- **The version-cut procedure**, owned by
  `2026-08-18-serve-version-cut-instructions-from-tcw-config-yaml-instead-of-the-agent-guide`.
- **Renaming any skill or agent**, owned by
  `2026-09-15-drop-the-tcw-prefix-from-the-plugin-s-skill-and-agent-names`.
- **Codex install and `<plugin>` placeholder gaps**, owned by
  `2026-09-15-fill-codex-gaps-in-skills-and-give-each-skill-one-capability`.

## Design

### The test, stated once

**Rule 1 — authority.** TCW owns the shape of what is produced: the three axes'
data model, the artifacts, the transitions, the configuration surface, and TCW's
own upstream processes. The project owns the conduct that produces it.

**Rule 2 — payload.** A skill carrying no procedure of its own has nothing to
override, whatever Rule 1 says about its subject.

Rule 2 is checked first, because it is cheaper and decides the four command
skills without an authority argument.

### Where the mechanism goes

**A CLI verb, not injection.** `docs/lifecycle/harness.md` is binding here:
"anything that must be guaranteed belongs in the `tcw` CLI, which behaves
identically under both harnesses", and dynamic context injection is Claude-only.
A converted skill's instructions are a requirement, not an ergonomic, so the
composition happens in `tcw`. Injection is how a Claude reader gets it inline;
the manual fallback block — as
`skills/tcw-work-stage/SKILL.md:41-49` already does it — is how a Codex reader
gets the same text.

**`work.procedures`, a sibling of `work.lifecycle`, not a key inside it.**
Procedures have no gate, no artifact, no `pre` and no position in the ladder.
Nesting them under `lifecycle` would put four keys that mean "stage machinery"
beside one that does not, and `tcw/store/base.py:2267`'s top-level set is the
place that would have to lie about it.

**Everything else is reused.** `Binding` and its kinds, `when:`, the
`timeout`/`output-cap` limits, `_resolve_one` (`tcw/work/resolve.py:188-209`)
and the `or [Binding(kind="builtin")]` floor (`:445`) are the mechanism; a
`PROCEDURE_IDS` tuple beside `STAGE_IDS` and a `tcw/work/procedures/<id>.md`
directory beside `tcw/work/prompts/` are the additions. `load_builtins()`
already derives its set from the id tuple and raises when a file is missing
(`tcw/work/resolve.py:70-85`), so adding an id without its default text fails at
load rather than shipping a silent procedure.

**Storage abstraction.** A procedure's bindings are node configuration, read
through the same config path as `work.lifecycle`; resolution reads files under
the node root and package resources. Neither is a store operation, so the
litmus test is satisfied for the same reason it is for stage prompts. No
`WorkItem`, no status and no transition is involved — a procedure is not
item-scoped, which is also why it needs no gate.

### The marker

A frontmatter key on every `SKILL.md`, proposed by the requester as
`dynamic_skill: true|false`. It is inert to both harnesses and exists for a human
reader. A test asserts that every shipped skill carries it and that its value
agrees with the classification document, so the marker cannot drift from the
verdicts — which is what turns a comment into a check. Whether `tcw validate`
should also report it is left to the child; it governs TCW's own skills, not a
user's project, so the test is the stronger place.

### Child boundaries

| # | Child | Delivers | Blocked by |
| --- | --- | --- | --- |
| 1 | The two rules and the classification | The rules document, the verdict for every skill, reference document and agent, and the frontmatter marker with its test | the routing item |
| 2 | The procedure composition point | `PROCEDURE_IDS`, `tcw/work/procedures/`, `work.procedures` config and validation, the CLI verb, `tcw-configure` reference text, tests | the routing item |
| 3 | Convert `tcw-extras-autonomous-work` | The exemplar: body states requirements, today's text becomes its default, frontmatter declares its dependencies | 1, 2 |
| 4 | Convert `references/procedures/*` | All five documents, current contents as defaults | 1, 2 |
| 5 | Convert `tcw-extras-triage-issues` and `tcw-post-mortem` | Both, with the forge question answered for the first | 1, 2 |
| 6 | Convert `documentation-sync` and `tcw-work-create` | Both; coordinates with the version-cut item if it has landed | 1, 2 |

Children 3–6 are genuinely parallel and must not be chained to each other —
`epic-deltas.md` calls a false blocker "a lie the tool will enforce". Child 1
does not block 2: the mechanism's shape does not depend on which skills use it,
and 2 is the long pole.

### Affected nodes

One node, `tcw` itself. No `delegate`, no cross-node relation. The Proposit
workspace's `autonomous-work-proposit` is a sibling copy of the exemplar in a
different repository and is out of scope here; whether it follows is that
workspace's decision once this lands.

## Acceptance criteria

The initiative is done when all of these hold on `main`.

1. A document under `skills/` states Rule 1 and Rule 2 and is reachable from a
   shipped skill, so an author meets it without being told it exists.
2. Every `skills/*/SKILL.md` carries the marker key, and a test fails if one does
   not, or if a file's value disagrees with the classification document.
3. The marker reads fixed for `tcw-taxonomy`, `tcw-work`, `tcw-capabilities`,
   `tcw-configure`, `tcw-extras-report`, `tcw-setup` and the four
   `tcw-commands-*`; overridable for `tcw-extras-autonomous-work`,
   `tcw-extras-triage-issues`, `documentation-sync`, `tcw-post-mortem` and
   `tcw-work-create`. `tcw-work-stage` is recorded with its own verdict and the
   reason, since it composes already.
4. `tcw work procedure prompt <id>` (or the verb the mechanism child names)
   prints TCW's shipped text for every procedure id in a checkout that has
   configured nothing, and exits 0.
5. With a `work.procedures` binding declared for an id, the same command prints
   the project's text in declaration order, and `builtin: true` still resolves to
   TCW's own — the behaviour `resolve.py:445` gives stages today.
6. `tcw validate` reports an unknown procedure id, a malformed binding shape, a
   blank or duplicated reference, and a kind used where it is not allowed — the
   checks `skills/tcw-configure/references/work.md:16-19` already promises for
   lifecycle bindings.
7. Adding a procedure id without its default file raises at load, the way a
   missing stage prompt does (`tcw/work/resolve.py:76-80`).
8. Every converted skill's body contains no named third-party binary, model,
   agent name or git branch name. `grep -niE '\b(codex|opus|sonnet|haiku|sendmessage|adversarial-code-reviewer)\b'`
   over the converted `SKILL.md` files prints nothing.
9. `skills/tcw-extras-autonomous-work/SKILL.md` states what an advisor must be
   and how many are wanted, and names no specific one. Its frontmatter declares
   its tool requirements, as `tcw-setup` and `tcw-extras-triage-issues` do.
10. Running the exemplar in a checkout that has configured nothing yields the
    same advisors, closeout and version policy as today, because they are the
    shipped default — demonstrated by the resolved text, not by prose.
11. Every converted skill carries a manual fallback block for a harness that
    ran no injected commands, as `skills/tcw-work-stage/SKILL.md:41-49` does.
12. `pytest` passes, bare, as CI runs it.
13. `tcw capabilities check` exits 0, and the ledger carries the two new
    capabilities and each converted skill's `changed:` entry.
14. Every child item is resolved, and `tcw work reconcile` on this epic reports
    it ready to close.

## Risks

- **This plans against a tree that does not exist.** Every claim about the
  post-merge state is read from
  `2026-09-16-route-agents-to-tcw-work-stage-for-stage-instructions-and-validate-its-arguments`'s
  `spec.md`, not from code. If that item changes course, Rule 2's exclusion of
  the four command skills is the first thing to re-check: it holds only because
  their substance becomes an invocation of `tcw-work-stage`. Each child
  re-reads the merged tree before it specs.
- **A second id space invites a third.** `STAGE_IDS` and `PROCEDURE_IDS` are two
  fixed tuples of TCW's own ids, and a project still cannot add one. That is
  deliberate — a project overrides a procedure's *text*, not TCW's set of
  procedures — but the first request for a project-defined procedure will read
  this as arbitrary. The rules document should say why.
- **"Conduct" and "shape" blur at the edges.** `tcw-work-create` enforces board
  invariants (one outcome, no duplicate items) while describing conduct; the
  same is true of `tcw-post-mortem` reasoning over the stage ladder. A child
  converting one of these must keep the invariant in the fixed part and move only
  the conduct, or the override becomes a way to disable a rule.
- **Defaults carry the same opinions, one layer down.** The requester accepted
  that TCW keeps shipping a default naming a third-party CLI. It stops being a
  requirement, but a user who never reads `tcw-configure` still gets it, and the
  frontmatter declaration is what stops that being a surprise. Criterion 9 exists
  for that reason.
- **Six children, one reviewer.** The conversions are parallel and touch
  neighbouring files; two landing together can conflict in
  `docs/capabilities/` and in the marker test's expectations. Ordering is not
  the remedy — the classification child fixes the expected values first, and the
  conversions assert against it.

## Notes

- Grounded on this branch at `9bc5432` merged with `origin/main` at `c5d30a9`.
  Line citations into `skills/` and `tcw/` are from that tree; citations into the
  routing item are to its `spec.md` as filed, which is planned but not
  implemented.
- Assumption, not verified: that no test enumerates permitted `SKILL.md`
  frontmatter keys, so the marker can be added without one failing.
  `tests/test_plugin_manifests.py` and `tests/test_skill_lifecycle_parity.py`
  both read skill files; child 1 confirms before adding the key.
- The requester's answers behind this spec are recorded in
  `initial-request.md` under `## Notes`, including the reversal on whether a
  default roster ships.
- Not swept, and deliberately: `evals/`. The harness measures whether skill text
  reaches an agent, and converting a skill changes where its text comes from, so
  an eval arm may need updating. That belongs to whichever child converts the
  skill an arm covers, and
  `2026-09-11-refine-the-plugin-skills-and-lifecycle-prompts-against-the-eval-findings`
  owns the findings themselves.
