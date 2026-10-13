As a user or agent, I read what a lifecycle stage asks of me with `tcw work stage prompt <stage> [<slug>]`: the stage's instructions, composed from my project's configuration, on stdout and nothing else, so I can pipe them straight into an agent.

**Reading checks nothing.** The command runs no gate and moves nothing, so asking what a stage involves is always safe. The text opens with a line saying so, and naming `tcw work advance <slug> --dry-run`, which is what tells me whether the item may move on and what would stop it.

**With nothing configured for a stage, the instructions are TCW's own**, so the command is useful on a project that has never written a line of lifecycle configuration. A stage my project configures replaces them outright; `builtin: true` in that stage's `prompt:` list puts them back, composed with my own in the order I declared them — see [Configure the work lifecycle](tcw://C/work/configure-the-work-lifecycle). A stage whose packaged text TCW does not ship fails with exit 1 naming the missing file, rather than printing an empty prompt.

Those instructions are opinionated where it counts. `implement` does not merely say to write the failing test first; it tells me what to do when a *new* test passes on its first run — break the behaviour it names and confirm it goes red, because a green that was never earned is the same as no test.

**The item is optional and changes what resolves.** With one, `when:` conditions test its tags, a `generate:` script receives its record, and the `{{tcw:request}}` span in the text becomes the item's request. Without one, I get the stage's generic instructions and the span shows its own fallback words. `inbox` runs before an item exists, so it takes no item, and naming one is refused.

Errors go to stderr and print nothing on stdout, so a pipeline receives the whole instruction or none of it. An unknown stage name is a usage error (exit 2) whose message lists the stages, and an item that does not exist exits 4. `stage prompt` is the only `tcw work stage` command; whether an item may move on is `tcw work advance <slug> --dry-run`. A disabled stage still prints, with a note on stderr. `--no-exec` lists on stderr what would resolve, marking the bindings a `when:` skipped, runs nothing, reads no `file:`, and prints nothing on stdout.

I name the item by its full slug (`<project-id>/<folder>`) or its folder name, or by its ticket key when the project keeps its items in Jira. An item in another project resolves against that project's configuration.
