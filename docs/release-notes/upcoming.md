# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## The implement stage says more about tests that pass

`tcw work stage implement` has always told you to write the failing test first
and watch it fail. It now also tells you what to do in the case that actually
catches people out: a brand-new test that passes the first time you run it.

The advice is to break the thing the test is named after and check that the test
goes red. If it stays green, it is not testing what its name says — and the
reason it passed, however sensible, is beside the point. It takes half a minute
and it catches a test that is quietly checking somebody else's behaviour instead
of yours.
