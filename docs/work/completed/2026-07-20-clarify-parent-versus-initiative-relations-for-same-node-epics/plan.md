# Plan — Clarify parent versus initiative relations

1. Update `skills/tcw-work/SKILL.md` so its routing and quick reference distinguish
   nested decomposition from independently scheduled initiative tasks.
2. Rewrite the relationship choice in
   `skills/tcw-work/references/epic-lifecycle.md` around scheduling semantics and
   state that initiative children may be local or cross-node.
3. Tighten `skills/tcw-work/references/decompose.md` to reserve `--parent` for
   coupled nested work and route independent same-node tasks to `--initiative`.
4. Verify the changed text with targeted searches, Markdown diff inspection,
   `tcw validate`, and `git diff --check`.
5. Evaluate Documentation Sync. Because this is an agent-skill documentation
   correction with no code or public CLI behavior change, `README.md`, release
   notes, and the Any-Code-Change changelog are not expected to change; the
   matching `tcw-work` skill is the implementation surface itself.
