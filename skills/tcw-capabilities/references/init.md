# Bootstrap capabilities from an existing codebase

Seed `docs/capabilities/` for a project adopting TCW. Same four-beat shape as the
taxonomy bootstrap; **do not invoke `superpowers:brainstorming`**.

## 0. Taxonomy first

Capabilities reference terms (their **Subject**). If `docs/taxonomy/` is empty, point
the user at `/tcw-taxonomy-init` before seeding capabilities.

## 1. Ensure the tree exists

`tcw capabilities init` if `docs/capabilities/` is absent.

## 2. Deep-dive (draft)

Survey the codebase for **user stories — what a user can do**: routes, CLI commands,
request handlers, user-facing features and flows. Group candidates by namespace
(one per major surface/component). For each, draft a `## <Capability name>` with a
one-line "As a user, I …" body and a status: `Supported` for what already ships,
`Missing` / `Partial` otherwise.

## 3. Refine + write

Present the draft; run the lightweight add / cut / rename / regroup loop with the
user. Then write each agreed capability:
`tcw capabilities add <namespace/path> "<Name>" --status <Status>` (pipe the body),
and set status/fields with `tcw capabilities set` where needed. A new namespace's
first capability is a fresh single-capability file; add later ones in that namespace
as additional flat files (`<namespace>/<slug>`). Finish with `tcw capabilities check`.
