# Resolve Self-Qualified TCW Links in TCW Serve Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make self-qualified work links navigable and explain valid links whose projects are outside the served board.

**Architecture:** Define hosted project IDs from the same roots used to build the board, enrich only the unhosted resolver result, and render that result accessibly in the React Markdown component. Rebuild the vendored client consumed by the Python server.

**Tech Stack:** Python HTTP server, React, TypeScript, Vite, pytest, Vitest/npm tooling.

---

### Task 1: Correct the server's hosted-project contract

**Files:**
- Modify: `tests/test_serve_resolve.py:65-145`
- Modify: `tcw/serve/__init__.py:399-413,919-934`

- [ ] **Step 1: Add failing anchor-resolution tests**

Add a parameterized test over `include_descendants=False/True`. Register anchor `root`, create a work item, resolve both accepted qualified spellings (`tcw://root/W/<slug>` and `tcw://W/root/<slug>`), and expect `ok: true`, axis `work`, key `<slug>`.

- [ ] **Step 2: Tighten the descendant/ancestor expectations**

Change the existing non-aggregated descendant and ancestor assertions to expect `{"ok": false, "reason": "unhosted-project", "project": <id>}`. Keep malformed/missing references exactly `{"ok": false}`.

- [ ] **Step 3: Run the resolver tests red**

Run: `pytest tests/test_serve_resolve.py -v`

Expected: FAIL because the anchor is absent and unhosted failures carry no context.

- [ ] **Step 4: Build hosted IDs from served roots**

In `_hosted_projects`, initialize with `registered_project_id(anchor, anchor)` and union descendants only when enabled. In `/api/resolve`, distinguish `r.ok` plus unhosted project from an invalid resolution and emit the structured failure.

- [ ] **Step 5: Run server tests green and commit**

Run: `pytest tests/test_serve_resolve.py tests/test_serve.py -q`

Expected: PASS.

```bash
git add tcw/serve/__init__.py tests/test_serve_resolve.py
git commit -m "fix: host self-qualified work links"
```

### Task 2: Render unhosted projects distinctly

**Files:**
- Modify: `web/client/src/ui/shared-components.tsx`
- Modify: `web/client/src/ui/shared-components.test.tsx`
- Modify: `web/client/src/style.css`

- [ ] **Step 1: Add a failing component test**

Mock `/api/resolve` with `reason: "unhosted-project", project: "remote"`. Assert the anchor is non-navigable, includes explanatory accessible text, and displays a `remote` project badge. Add a control assertion that a generic unresolved URI has no project badge.

- [ ] **Step 2: Run the focused client test red**

Run: `pnpm test web/client/src/ui/shared-components.test.tsx`

Expected: FAIL because the component only adds `tcw-inert` and a URI title.

- [ ] **Step 3: Implement reason-aware rendering**

Extend the resolver response TypeScript type. For unhosted projects, add an explanatory title/ARIA description and append a styled badge without replacing the author's link text. Retain current generic unresolved behavior.

- [ ] **Step 4: Run client tests and commit source**

Run: `pnpm test`

Expected: PASS.

```bash
git add web/client/src/ui/shared-components.tsx web/client/src/ui/shared-components.test.tsx web/client/src/style.css
git commit -m "fix: explain unhosted tcw links"
```

### Task 3: Rebuild the bundled web application

**Files:**
- Modify: `tcw/serve/dist/**`

- [ ] **Step 1: Produce a clean production bundle**

Run: `pnpm build`

Expected: Vite exits 0 and refreshes hashed assets plus `tcw/serve/dist/index.html` references.

- [ ] **Step 2: Verify bundle tests**

Run the package script that checks the vendored distribution, then run `pytest tests/test_serve.py tests/test_serve_resolve.py -q`.

Expected: PASS.

- [ ] **Step 3: Commit generated output separately**

```bash
git add tcw/serve/dist
git commit -m "build: refresh tcw serve client"
```

### Task 4: Documentation Sync

**Files:**
- Modify: `README.md`
- Modify: `docs/release-notes/upcoming.md`
- Modify: `docs/changelogs/upcoming.md`
- Modify: `skills/tcw-work/SKILL.md` or a matching reference

- [ ] **Step 1: Update viewer behavior documentation**

Describe self-qualified navigation and how the viewer marks a valid reference to an unhosted project.

- [ ] **Step 2: Add release and changelog entries**

Use plain language in release notes; use a technical Fixed entry for anchor membership, resolver reason metadata, and client presentation.

- [ ] **Step 3: Keep the work-driving skill aligned**

Update the cross-node link reference rather than bloating the router if this belongs only to cross-node work.

- [ ] **Step 4: Commit the documentation block**

```bash
git add README.md docs/release-notes/upcoming.md docs/changelogs/upcoming.md skills/tcw-work
git commit -m "docs: explain hosted tcw links"
```

### Task 5: Final verification and visual check

- [ ] **Step 1: Run all automated checks**

Run: `pytest -q && pnpm test && pnpm build && pnpm check:build`

Expected: all commands pass and the final build leaves no unexplained generated diff.

- [ ] **Step 2: Launch the viewer and capture the perceptible change**

Create a fixture with a self-qualified local link and an unhosted descendant/ancestor link, run `tcw serve --no-open`, and capture a screenshot showing the navigable self-link and labeled inert remote link.

- [ ] **Step 3: Validate formatting and state**

Run: `git diff --check && git status --short`

Expected: no whitespace errors or unexpected files.

## Verification

The accessible label and badge require a browser screenshot in addition to automated assertions. Confirm keyboard focus does not offer navigation for the inert reference and that light/dark themes keep the badge legible.
