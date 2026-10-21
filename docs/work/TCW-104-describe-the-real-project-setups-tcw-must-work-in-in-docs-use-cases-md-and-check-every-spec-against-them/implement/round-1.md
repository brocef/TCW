# Implement round 1 — TCW-104

## What was done, by plan step

1. **`docs/use-cases.md`.** Eight architectures (UC-1 to UC-8) and eleven
   situations that cut across them (S-1 to S-11), a checklist, and how to add
   a case. The user asked mid-implement for more detail and for scenarios to
   anticipate; the cases marked **Expected** (UC-7, S-10, parts of UC-6, S-6,
   S-7, S-9, S-11) answer that.
2. **Spec outlines.** `## Use cases` added to `docs/lifecycle/templates/spec.md`
   and `spec-bug.md`, before `## Acceptance criteria`.
3. **Documentation entry** `docs/use-cases.md` [Project-Setup-Change] in
   `tcw-config.yaml`; `DOCUMENTATION` in `tests/test_repo_lifecycle.py`.
4. **`AGENTS.md`** (which `CLAUDE.md` links to) names the document beside the
   prime directive.
5. **Changelog** entry under Internal. No release note: nothing changes for
   TCW's users.
6. **Checks**: `tests/test_repo_lifecycle.py`, `tests/test_shipped_text.py`,
   `tests/test_prompt_fallback.py`: 222 passed. `tcw validate`: 0 errors, 0
   warnings, 0 unresolved. `tcw work docs` lists the new entry. The full suite
   runs before the push.
7. **Fact check** by a separate read-only agent, against the code, the real
   configurations and runs in a scratch folder. It found:
   - three false statements: UC-4 overstated what the workspace stores; the
     UC-1 file-based example was never migrated to 3.0; UC-8's retired copy
     lacks a counterpart of `app`;
   - overstatements: UC-5's Jira filtering, S-1, S-6, S-7, S-10, S-11;
   - ten requirements TCW does not meet;
   - unclear wording.
   All accepted. The ten unmet requirements are listed as known gaps, marked
   "No item yet".

## What the plan or spec got wrong

- **The spec named private projects as examples.** This repository is public,
  and the projects are private. A peer session flagged it before any push.
  The document now describes them by shape under generic names (`core`, `app`,
  `workspace`, Jira project `APP`), and its "Adding a case" rule forbids
  private names. Spec Design 1's "Real projects are named" is wrong: they are
  described, not named.
- **Acceptance criterion 1 asked for "a real example" in every case.** UC-7 has
  none, and is marked Expected instead.
- **The plan's step 4 said `CLAUDE.md`.** It is a link to `AGENTS.md`, which is
  the file edited.

## Records changed

None (no capability changes).
