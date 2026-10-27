# Naqsh program index

Mirrors the epic/sub-issue habit re-created for this repo: one epic per phase,
sub-issues only when a phase starts. The phase list, gates, and fallbacks live in
[`docs/plan.md`](../../docs/plan.md); this file is the issue-side index and links
the issue bodies kept in this folder.

## Phases

| Phase | Issue | Status |
| --- | --- | --- |
| 1 — Setup and API smoke tests | #1 (epic body: `phase-1-setup.md`) | in progress |
| 2 — Vertical slice | not created yet | blocked on Phase 1 exit + plan approval |
| 3 — RTL typesetting and fitting | not created yet | — |
| 4 — Clean plate quality | not created yet | — |
| 5 — Region strategy | not created yet | — |
| 6 — Layer editor and export | not created yet | — |
| 7 — Impact measurement and backup video | not created yet | — |
| 8 — Polish and second page type | not created yet | — |
| 9 — Freeze and final video | not created yet | — |
| 10 — Submission | not created yet | — |

## Rules

- A phase starts only after its plan is approved (from Phase 2 onward).
- A slice is not `agent-ready` until its sub-issue has the problem, scope,
  acceptance criteria, gate evidence, fallback, and no open decision.
- Every commit and PR references its issue.
