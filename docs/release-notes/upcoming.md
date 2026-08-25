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
  back to you. One case is not covered yet: a link written as a plain work-item
  name that does not exist is still treated as valid, and is being tracked
  separately.
- Links inside a work item's **Initial Request**, **Spec**, and **Implementation
  Plan** tabs work again. They were rendering as plain text: a link to another
  item did not go anywhere when clicked, and a broken one was not marked as
  broken. Everything described above now applies there too.
- Neither kind of dead link can be clicked any more. Both used to look
  unclickable and still respond to a click; now they behave the way they look.
