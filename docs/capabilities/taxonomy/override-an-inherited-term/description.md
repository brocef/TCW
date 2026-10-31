As a user, I change a term my project inherits from a parent by putting my
project's own term at the same path, holding only what I change: a different
name, a description, or a feature's vocabulary. Nothing in its files points at
the inherited term. The two are combined field by field: a field my term sets
replaces the inherited one, a field set to `null` removes it, and a field it
leaves out keeps the inherited value; a list such as `relatesTo` or
`vocabulary` is replaced whole. The parent's term is never modified.

`tcw taxonomy add` at a path my project already inherits a term at writes such
a term, holding only what differs from the inherited one (a name only when it
differs, a kind only when `--kind` is given and differs, the vocabulary when
`--vocab` is given, and a description only when the one on standard input is
not empty), and says on standard error `<new full id> overrides <inherited full
id>`. When nothing given differs it is refused (exit 3) and writes nothing.

The listing's JSON records and `tcw taxonomy show` name the term it overrides:
each record carries `overrides`, the full identifier of the inherited term or
`null`, and `show` prints an `overrides:` line. `tcw taxonomy rm <path>` removes
my term, and says what the path shows afterwards, the inherited term again. A
term of my own that overrides nothing must be complete, a name and a
`description.md` (which may be empty), so `tcw validate` reports an override
whose original was moved or removed.
