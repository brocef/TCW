As a user, I shape my project's work lifecycle in `tcw-config.yaml` under `work.stages`, one entry per stage of TCW's stage table, so TCW's fixed order of stages carries my team's methodology without TCW knowing anything about it.

For each stage I can say whether it is `enabled` (the optional ones — spec, plan, review, qa and postmortem — can be turned off; the others cannot), and bind three lists. `prompt:` is the instructions my agent reads at that stage, composed in the order I wrote them. `pre:` is the checks that must pass before an item may move into the stage. `post:` runs after an item has moved in.

A binding declares one **kind** explicitly — a bare string is rejected rather than guessed at. `blob:` is text I write inline, `file:` is a path in my project, `generate:` is a script of mine that prints the text, `builtin: true` is TCW's own text for the stage so I can add to it rather than replace it, `skill:` names an agent skill, and `command:` runs a program. A `pre:` list takes only `command:`, since a check TCW cannot run would always pass; a `post:` list takes `command:` and `skill:`; `prompt:` takes every kind but `command:`, and names `generate:` when I reach for it.

A stage I write no `prompt:` for gets TCW's own text. A list without `builtin: true` replaces it, and an empty list says nothing at all.

Any binding may carry `when: {tags, not_tags}`, so a bug gets different instructions than a feature. Anything harder belongs in a `generate:` script, which is real code and can decide anything. Work items have no type, so `when: {type}` is refused. An artifact template is a `file:` binding with a `when:` in the stage's `prompt` list.

Every `tcw work` command reads this through one parser, and a problem — an unknown stage or key, a malformed binding, a kind where it is not allowed, a `when:` with an unknown key — is an error naming the key, from every command and from `tcw validate`. A key TCW 2.x used and 3.0 removed (`work.lifecycle`, `work.tracker`, `work.retain`, `work.auto-commit-transitions`, `work.publish-transitions`, `work.trunk-branch`) is refused the same way, naming the migration guide.

`pre` and `post` commands run from the project root under the timeout in `work.hooks.timeout`, with `TCW_SLUG` (the item's full slug), `TCW_STAGE` (the stage being moved into), `TCW_FROM_STAGE`, `TCW_ITEM_PATH` and `TCW_PROJECT_ROOT` set, and `TCW_FORCED` and `TCW_REASON` on a forced move. A `pre` failure refuses the move before anything is written; a `post` failure never undoes it. `skill:` bindings are named for my agent to invoke; the CLI cannot run them.

A `generate:` script receives one JSON object on stdin — the item's record, its request text (capped, with a flag saying when it was cut) and what the hook is — plus `TCW_HOOK_ROLE`, `TCW_HOOK_KIND`, `TCW_HOOK_ID` and `TCW_HOOK_PHASE`, so a one-line script needs no JSON parser. Its output is capped by `work.hooks.output-cap`, and **a script that exits non-zero contributes nothing at all** rather than half a prompt. Because composing can re-run, a generator has to be side-effect-free.

`tcw serve` runs no hooks.
