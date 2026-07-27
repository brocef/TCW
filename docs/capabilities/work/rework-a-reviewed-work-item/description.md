As a user, I run `tcw work rework <slug>` to move an item from review back into active after verification rejected the work. This is the only reverse transition in the state machine.
The tool refuses while `refined-outcome.md` is still present, because that document asserts the work was verified and accepted. I delete it myself and record what remains in `rework.md`; TCW never deletes it for me.
