# TCW-118 design note: a child's folder goes inside its parent's by default

Decided by the user on 2026-10-29, as a follow-up folded into TCW-118 (it
changes the 4.0 surface before release, on all three axes).

## Why

TCW-99's model is unchanged: `parent:` in the state file is the one record of
a parent, because a parent in another project (an inherited term or
capability, or an epic in another project) has no folder this project can
put the child in. Folders are how a project lays things out, and TCW
encourages a child's folder inside its parent's. Today only
`tcw taxonomy add --parent` does that. `tcw capabilities add --parent`
records the field and needs the nested path repeated, and `tcw work new
--parent` needs `--nest` as well. The user wants children placed inside
their parent's folder by default on every axis, with a flat layout still
possible.

## Decisions

1. **`--parent` places the new object's folder inside its parent's folder**
   on `tcw taxonomy add`, `tcw capabilities add` and `tcw work new`, when the
   parent is one of this project's own objects. `parent:` is still written,
   exactly as today.
2. **`--flat`** on those three commands keeps the new folder where it would
   be without a parent: the top of the taxonomy or work store, or the path
   given for a capability. It records `parent:` all the same. `--flat`
   without `--parent` is refused with exit 2, as `--nest` without
   `--parent` is today.
3. **`tcw work new --nest` is removed.** 4.0 is not released, so nothing
   depends on it. Every mention (the plan prompt, skills, guides, the
   migration guide's "New in 4.0" table and epic-parts section, capability
   records, the README, changelog and release-note entries) changes to the
   default, with `--flat` where a flat layout is meant.
4. **A capability's path with `--parent`.** The positional path is read
   relative to the parent's folder, unless it already starts with the
   parent's path followed by `/`, in which case it is used as given (so the
   form documented today keeps working). With parent `billing/invoices`:
   `bulk` gives `billing/invoices/bulk`, and `billing/invoices/bulk` gives
   `billing/invoices/bulk`. Once the parent's path is taken off (from either
   form), every folder between the parent and the new capability must
   already be a capability of this project: `extra/bulk` is refused with exit
   2 before anything is written, unless `billing/invoices/extra` is a
   capability, with a message saying the path is read inside the parent's
   folder, where only capabilities and `resources/` may sit, suggesting the
   one-part form and, for the relative form, `--flat`. A path equal to the
   parent's is refused too. Without `--parent`, or with `--flat`, the path is read
   as today: namespace folder first. The usage line and `--help` say this.

   *Revised at implement (2026-10-29).* The first version of this decision
   let `extra/bulk` make `billing/invoices/extra/bulk`, calling `extra/` an
   organising folder. It is not one: an organising folder may sit only where
   no object's folder is above it, and `tcw validate` reports a folder with
   no state file inside a capability's folder as an error ("is not a child
   object"). So that form is refused instead. Review round 1 extended the
   refusal to the long form (`billing/invoices/extra/bulk`), which made the
   same folder, and allowed a folder between that is already a capability.
5. **A parent that is not this project's own** (inherited, or another
   project's item) cannot hold the folder. The command behaves as `--flat`
   and says so in one line, as `tcw work new --nest` does today for a parent
   in another project. For a capability, the path is then read as given, so
   it must name its namespace folder. *Added at implement:* an inherited
   capability holds the folder when this project has its own override at
   its path, since that override is a capability of this project's own and
   its folder is this project's; this matches `tcw taxonomy add`, which
   already nests under an inherited term this project overrides. The
   `not nested:` line is said only when the folder is not inside the
   parent's path, and only once every refusal has passed.
6. **The web app's create form** loses the "nest" option and gains the
   matching "keep it at the top" option, unticked by default. Principle 4
   holds: every control has a matching flag.
7. **Unchanged:** `tcw migrate` moves no folder, so migrated 3.x children
   stay where they are; `move`, `rename`, `rm` and `set --parent` are
   untouched (`set --parent` records the field only and never moves a
   folder; `move` is how an object is put somewhere else); `tcw validate`'s
   warnings stay as they are (an object nested in a folder that is not its
   parent's; a flat child is no finding).

## The litmus test

Placing a folder is the deployment layer (TCW-99, "What any store must
support"): a store that is not a folder of files implements `--parent` and
ignores placement, and `--flat` is then a no-op there. The model's operation,
recording a parent, is unchanged.
