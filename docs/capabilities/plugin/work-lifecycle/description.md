As a user, I can ask the TCW plugin to plan a request into a work item or drive an existing work item through the remaining SDLC stages. The agent records the lifecycle artifacts in the work item folder and stops for explicit verification before closeout.

For complex work, the agent can keep `plan.md` concise while declaring bounded
stage documents. It reads the manifest first and selectively loads the relevant
stage, including its pre- and post-checks. Dependencies communicate ordering and
parallelism without becoming formal lifecycle state.
