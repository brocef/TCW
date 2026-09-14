# tcw taxonomy rm deletes nested terms without a word

`tcw taxonomy rm <path>` deletes the term's whole folder. `FsTaxonomyStore.remove`
(`tcw/store/fs.py`, the `remove` method of `FsTaxonomyStore`) calls `_rm`, which runs
`git rm -rf` on the folder. Terms nest (`tcw taxonomy add Permission --parent admin`
puts `admin/permission` inside `admin/`), so `tcw taxonomy rm admin` also deletes
`admin/permission`, and the command reports only `Removed term admin`.

It also only warns when another term's `relatesTo` still points at the removed term,
so `tcw taxonomy check` can fail straight after a command that reported success.

`tcw capabilities rm`, added by
`2026-09-14-delete-a-capability-with-tcw-capabilities-rm`, refuses both cases for
capabilities: it names the nested entries and the referring fields, and deletes
nothing. That item left `tcw taxonomy rm` alone because changing a shipped command's
behavior is a separate decision (its spec, "Non-goals").

The question for triage: should `tcw taxonomy rm` refuse the same way, for
consistency between the two axes?
