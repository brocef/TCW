# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Initialize one component at a time

Each component group now has its own `init`, so you can set up just one tree
without naming it as an argument:

```
tcw taxonomy init
tcw capabilities init
tcw work init
```

Each does exactly what `tcw init <component>` does. `tcw init` on its own still
sets up all three at once.
