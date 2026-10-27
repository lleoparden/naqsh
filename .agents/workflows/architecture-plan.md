# Architecture plan workflow

Use for anything that adds a new stage, a new persistent shape, or a new paid call
per page. Produces a plan in `docs/plan.md` or a sub-issue; no product code until
the owner approves.

1. **Restate the requirement** in one paragraph, including who benefits.
2. **Name the cheapest version that proves it** — the smallest experiment that
   produces evidence, not the finished feature.
3. **List the boundaries** it crosses: frontend/backend, model API, cost, export
   format, stored data.
4. **Decide the gate** — the measurable result that says go, and the fallback if it
   fails (a different model, a local algorithm, or cutting the feature).
5. **Write the task list** with the file for each task and the check that proves it.
6. **State the risks and the rollback.**
7. **Stop for approval** before writing code for any phase after Phase 1.
