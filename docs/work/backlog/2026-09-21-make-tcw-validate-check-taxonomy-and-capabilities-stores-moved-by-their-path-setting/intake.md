# Make tcw validate check taxonomy and capabilities stores moved by their path setting

`tcw validate` decides whether to run the taxonomy and capabilities checks by
testing whether the default folder (`docs/taxonomy`, `docs/capabilities`) exists.
A store moved elsewhere with `<component>.path` (or kept in another repository with
`<component>.repository`) is therefore never checked, unless a stray default folder
also exists, and it is never scanned for YAML syntax or links either. In a scratch
reproduction, a moved taxonomy holding a bad term gave one problem from
`tcw taxonomy check` and none from `tcw validate`.

## Origin

Found on 2026-09-21 while writing the spec for
`2026-09-21-report-a-leftover-pre-2-5-0-store-config-file-instead-of-silently-dropping-its-extends`.
Its advisors (Codex and Opus) agreed the general fix belongs in its own item. That
item adds only the narrow direct report its leftover-file problem needs, plus a
direct report of a store that fails to open. This item should remove that
bookkeeping once `validate` selects and scans stores by their resolved location.

## References

- `tcw/validate.py` (around lines 321-336): the check selection and the skip after
  a YAML problem.
- `2026-09-21-report-a-leftover-pre-2-5-0-store-config-file-instead-of-silently-dropping-its-extends`
  spec, design section 4: the temporary bookkeeping this item retires.
