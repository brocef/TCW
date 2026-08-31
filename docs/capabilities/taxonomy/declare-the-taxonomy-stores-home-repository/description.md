As a project owner whose taxonomy lives in a repository other than the code
repository, I can record that repository under `taxonomy.repository` — its URL,
optionally a ref, the tree's path within it, and optionally where a working copy
should live on this machine — and obtain it with `tcw provision`, exactly as I
can for work items.

The declaration is a fallback, never an override: a tree already present at
`taxonomy.path` keeps being used untouched, so one configuration serves a laptop
that has the folder and a session that cloned only the code. Where the tree is
absent, every command says so, names the declared remote and the command that
fetches it, and never reports the project as having no taxonomy — which was the
old answer for a checkout that simply had no `docs/taxonomy/` folder, and the
answer that sent me to `tcw init`.

**What this promises is weaker than the work store's, deliberately.** A work
store is recognizable — it names six status folders, and TCW checks them. A
taxonomy tree names nothing: it is a directory of term folders, with no required
marker. So "the tree is here" means the directory is there, and a declared
repository whose tree path holds an empty or unrelated directory is accepted
rather than refused. What is still guaranteed is that a failure leaves nothing
behind: a repository with no directory at the declared path is refused before
any working copy is published.
