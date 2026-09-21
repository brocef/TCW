# Warn when the loaded plugin skills are from a different version than the tcw CLI

The `tcw` CLI on PATH and the plugin skills an agent follows can come from different
releases, and nothing says so. The agent then follows instructions written for a
version it isn't running.

## What happened

In proposit-app on 2026-09-21, the CLI was 2.5.0 while the newest plugin skill cache
was 2.4.0 (`~/.claude/plugins/cache/tcw/tcw/2.4.0`). The skills the reporter followed
(capabilities, work-stage, the drive-work command) described 2.4.0 behavior. The
2.4.0 capabilities skill documents `tcw capabilities extends` without saying the key
now lives in tcw-config.yaml, and nothing mentioned `tracker create`. Combined with
the silent config break in 2.5.0, this cost the reporter real time.

## What is wanted

A version check that warns when the CLI and the loaded skills disagree. Candidate
places: the plugin's SessionStart hook, which already installs or checks the CLI;
a skill-side check against `tcw --version`; or a CLI-side check that the skills can
call. It should work under both Claude and Codex, since Codex has no hook.

## Origin

Reported 2026-09-21 by the Claude session working in proposit-app. The requester
asked for it to be tracked at high priority.

## References

- `2026-08-12-separate-the-agent-plugin-from-the-python-cli-source`: splitting the
  plugin from the CLI makes the two versions drift apart more easily, so the check
  matters more after it lands.
- `scripts/session_bootstrap.sh`: the published install path the SessionStart hook runs.
