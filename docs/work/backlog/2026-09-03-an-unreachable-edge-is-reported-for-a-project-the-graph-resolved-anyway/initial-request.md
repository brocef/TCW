# An unreachable edge is reported for a project the graph resolved anyway

An unreachable report should mean *this checkout does not have that project*, not
*one of the several configs naming it pointed somewhere that is not here*. In a
reciprocal graph the second is routine and says nothing.

What should be true when this is done:

- A project that ends up in the graph is not reported unreachable, however many
  of the locators naming it failed to resolve.
- A project genuinely absent is still reported, with the same wording.
- The distinction is drawn by project id, which is identity.

## Notes

Asked for reference material; none provided beyond the session itself. The
reproduction is in `intake.md`.

Both of the false reports it names are of the same shape and one fix removes
both, which is why this is one item rather than two.
