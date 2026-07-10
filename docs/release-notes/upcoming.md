# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Share capabilities across projects

If two projects offer the same things to users — say a web app and a mobile app
that talk to the same backend — you no longer have to describe those capabilities
twice and hope they stay in sync. One project can now **inherit** another's
capabilities:

```sh
tcw capabilities extends shared ../web-frontend
```

The inherited capabilities show up in your project's list, marked with where they
came from. You can't delete an inherited capability, but you can **tailor it** to
your project:

- mark it a different status — e.g. `Missing` if you haven't built it yet, or
  `Omitted` if your project deliberately doesn't have it;
- add project-specific detail to its description — for example, a mobile app can
  append "…or take a photo with the device camera" to a shared "upload an image"
  capability — while still sharing the same underlying story.

## Capabilities are now folders addressed by path

Each capability lives in its own folder and is addressed by a simple path like
`billing/invoices` (no more `#heading` anchors). Every capability gets a stable
id that stays put even if you reword it. The `Subject` link to your taxonomy can
now point at more than one term.

Existing capabilities are migrated automatically.

## Address a work item by its status path

Work commands now accept a status-qualified path (e.g. `active/my-item`) in
addition to the bare item name, so you can paste the path a listing shows.
