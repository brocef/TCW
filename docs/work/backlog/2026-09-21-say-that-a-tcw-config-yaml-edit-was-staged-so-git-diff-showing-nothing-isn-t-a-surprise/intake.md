# Say that a tcw-config.yaml edit was staged, so git diff showing nothing isn't a surprise

Since v2.5.1, `tcw capabilities extends`, `tcw taxonomy extends add|rm`,
`tcw work tags add|rm` and `tcw init` change only their own lines of
`tcw-config.yaml`, and they stage the change in git. A user who then runs a plain
`git diff` sees nothing, because the change is in the index (`git status` shows
`M `). The proposit-app agent was briefly confused by this. Add a line to these
commands' output saying the change to tcw-config.yaml was staged, and that
`git diff --cached` shows it. Or reconsider whether staging is right. See also
2026-08-18-decide-whether-tcw-work-scaffold-should-stage-its-draft-in-git.

## Origin

Reported by the proposit-app agent on 2026-09-21 while testing v2.5.1.

## References

- 2026-08-18-decide-whether-tcw-work-scaffold-should-stage-its-draft-in-git: the same question for another command
