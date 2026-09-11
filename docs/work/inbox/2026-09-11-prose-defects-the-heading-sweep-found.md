# Five defects the heading sweep found that no heading can fix

## Desired outcome

`README.md` and `docs/guide/` contain no duplicated sentence, no cross-reference
that points the wrong way or nowhere, and no section describing repository-wide
contributor tooling from inside a document about one feature. And
`pnpm prettify:check`, which `docs/guide/web-viewer.md` calls "repository-wide
and deterministic", passes on a clean checkout.

## Context

Found while doing
`2026-08-18-close-the-readme-lifecycle-heading-so-it-stops-swallowing-the-rest-of-the-document`,
which swept `README.md` and every file under `docs/guide/` for headings that
name one topic and swallow another. That item fixed thirteen of those by
inserting headings and touching no prose. Its acceptance criteria pin that: a
diff check that must show no removed line is the only mechanical proof the
request's "without reflowing the content itself" was honoured.

These five cannot be fixed that way. Each needs a sentence deleted, moved, or
rewritten, so folding them in would have destroyed that check. They were
recorded rather than done, with the requester's rule in mind that a scope
inherited from a previous stage is a scope nobody chose.

All five verified at `3a063f6f`. Line numbers are from that commit and have
since shifted by the heading insertions.

1. **`docs/guide/configuration.md:223-226`** — a four-line tail under
   `## Declaring which documents track which changes` that is about neither
   documents nor tracking. Its first sentence ("`tcw-config.yaml` is a file in
   your own repository and is trusted exactly as much as any other file there —
   this is not a sandbox") repeats `:3-5` of the same file almost word for word.
   Its second ("`tcw serve` does **not** run hooks, so a `pre` hook that would
   block a transition does not block it from the web app") is about hook
   execution and now has a home: `## How bindings run`, added by the heading
   item.

2. **`docs/guide/taxonomy-and-capabilities.md:53-54`** — "see `tcw capabilities`
   **above**", but `## tcw capabilities — the user stories` is at `:60`, below.
   One word.

3. **`docs/guide/web-viewer.md:47`** — links to
   `#tcw-links--reference-a-tcw-object` as a same-page anchor. That heading lives
   in `docs/guide/linking-and-validation.md:6`, so the link resolves to nothing.
   Probably created by the README split, and worth checking whether the split
   left other same-page anchors pointing at headings that moved.

4. **`docs/guide/web-viewer.md:20-31`** — documents `pnpm prettify` and
   `pnpm prettify:check`, repository-wide contributor formatting with nothing to
   do with the web viewer, inside a document titled "The local web viewer". The
   fix is moving it to contributor documentation, which is a judgment about
   where contributor tooling is documented. Separately, `:3` and `:5` state
   nearly the same sentence twice.

5. **`pnpm prettify:check` fails on 168 files at `3a063f6f`** — test fixtures
   under `tests/fixtures/` and sources under `web/client/` that are inside the
   formatting surface and are not formatted. This is the one entry here that is
   not a documentation change: a documented contributor command that is red on a
   clean checkout teaches contributors to ignore it, and the prose in item 4
   calling it deterministic is false while it stays that way.

## Constraints

- **Items 1 through 4 are prose edits and item 5 is not.** Item 5 is either a
  large mechanical reformat or a `.prettierignore` change, and which one it
  should be is a real decision. It may deserve its own item.
- **Item 4's repair needs a destination.** There is no contributor guide today.
  Deciding where contributor tooling is documented is the substance of it, and
  is why it was not folded into the heading item.
- **Do not re-open the heading question.** The heading item swept both trees and
  recorded what it inspected and deliberately left alone, with reasons. Those
  calls are reviewable in its `spec.md`; disagreeing with one is a separate
  request, not part of this.

## Supporting resources

- `docs/work/.../2026-08-18-close-the-readme-lifecycle-heading-so-it-stops-swallowing-the-rest-of-the-document/spec.md`
  — its *Found but not fixed here* section is where these five were recorded,
  and its *Inspected and deliberately left alone* section is the rest of the
  sweep.
