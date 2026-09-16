# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Breaking change: the skills and agents lost their `tcw-` prefix

Every skill the plugin ships is already addressed through the plugin's own name,
and then repeated it: the work skill was invoked as `/tcw:tcw-work` under Claude
and `$tcw:tcw-work` under Codex. The second `tcw` distinguished nothing — it was
four more characters to type and a stutter to read in a list of skills.

The prefix is gone. The same skill is now `/tcw:work` and `$tcw:work`.

**The old names stop working.** Neither Claude Code nor Codex offers a way to
keep an old skill name pointing at a renamed one, so there is no deprecation
period: after you update the plugin, typing `/tcw:tcw-work` will not find
anything. The full list is below so you can find whichever one your fingers
know.

The groupings stay. `commands-` still marks the four everyday workflow skills and
`extras-` the three optional ones, so they still sort together when you are
scanning for one.

### Skills

| Type this now                       | Instead of                              |
| ----------------------------------- | --------------------------------------- |
| `work`                              | `tcw-work`                              |
| `work-stage`                        | `tcw-work-stage`                        |
| `work-create`                       | `tcw-work-create`                       |
| `capabilities`                      | `tcw-capabilities`                      |
| `taxonomy`                          | `tcw-taxonomy`                          |
| `setup`                             | `tcw-setup`                             |
| `configure`                         | `tcw-configure`                         |
| `post-mortem`                       | `tcw-post-mortem`                       |
| `commands-plan-work`                | `tcw-commands-plan-work`                |
| `commands-drive-work-to-completion` | `tcw-commands-drive-work-to-completion` |
| `commands-verify-work`              | `tcw-commands-verify-work`              |
| `commands-process-inbox`            | `tcw-commands-process-inbox`            |
| `extras-autonomous-work`            | `tcw-extras-autonomous-work`            |
| `extras-triage-issues`              | `tcw-extras-triage-issues`              |
| `extras-report`                     | `tcw-extras-report`                     |

`documentation-sync` is unchanged — it never carried the prefix, and it is the
shape the others have moved to.

### Agents

The three read-only agents are renamed for the same reason. `post-mortem` names
both a skill and an agent, as it did before.

| Now               | Instead of            |
| ----------------- | --------------------- |
| `verifier`        | `tcw-verifier`        |
| `backlog-auditor` | `tcw-backlog-auditor` |
| `post-mortem`     | `tcw-post-mortem`     |

### What this does not break

**Your project's configuration.** A skill name reaches TCW only if you named one
in a lifecycle hook in your `tcw-config.yaml`. If you did — an entry reading
`skill: tcw:tcw-work` or similar — update it to the new name. Nothing else in a
configuration file refers to a skill, so for most projects there is nothing to
change. `tcw validate` does not check skill names, so it will not find an old
one for you: search `tcw-config.yaml` for `skill:` values that start with `tcw-`
or `tcw:tcw-`.

**Your work items, taxonomy or capabilities.** Nothing about your own project's
content is touched.

If your own `AGENTS.md` or `CLAUDE.md` tells contributors to "use the `tcw-work`
skill", that sentence now points at a skill that is not there. It will not break
anything, but it is worth a search-and-replace the next time you are in the file.
