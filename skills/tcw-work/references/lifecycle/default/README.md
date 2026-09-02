# The built-in stage prompts

**They are not in this folder, and this note is the only thing here.** TCW's
default instructions for all seven lifecycle stages live at
`tcw/work/prompts/*.md`, inside the installed `tcw` package.

## Why there and not here

Packaging. `pyproject.toml` ships the `tcw*` packages and their package data;
`skills/` reaches users through the plugin, which is a different channel
entirely. A project that installs `tcw-cli` from PyPI and never installs the
plugin must still get instructions at every stage — so the prompts travel with
the code that reads them, and moving them here would leave every PyPI-only
install with no defaults at all.

That is the same rule stated the other way round in
[`harness.md`](../../../../../docs/lifecycle/harness.md): anything that must be
guaranteed belongs in the CLI, because the CLI behaves identically under Claude
and Codex while a skill only reaches whoever installed the plugin.

## Reading one

```sh
tcw work stage <id> <slug>     # `inbox` takes no reference — it runs first
```

No checkout required: the command resolves the prompt out of the installed
package. What it prints is what a stage actually receives, which a file in this
repository would only approximate.

## Which text wins

The stage documents beside this folder are routers, not copies — reading them
is not a substitute for running the command.

- **Nothing configured** → the built-in prompt. This is the floor, and it is why
  a node that configures no lifecycle at all still gets instructions.
- **A project binds `prompt:` for the stage** → its bindings replace the
  built-in outright. Every matching binding is used, concatenated in declaration
  order.
- **`builtin: true` appears in that list** → the default goes back in, at that
  position in the order.

[`hooks.md`](../../hooks.md) has the binding shapes and the conditions that
select between them.
