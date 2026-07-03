# Per-object capability revision token (fix file-scoped 409s)

## Origin

Dual-review finding #10 on `2026-07-02-interactive-local-web-editor-for-tcw-objects`
(accepted for v1). Non-blocking; no data corruption.

## Problem

`FsCapabilitiesStore.get_capability_detail` derives the revision token from a hash
of the **whole capability file** (`_revision(file_text)`). When a file holds more
than one `## capability`, all co-located capabilities share one token. Editing
capability B rotates the token, so an in-flight edit of capability A in the same
file gets a spurious `409` on save even though A was untouched.

## Desired outcome

Scope the capability revision token to the individual capability entry (its own
heading block / fields + body), not the whole file — matching the spec's
"one token per editable resource" intent. Two edits to different capabilities in
the same file should not conflict.

## Notes

- Keep the token an opaque adapter-owned string (litmus test).
- Add a regression test: edit two capabilities in one file, save both against
  their own tokens; the second save must not 409.
