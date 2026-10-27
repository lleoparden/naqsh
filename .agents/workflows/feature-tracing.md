# Feature tracing before changing an established area

Run this before editing a pipeline stage, the model client, or the editor state
model. It produces a short written trace, not code.

1. **User flow** — the clicks and uploads that reach this area, and what the user
   sees when it works and when it fails.
2. **Data shape** — the exact objects crossing the boundary (Python dict / TS type),
   including units: pixels versus page units, source versus display coordinates.
3. **Model calls** — which Meta model, which request fields, what the response
   contains, what it costs, and what happens when it returns nothing.
4. **Cost and latency** — the paid calls this path adds per page, and the measured
   time it adds (not estimated).
5. **Failure modes** — empty masks, zero matches, a 400 from an unknown field, a
   safety refusal, a timeout. What the user sees, what the logs say.
6. **Rollback** — what is reverted if this change is wrong, and whether stored
   data becomes unreadable.

Write the trace in the sub-issue or the PR description. If any of the six cannot be
answered, the change is not ready.
