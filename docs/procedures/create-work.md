<!-- Bound to the `create-work` procedure in `tcw-config.yaml`, after TCW's own
     text. Read as a continuation of it, not on its own. -->

## This project: say why the work is worth doing

Every item or inbox entry you create, whether in step 4 or as step 1's raw
inbox entry, carries a `## Why` section. Place it right after the idea and
before `## Origin`.

The section makes the case for the work. Whoever picks the item up later, or
decides whether it is worth picking up at all, can then weigh it without
reconstructing your reasoning. Cover:

- **Without it:** what happens if nobody ever does this. Say who or what is
  affected, how often, and how badly. "Nothing yet; it only matters once X
  happens" is an honest answer, and it tells the reader the item can wait.
- **With it:** what gets better, and for whom.
- **Cost and risk:** roughly how large the change is, and what it could
  break.
- **Alternatives,** when there are any: a smaller fix, a workaround, or
  leaving it alone, and why this is better than each.

Use short bullets. Write only what you have evidence for: the symptom, the
review finding, or the user's own words. Where you cannot say, write
"unknown" rather than inventing a benefit, because an honest gap is more
useful to the reader than a plausible guess.

If you cannot answer **Without it** at all, the case for the work is unclear:

- **Interactive:** include it in the step 4 question to the user.
- **Delegated:** write "unknown — not in the brief".
- **Unattended:** write "unknown", and say what would settle it.

When you append to an existing item (step 3), add to its `## Why` only if
the new information changes the case for doing the work, and do so under the
same dated `## Added <YYYY-MM-DD>` heading as the rest of the append. The
body template in step 4 therefore becomes:

```markdown
# <title, as a change>

<the idea: what should change>

## Why

- **Without it:** <impact of not doing it>
- **With it:** <benefit of doing it>
- **Cost and risk:** <size of the change, what it could break>
- **Alternatives:** <other options, and why not them — omit if none>

## Origin

...
```
