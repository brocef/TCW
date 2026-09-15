# Plan — Add tcw-report skill

1. Write `skills/tcw-report/SKILL.md` — frontmatter matching sibling skills
   (`name`, `description`, `when_to_use`, `allowed-tools: Bash(tcw *), Read`,
   `metadata.author`, `license`); body with the issues URL, a "before filing"
   checklist (search first, pick the kind, grab `tcw --version`), and the two
   fill-in skeletons.
2. Add a `tcw-report` entry to the `tcw-plugin` skill map, framed as orthogonal
   to the three axes and distinct from `tcw-work`.
3. Documentation sync: README skills section (four→five) + `docs/changelogs`
   and `docs/release-notes` upcoming entries.
4. Complete the item (`tcw work complete … --resolution done`) in an atomic
   commit carrying the skill + status transition.
