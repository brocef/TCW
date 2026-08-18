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
