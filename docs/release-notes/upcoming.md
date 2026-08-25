# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Web viewer

- A link to an item that lives on another project's board no longer looks
  broken. It is marked in a warning colour, keeps the project's name beside the
  link text, and says "Project _name_ is not included in this board" — so a
  document written across projects reads as complete rather than as full of
  mistakes.
- A link that really is broken now says why — a misspelled address, or a
  destination the project does not have — instead of only repeating the address
  back to you.
- A link to a work item that does not exist is finally treated as broken. It used
  to pass `tcw validate` without comment and appear as a working link that led
  nowhere, so a typo in an item name could sit unnoticed in a document
  indefinitely.
- Links inside a work item's **Initial Request** tab work again. They were
  rendering as plain text: a link to another item did not go anywhere when
  clicked, and a broken one was not marked as broken. Everything described above
  now applies there too. The same fix covers the Spec and Implementation Plan
  tabs, which share that rendering.
- Neither kind of dead link can be clicked any more. Both used to look
  unclickable and still respond to a click; now they behave the way they look.
