"""`tcw migrate`: move a TCW 3.x project to TCW 4 (TCW-116).

The command plans every change in memory first, refuses before writing
anything when a blocker is found, then writes the plan in phases, keeping a
progress record so a run that stopped can be finished by running it again.
`cli` registers the command; the other modules are the plan's parts.
"""
