# Harden _effect_transition against a lost status-transition race

## Product changes

Two agents racing the same `submit` / `complete` / `rework` on one item: the
loser should get a comprehensible error rather than an internal crash. What the
loser *should* see is the open question.

## Technical changes

`FsWorkStore._effect_transition` reads `src = self._find(slug)` and hands it
straight to `self._mv(src, dst)` with no `None` check.

## Meta changes

None.

---

## Requested outcome

Found while fixing the sibling defect in `FsWorkStore.start`
(`2026-08-11-fix-typeerror-when-a-work-claim-loses-the-race-at-find`, completed
2026-08-11). That fix deliberately did not touch this one.

`tcw/store/fs.py:2721-2737`:

```python
def _effect_transition(self, slug: str, to_status: str) -> None:
    item = self.get(slug)
    src = self._find(slug)          # -> Path | None
    ...
    self._mv(src, dst)              # None is never checked for
```

Identical in shape to the bug just fixed in `start()`: `_find` is declared
`-> Path | None` (`fs.py:2065`), and a competing process that moves the folder
between the `get()` and the `_find()` leaves `src` as `None`.

## Why this was split out, and why it is not a copy-paste of the other fix

`start()` had somewhere obvious to land: a claiming protocol with a `.claiming/`
staging folder, a retry loop, and an `AlreadyClaimed` error already built for
"someone else got there first". Normalizing `None` into that existing recovery
was three lines.

`_effect_transition` has **none of that**. `submit`, `complete`, and `rework` are
not covered by the claiming mechanism, so there is no protocol to fall into and
no established answer to "what should the loser be told?" That is a design
question, which is why it was held back rather than patched by analogy.

## Open questions for spec

- What *should* a losing transition do? Plausible answers: re-read and report the
  item's actual current status; raise a typed error the CLI can render; or bring
  these transitions under the same claiming protocol as `start`. They differ a
  lot in scope.
- Is the window even reachable in practice? `start` is the transition two agents
  genuinely race (both picking up the same backlog item). Racing `submit` on the
  same item is rarer — worth establishing before choosing an expensive answer.
- Does `_mv` fail usefully on `None`, or with the same opaque `TypeError`? Worth
  checking before assuming the symptom.
- Are there other `_find` call sites with the same assumption? About twenty
  exist; most run after the item's existence was established in a non-racing
  path, but that was assessed quickly, not exhaustively.

## Non-goals

- Anything about `start()` — already fixed.

## Notes

- **Not known to have failed in the wild.** The `start()` bug was caught by a
  real CI failure; this one is reasoning from a shared code shape. Confirm the
  window is reachable before building much.
- No reproduction exists yet. Expect the same difficulty the sibling had: no
  arrangement of files reproduces it, because whatever makes `get()` succeed also
  makes `_find` succeed — the window is the gap between the two calls.
