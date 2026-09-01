As someone working in a checkout that will not last — a cloud session, a
container — I can rely on my work leaving the machine. A work store I obtained
with `tcw provision` brings itself up to date with the repository it came from
before a transition moves anything, and pushes the result afterwards, so
starting, submitting or completing an item survives the session that did it.

**Only a store TCW fetched for me publishes.** A store already at my own
`work.path` does not, even when a `repository` block is also present: the
declaration is a fallback and did not answer the read, so it does not cause a
write, and that copy is mine to push. A store with no declaration at all never
publishes — its repository usually has an `origin` of its own, and changing an
item's status is not a reason for a tool to push my project.

What happens when the remote cannot be reached depends on when it fails, and I
can tell the two apart. If the update at the start fails, nothing has moved and
the transition stops — my item is exactly as it was. If the push at the end
fails, the item has moved and been committed here, and I am told where it is
saved and what to run once the remote is back; nothing is undone on my behalf.
If someone else changed the same store incompatibly I am told it has diverged,
that every transition will stop until it is reconciled, and the command that
shows me both sides. Nothing is ever merged for me.

Publication happens at transition boundaries. Artifacts I write into an item's
folder are carried by the next transition's commit; if I write and never
transition, that work is committed nowhere and pushed nowhere — which is TCW's
existing rule that ordinary writes stage rather than commit, not a new one.

I can turn all of it off with `work.publish-transitions: false`, and I must if my
declaration pins `ref` to a tag or a commit, which is read-only by nature and has
no branch to publish to.
