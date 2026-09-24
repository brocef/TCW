`tcw work scaffold <artifact> <slug>` writes the draft and then stages it in git
(`self._stage(p)` at `tcw/store/fs.py:3538`).

That contradicts how the draft is framed everywhere else. README: "A draft is a
file to type into, never the document" — the board does not show it, 
`tcw work show --json` reports the artifact absent, and the web app does not
list it. But it is in the index, so the next `git commit -a` (or any `git commit`
at all, since it is already staged) sweeps an empty scratch template into the
repository under the author's name.

Found while dogfooding the 1.0.0 lifecycle configuration in this repo: running
`tcw work scaffold` a few times to check the `when:` conditions left three staged
`*.draft.md` files that had to be `git reset` by hand before the real work could
be committed cleanly.

The other write paths stage deliberately because they write documents. A draft is
explicitly not a document, which is the whole point of the `.draft.md` name and of
`artifacts()` never seeing it — so it is the one write that arguably should not
stage. Worth deciding either way: if staging is intended, the README sentence
about drafts should say so, because a reader today would not expect it.

## Folded in: 2026-09-21-say-that-a-tcw-config-yaml-edit-was-staged-so-git-diff-showing-nothing-isn-t-a-surprise

_Merged here during the 2026-09-24 backlog cleanup; the source was closed as superseded._

## Say that a tcw-config.yaml edit was staged, so git diff showing nothing isn't a surprise

Since v2.5.1, `tcw capabilities extends`, `tcw taxonomy extends add|rm`,
`tcw work tags add|rm` and `tcw init` change only their own lines of
`tcw-config.yaml`, and they stage the change in git. A user who then runs a plain
`git diff` sees nothing, because the change is in the index (`git status` shows
`M `). The proposit-app agent was briefly confused by this. Add a line to these
commands' output saying the change to tcw-config.yaml was staged, and that
`git diff --cached` shows it. Or reconsider whether staging is right. See also
2026-08-18-decide-whether-tcw-work-scaffold-should-stage-its-draft-in-git.

### Origin

Reported by the proposit-app agent on 2026-09-21 while testing v2.5.1.

### References

- 2026-08-18-decide-whether-tcw-work-scaffold-should-stage-its-draft-in-git: the same question for another command
